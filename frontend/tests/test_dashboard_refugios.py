"""Tests de F3.c + F5.a — módulo Refugios del panel.

F3.c: list, detail, cambiar estado.
F5.a: create, update, inactivar (soft delete) con permisos granulares
      y scoping por organización.

Reglas de permisos (Membresia.rol):
- ADMIN_ORGANIZACION: ver, crear, editar, eliminar, cambiar estado.
- COORDINADOR:       ver, crear, editar, cambiar estado.
- OPERADOR:          ver, cambiar estado.
- SANITARIO/LOGISTICA/CONSULTA: ver solo.

Cambio respecto a F3.c: `_base_queryset(user)` filtra por las
Membresias ACTIVAS del usuario. Los tests ahora crean Membresia
explícita. F3.c tenía un bug: cualquier user logueado veía TODOS
los refugios.
"""
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.organizaciones.models import Organizacion, Membresia
from apps.refugios.models import Refugio, Necesidad, RegistroOcupacion

User = get_user_model()


# ── Factories ─────────────────────────────────────────────────────────
def _mk_org(codigo=None):
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipos = [c[0] for c in tipo_f.choices] if tipo_f.choices else []
    estados = [c[0] for c in estado_f.choices] if estado_f.choices else []
    tipo = "OTRO" if "OTRO" in tipos else (tipos[0] if tipos else "OTRO")
    # CRÍTICO: priorizar ACTIVA — orgs_donde_puede filtra por estado ACTIVA
    estado = "ACTIVA" if "ACTIVA" in estados else (estados[0] if estados else "ACTIVA")
    code = codigo or f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=f"Org {code}", codigo=code, tipo=tipo, estado=estado,
    )


def _mk_refugio(org, codigo=None, estado="ACTIVO", **kw):
    code = codigo or f"ref-{uuid.uuid4().hex[:8]}"
    return Refugio.objects.create(
        codigo=code, nombre=f"Refugio {code}", tipo="REFUGIO",
        organizacion=org, direccion="Calle test 123",
        capacidad_total=100, ocupacion_actual=10,
        estado_operativo=estado, **kw,
    )


def _mk_user(username, groups=(), is_staff=False):
    u = User.objects.create_user(username=username, password="x")
    if is_staff:
        u.is_staff = True
        u.save()
    for n in groups:
        g, _ = Group.objects.get_or_create(name=n)
        u.groups.add(g)
    return u


def _mk_membresia(user, org, rol="COORDINADOR", estado="ACTIVA"):
    """Crea Membresia — requerida por _base_queryset (F5.a)."""
    return Membresia.objects.create(
        usuario=user, organizacion=org,
        rol=rol, estado=estado,
    )


# ── Tests de lista ────────────────────────────────────────────────────
class RefugiosListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("listuser")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")

    def test_list_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:refugios_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_list_renders_empty(self):
        r = self.client.get(reverse("dashboard:refugios_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Refugios")

    def test_list_shows_refugios(self):
        _mk_refugio(self.org, codigo="ref-abc")
        r = self.client.get(reverse("dashboard:refugios_list"))
        self.assertContains(r, "ref-abc")

    def test_list_filters_by_estado(self):
        _mk_refugio(self.org, codigo="ref-activo", estado="ACTIVO")
        _mk_refugio(self.org, codigo="ref-cerrado", estado="CERRADO")
        r = self.client.get(
            reverse("dashboard:refugios_list") + "?estado_operativo=CERRADO"
        )
        self.assertContains(r, "ref-cerrado")
        self.assertNotContains(r, "ref-activo")

    def test_list_query_count_bounded(self):
        for _ in range(3):
            _mk_refugio(self.org)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:refugios_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 16,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )

    def test_list_no_expone_otras_orgs(self):
        """F5.a: el scoping impide ver refugios de otras orgs."""
        otra_org = _mk_org()
        _mk_refugio(self.org, codigo="ref-mia")
        _mk_refugio(otra_org, codigo="ref-ajena")
        r = self.client.get(reverse("dashboard:refugios_list"))
        self.assertContains(r, "ref-mia")
        self.assertNotContains(r, "ref-ajena")


