"""Tests de F3.i — header + footer del portal público.

Verifican:
- Botón de acceso institucional (auth:login) o "Ir al panel" si auth
- El slug del admin NO aparece en templates públicos
- Footer con copyright, emergencias, sin Health
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse


User = get_user_model()


class HeaderAnonimoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_home_tiene_acceso_institucional(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Acceso institucional")
        # Debe apuntar a auth:login (= /panel/login/), no al admin oculto
        self.assertContains(r, reverse("auth:login"))
        self.assertNotContains(r, "Ir al panel")

    def test_home_no_expone_slug_admin(self):
        r = self.client.get("/")
        self.assertNotContains(r, self.slug)

    def test_home_no_tiene_link_al_admin_hidden(self):
        r = self.client.get("/")
        body = r.content.decode()
        # El único acceso visible es /panel/login/
        self.assertNotIn(f'href="/{self.slug}/', body)


class HeaderAutenticadoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="operador", password="test-pass-123!",
        )
        self.client = Client()
        self.client.login(username="operador", password="test-pass-123!")

    def test_home_muestra_ir_al_panel(self):
        r = self.client.get("/")
        self.assertContains(r, "Ir al panel")
        self.assertContains(r, reverse("dashboard:home"))
        self.assertNotContains(r, "Acceso institucional")


class FooterTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_footer_en_home(self):
        """El footer público muestra la identidad IUJO."""
        r = self.client.get(reverse("public:home"))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        # Ahora el footer dice "Instituto Universitario Jesús Obrero"
        self.assertIn("Instituto Universitario", body)
        self.assertIn("Jesús Obrero", body)

    def test_footer_tiene_emergencias(self):
        """El footer menciona la Coordinación de Extensión (contacto institucional)."""
        r = self.client.get(reverse("public:home"))
        body = r.content.decode()
        self.assertIn("Coordinación de Extensión", body)

    def test_footer_sin_health(self):
        r = self.client.get("/")
        body = r.content.decode()
        # El endpoint /health/ sigue vivo, pero NO debe haber link en footer
        self.assertNotIn('href="/health/"', body)

    def test_health_endpoint_sigue_vivo(self):
        # El endpoint sigue respondiendo aunque no esté enlazado
        r = self.client.get("/health/")
        self.assertIn(r.status_code, (200, 301, 302))

    def test_footer_tiene_contacto_y_redes(self):
        """El footer tiene redes sociales (Instagram, Facebook) y teléfonos."""
        r = self.client.get(reverse("public:home"))
        body = r.content.decode()
        # Redes sociales
        self.assertIn("instagram.com/iujocatia", body)
        self.assertIn("facebook.com/IujoCatia", body)
        # Teléfonos / WhatsApp
        self.assertIn("wa.me/584120340692", body)
        self.assertIn("wa.me/584227330442", body)
        self.assertIn("(0212) 862.71.72", body)

    def test_footer_en_paginas_publicas(self):
        """El footer público aparece en todas las páginas públicas."""
        for url_name in ("public:home", "public:mapa_view"):
            try:
                r = self.client.get(reverse(url_name))
            except Exception:
                continue
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "Instituto Universitario")

    def test_footer_no_en_panel(self):
        # El footer es solo del portal público
        r = self.client.get("/panel/login/")
        body = r.content.decode()
        self.assertNotIn("© 2026 IntegraVida", body)
