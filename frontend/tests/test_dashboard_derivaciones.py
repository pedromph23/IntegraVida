"""Tests de F3.f.2 — Derivaciones (lista, detalle, transiciones).

La lógica de transiciones vive en apps.derivaciones.services (cubierta
por apps/derivaciones/tests.py). Aquí testeamos la UI + que la vista
delega correctamente las excepciones de services.

Reglas de acceso:
- Lista/detalle: puede_administrar_plataforma (superuser) ve todo;
  usuario con Membresia ACTIVA ve solo sus orgs.
- POST transición: services exige Membresia ACTIVA en origen o destino
  (NO acepta superuser sin membresía).
"""
import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.derivaciones.models import Derivacion, TransicionEstado
from apps.hospitales.models import Hospital
from apps.organizaciones.models import Membresia, Organizacion
from apps.pacientes.models import Episodio, Paciente

User = get_user_model()


def _mk_superuser(username):
    return User.objects.create_superuser(username=username, password="x")


def _mk_user(username):
    return User.objects.create_user(username=username, password="x")


def _mk_org():
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipos = [c[0] for c in tipo_f.choices] if tipo_f.choices else []
    estados = [c[0] for c in estado_f.choices] if estado_f.choices else []
    code = f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=f"Org {code}", codigo=code,
        tipo="OTRO" if "OTRO" in tipos else (tipos[0] if tipos else "OTRO"),
        estado="ACTIVA" if "ACTIVA" in estados else (estados[0] if estados else "ACTIVA"),
    )


def _mk_membresia(user, org):
    rol_f = Membresia._meta.get_field("rol")
    roles = [c[0] for c in rol_f.choices] if rol_f.choices else []
    # Rol de operación plena si existe; si no, el primero disponible
    rol = "OPERADOR" if "OPERADOR" in roles else (roles[0] if roles else "")
    return Membresia.objects.create(
        usuario=user, organizacion=org,
        rol=rol,
        estado=Membresia.Estado.ACTIVA,
    )


def _mk_hospital(org):
    code = f"hosp-{uuid.uuid4().hex[:8]}"
    return Hospital.objects.create(
        codigo=code, nombre=f"Hospital {code}",
        tipo="HOSPITAL", nivel="NIVEL_I",
        organizacion=org, direccion="Calle test",
        estado_operativo="DISPONIBLE",
    )


def _mk_paciente():
    return Paciente.objects.create(
        nombres="Juan Carlos", apellidos="Pérez",
        cedula="V-12345678", cedula_hash=None,
        sexo_biologico="M",
    )


def _mk_episodio(paciente, hospital, autor):
    return Episodio.objects.create(
        paciente=paciente, hospital=hospital,
        motivo_consulta="Motivo test", estado="ABIERTO",
        registrado_por=autor,
    )


def _mk_derivacion(episodio, hosp_origen, hosp_destino, autor, estado="SOLICITADA"):
    return Derivacion.objects.create(
        episodio=episodio,
        hospital_origen=hosp_origen,
        hospital_destino=hosp_destino,
        prioridad="MEDIA",
        estado=estado,
        motivo="Motivo derivación",
        solicitada_por=autor,
    )


class DerivacionesListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        org = _mk_org()
        self.hosp_o = _mk_hospital(org)
        self.hosp_d = _mk_hospital(org)
        self.pac = _mk_paciente()
        self.ep = _mk_episodio(self.pac, self.hosp_o, self.admin)

    def test_list_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:derivaciones_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_list_renders_empty(self):
        r = self.client.get(reverse("dashboard:derivaciones_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Derivaciones")

    def test_list_shows_derivacion(self):
        _mk_derivacion(self.ep, self.hosp_o, self.hosp_d, self.admin)
        r = self.client.get(reverse("dashboard:derivaciones_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("J***", table)

    def test_list_filters_by_estado(self):
        _mk_derivacion(self.ep, self.hosp_o, self.hosp_d, self.admin, estado="SOLICITADA")
        _mk_derivacion(self.ep, self.hosp_o, self.hosp_d, self.admin, estado="CANCELADA")
        r = self.client.get(
            reverse("dashboard:derivaciones_list") + "?estado=CANCELADA"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Cancelada", table)
        self.assertNotIn("Solicitada", table)

    def test_list_query_count_bounded(self):
        _mk_derivacion(self.ep, self.hosp_o, self.hosp_d, self.admin)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:derivaciones_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 20,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class DerivacionesScopeTests(TestCase):
    def test_plain_user_sees_nothing(self):
        admin = _mk_superuser("admin")
        org = _mk_org()
        hosp_o = _mk_hospital(org)
        hosp_d = _mk_hospital(org)
        pac = _mk_paciente()
        ep = _mk_episodio(pac, hosp_o, admin)
        _mk_derivacion(ep, hosp_o, hosp_d, admin)

        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.get(reverse("dashboard:derivaciones_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("No hay derivaciones", table)


class DerivacionDetailTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        org = _mk_org()
        self.hosp_o = _mk_hospital(org)
        self.hosp_d = _mk_hospital(org)
        self.pac = _mk_paciente()
        self.ep = _mk_episodio(self.pac, self.hosp_o, self.admin)
        self.der = _mk_derivacion(self.ep, self.hosp_o, self.hosp_d, self.admin)

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:derivacion_detail", args=[self.der.id])
        )
        self.assertEqual(r.status_code, 200)

    def test_detail_404_unknown(self):
        r = self.client.get(
            reverse("dashboard:derivacion_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_historial(self):
        TransicionEstado.objects.create(
            derivacion=self.der, estado_anterior="",
            estado_nuevo="SOLICITADA",
            usuario=self.admin,
            motivo="Creación inicial",
        )
        r = self.client.get(
            reverse("dashboard:derivacion_detail", args=[self.der.id])
        )
        self.assertContains(r, "Creación inicial")


class TransicionarTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.org = _mk_org()
        self.hosp_o = _mk_hospital(self.org)
        self.hosp_d = _mk_hospital(self.org)
        self.pac = _mk_paciente()
        self.ep = _mk_episodio(self.pac, self.hosp_o, self.admin)
        self.der = _mk_derivacion(self.ep, self.hosp_o, self.hosp_d, self.admin)
        self.url = reverse(
            "dashboard:derivacion_transicionar", args=[self.der.id],
        )

    def test_requires_auth(self):
        r = self.client.post(self.url, {"estado": "ACEPTADA"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_plain_user_forbidden(self):
        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.post(self.url, {"estado": "ACEPTADA"})
        # _base_queryset filtra por membresía → no ve la derivación → 404
        # (nunca llega a services.transicionar_derivacion)
        self.assertEqual(r.status_code, 404)

    def test_operador_with_membership_can_transition(self):
        op = _mk_user("op")
        _mk_membresia(op, self.org)
        self.client.force_login(op)
        r = self.client.post(self.url, {"estado": "ACEPTADA"})
        self.assertEqual(r.status_code, 302)
        self.der.refresh_from_db()
        self.assertEqual(self.der.estado, "ACEPTADA")
        self.assertEqual(self.der.aceptada_por, op)

    def test_invalid_jump_shows_error_and_keeps_state(self):
        op = _mk_user("op2")
        _mk_membresia(op, self.org)
        self.client.force_login(op)
        # SOLICITADA → COMPLETADA no permitida (salto)
        r = self.client.post(self.url, {"estado": "COMPLETADA"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.der.refresh_from_db()
        self.assertEqual(self.der.estado, "SOLICITADA")
        self.assertContains(r, "Transición inválida")

    def test_transition_creates_audit_row(self):
        op = _mk_user("op3")
        _mk_membresia(op, self.org)
        self.client.force_login(op)
        before = TransicionEstado.objects.filter(derivacion=self.der).count()
        self.client.post(self.url, {"estado": "ACEPTADA"})
        after = TransicionEstado.objects.filter(derivacion=self.der).count()
        self.assertEqual(after, before + 1)
