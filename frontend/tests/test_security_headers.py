"""Tests de F4.e — CSP + headers de seguridad.

Verifican que todas las respuestas relevantes llevan:
- Content-Security-Policy restrictiva
- X-Content-Type-Options: nosniff
- Referrer-Policy
- Permissions-Policy
"""
from django.conf import settings
from django.test import TestCase, Client


class SecurityHeadersTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_csp_en_home(self):
        r = self.client.get("/")
        csp = r.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_csp_en_panel_login(self):
        r = self.client.get("/panel/login/")
        csp = r.get("Content-Security-Policy", "")
        self.assertIn("frame-ancestors 'none'", csp)

    def test_csp_en_admin_login(self):
        r = self.client.get(f"/{self.slug}/login/")
        csp = r.get("Content-Security-Policy", "")
        self.assertIn("frame-ancestors 'none'", csp)

    def test_csp_en_404_admin(self):
        # /admin/ → 404 también debe llevar CSP (viene del middleware
        # que se ejecuta antes del 404)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 404)
        csp = r.get("Content-Security-Policy", "")
        self.assertIn("frame-ancestors 'none'", csp)

    def test_x_content_type_options(self):
        r = self.client.get("/")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_referrer_policy(self):
        r = self.client.get("/")
        self.assertEqual(
            r["Referrer-Policy"], "strict-origin-when-cross-origin",
        )

    def test_permissions_policy(self):
        r = self.client.get("/")
        pp = r.get("Permissions-Policy", "")
        self.assertIn("geolocation=()", pp)
        self.assertIn("microphone=()", pp)
        self.assertIn("camera=()", pp)

    def test_x_frame_options_deny(self):
        r = self.client.get("/")
        self.assertEqual(r.get("X-Frame-Options"), "DENY")

    def test_csp_no_permite_frame(self):
        r = self.client.get("/")
        csp = r.get("Content-Security-Policy", "")
        # No debe permitir frame-ancestors desde ningún origen
        self.assertNotIn("frame-ancestors *", csp)
        self.assertNotIn("frame-ancestors 'self'", csp)
