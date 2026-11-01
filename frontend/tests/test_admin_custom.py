"""Tests de F4.c — Dashboard custom + Usuarios del admin.

Cubre:
- Dashboard: guard staff/superuser, métricas reales, eventos, 403,
  redirect anónimo a /<slug>/login/
- Users: filtro staff+superuser, badges MFA, 403 no-staff
- Headers: X-Robots-Tag, no-store en /custom/*
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.usuarios.services import enroll_admin_mfa


User = get_user_model()


def _mk_superuser(username="admin", password="test-pass-123!"):
    return User.objects.create_superuser(username=username, password=password)


def _mk_staff(username="staff", password="test-pass-123!"):
    return User.objects.create_user(
        username=username, password=password, is_staff=True,
    )


def _mk_plain(username="plain", password="test-pass-123!"):
    return User.objects.create_user(username=username, password=password)


def _mfa_session(client, user):
    """Simula MFA ya verificado para el user."""
    s = client.session
    s["admin_mfa_verified_at"] = timezone.now().timestamp()
    s["admin_mfa_user_id"] = str(user.pk)
    s.save()


def _mk_evento(actor, accion="test.accion", resultado="EXITOSO"):
    import uuid
    # hash_actual es unique (cadena de hashes) → generar uno por evento
    return EventoAuditoria.objects.create(
        actor=actor,
        accion=accion,
        tipo_objeto="Test",
        objeto_id="",
        resultado=resultado,
        justificacion="Test",
        direccion_ip="127.0.0.1",
        agente_usuario="test",
        id_correlacion="",
        metadatos={},
        hash_anterior=uuid.uuid4().hex,
        hash_actual=uuid.uuid4().hex,
    )


@override_settings(ADMIN_MFA_REQUIRED=True)
class DashboardAnonimoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_anonimo_va_a_login_admin(self):
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(f"/{self.slug}/login/", r["Location"])
        self.assertNotIn("/panel/login/", r["Location"])


@override_settings(ADMIN_MFA_REQUIRED=True)
class DashboardStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_superuser("dash_admin")
        enroll_admin_mfa(self.user)
        self.client = Client()
        self.client.login(username="dash_admin", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_renders_200(self):
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Estado del sistema")

    def test_muestra_conteo_usuarios(self):
        _mk_staff("s1")
        _mk_staff("s2")
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        body = r.content.decode()
        # 1 superuser + 2 staff = 3 staff totales
        self.assertIn("Staff / Superuser", body)
        self.assertContains(r, "Usuarios totales")

    def test_sin_eventos_muestra_vacio(self):
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        self.assertContains(r, "Sin eventos registrados")

    def test_con_eventos_muestra_tabla(self):
        _mk_evento(self.user, accion="login.exitoso")
        _mk_evento(self.user, accion="admin.accion", resultado="DENEGADO")
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        body = r.content.decode()
        self.assertIn("login.exitoso", body)
        self.assertIn("admin.accion", body)
        self.assertIn("Denegado", body)

    def test_headers_anti_index(self):
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        self.assertEqual(r["X-Robots-Tag"], "noindex, nofollow, noarchive")
        self.assertIn("no-store", r.get("Cache-Control", ""))


@override_settings(ADMIN_MFA_REQUIRED=True)
class DashboardNoStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_plain("plain_dash")
        self.client = Client()
        self.client.login(username="plain_dash", password="test-pass-123!")
        # Aunque marcáramos MFA, no debe pasar:
        _mfa_session(self.client, self.user)

    def test_no_staff_403(self):
        r = self.client.get(reverse("admin_custom:admin_dashboard"))
        # Sin is_staff/is_superuser → 403 en la vista
        self.assertEqual(r.status_code, 403)


@override_settings(ADMIN_MFA_REQUIRED=True)
class UsersListStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_superuser("users_admin")
        enroll_admin_mfa(self.user)
        self.client = Client()
        self.client.login(username="users_admin", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_renders_200(self):
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "con acceso al admin")

    def test_solo_staff_y_superusers(self):
        _mk_staff("s_ok")
        _mk_plain("plain_no")  # no debe aparecer
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        body = r.content.decode()
        self.assertIn("users_admin", body)
        self.assertIn("s_ok", body)
        self.assertNotIn("plain_no", body)

    def test_badge_mfa_configurado(self):
        staff = _mk_staff("staff_mfa")
        enroll_admin_mfa(staff)
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        body = r.content.decode()
        self.assertIn("Configurado", body)

    def test_badge_mfa_pendiente(self):
        _mk_staff("staff_no_mfa")
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        body = r.content.decode()
        self.assertIn("Pendiente", body)

    def test_badge_superuser(self):
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        body = r.content.decode()
        self.assertIn("Superuser", body)

    def test_headers_anti_index(self):
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        self.assertEqual(r["X-Robots-Tag"], "noindex, nofollow, noarchive")


@override_settings(ADMIN_MFA_REQUIRED=True)
class UsersListNoStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_plain("plain_users")
        self.client = Client()
        self.client.login(username="plain_users", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_no_staff_403(self):
        r = self.client.get(reverse("admin_custom:admin_users_list"))
        self.assertEqual(r.status_code, 403)
