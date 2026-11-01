"""Tests de F3.d — módulo Emergencias del panel."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.emergencias.models import Emergencia, ReporteEmergencia

User = get_user_model()


def _first_gravedad():
    choices = Emergencia._meta.get_field("gravedad").choices
    return choices[0][0] if choices else 1


def _mk_emergencia(estado="RECIBIDA", gravedad=None, **kw):
    return Emergencia.objects.create(
        titulo=kw.pop("titulo", "Emergencia test"),
        descripcion=kw.pop("descripcion", "Descripción de prueba"),
        categoria=kw.pop("categoria", "OTRA"),
        gravedad=gravedad if gravedad is not None else _first_gravedad(),
        estado=estado,
        ubicacion_texto=kw.pop("ubicacion_texto", "Ubicación test"),
        **kw,
    )


def _mk_reporte(emergencia, **kw):
    return ReporteEmergencia.objects.create(
        emergencia=emergencia,
        categoria=kw.pop("categoria", "OTRA"),
        descripcion=kw.pop("descripcion", "Reporte de prueba"),
        ubicacion_texto=kw.pop("ubicacion_texto", "Ubicación reporte"),
        canal=kw.pop("canal", "WEB"),
        estado_revision=kw.pop("estado_revision", "PENDIENTE"),
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


class EmergenciasListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("emlist")
        self.client.force_login(self.user)

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
        _mk_emergencia(titulo="Inundación Petare")
        r = self.client.get(reverse("dashboard:emergencias_list"))
        self.assertContains(r, "Inundación Petare")

    def test_list_filters_by_estado(self):
        _mk_emergencia(titulo="Recibida X", estado="RECIBIDA")
        _mk_emergencia(titulo="Confirmada Y", estado="CONFIRMADA")
        r = self.client.get(
            reverse("dashboard:emergencias_list") + "?estado=CONFIRMADA"
        )
        self.assertContains(r, "Confirmada Y")
        self.assertNotContains(r, "Recibida X")

    def test_list_query_count_bounded(self):
        for i in range(3):
            _mk_emergencia(titulo=f"E{i}")
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:emergencias_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 14,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class EmergenciaDetailTests(TestCase):
    def setUp(self):
        self.user = _mk_user("emdetail")
        self.client.force_login(self.user)

    def test_detail_renders(self):
        e = _mk_emergencia(titulo="Detalle uno")
        r = self.client.get(
            reverse("dashboard:emergencia_detail", args=[e.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Detalle uno")

    def test_detail_404_unknown(self):
        import uuid
        r = self.client.get(
            reverse("dashboard:emergencia_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_reportes(self):
        e = _mk_emergencia()
        _mk_reporte(e, descripcion="Reporte vinculado X")
        r = self.client.get(
            reverse("dashboard:emergencia_detail", args=[e.id])
        )
        self.assertContains(r, "Reporte vinculado X")


class CambiarEstadoEmergenciaTests(TestCase):
    def setUp(self):
        self.emergencia = _mk_emergencia(estado="RECIBIDA")
        self.url = reverse(
            "dashboard:emergencia_cambiar_estado",
            args=[self.emergencia.id],
        )

    def test_requires_auth(self):
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        u = _mk_user("op", ["OPERADOR_EMERGENCIA"])
        self.client.force_login(u)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_plain_user_forbidden(self):
        u = _mk_user("plain")
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
        self.assertEqual(r.status_code, 403)

    def test_operador_valid_transition(self):
        u = _mk_user("op2", ["OPERADOR_EMERGENCIA"])
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "EN_VERIFICACION"})
        self.assertEqual(r.status_code, 302)
        self.emergencia.refresh_from_db()
        self.assertEqual(self.emergencia.estado, "EN_VERIFICACION")

    def test_operador_invalid_transition_rejected(self):
        # RECIBIDA → RESUELTA no está en whitelist
        u = _mk_user("op3", ["OPERADOR_EMERGENCIA"])
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "RESUELTA"})
        self.assertEqual(r.status_code, 302)
        self.emergencia.refresh_from_db()
        self.assertEqual(self.emergencia.estado, "RECIBIDA")

    def test_staff_can_force_transition(self):
        u = _mk_user("staff", is_staff=True)
        self.client.force_login(u)
        r = self.client.post(self.url, {"estado": "RESUELTA"})
        self.assertEqual(r.status_code, 302)
        self.emergencia.refresh_from_db()
        self.assertEqual(self.emergencia.estado, "RESUELTA")
