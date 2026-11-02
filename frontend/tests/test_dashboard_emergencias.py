"""Tests de F3.d + F5.c — módulo Emergencias del panel.

F3.d: list, detail, cambiar estado (transiciones whitelist).
F5.c: create, update. NO delete (evento que ocurrió).
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, Client
from django.urls import reverse

from apps.emergencias.models import Emergencia, ReporteEmergencia
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


def _mk_emergencia(org, estado="RECIBIDA", **kw):
    gravedad_f = Emergencia._meta.get_field("gravedad")
    gravedad = gravedad_f.choices[0][0] if gravedad_f.choices else 1
    return Emergencia.objects.create(
        titulo=kw.pop("titulo", "Emergencia test"),
        descripcion=kw.pop("descripcion", "Descripción de prueba"),
        categoria=kw.pop("categoria", "OTRA"),
        gravedad=gravedad,
        estado=estado,
        ubicacion_texto=kw.pop("ubicacion_texto", "Ubicación test"),
        organizacion=org,
        **kw,
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
        usuario=user, organizacion=org, rol=rol, estado=estado,
    )


# ── Lista ────────────────────────────────────────────────────────────
class EmergenciasListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("emlist")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")

    def test_list_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:emergencias_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_list_renders_empty(self):
        r = self.client.get(reverse("dashboard:emergencias_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Emergencias")

    def test_list_shows_emergencias(self):
        _mk_emergencia(self.org, titulo="Inundación Petare")
        r = self.client.get(reverse("dashboard:emergencias_list"))
        self.assertContains(r, "Inundación Petare")

    def test_list_filters_by_estado(self):
        _mk_emergencia(self.org, titulo="Recibida X", estado="RECIBIDA")
        _mk_emergencia(self.org, titulo="Confirmada Y", estado="CONFIRMADA")
        r = self.client.get(
            reverse("dashboard:emergencias_list") + "?estado=CONFIRMADA"
        )
        self.assertContains(r, "Confirmada Y")
        self.assertNotContains(r, "Recibida X")

    def test_list_no_expone_otras_orgs(self):
        otra_org = _mk_org()
        _mk_emergencia(self.org, titulo="Mi emergencia")
        _mk_emergencia(otra_org, titulo="Ajena emergencia")
        r = self.client.get(reverse("dashboard:emergencias_list"))
        self.assertContains(r, "Mi emergencia")
        self.assertNotContains(r, "Ajena emergencia")


# ── Detalle ──────────────────────────────────────────────────────────
class EmergenciaDetailTests(TestCase):
    def setUp(self):
        self.user = _mk_user("emdetail")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")
        self.emergencia = _mk_emergencia(self.org, titulo="Detalle uno")

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:emergencia_detail", args=[self.emergencia.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Detalle uno")

    def test_detail_404_unknown(self):
        r = self.client.get(
            reverse("dashboard:emergencia_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_404_otra_org(self):
        otra_org = _mk_org()
        e = _mk_emergencia(otra_org, titulo="Ajena")
        r = self.client.get(
            reverse("dashboard:emergencia_detail", args=[e.id])
        )
        self.assertEqual(r.status_code, 404)


# ── Cambiar estado ───────────────────────────────────────────────────
class CambiarEstadoTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.emergencia = _mk_emergencia(self.org, estado="RECIBIDA")
        self.url = reverse(
            "dashboard:emergencia_cambiar_estado", args=[self.emergencia.id],
        )

    def test_requires_auth(self):
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
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
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
        self.assertEqual(r.status_code, 403)

    def test_operador_valid_transition(self):
        u = _mk_user("op2")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
        self.assertEqual(r.status_code, 302)
        self.emergencia.refresh_from_db()
        self.assertEqual(self.emergencia.estado, "EN_VERIFICACION")

    def test_operador_invalid_transition_rejected(self):
        u = _mk_user("op3")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "RESUELTA"})
        self.assertEqual(r.status_code, 302)
        self.emergencia.refresh_from_db()
        self.assertEqual(self.emergencia.estado, "RECIBIDA")

    def test_sanitario_puede_cambiar_estado(self):
        u = _mk_user("san")
        _mk_membresia(u, self.org, rol="SANITARIO")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
        self.assertEqual(r.status_code, 302)


# ── Crear ────────────────────────────────────────────────────────────
class CrearEmergenciaTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.url_form = reverse("dashboard:emergencia_create_form")
        self.url_submit = reverse("dashboard:emergencia_create_submit")

    def _form_data(self, **overrides):
        gravedad_f = Emergencia._meta.get_field("gravedad")
        gravedad = gravedad_f.choices[0][0] if gravedad_f.choices else 1
        data = {
            "organizacion": self.org.pk,
            "titulo": "Emergencia nueva",
            "descripcion": "Descripción de prueba",
            "categoria": "OTRA",
            "gravedad": str(gravedad),
            "ubicacion_texto": "Av. Test 123",
            "referencia_lugar": "",
        }
        data.update(overrides)
        return data

    def test_coordinador_puede_crear(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)

        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 200)

        r = self.client.post(self.url_submit, self._form_data())
        self.assertEqual(r.status_code, 302)
        e = Emergencia.objects.filter(titulo="Emergencia nueva").first()
        self.assertIsNotNone(e)
        self.assertEqual(e.estado, "RECIBIDA")
        self.assertEqual(e.reportada_por, u)

    def test_operador_no_puede_crear(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 302)


# ── Editar ───────────────────────────────────────────────────────────
class EditarEmergenciaTests(TestCase):
    def setUp(self):
        self.org = _mk_org()
        self.emergencia = _mk_emergencia(self.org, titulo="Original")

    def test_coordinador_puede_editar(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:emergencia_update_form", args=[self.emergencia.id])
        )
        self.assertEqual(r.status_code, 200)

    def test_operador_no_puede_editar(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:emergencia_update_form", args=[self.emergencia.id])
        )
        self.assertEqual(r.status_code, 403)

    def test_update_persiste_cambios(self):
        u = _mk_user("coord2")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        gravedad_f = Emergencia._meta.get_field("gravedad")
        gravedad = gravedad_f.choices[0][0] if gravedad_f.choices else 1
        data = {
            "organizacion": self.org.pk,
            "titulo": "Título actualizado",
            "descripcion": self.emergencia.descripcion,
            "categoria": self.emergencia.categoria,
            "gravedad": str(gravedad),
            "ubicacion_texto": "Nueva ubicación",
            "referencia_lugar": "",
        }
        r = self.client.post(
            reverse("dashboard:emergencia_update_submit", args=[self.emergencia.id]),
            data,
        )
        self.assertEqual(r.status_code, 302)
        self.emergencia.refresh_from_db()
        self.assertEqual(self.emergencia.titulo, "Título actualizado")
