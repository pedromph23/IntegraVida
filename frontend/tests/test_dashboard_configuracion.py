"""Tests de F3.h.2 — Configuración (Membresías)."""
import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.organizaciones.models import Membresia, Organizacion

User = get_user_model()


def _mk_superuser(username):
    return User.objects.create_superuser(username=username, password="x")


def _mk_user(username):
    return User.objects.create_user(username=username, password="x")


def _mk_org(nombre=None):
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipos = [c[0] for c in tipo_f.choices] if tipo_f.choices else []
    estados = [c[0] for c in estado_f.choices] if estado_f.choices else []
    code = f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=nombre or f"Org {code}", codigo=code,
        tipo="OTRO" if "OTRO" in tipos else (tipos[0] if tipos else "OTRO"),
        estado="ACTIVA" if "ACTIVA" in estados else (estados[0] if estados else "ACTIVA"),
    )


def _mk_membresia(user, org, rol="OPERADOR", estado="ACTIVA"):
    return Membresia.objects.create(
        usuario=user, organizacion=org,
        rol=rol, estado=estado,
    )


class ConfiguracionIndexTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:configuracion_index"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_renders(self):
        r = self.client.get(reverse("dashboard:configuracion_index"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Configuración")
        self.assertContains(r, "Membresías")


class MembresiasListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org("Org A")

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:membresias_list"))
        self.assertEqual(r.status_code, 302)

    def test_renders_empty(self):
        r = self.client.get(reverse("dashboard:membresias_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Membresías")

    def test_lists_membresias(self):
        u = _mk_user("carlos")
        _mk_membresia(u, self.org)
        r = self.client.get(reverse("dashboard:membresias_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("carlos", table)
        self.assertIn("Org A", table)

    def test_filters_by_estado(self):
        u1 = _mk_user("u_activa")
        u2 = _mk_user("u_suspendida")
        _mk_membresia(u1, self.org, estado="ACTIVA")
        _mk_membresia(u2, self.org, estado="SUSPENDIDA")
        r = self.client.get(
            reverse("dashboard:membresias_list") + "?estado=SUSPENDIDA"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("u_suspendida", table)
        self.assertNotIn("u_activa", table)

    def test_filters_by_rol(self):
        u1 = _mk_user("u_coord")
        u2 = _mk_user("u_op")
        _mk_membresia(u1, self.org, rol="COORDINADOR")
        _mk_membresia(u2, self.org, rol="OPERADOR")
        r = self.client.get(
            reverse("dashboard:membresias_list") + "?rol=COORDINADOR"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("u_coord", table)
        self.assertNotIn("u_op", table)

    def test_query_count_bounded(self):
        for _ in range(3):
            u = _mk_user(f"u{uuid.uuid4().hex[:6]}")
            _mk_membresia(u, self.org)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:membresias_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 15,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class MembresiaUpdateTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org("Org A")
        self.target = _mk_user("target")
        self.m = _mk_membresia(
            self.target, self.org, rol="OPERADOR", estado="ACTIVA",
        )
        self.url = reverse("dashboard:membresia_update", args=[self.m.id])

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.post(self.url, {"estado": "SUSPENDIDA"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_superuser_can_change_estado(self):
        r = self.client.post(self.url, {"estado": "SUSPENDIDA"})
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertEqual(self.m.estado, "SUSPENDIDA")

    def test_superuser_can_change_rol(self):
        r = self.client.post(self.url, {"rol": "COORDINADOR"})
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertEqual(self.m.rol, "COORDINADOR")

    def test_invalid_values_no_change(self):
        r = self.client.post(
            self.url, {"estado": "INVENTADO", "rol": "INVENTADO"}
        )
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertEqual(self.m.estado, "ACTIVA")
        self.assertEqual(self.m.rol, "OPERADOR")

    def test_plain_user_forbidden(self):
        self.client.logout()
        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.post(self.url, {"estado": "SUSPENDIDA"})
        self.assertEqual(r.status_code, 403)

    def test_admin_org_of_same_org_can_change(self):
        self.client.logout()
        admin2 = _mk_user("admin_org")
        _mk_membresia(admin2, self.org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin2)
        r = self.client.post(self.url, {"estado": "SUSPENDIDA"})
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertEqual(self.m.estado, "SUSPENDIDA")

    def test_admin_org_other_org_forbidden(self):
        self.client.logout()
        other_org = _mk_org("Org B")
        admin2 = _mk_user("admin_org_b")
        _mk_membresia(admin2, other_org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin2)
        r = self.client.post(self.url, {"estado": "SUSPENDIDA"})
        self.assertEqual(r.status_code, 403)


class MembresiasScopeTests(TestCase):
    def test_plain_user_sees_nothing(self):
        admin = _mk_superuser("admin")
        org = _mk_org("Org O")
        u = _mk_user("u1")
        _mk_membresia(u, org)

        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.get(reverse("dashboard:membresias_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("No hay membresías", table)

    def test_admin_org_sees_only_own_org(self):
        admin = _mk_superuser("admin")
        org1 = _mk_org("Org1")
        org2 = _mk_org("Org2")
        u1 = _mk_user("user1")
        u2 = _mk_user("user2")
        _mk_membresia(u1, org1)
        _mk_membresia(u2, org2)

        admin1 = _mk_user("admin1")
        _mk_membresia(admin1, org1, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin1)
        r = self.client.get(reverse("dashboard:membresias_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("user1", table)
        self.assertNotIn("user2", table)
