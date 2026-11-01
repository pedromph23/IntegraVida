"""Tests de F3.c — módulo Refugios del panel."""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.refugios.models import Refugio, Necesidad, RegistroOcupacion
from apps.organizaciones.models import Organizacion

User = get_user_model()


def _mk_org(codigo=None):
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipo = tipo_f.choices[0][0] if tipo_f.choices else "OTRO"
    estado = estado_f.choices[0][0] if estado_f.choices else "ACTIVA"
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


class RefugiosListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("listuser")
        self.client.force_login(self.user)
        self.org = _mk_org()

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
            len(ctx.captured_queries), 12,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class RefugioDetailTests(TestCase):
    def setUp(self):
        self.user = _mk_user("detailuser")
        self.client.force_login(self.user)
        self.org = _mk_org()
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
        body = r.content.decode()
        # El template usa get_fuente_display() → "Manual", no "MANUAL"
        self.assertTrue(
            "Manual" in body or "MANUAL" in body,
            "Ni 'Manual' ni 'MANUAL' aparecen en el detalle",
        )


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
        u = _mk_user("op", ["OPERADOR_REFUGIO"])
        self.client.force_login(u)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_plain_user_forbidden(self):
        u = _mk_user("plain")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "CERRADO"})
        self.assertEqual(r.status_code, 403)

    def test_operador_can_change(self):
        u = _mk_user("op", ["OPERADOR_REFUGIO"])
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "CERRADO"})
        self.assertEqual(r.status_code, 302)
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.estado_operativo, "CERRADO")

    def test_invalid_estado_no_change(self):
        u = _mk_user("op2", ["OPERADOR_REFUGIO"])
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "INVENTADO"})
        self.assertEqual(r.status_code, 302)
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.estado_operativo, "ACTIVO")
