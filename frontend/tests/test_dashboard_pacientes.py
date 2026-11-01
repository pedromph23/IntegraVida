"""Tests de F3.e.2 — módulo Pacientes del panel.

Incluye tests de ENMASCARAMIENTO OBLIGATORIOS (§12):
- la lista nunca expone PII en el HTML.
- el detalle condiciona PII a roles privilegiados.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.pacientes.models import Paciente, ContactoEmergencia, Episodio

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


def _mk_paciente(
    nombres="Juan Carlos", apellidos="Pérez Rodríguez",
    cedula="V-12345678", **kw,
):
    return Paciente.objects.create(
        nombres=nombres, apellidos=apellidos,
        cedula=cedula, cedula_hash="",
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
        self.assertNotIn("Juan Carlos", body, "Nombre completo NO debe filtrarse")
        self.assertNotIn("Pérez Rodríguez", body, "Apellidos NO deben filtrarse")

    def test_list_query_count_bounded(self):
        for i in range(3):
            _mk_paciente(nombres=f"P{i}", apellidos="Test")
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:pacientes_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 12,
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

    def test_detail_operator_masks_cedula(self):
        u = _mk_user("op", groups=["OPERADOR_HOSPITAL"])
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        body = r.content.decode()
        # Nombres completos (los necesita para operar)
        self.assertIn("María José", body)
        self.assertIn("González", body)
        # Cédula enmascarada
        self.assertNotIn("V-98765432", body)
        self.assertIn("5432", body)
        # Notas internas ocultas
        self.assertNotIn("alergia a penicilina", body)

    def test_detail_plain_user_masks_everything(self):
        u = _mk_user("plain")
        self.client.force_login(u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        body = r.content.decode()
        # Nombres enmascarados (inicial + asteriscos)
        self.assertNotIn("María José", body)
        self.assertNotIn("V-98765432", body)
        self.assertNotIn("alergia a penicilina", body)

    def test_detail_404_unknown(self):
        import uuid
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
        Episodio.objects.create(
            paciente=self.paciente,
            motivo_consulta="Dolor abdominal",
            estado="ABIERTO",
            registrado_por=u,
        )
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[self.paciente.id])
        )
        self.assertContains(r, "Carlos Test")
        self.assertContains(r, "Dolor abdominal")
