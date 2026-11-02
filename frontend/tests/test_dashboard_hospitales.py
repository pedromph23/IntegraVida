"""Tests de F3.e.1 + F5.b — módulo Hospitales del panel.

F3.e.1: list, detail, cambiar estado.
F5.b: create, update, inactivar (soft: NO_OPERATIVO), reactivar.

Reglas de permisos: ver app/usuarios/permisos.py (mismo mapa que refugios
pero con modulo="hospitales").
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.hospitales.models import Hospital
from apps.organizaciones.models import Organizacion, Membresia

User = get_user_model()


# ── Factories ────────────────────────────────────────────────────────
def _mk_org(codigo=None):
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipos = [c[0] for c in tipo_f.choices] if tipo_f.choices else []
    estados = [c[0] for c in estado_f.choices] if estado_f.choices else []
    tipo = "OTRO" if "OTRO" in tipos else (tipos[0] if tipos else "OTRO")
    estado = "ACTIVA" if "ACTIVA" in estados else (estados[0] if estados else "ACTIVA")
    code = codigo or f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=f"Org {code}", codigo=code, tipo=tipo, estado=estado,
    )


def _mk_hospital(org, codigo=None, estado="DISPONIBLE", **kw):
    code = codigo or f"hosp-{uuid.uuid4().hex[:8]}"
    return Hospital.objects.create(
        codigo=code, nombre=f"Hospital {code}",
        tipo="HOSPITAL", nivel="NIVEL_I",
        organizacion=org, direccion="Avenida test 456",
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
    return Membresia.objects.create(
        usuario=user, organizacion=org,
        rol=rol, estado=estado,
    )


# ── Lista ────────────────────────────────────────────────────────────
class HospitalesListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("listuser")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")

    def test_list_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:hospitales_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_list_renders_empty(self):
        r = self.client.get(reverse("dashboard:hospitales_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Hospitales")

    def test_list_shows_hospitales(self):
        _mk_hospital(self.org, codigo="hosp-abc")
        r = self.client.get(reverse("dashboard:hospitales_list"))
        self.assertContains(r, "hosp-abc")

    def test_list_filters_by_estado(self):
        _mk_hospital(self.org, codigo="hosp-disp", estado="DISPONIBLE")
        _mk_hospital(self.org, codigo="hosp-colap", estado="COLAPSADO")
        r = self.client.get(
            reverse("dashboard:hospitales_list") + "?estado_operativo=COLAPSADO"
        )
        self.assertContains(r, "hosp-colap")
        self.assertNotContains(r, "hosp-disp")

    def test_list_query_count_bounded(self):
        for i in range(3):
            _mk_hospital(self.org, codigo=f"hosp-{i}")
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:hospitales_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 16,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )

    def test_list_no_expone_otras_orgs(self):
        """F5.b: scoping impide ver hospitales de otras orgs."""
        otra_org = _mk_org()
        _mk_hospital(self.org, codigo="hosp-mio")
        _mk_hospital(otra_org, codigo="hosp-ajeno")
        r = self.client.get(reverse("dashboard:hospitales_list"))
        self.assertContains(r, "hosp-mio")
        self.assertNotContains(r, "hosp-ajeno")


# ── Detalle ──────────────────────────────────────────────────────────
class HospitalDetailTests(TestCase):
    def setUp(self):
        self.user = _mk_user("detailuser")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")
        self.hospital = _mk_hospital(self.org, codigo="hosp-detalle")

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:hospital_detail", args=["hosp-detalle"])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "hosp-detalle")

    def test_detail_404_unknown(self):
        r = self.client.get(
            reverse("dashboard:hospital_detail", args=["nope"])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_404_otra_org(self):
        otra_org = _mk_org()
        _mk_hospital(otra_org, codigo="hosp-ajeno")
        r = self.client.get(
            reverse("dashboard:hospital_detail", args=["hosp-ajeno"])
        )
        self.assertEqual(r.status_code, 404)


# ── Cambiar estado ───────────────────────────────────────────────────
class CambiarEstadoHospitalTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.hospital = _mk_hospital(
            self.org, codigo="hosp-cambiar", estado="DISPONIBLE",
        )
        self.url = reverse(
            "dashboard:hospital_cambiar_estado", args=["hosp-cambiar"],
        )

    def test_requires_auth(self):
        r = self.client.post(self.url, {"estado_operativo": "SATURADO"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_consulta_forbidden(self):
        u = _mk_user("cons")
        _mk_membresia(u, self.org, rol="CONSULTA")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "SATURADO"})
        self.assertEqual(r.status_code, 403)

    def test_operador_can_change(self):
        u = _mk_user("op2")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "SATURADO"})
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.estado_operativo, "SATURADO")

    def test_invalid_estado_no_change(self):
        u = _mk_user("op3")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "INVENTADO"})
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.estado_operativo, "DISPONIBLE")

    def test_no_membresia_404(self):
        u = _mk_user("sin_org")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "SATURADO"})
        self.assertEqual(r.status_code, 404)


# ── Crear ────────────────────────────────────────────────────────────
class CrearHospitalTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.url_form = reverse("dashboard:hospital_create_form")
        self.url_submit = reverse("dashboard:hospital_create_submit")

    def _form_data(self, **overrides):
        data = {
            "organizacion": self.org.pk,
            "codigo": f"hosp-nuevo-{uuid.uuid4().hex[:6]}",
            "nombre": "Hospital nuevo",
            "tipo": "HOSPITAL",
            "nivel": "NIVEL_I",
            "direccion": "Av. nueva 1",
            "referencia_lugar": "",
            "telefono_publico": "",
            "correo_publico": "",
            "notas_internas": "",
        }
        data.update(overrides)
        return data

    def test_coordinador_puede_crear(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)

        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 200)

        data = self._form_data()
        r = self.client.post(self.url_submit, data)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Hospital.objects.filter(codigo=data["codigo"]).exists())

    def test_operador_no_puede_crear(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 302)


# ── Editar ───────────────────────────────────────────────────────────
class EditarHospitalTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.hospital = _mk_hospital(self.org, codigo="hosp-edit")

    def test_coordinador_puede_editar(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:hospital_update_form", args=["hosp-edit"])
        )
        self.assertEqual(r.status_code, 200)

    def test_operador_no_puede_editar(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:hospital_update_form", args=["hosp-edit"])
        )
        self.assertEqual(r.status_code, 403)

    def test_update_persiste_cambios(self):
        u = _mk_user("coord2")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        data = {
            "organizacion": self.org.pk,
            "codigo": self.hospital.codigo,
            "nombre": "Nombre actualizado",
            "tipo": self.hospital.tipo,
            "nivel": self.hospital.nivel,
            "direccion": "Nueva dirección 456",
            "referencia_lugar": "",
            "telefono_publico": "",
            "correo_publico": "",
            "notas_internas": "",
        }
        r = self.client.post(
            reverse("dashboard:hospital_update_submit", args=["hosp-edit"]),
            data,
        )
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.nombre, "Nombre actualizado")


# ── Inactivar (soft: NO_OPERATIVO) + Reactivar ──────────────────────
class InactivarReactivarHospitalTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.hospital = _mk_hospital(
            self.org, codigo="hosp-del", estado="DISPONIBLE",
        )

    def test_admin_org_puede_inactivar(self):
        u = _mk_user("admin_org")
        _mk_membresia(u, self.org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(u)
        r = self.client.post(
            reverse("dashboard:hospital_inactivar_submit", args=["hosp-del"])
        )
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(
            self.hospital.estado_operativo,
            Hospital.EstadoOperativo.NO_OPERATIVO,
        )

    def test_coordinador_no_puede_inactivar(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        r = self.client.post(
            reverse("dashboard:hospital_inactivar_submit", args=["hosp-del"])
        )
        self.assertEqual(r.status_code, 403)

    def test_reactivar_cambia_a_disponible(self):
        u = _mk_user("admin_org")
        _mk_membresia(u, self.org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(u)
        self.hospital.estado_operativo = "NO_OPERATIVO"
        self.hospital.save(update_fields=["estado_operativo"])

        r = self.client.post(
            reverse("dashboard:hospital_reactivar", args=["hosp-del"])
        )
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(
            self.hospital.estado_operativo,
            Hospital.EstadoOperativo.DISPONIBLE,
        )
