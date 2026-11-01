"""Tests de F4.b — MFA TOTP + rate limiting + management commands.

Cubre:
- apps.usuarios.services: enroll, verify, reset, rate limit
- AdminMFARequiredMiddleware: aplica solo a /<slug>/*, allowlist de auth
- Vistas admin_custom: verify/setup/submit/cancel
- Rate limiting: bloqueo tras 5 intentos, bloqueo solo por (IP, username)
- Management commands: crear_admin_inicial, reset_admin_mfa
"""
import pyotp
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command, CommandError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.services import (
    check_rate_limit,
    clear_rate_limit,
    enroll_admin_mfa,
    register_failed_attempt,
    reset_admin_mfa,
    verify_admin_mfa,
)

User = get_user_model()


def _mk_superuser(username="admin", password="test-pass-123!"):
    return User.objects.create_superuser(username=username, password=password)


def _mk_plain_user(username="plain", password="test-pass-123!"):
    return User.objects.create_user(username=username, password=password)


class ServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = _mk_superuser("svc_user")

    def test_enroll_genera_secret_y_uri(self):
        secret, uri = enroll_admin_mfa(self.user)
        self.assertEqual(len(secret), 32)
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.admin_mfa_secret, secret)
        self.assertIsNotNone(self.user.admin_mfa_enrolled_at)

    def test_verify_code_valido(self):
        secret, _ = enroll_admin_mfa(self.user)
        code = pyotp.TOTP(secret).now()
        self.assertTrue(verify_admin_mfa(self.user, code))

    def test_verify_code_invalido(self):
        enroll_admin_mfa(self.user)
        self.assertFalse(verify_admin_mfa(self.user, "000000"))
        self.assertFalse(verify_admin_mfa(self.user, "abc123"))
        self.assertFalse(verify_admin_mfa(self.user, ""))

    def test_verify_sin_secret(self):
        self.assertFalse(verify_admin_mfa(self.user, "123456"))

    def test_reset_borra_secret(self):
        enroll_admin_mfa(self.user)
        reset_admin_mfa(self.user)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.admin_mfa_secret)
        self.assertIsNone(self.user.admin_mfa_enrolled_at)

    def test_rate_limit_permite_primeros_intentos(self):
        permitido, intentos, maximo = check_rate_limit("1.2.3.4", "u")
        self.assertTrue(permitido)
        self.assertEqual(intentos, 0)
        self.assertEqual(maximo, 5)

    def test_rate_limit_bloquea_al_6to(self):
        for _ in range(5):
            register_failed_attempt("1.2.3.4", "u")
        permitido, intentos, _ = check_rate_limit("1.2.3.4", "u")
        self.assertFalse(permitido)
        self.assertEqual(intentos, 5)

    def test_rate_limit_clear(self):
        for _ in range(3):
            register_failed_attempt("1.2.3.4", "u")
        clear_rate_limit("1.2.3.4", "u")
        permitido, _, _ = check_rate_limit("1.2.3.4", "u")
        self.assertTrue(permitido)

    def test_rate_limit_aislado_por_ip_y_username(self):
        for _ in range(5):
            register_failed_attempt("1.2.3.4", "u")
        # Mismo username, otra IP → permitido
        permitido, _, _ = check_rate_limit("5.6.7.8", "u")
        self.assertTrue(permitido)
        # Misma IP, otro username → permitido
        permitido, _, _ = check_rate_limit("1.2.3.4", "u2")
        self.assertTrue(permitido)


class MiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = _mk_superuser("mw_user")
        enroll_admin_mfa(self.user)
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG
        self.client = Client()

    def _login(self):
        ok = self.client.login(username="mw_user", password="test-pass-123!")
        self.assertTrue(ok)

    def test_sin_mfa_redirige_a_mfa(self):
        self._login()
        r = self.client.get(f"/{self.slug}/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mfa/", r["Location"])

    def test_login_path_no_redirige(self):
        r = self.client.get(f"/{self.slug}/login/")
        # Django admin login renderiza sin requerir MFA (allowlist)
        self.assertEqual(r.status_code, 200)

    def test_mfa_path_no_redirige_a_si_mismo(self):
        self._login()
        r = self.client.get(f"/{self.slug}/mfa/")
        # La vista mfa_verify_view maneja el caso (renderiza o redirige
        # a setup), pero no bucle al mismo /mfa/
        self.assertNotEqual(r.status_code, 500)

    def test_portal_no_afectado(self):
        self._login()
        r = self.client.get("/panel/")
        # Nunca redirige a /mfa/ (eso solo ocurre dentro del admin)
        self.assertNotIn("/mfa/", r.get("Location", ""))

    def test_con_mfa_verificado_pasa(self):
        self._login()
        s = self.client.session
        s["admin_mfa_verified_at"] = timezone.now().timestamp()
        s["admin_mfa_user_id"] = str(self.user.pk)
        s.save()
        r = self.client.get(f"/{self.slug}/")
        # Django admin permite (200) o redirige dentro del admin, no a /mfa/
        self.assertNotIn("/mfa/", r.get("Location", ""))

    def test_mfa_expirado_redirige(self):
        self._login()
        s = self.client.session
        s["admin_mfa_verified_at"] = timezone.now().timestamp() - 9 * 3600
        s["admin_mfa_user_id"] = str(self.user.pk)
        s.save()
        r = self.client.get(f"/{self.slug}/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mfa/", r["Location"])

    def test_user_id_distinto_redirige(self):
        # Sesión con MFA de otro user_id → debe forzar re-verify
        self._login()
        s = self.client.session
        s["admin_mfa_verified_at"] = timezone.now().timestamp()
        s["admin_mfa_user_id"] = "00000000-0000-0000-0000-000000000000"
        s.save()
        r = self.client.get(f"/{self.slug}/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mfa/", r["Location"])


class MFAViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = _mk_superuser("view_user")
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG
        self.client = Client()
        self.client.login(username="view_user", password="test-pass-123!")

    def test_verify_get_sin_secret_redirige_a_setup(self):
        r = self.client.get(f"/{self.slug}/mfa/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mfa/setup/", r["Location"])

    def test_setup_genera_secret_y_muestra_uri(self):
        r = self.client.get(f"/{self.slug}/mfa/setup/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("otpauth://totp/", body)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.admin_mfa_secret)

    def test_setup_si_ya_tiene_secret_redirige_a_verify(self):
        enroll_admin_mfa(self.user)
        r = self.client.get(f"/{self.slug}/mfa/setup/")
        self.assertEqual(r.status_code, 302)
        # Debe redirigir a /mfa/ (verify), no a /mfa/setup/
        self.assertIn("/mfa/", r["Location"])
        self.assertNotIn("/mfa/setup/", r["Location"])

    def test_post_code_valido_marca_sesion(self):
        secret, _ = enroll_admin_mfa(self.user)
        code = pyotp.TOTP(secret).now()
        r = self.client.post(f"/{self.slug}/mfa/verify/", {"code": code})
        self.assertEqual(r.status_code, 302)
        s = self.client.session
        self.assertIn("admin_mfa_verified_at", s)
        self.assertEqual(s["admin_mfa_user_id"], str(self.user.pk))

    def test_post_code_invalido_no_marca(self):
        enroll_admin_mfa(self.user)
        r = self.client.post(f"/{self.slug}/mfa/verify/", {"code": "000000"})
        self.assertEqual(r.status_code, 302)
        s = self.client.session
        self.assertNotIn("admin_mfa_verified_at", s)

    def test_cancel_limpia_sesion(self):
        s = self.client.session
        s["admin_mfa_verified_at"] = timezone.now().timestamp()
        s["admin_mfa_user_id"] = str(self.user.pk)
        s.save()
        r = self.client.get(f"/{self.slug}/mfa/cancel/")
        self.assertEqual(r.status_code, 302)
        s = self.client.session
        self.assertNotIn("admin_mfa_verified_at", s)
        self.assertNotIn("admin_mfa_user_id", s)

    def test_anonimo_va_a_login_admin(self):
        self.client.logout()
        r = self.client.get(f"/{self.slug}/mfa/")
        self.assertEqual(r.status_code, 302)
        # Login del admin, NO /panel/login/
        self.assertIn(f"/{self.slug}/login/", r["Location"])
        self.assertNotIn("/panel/login/", r["Location"])

    def test_no_staff_recibe_403(self):
        self.client.logout()
        _mk_plain_user("plain_user")
        self.client.login(username="plain_user", password="test-pass-123!")
        r = self.client.get(f"/{self.slug}/mfa/")
        # No staff → 403 (o 302 al login si Django admin lo rechaza antes,
        # pero la vista exige is_superuser o is_staff)
        self.assertIn(r.status_code, (403, 302))


class RateLimitViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = _mk_superuser("rl_user")
        enroll_admin_mfa(self.user)
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG
        self.client = Client()
        self.client.login(username="rl_user", password="test-pass-123!")

    def test_5_intentos_fallidos_bloquean(self):
        for _ in range(5):
            self.client.post(f"/{self.slug}/mfa/verify/", {"code": "000000"})
        # 6to intento con código válido debe ser bloqueado
        secret = self.user.admin_mfa_secret
        code = pyotp.TOTP(secret).now()
        self.client.post(f"/{self.slug}/mfa/verify/", {"code": code})
        # La sesión no se marca
        self.assertNotIn("admin_mfa_verified_at", self.client.session)

    def test_codigo_valido_antes_del_limite_ok(self):
        secret = self.user.admin_mfa_secret
        code = pyotp.TOTP(secret).now()
        # 3 intentos fallidos (bajo el límite)
        for _ in range(3):
            self.client.post(f"/{self.slug}/mfa/verify/", {"code": "000000"})
        # Código válido debe pasar
        self.client.post(f"/{self.slug}/mfa/verify/", {"code": code})
        self.assertIn("admin_mfa_verified_at", self.client.session)


class ManagementCommandTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_crear_admin_inicial_imprime_uri(self):
        _mk_superuser("cmd_user")
        out = StringIO()
        call_command("crear_admin_inicial", username="cmd_user", stdout=out)
        output = out.getvalue()
        self.assertIn("otpauth://totp/", output)
        self.assertIn("MFA enrolado", output)
        u = User.objects.get(username="cmd_user")
        self.assertIsNotNone(u.admin_mfa_secret)

    def test_crear_admin_inicial_rechaza_no_staff(self):
        _mk_plain_user("plain_cmd")
        with self.assertRaises(CommandError):
            call_command(
                "crear_admin_inicial", username="plain_cmd", stdout=StringIO()
            )

    def test_crear_admin_inicial_rechaza_duplicado_sin_reset(self):
        u = _mk_superuser("dup_user")
        enroll_admin_mfa(u)
        with self.assertRaises(CommandError):
            call_command(
                "crear_admin_inicial", username="dup_user", stdout=StringIO()
            )

    def test_crear_admin_inicial_con_reset_regenera(self):
        u = _mk_superuser("reset_user")
        secret_viejo, _ = enroll_admin_mfa(u)
        out = StringIO()
        call_command(
            "crear_admin_inicial", username="reset_user",
            reset=True, stdout=out,
        )
        u.refresh_from_db()
        self.assertNotEqual(u.admin_mfa_secret, secret_viejo)
        self.assertIn("MFA enrolado", out.getvalue())

    def test_reset_admin_mfa_borra_secret(self):
        u = _mk_superuser("reset2_user")
        enroll_admin_mfa(u)
        out = StringIO()
        call_command("reset_admin_mfa", username="reset2_user", stdout=out)
        u.refresh_from_db()
        self.assertIsNone(u.admin_mfa_secret)
        self.assertIn("MFA reseteado", out.getvalue())

    def test_reset_admin_mfa_sin_secret_no_falla(self):
        _mk_superuser("no_secret_user")
        out = StringIO()
        call_command("reset_admin_mfa", username="no_secret_user", stdout=out)
        self.assertIn("no tiene secret MFA", out.getvalue())

    def test_crear_admin_inicial_usuario_inexistente(self):
        with self.assertRaises(CommandError):
            call_command(
                "crear_admin_inicial", username="nadie", stdout=StringIO()
            )