# ── Tests de detalle ──────────────────────────────────────────────────
class RefugioDetailTests(TestCase):
    def setUp(self):
        self.user = _mk_user("detailuser")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")
        self.refugio = _mk_refugio(self.org, codigo="ref-detalle")

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:refugio_detail", args=["ref-detalle"])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "ref-detalle")

    def test_detail_404_unknown(self):
        r = self.client.get(
            reverse("dashboard:refugio_detail", args=["nope"])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_necesidades(self):
        Necesidad.objects.create(
            refugio=self.refugio, categoria="AGUA",
            descripcion="Agua potable urgente",
            prioridad=1, cubierta=False,
        )
        r = self.client.get(
            reverse("dashboard:refugio_detail", args=["ref-detalle"])
        )
        self.assertContains(r, "Agua potable urgente")

    def test_detail_shows_registros(self):
        RegistroOcupacion.objects.create(
            refugio=self.refugio, cantidad_anterior=10,
            cantidad_nueva=15, diferencia=5, fuente="MANUAL",
        )
        r = self.client.get(
            reverse("dashboard:refugio_detail", args=["ref-detalle"])
        )
        # El template usa get_fuente_display → "Manual", no "MANUAL"
        body = r.content.decode()
        self.assertTrue(
            "Manual" in body or "MANUAL" in body,
            "Ni 'Manual' ni 'MANUAL' aparecen en el detalle",
        )

    def test_detail_404_refugio_de_otra_org(self):
        """F5.a: no se puede ver un refugio de otra organización."""
        otra_org = _mk_org()
        _mk_refugio(otra_org, codigo="ref-ajena")
        r = self.client.get(
            reverse("dashboard:refugio_detail", args=["ref-ajena"])
        )
        self.assertEqual(r.status_code, 404)


# ── Tests de cambiar estado ───────────────────────────────────────────
class CambiarEstadoTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.refugio = _mk_refugio(
            self.org, codigo="ref-cambiar", estado="ACTIVO"
        )
        self.url = reverse(
            "dashboard:refugio_cambiar_estado", args=["ref-cambiar"]
        )

    def test_requires_auth(self):
        r = self.client.post(self.url, {"estado_operativo": "CERRADO"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_consulta_forbidden(self):
        """Usuario CONSULTA (solo view) no puede cambiar estado."""
        u = _mk_user("plain")
        _mk_membresia(u, self.org, rol="CONSULTA")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "CERRADO"})
        self.assertEqual(r.status_code, 403)

    def test_operador_can_change(self):
        u = _mk_user("op2")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "CERRADO"})
        self.assertEqual(r.status_code, 302)
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.estado_operativo, "CERRADO")

    def test_invalid_estado_no_change(self):
        u = _mk_user("op3")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "INVENTADO"})
        self.assertEqual(r.status_code, 302)
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.estado_operativo, "ACTIVO")

    def test_no_membresia_404(self):
        """Sin Membresia → no ve el refugio → 404 (no 403, no 302)."""
        u = _mk_user("sin_org")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "CERRADO"})
        self.assertEqual(r.status_code, 404)


# ── Tests de crear (F5.a) ────────────────────────────────────────────
class CrearRefugioTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.url_form = reverse("dashboard:refugio_create_form")
        self.url_submit = reverse("dashboard:refugio_create_submit")

    def _form_data(self, **overrides):
        data = {
            "organizacion": self.org.pk,
            "codigo": f"nuevo-{uuid.uuid4().hex[:6]}",
            "nombre": "Refugio nuevo",
            "tipo": "REFUGIO",
            "direccion": "Av. nueva 1",
            "capacidad_total": "100",
            "telefono_publico": "",
            "correo_publico": "",
        }
        data.update(overrides)
        return data

    def test_coordinador_puede_crear(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)

        # GET form
        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 200)

        # POST submit
        data = self._form_data()
        r = self.client.post(self.url_submit, data)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Refugio.objects.filter(codigo=data["codigo"]).exists())

    def test_operador_no_puede_crear(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(self.url_form)
        # permiso_requerido redirige con mensaje flash (redirect_to list)
        self.assertEqual(r.status_code, 302)
        self.assertIn("refugios", r.url.lower())

    def test_consulta_no_puede_crear(self):
        u = _mk_user("cons")
        _mk_membresia(u, self.org, rol="CONSULTA")
        self.client.force_login(u)
        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 302)


# ── Tests de editar (F5.a) ──────────────────────────────────────────
class EditarRefugioTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.refugio = _mk_refugio(self.org, codigo="ref-edit")

    def test_coordinador_puede_editar(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:refugio_update_form", args=["ref-edit"])
        )
        self.assertEqual(r.status_code, 200)

    def test_operador_no_puede_editar(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:refugio_update_form", args=["ref-edit"])
        )
        self.assertEqual(r.status_code, 403)

    def test_update_persiste_cambios(self):
        u = _mk_user("coord2")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        data = {
            "organizacion": self.org.pk,
            "codigo": self.refugio.codigo,
            "nombre": "Nombre actualizado",
            "tipo": self.refugio.tipo,
            "direccion": "Nueva dirección 456",
            "capacidad_total": "200",
            "telefono_publico": "",
            "correo_publico": "",
        }
        r = self.client.post(
            reverse("dashboard:refugio_update_submit", args=["ref-edit"]),
            data,
        )
        self.assertEqual(r.status_code, 302)
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.nombre, "Nombre actualizado")
        self.assertEqual(self.refugio.capacidad_total, 200)


# ── Tests de inactivar (F5.a — soft delete) ─────────────────────────
class InactivarRefugioTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.refugio = _mk_refugio(self.org, codigo="ref-del", estado="ACTIVO")

    def test_admin_org_puede_inactivar(self):
        u = _mk_user("admin_org")
        _mk_membresia(u, self.org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(u)
        r = self.client.post(
            reverse("dashboard:refugio_inactivar_submit", args=["ref-del"])
        )
        self.assertEqual(r.status_code, 302)
        self.refugio.refresh_from_db()
        self.assertEqual(
            self.refugio.estado_operativo,
            Refugio.EstadoOperativo.INACTIVO,
        )

    def test_coordinador_no_puede_inactivar(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        r = self.client.post(
            reverse("dashboard:refugio_inactivar_submit", args=["ref-del"])
        )
        self.assertEqual(r.status_code, 403)
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.estado_operativo, "ACTIVO")
