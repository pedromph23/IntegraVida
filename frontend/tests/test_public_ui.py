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
        r = self.client.get("/")
        body = r.content.decode()
        self.assertIn("© 2026 IntegraVida", body)
        self.assertIn("Todos los derechos reservados", body)

    def test_footer_tiene_emergencias(self):
        r = self.client.get("/")
        body = r.content.decode()
        self.assertIn("tel:911", body)
        self.assertIn("tel:171", body)
        self.assertIn("Emergencias", body)

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
        r = self.client.get("/")
        body = r.content.decode()
        self.assertIn("contacto@integravida.org", body)
        self.assertIn("wa.me/", body)
        self.assertIn("x.com/integravida", body)
        self.assertIn("instagram.com/integravida", body)
        self.assertIn("t.me/integravida", body)

    def test_footer_en_paginas_publicas(self):
        # El footer debe aparecer en todas las páginas públicas
        for path in ("/", "/hospitales/", "/refugios/", "/alertas/"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, f"Fallo en {path}")
            self.assertContains(r, "© 2026 IntegraVida")

    def test_footer_no_en_panel(self):
        # El footer es solo del portal público
        r = self.client.get("/panel/login/")
        body = r.content.decode()
        self.assertNotIn("© 2026 IntegraVida", body)
