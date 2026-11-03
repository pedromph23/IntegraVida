"""Tests de F3.e.2 + F5.d — módulo Pacientes del panel.

F3.e.2: list, detail con masking PII condicional.
F5.d: scoping por organización (vía episodios) + edición de PII
      restringida a ADMIN_ORGANIZACION o COORDINADOR.

Cambio respecto a F3.e.2: ahora _base_queryset(user) filtra pacientes
por episodios en orgs del user. Los tests ahora crean Episodio con
Hospital en la org del user (constraint XOR: exactamente uno de
hospital/refugio en Episodio).
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, Client
from django.urls import reverse

from apps.hospitales.models import Hospital
from apps.organizaciones.models import Organizacion, Membresia
from apps.pacientes.models import Paciente, ContactoEmergencia, Episodio

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


def _mk_hospital(org, codigo=None):
    code = codigo or f"hosp-{uuid.uuid4().hex[:8]}"
    return Hospital.objects.create(
        codigo=code, nombre=f"Hospital {code}",
        tipo="HOSPITAL", nivel="NIVEL_I",
        organizacion=org, direccion="Calle test 456",
        estado_operativo="DISPONIBLE",
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


def _mk_paciente(nombres="Juan Carlos", apellidos="Pérez Rodríguez",
                 cedula="V-12345678", **kw):
    return Paciente.objects.create(
        nombres=nombres, apellidos=apellidos,
        cedula=cedula, cedula_hash=None,
        sexo_biologico="M", **kw,
    )


def _mk_episodio(paciente, hospital, autor):
    return Episodio.objects.create(
        paciente=paciente, hospital=hospital,
        motivo_consulta="Motivo test", estado="ABIERTO",
        registrado_por=autor,
    )


def _linked_paciente(org, autor, **kw):
    """Paciente CON episodio en hospital de `org` → visible en ese scope."""
    paciente = _mk_paciente(**kw)
    hospital = _mk_hospital(org)
    _mk_episodio(paciente, hospital, autor)
    return paciente


# ── Lista ────────────────────────────────────────────────────────────
class PacientesListTests(TestCase):
    def setUp(self):
        self.user = _mk_user("plist")
        self.client.force_login(self.user)
        self.org = _mk_org()
        _mk_membresia(self.user, self.org, rol="COORDINADOR")

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
        _linked_paciente(self.org, self.user, cedula="V-12345678")
        r = self.client.get(reverse("dashboard:pacientes_list"))
        body = r.content.decode()
        self.assertNotIn("V-12345678", body)
        self.assertIn("5678", body)

    def test_list_masks_nombres(self):
        _linked_paciente(
            self.org, self.user,
            nombres="Juan Carlos", apellidos="Pérez Rodríguez",
        )
        r = self.client.get(reverse("dashboard:pacientes_list"))
        body = r.content.decode()
        self.assertNotIn("Juan Carlos", body)
        self.assertNotIn("Pérez Rodríguez", body)

    def test_list_no_expone_pacientes_sin_episodio(self):
        """F5.d: paciente sin episodio no tiene scope → invisible."""
        _mk_paciente(nombres="Huerfano", apellidos="Sin Episodio")
        r = self.client.get(reverse("dashboard:pacientes_list"))
        self.assertNotContains(r, "Huerfano")

    def test_list_no_expone_otras_orgs(self):
        """Paciente de otra org no aparece ni enmascarado."""
        otra_org = _mk_org()
        _linked_paciente(
            self.org, self.user,
            nombres="Mio", apellidos="Paciente",
        )
        _linked_paciente(
            otra_org, self.user,
            nombres="Ajeno", apellidos="Paciente",
        )
        r = self.client.get(reverse("dashboard:pacientes_list"))
        body = r.content.decode()
        self.assertIn("M*** P***", body)
        self.assertNotIn("A*** P***", body)
        self.assertNotIn("Ajeno", body)
        self.assertEqual(body.count("Ver →"), 1)


class PacientesListNoPermisoTests(TestCase):
    """Roles LOGISTICA / CONSULTA no ven pacientes."""

    def test_logistica_forbidden(self):
        u = _mk_user("log")
        org = _mk_org()
        _mk_membresia(u, org, rol="LOGISTICA")
        self.client.force_login(u)
        r = self.client.get(reverse("dashboard:pacientes_list"))
        self.assertEqual(r.status_code, 403)


# ── Detalle ──────────────────────────────────────────────────────────
class PacienteDetailTests(TestCase):
    def setUp(self):
        self.org = _mk_org()

    def test_detail_admin_sees_full_pii(self):
        u = _mk_user("admin", groups=["ADMIN"])
        _mk_membresia(u, self.org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(u)
        p = _linked_paciente(
            self.org, u, cedula="V-98765432",
            nombres="María José", apellidos="González",
            notas_internas="Paciente con alergia a penicilina",
        )
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[p.id])
        )
        body = r.content.decode()
        self.assertIn("María José", body)
        self.assertIn("V-98765432", body)
        self.assertIn("alergia a penicilina", body)

    def test_detail_operador_masks_cedula(self):
        u = _mk_user("op", groups=["OPERADOR_HOSPITAL"])
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        p = _linked_paciente(
            self.org, u, cedula="V-98765432",
            nombres="María José", apellidos="González",
            notas_internas="Paciente con alergia a penicilina",
        )
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[p.id])
        )
        body = r.content.decode()
        self.assertIn("María José", body)
        self.assertNotIn("V-98765432", body)
        self.assertIn("5432", body)
        self.assertNotIn("alergia a penicilina", body)

    def test_detail_coordinador_muestra_boton_editar(self):
        u = _mk_user("coord_btn")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u)
        r = self.client.get(reverse("dashboard:paciente_detail", args=[p.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Editar datos")

    def test_detail_operador_no_muestra_boton_editar(self):
        u = _mk_user("op_btn")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u)
        r = self.client.get(reverse("dashboard:paciente_detail", args=[p.id]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Editar datos")

    def test_detail_consulta_forbidden(self):
        u = _mk_user("cons")
        _mk_membresia(u, self.org, rol="CONSULTA")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[p.id])
        )
        self.assertEqual(r.status_code, 403)

    def test_detail_404_otra_org(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        otra_org = _mk_org()
        p = _linked_paciente(otra_org, u)
        r = self.client.get(
            reverse("dashboard:paciente_detail", args=[p.id])
        )
        self.assertEqual(r.status_code, 404)


# ── Editar (F5.d) ────────────────────────────────────────────────────
class PacienteEditTests(TestCase):
    def setUp(self):
        self.org = _mk_org()

    def test_coordinador_puede_editar(self):
        u = _mk_user("coord")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u)
        r = self.client.get(
            reverse("dashboard:paciente_update_form", args=[p.id])
        )
        self.assertEqual(r.status_code, 200)

    def test_operador_no_puede_editar(self):
        u = _mk_user("op")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u)
        r = self.client.get(
            reverse("dashboard:paciente_update_form", args=[p.id])
        )
        self.assertEqual(r.status_code, 403)

    def test_consulta_no_puede_editar(self):
        u = _mk_user("cons")
        _mk_membresia(u, self.org, rol="CONSULTA")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u)
        r = self.client.get(
            reverse("dashboard:paciente_update_form", args=[p.id])
        )
        self.assertEqual(r.status_code, 403)

    def test_update_persiste_cambios(self):
        u = _mk_user("coord2")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        p = _linked_paciente(self.org, u, nombres="Original")
        data = {
            "nombres": "Actualizado",
            "apellidos": p.apellidos,
            "cedula": p.cedula,
            "fecha_nacimiento": "",
            "sexo_biologico": p.sexo_biologico,
            "telefono": "+58 412-9999999",
            "email": "",
            "notas_internas": "",
        }
        r = self.client.post(
            reverse("dashboard:paciente_update_submit", args=[p.id]),
            data,
        )
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.nombres, "Actualizado")
        self.assertEqual(p.telefono, "+58 412-9999999")

    def test_update_404_otra_org(self):
        u = _mk_user("coord3")
        _mk_membresia(u, self.org, rol="COORDINADOR")
        self.client.force_login(u)
        otra_org = _mk_org()
        p = _linked_paciente(otra_org, u)
        data = {
            "nombres": "Hack", "apellidos": "Intento",
            "cedula": p.cedula, "fecha_nacimiento": "",
            "sexo_biologico": p.sexo_biologico, "telefono": "",
            "email": "", "notas_internas": "",
        }
        r = self.client.post(
            reverse("dashboard:paciente_update_submit", args=[p.id]),
            data,
        )
        self.assertEqual(r.status_code, 404)
        p.refresh_from_db()
        self.assertNotEqual(p.nombres, "Hack")
