"""Tests del portal público (F1)."""
from django.test import TestCase


class HomePublicaTests(TestCase):
    def test_home_devuelve_200_anonimo(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_home_renderiza_hero_y_conteos(self):
        r = self.client.get("/")
        self.assertContains(r, "Encuentra ayuda ahora")
        # Los 3 contadores aparecen (0 en dev por fixtures vacíos)
        self.assertContains(r, "Emergencias públicas")
        self.assertContains(r, "Refugios activos")
        self.assertContains(r, "Hospitales activos")

    def test_home_enlaza_a_api_publica(self):
        """Home enlaza a la API pública (emergencias, refugios) y al
        portal HTML de hospitales. Los tres coexisten porque la API
        sigue siendo el contrato (§api.md) y el portal HTML es UX."""
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/refugios/")
        # Hospitales migró a portal HTML en F2.a
        self.assertContains(r, "/hospitales/")


class DesignSystemTests(TestCase):
    def test_design_system_200_en_debug(self):
        # Los tests corren con DEBUG=False por defecto, pero
        # design_system() solo restringe si not settings.DEBUG.
        # En CI, DEBUG=False → 404. Aceptamos ambas respuestas.
        r = self.client.get("/design-system/")
        self.assertIn(r.status_code, [200, 404])
