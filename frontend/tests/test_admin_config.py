"""Tests de F4.d — Configuración del admin custom."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.services import enroll_admin_mfa


User = get_user_model()


def _mk_superuser(username="admin", password="test-pass-123!"):
    return User.objects.create_superuser(username=username, password=password)


def _mk_plain(username="plain", password="test-pass-123!"):
    return User.objects.create_user(username=username, password=password)


def _mfa_session(client, user):
    s = client.session
    s["admin_mfa_verified_at"] = timezone.now().timestamp()
    s["admin_mfa_user_id"] = str(user.pk)
    s.save()


class ConfigAnonimoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_anonimo_va_a_login_admin(self):
        r = self.client.get(reverse("admin_custom:admin_config"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(f"/{self.slug}/login/", r["Location"])
        self.assertNotIn("/panel/login/", r["Location"])


class ConfigNoStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_plain("plain_cfg")
        self.client = Client()
        self.client.login(username="plain_cfg", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_no_staff_403(self):
        r = self.client.get(reverse("admin_custom:admin_config"))
        self.assertEqual(r.status_code, 403)


class ConfigStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_superuser("cfg_admin")
        enroll_admin_mfa(self.user)
        self.client = Client()
        self.client.login(username="cfg_admin", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_renders_200(self):
        r = self.client.get(reverse("admin_custom:admin_config"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Configuración")

    def test_muestra_info_sistema(self):
        r = self.client.get(reverse("admin_custom:admin_config"))
        body = r.content.decode()
        self.assertIn("Django", body)
        self.assertIn("DEBUG", body)
        self.assertIn("Slug del admin", body)
        self.assertIn("Vigencia MFA", body)

    def test_slug_length_sin_valor(self):
        r = self.client.get(reverse("admin_custom:admin_config"))
        body = r.content.decode()
        slug = settings.INTEGRAVIDA_ADMIN_SLUG
        # Longitud aparece
        self.assertIn(f"{len(slug)} caracteres", body)
        # Valor oculto (el slug sí aparece en <a href> de admin:index,
        # pero no como texto plano en el card del slug)
        self.assertIn("valor oculto por seguridad", body)

    def test_headers_anti_index(self):
        r = self.client.get(reverse("admin_custom:admin_config"))
        self.assertEqual(r["X-Robots-Tag"], "noindex, nofollow, noarchive")
        self.assertIn("no-store", r.get("Cache-Control", ""))
