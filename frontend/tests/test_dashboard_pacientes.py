"""Tests de F3.e.2 — módulo Pacientes del panel.

Incluye tests de ENMASCARAMIENTO OBLIGATORIOS (§12).
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.pacientes.models import Paciente, ContactoEmergencia, Episodio
from apps.hospitales.models import Hospital
from apps.organizaciones.models import Organizacion

User = get_user_model()


def _mk_user(username, groups=(), is_staff=False):
    u = User.objects.create_user(username=username, password="x")
    if is_staff:
        u.is_staff = True
        u.save()
    for n in groups:
        g, _ = Group.objects.get_or_create(name=n)
        u.groups.add(g)
    return u


def _mk_org():
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipo = tipo_f.choices[0][0] if tipo_f.choices else "OTRO"
    estado = estado_f.choices[0][0] if estado_f.choices else "ACTIVA"
    code = f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=f"Org {code}", codigo=code, tipo=tipo, estado=estado,
    )


def _mk_hospital(org=None):
    org = org or _mk_org()
    code = f"hosp-{uuid.uuid4().hex[:8]}"
    return Hospital.objects.create(
        codigo=code, nombre=f"Hospital {code}",
        tipo="HOSPITAL", nivel="NIVEL_I",
        organizacion=org, direccion="Calle test",
        estado_operativo="DISPONIBLE",
    )


def _mk_paciente(
    nombres="Juan Carlos", apellidos="Pérez Rodríguez",
    cedula="V-12345678", **kw,
):
    return Paciente.objects.create(
        nombres=nombres, apellidos=apellidos,
        cedula=cedula, cedula_hash=None,
        sexo_biologico="M", **kw,
    )


class PacientesListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("plist")
        self.client.force_login(self.user)

    def test_list_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:pacientes_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_list_renders_empty(self):
        r = self.client.get(reverse("dashboard:pacientes_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Pacientes")

    def test_list_masks_cedula(self):
        _mk_paciente(cedula="V-12345678")
        r = self.client.get(reverse("dashboard:pacientes_list"))
        body = r.content.decode()
        self.assertNotIn("V-12345678", body, "Cédula completa NO debe filtrarse")
        self.assertIn("5678", body, "Últimos 4 dígitos sí deben verse")

    def test_list_masks_nombres(self):
        _mk_paciente(nombres="Juan Carlos", apellidos="Pérez Rodríguez")
        r = self.client.get(reverse("dashboard:pacientes_list"))
        body = r.content.decode()
        self.assertNotIn("Juan Carlos", body)
        self.assertNotIn("Pérez Rodríguez", body)

    def test_list_query_count_bounded(self):
        for i in range(3):
            _mk_paciente(nombres=f"P{i}", apellidos="Test")
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:pacientes_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 16,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class PacienteDetailTests(TestCase):
    def setUp(self):
        self.paciente = _mk_paciente(
            cedula="V-98765432",
            nombres="María José",
            apellidos="González",
            notas_internas="Paciente con alergia a penicilina",
        )

    def test_detail_requires_auth(self):
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        self.assertEqual(r.status_code, 302)

    def test_detail_admin_sees_full_pii(self):
        u = _mk_user("admin", groups=["ADMIN"])
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        body = r.content.decode()
        self.assertIn("María José", body)
        self.assertIn("González", body)
        self.assertIn("V-98765432", body)
        self.assertIn("alergia a penicilina", body)

    def test_detail_operator_sees_names_but_masked_cedula(self):
        u = _mk_user("op", groups=["OPERADOR_HOSPITAL"])
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        body = r.content.decode()
        self.assertIn("María José", body)
        self.assertIn("González", body)
        self.assertNotIn("V-98765432", body)
        self.assertIn("5432", body)
        self.assertNotIn("alergia a penicilina", body)

    def test_detail_plain_user_masks_everything(self):
        u = _mk_user("plain")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        body = r.content.decode()
        self.assertNotIn("María José", body)
        self.assertNotIn("V-98765432", body)
        self.assertNotIn("alergia a penicilina", body)

    def test_detail_404_unknown(self):
        u = _mk_user("op2", groups=["ADMIN"])
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_contactos_and_episodios(self):
        u = _mk_user("op3", groups=["ADMIN"])
        self.client.force_login(u)

        ContactoEmergencia.objects.create(
            paciente=self.paciente, nombre="Carlos Test",
            parentesco="FAMILIAR", telefono="+58-555-1234",
            es_principal=True,
        )
        # Constraint: exactamente uno de hospital/refugio en Episodio.
        hosp = _mk_hospital()
        Episodio.objects.create(
            paciente=self.paciente,
            hospital=hosp,
            motivo_consulta="Dolor abdominal",
            estado="ABIERTO",
            registrado_por=u,
        )
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        self.assertContains(r, "Carlos Test")
        self.assertContains(r, "Dolor abdominal")
