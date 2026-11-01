"""Tests de F3.f.1 — módulo Triaje del panel (solo lectura).

La creación de triajes NO se testea aquí (ya cubierto en
apps/triaje/tests.py). Aquí validamos: lista, filtros, aislamiento por
ámbito, detalle, PII y N+1.
"""
import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.organizaciones.models import Organizacion
from apps.hospitales.models import Hospital
from apps.pacientes.models import Paciente, Episodio
from apps.triaje.models import Triaje

User = get_user_model()


def _mk_superuser(username):
    return User.objects.create_superuser(username=username, password="x")


def _mk_plain_user(username):
    return User.objects.create_user(username=username, password="x")


def _mk_org():
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    code = f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=f"Org {code}", codigo=code,
        tipo=tipo_f.choices[0][0] if tipo_f.choices else "OTRO",
        estado=estado_f.choices[0][0] if estado_f.choices else "ACTIVA",
    )


def _mk_hospital(org):
    code = f"hosp-{uuid.uuid4().hex[:8]}"
    return Hospital.objects.create(
        codigo=code, nombre=f"Hospital {code}",
        tipo="HOSPITAL", nivel="NIVEL_I",
        organizacion=org, direccion="Calle test",
        estado_operativo="DISPONIBLE",
    )


def _mk_paciente(nombres="Juan Carlos", apellidos="Pérez"):
    return Paciente.objects.create(
        nombres=nombres, apellidos=apellidos,
        cedula="V-12345678", cedula_hash=None,
        sexo_biologico="M",
    )


def _mk_episodio(paciente, hospital, registrado_por):
    return Episodio.objects.create(
        paciente=paciente, hospital=hospital,
        motivo_consulta="Motivo test", estado="ABIERTO",
        registrado_por=registrado_por,
    )


def _mk_triaje(episodio, evaluado_por, clasificacion="VERDE", vigente=True):
    return Triaje.objects.create(
        episodio=episodio, clasificacion=clasificacion,
        signos_vitales={"TA": "120/80", "FC": 72},
        observaciones="Obs test",
        evaluado_por=evaluado_por, vigente=vigente,
    )


class TriajesListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.hosp = _mk_hospital(self.org)
        self.paciente = _mk_paciente()
        self.episodio = _mk_episodio(self.paciente, self.hosp, self.admin)

    def test_list_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:triajes_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_list_renders_empty(self):
        r = self.client.get(reverse("dashboard:triajes_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Triajes")

    def test_list_shows_triaje(self):
        _mk_triaje(self.episodio, self.admin, clasificacion="ROJO")
        r = self.client.get(reverse("dashboard:triajes_list"))
        self.assertContains(r, "Rojo")

    def test_list_filters_by_clasificacion(self):
        _mk_triaje(self.episodio, self.admin, clasificacion="ROJO")
        r = self.client.get(
            reverse("dashboard:triajes_list") + "?clasificacion=ROJO"
        )
        body = r.content.decode()
        # Solo la tabla, no el <select> del filtro (que siempre tiene todos
        # los choices como <option>)
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Rojo", table)
        self.assertNotIn("Verde", table)

    def test_list_default_shows_only_vigente(self):
        _mk_triaje(self.episodio, self.admin, clasificacion="ROJO", vigente=False)
        r = self.client.get(reverse("dashboard:triajes_list"))
        # Default vigente=true → el histórico no aparece en la tabla
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertNotIn("Rojo", table)

    def test_list_todos_shows_historico(self):
        _mk_triaje(self.episodio, self.admin, clasificacion="ROJO", vigente=False)
        r = self.client.get(
            reverse("dashboard:triajes_list") + "?vigente=todos"
        )
        self.assertContains(r, "Rojo")

    def test_list_query_count_bounded(self):
        _mk_triaje(self.episodio, self.admin)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:triajes_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 16,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class TriajesScopeTests(TestCase):
    """Aislamiento por ámbito: usuario sin membresía no ve nada."""

    def test_plain_user_sees_nothing(self):
        admin = _mk_superuser("admin")
        org = _mk_org()
        hosp = _mk_hospital(org)
        pac = _mk_paciente()
        ep = _mk_episodio(pac, hosp, admin)
        _mk_triaje(ep, admin, clasificacion="ROJO")

        plain = _mk_plain_user("plain")
        self.client.force_login(plain)
        r = self.client.get(reverse("dashboard:triajes_list"))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertNotIn("Rojo", table)
        self.assertIn("No hay triajes", table)


class TriajeDetailTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.hosp = _mk_hospital(self.org)
        self.paciente = _mk_paciente()
        self.episodio = _mk_episodio(self.paciente, self.hosp, self.admin)
        self.triaje = _mk_triaje(self.episodio, self.admin, clasificacion="ROJO")

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:triaje_detail", args=[self.triaje.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Rojo")

    def test_detail_404_unknown(self):
        r = self.client.get(
            reverse("dashboard:triaje_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_signos_vitales(self):
        r = self.client.get(
            reverse("dashboard:triaje_detail", args=[self.triaje.id])
        )
        self.assertContains(r, "120/80")
        self.assertContains(r, "FC")

    def test_detail_admin_sees_full_pii(self):
        r = self.client.get(
            reverse("dashboard:triaje_detail", args=[self.triaje.id])
        )
        body = r.content.decode()
        self.assertIn("Juan Carlos", body)
        self.assertIn("V-12345678", body)

    def test_detail_plain_user_masks_pii(self):
        # Reemplazar la sesión con usuario plain
        self.client.logout()
        plain = _mk_plain_user("plain")
        self.client.force_login(plain)
        # Admin de la sesión inicial no aplica; plain sin membresía no ve
        # nada. Este test verifica que aunque el template tenga el bloque
        # PII, no se filtren datos si el rol no lo permite.
        r = self.client.get(
            reverse("dashboard:triaje_detail", args=[self.triaje.id])
        )
        # Plain sin membresía → 404 (no ve el episodio)
        self.assertEqual(r.status_code, 404)
