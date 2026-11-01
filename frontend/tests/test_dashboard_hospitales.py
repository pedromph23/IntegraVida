"""Tests de F3.e.1 — módulo Hospitales del panel."""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.hospitales.models import Hospital
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


class HospitalesListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("hlist")
        self.client.force_login(self.user)
        self.org = _mk_org()

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
            len(ctx.captured_queries), 14,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class HospitalDetailTests(TestCase):
    def setUp(self):
        self.user = _mk_user("hdetail")
        self.client.force_login(self.user)
        self.org = _mk_org()
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
        u = _mk_user("op", ["OPERADOR_HOSPITAL"])
        self.client.force_login(u)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_plain_user_forbidden(self):
        u = _mk_user("plain")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "SATURADO"})
        self.assertEqual(r.status_code, 403)

    def test_operador_valid_transition(self):
        u = _mk_user("op2", ["OPERADOR_HOSPITAL"])
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "SATURADO"})
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.estado_operativo, "SATURADO")

    def test_operador_invalid_transition_rejected(self):
        # DISPONIBLE → no tiene NINGUNA transición hacia DISPONIBLE, pero
        # desde DISPONIBLE sí puede ir a NO_OPERATIVO. Probamos desde
        # COLAPSADO (seteado aparte) → DISPONIBLE es válido (COLAPSADO → SATURADO).
        # Para forzar una inválida: NO_OPERATIVO → COLAPSADO no está permitida
        self.hospital.estado_operativo = "NO_OPERATIVO"
        self.hospital.save(update_fields=["estado_operativo"])
        u = _mk_user("op3", ["OPERADOR_HOSPITAL"])
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "COLAPSADO"})
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.estado_operativo, "NO_OPERATIVO")

    def test_staff_can_force_transition(self):
        u = _mk_user("staff", is_staff=True)
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado_operativo": "COLAPSADO"})
        self.assertEqual(r.status_code, 302)
        self.hospital.refresh_from_db()
        self.assertEqual(self.hospital.estado_operativo, "COLAPSADO")
