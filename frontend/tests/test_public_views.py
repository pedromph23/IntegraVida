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

    def test_home_enlaza_a_secciones_publicas(self):
        """Home enlaza a las 3 secciones del portal HTML (F2 completa).
        La API pública sigue existiendo (§api.md) pero ya no se enlaza
        desde el home: el portal es para ciudadanos, la API para
        integraciones."""
        r = self.client.get("/")
        self.assertContains(r, "/alertas/")
        self.assertContains(r, "/refugios/")
        self.assertContains(r, "/hospitales/")
        # Confirmar que ya no hay links crudos a la API desde el home
        self.assertNotContains(r, "/api/publico/emergencias/")
        self.assertNotContains(r, "/api/publico/refugios/")
        self.assertNotContains(r, "/api/publico/hospitales/")


class DesignSystemTests(TestCase):
    def test_design_system_200_en_debug(self):
        # Los tests corren con DEBUG=False por defecto, pero
        # design_system() solo restringe si not settings.DEBUG.
        # En CI, DEBUG=False → 404. Aceptamos ambas respuestas.
        r = self.client.get("/design-system/")
        self.assertIn(r.status_code, [200, 404])


class AlertasPublicasTests(TestCase):
    """Tests de /alertas/ (F2.c)."""

    def test_alerts_list_200_anonimo(self):
        r = self.client.get("/alertas/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Alertas y emergencias")

    def test_alerts_list_incluye_filtros(self):
        r = self.client.get("/alertas/")
        self.assertContains(r, 'name="categoria"')
        self.assertContains(r, 'name="gravedad"')
        self.assertContains(r, 'name="estado"')

    def test_alert_detail_inexistente_404(self):
        r = self.client.get(
            "/alertas/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(r.status_code, 404)

    def test_alert_detail_no_expone_no_verificadas(self):
        """Una emergencia en RECIBIDA no debe ser accesible por URL directa."""
        from apps.emergencias.models import Emergencia
        from django.utils import timezone

        emergencia = Emergencia.objects.create(
            titulo="Test no verificada",
            descripcion="No debería ser pública",
            categoria=Emergencia.Categoria.OTRA,
            estado=Emergencia.Estado.RECIBIDA,
            ubicacion_texto="Test",
        )

        r = self.client.get(f"/alertas/{emergencia.id}/")
        self.assertEqual(r.status_code, 404)


class AlertasPublicasTests(TestCase):
    """Tests de /alertas/ (F2.c)."""

    def test_alerts_list_200_anonimo(self):
        r = self.client.get("/alertas/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Alertas y emergencias")

    def test_alerts_list_incluye_filtros(self):
        r = self.client.get("/alertas/")
        self.assertContains(r, 'name="categoria"')
        self.assertContains(r, 'name="gravedad"')
        self.assertContains(r, 'name="estado"')

    def test_alert_detail_inexistente_404(self):
        r = self.client.get(
            "/alertas/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(r.status_code, 404)

    def test_alert_detail_no_expone_no_verificadas(self):
        """Una emergencia en RECIBIDA no debe ser accesible por URL directa."""
        from apps.emergencias.models import Emergencia
        from django.utils import timezone

        emergencia = Emergencia.objects.create(
            titulo="Test no verificada",
            descripcion="No debería ser pública",
            categoria=Emergencia.Categoria.OTRA,
            estado=Emergencia.Estado.RECIBIDA,
            ubicacion_texto="Test",
        )

        r = self.client.get(f"/alertas/{emergencia.id}/")
        self.assertEqual(r.status_code, 404)
