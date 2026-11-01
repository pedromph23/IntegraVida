"""Tests de F4.a — Ocultamiento del admin (§7.1, §7.3).

Scope de F4.a:
- /admin/ y sub-paths → 404 directo (no 302, no 403, no login)
- /<slug>/ → admin Django (302 a login por ahora; MFA en F4.b)
- Headers X-Robots-Tag + Cache-Control en /<slug>/*
- /robots.txt con Disallow: /<slug>/
- NO se aplican headers del admin en /panel/ ni en portal público
"""
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse


class Admin404Tests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_admin_root_404(self):
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 404)

    def test_admin_login_404(self):
        r = self.client.get("/admin/login/")
        self.assertEqual(r.status_code, 404)

    def test_admin_cualquier_subpath_404(self):
        r = self.client.get("/admin/anything/else/here/")
        self.assertEqual(r.status_code, 404)

    def test_admin_404_no_redirect(self):
        # Ningún 3xx — el 404 es directo
        r = self.client.get("/admin/")
        self.assertNotIn(r.status_code, (301, 302))


class AdminSlugTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_slug_root_no_es_404(self):
        r = self.client.get(f"/{self.slug}/")
        self.assertNotEqual(r.status_code, 404)

    def test_slug_login_accesible(self):
        r = self.client.get(f"/{self.slug}/login/")
        self.assertEqual(r.status_code, 200)

    def test_slug_headers_noindex(self):
        r = self.client.get(f"/{self.slug}/login/")
        self.assertEqual(
            r.get("X-Robots-Tag"),
            "noindex, nofollow, noarchive",
        )

    def test_slug_headers_no_store(self):
        r = self.client.get(f"/{self.slug}/login/")
        cache = r.get("Cache-Control", "")
        self.assertIn("no-store", cache)

    def test_slug_x_frame_options_deny(self):
        r = self.client.get(f"/{self.slug}/login/")
        self.assertEqual(r.get("X-Frame-Options"), "DENY")


class PortalSinHeadersAdminTests(TestCase):
    """El portal y panel NO deben tener headers de ocultamiento."""

    def setUp(self):
        self.client = Client()

    def test_portal_no_tiene_x_robots_tag(self):
        r = self.client.get("/")
        self.assertIsNone(r.get("X-Robots-Tag"))

    def test_portal_no_tiene_no_store(self):
        # /panel/login/ tiene no-store por @never_cache de Django LoginView,
        # no por nuestro middleware. Verificamos sobre / (portal home),
        # que no lleva never_cache: no debe tener no-store.
        r = self.client.get("/")
        cache = r.get("Cache-Control", "")
        self.assertNotIn("no-store", cache)


class RobotsTxtTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_robots_txt_200(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/plain; charset=utf-8")

    def test_robots_txt_disallow_slug(self):
        r = self.client.get("/robots.txt")
        body = r.content.decode()
        self.assertIn(f"Disallow: /{self.slug}/", body)

    def test_robots_txt_disallow_admin(self):
        r = self.client.get("/robots.txt")
        body = r.content.decode()
        self.assertIn("Disallow: /admin/", body)

    def test_robots_txt_disallow_panel(self):
        r = self.client.get("/robots.txt")
        body = r.content.decode()
        self.assertIn("Disallow: /panel/", body)

    def test_robots_txt_allow_root(self):
        r = self.client.get("/robots.txt")
        body = r.content.decode()
        self.assertIn("Allow: /", body)


class SlugNoPredecibleTests(TestCase):
    def test_slug_no_es_prohibido(self):
        slug = settings.INTEGRAVIDA_ADMIN_SLUG
        prohibidos = {"admin", "administracion", "panel", "gestion", "staff"}
        self.assertNotIn(slug, prohibidos)

    def test_slug_minimo_8_chars(self):
        # El fallback dev es "dev-admin-fallback"; en prod debe ser 24+
        slug = settings.INTEGRAVIDA_ADMIN_SLUG
        self.assertGreaterEqual(len(slug), 8)
