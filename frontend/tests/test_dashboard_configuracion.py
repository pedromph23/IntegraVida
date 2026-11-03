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

    def test_filters_by_q(self):
        """Filtro q busca por username (o email) sin romper con input raro."""
        u1 = _mk_user("ana_busqueda")
        u2 = _mk_user("beto_busqueda")
        org = _mk_org()
        _mk_membresia(u1, org)
        _mk_membresia(u2, org)
        admin = _mk_user("admin_q")
        _mk_membresia(admin, org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin)
        r = self.client.get(
            reverse("dashboard:membresias_list"), {"q": "ana_busqueda"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("ana_busqueda", body)
        self.assertNotIn("beto_busqueda", body)

    def test_filters_by_q_no_rompe_con_wildcards(self):
        """Input con % y _ no rompe la búsqueda."""
        org = _mk_org()
        admin = _mk_user("admin_q2")
        _mk_membresia(admin, org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin)
        r = self.client.get(
            reverse("dashboard:membresias_list"),
            {"q": "%_"},  # wildcards LIKE (%, _)
        )
        self.assertEqual(r.status_code, 200)

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

    def test_admin_org_puede_autodemoverse_documenta_riesgo(self):
        """Comportamiento actual: un ADMIN_ORGANIZACION SÍ puede demoverse a sí
        mismo (no hay salvaguarda en _can_manage_membership).

        Política deliberada del test: documentar el comportamiento real y
        anotar el riesgo como deuda D-F5-03. Si en el futuro se añade
        salvaguarda, este test debe pasar a 403 y borrarse D-F5-03.
        """
        org = _mk_org()
        admin = _mk_user("self_admin")
        m = _mk_membresia(admin, org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin)
        r = self.client.post(
            reverse("dashboard:membresia_update", args=[m.id]),
            {"rol": "OPERADOR", "estado": "ACTIVA"},
        )
        # Comportamiento actual: permitido (302) y el cambio persiste.
        self.assertEqual(r.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.rol, "OPERADOR")

    def test_admin_org_puede_modificar_otro_admin_misma_org(self):
        """Un ADMIN_ORGANIZACION puede gestionar a otro ADMIN de su misma org
        (política esperada: peers horizontal)."""
        org = _mk_org()
        admin1 = _mk_user("admin_peer_1")
        admin2 = _mk_user("admin_peer_2")
        _mk_membresia(admin1, org, rol="ADMIN_ORGANIZACION")
        m2 = _mk_membresia(admin2, org, rol="ADMIN_ORGANIZACION")
        self.client.force_login(admin1)
        r = self.client.post(
            reverse("dashboard:membresia_update", args=[m2.id]),
            {"rol": "COORDINADOR", "estado": "ACTIVA"},
        )
        self.assertEqual(r.status_code, 302)
        m2.refresh_from_db()
        self.assertEqual(m2.rol, "COORDINADOR")

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


class MembresiaCRUDTests(TestCase):
    """Crear nueva membresía y revocar (cambio de estado)."""

    def setUp(self):
        self.org = _mk_org("OrgCRUD")
        self.admin = _mk_user("admin_crud")
        _mk_membresia(self.admin, self.org, rol="ADMIN_ORGANIZACION")
        self.url_form = reverse("dashboard:membresia_create_form")
        self.url_submit = reverse("dashboard:membresia_create_submit")

    def test_admin_org_puede_crear_membresia(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.url_form)
        self.assertEqual(r.status_code, 200)

        nuevo = _mk_user("nuevo_crud")
        data = {
            "usuario": nuevo.pk,
            "organizacion": self.org.pk,
            "rol": "OPERADOR",
            "estado": "ACTIVA",
        }
        r = self.client.post(self.url_submit, data)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Membresia.objects.filter(
                usuario=nuevo, organizacion=self.org, rol="OPERADOR",
            ).exists(),
            "La membresía debe crearse",
        )

    def test_user_sin_rol_admin_forbidden(self):
        u = _mk_user("peon_crud")
        _mk_membresia(u, self.org, rol="OPERADOR")
        self.client.force_login(u)
        r = self.client.get(self.url_form)
        # OPERADOR no gestiona membresías → sin orgs_admin → form vacío
        # (o 200 con queryset vacío). El POST sí debe fallar por orgs vacío.
        r = self.client.post(self.url_submit, {
            "usuario": self.admin.pk,
            "organizacion": self.org.pk,
            "rol": "OPERADOR",
            "estado": "ACTIVA",
        })
        # El form rechaza la org (no está en queryset) → 200 con errores
        # o 403/404 según implementación. Aceptamos 200 con error de validación.
        self.assertIn(r.status_code, (200, 403, 404))

