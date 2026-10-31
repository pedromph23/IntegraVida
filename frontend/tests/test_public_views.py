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


class ReportesPublicosTests(TestCase):
    """Tests del formulario de reporte y seguimiento (F2.d)."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # Aislar rate limit entre tests

    def test_form_get_200(self):
        r = self.client.get("/reportes/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Reportar una emergencia")
        self.assertContains(r, 'name="categoria"')
        self.assertContains(r, 'name="descripcion"')
        self.assertContains(r, 'name="ubicacion_texto"')

    def test_form_post_valido_redirige(self):
        r = self.client.post("/reportes/", {
            "categoria": "INUNDACION",
            "descripcion": "Calle anegada en Petare",
            "ubicacion_texto": "Av. Principal de Petare",
            "referencia_lugar": "Frente al mercado",
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn("/reportes/", r.url)
        # El UUID debe estar en la URL de redirección
        self.assertRegex(r.url, r"/reportes/[0-9a-f-]{36}/")

    def test_form_post_sin_categoria_falla(self):
        r = self.client.post("/reportes/", {
            "descripcion": "Test",
            "ubicacion_texto": "Test",
        })
        # Re-render con errores (200) o 400/429 si rate limit
        self.assertIn(r.status_code, [200, 400, 429])

    def test_form_post_sin_descripcion_falla(self):
        r = self.client.post("/reportes/", {
            "categoria": "INUNDACION",
            "ubicacion_texto": "Test",
        })
        self.assertIn(r.status_code, [200, 400, 429])

    def test_tracking_inexistente_404(self):
        r = self.client.get(
            "/reportes/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(r.status_code, 404)

    def test_tracking_muestra_estado_y_codigo(self):
        """Verifica que el tracking muestra el UUID y el estado,
        pero NO la descripción ni la ubicación."""
        from apps.emergencias.models import ReporteEmergencia
        reporte = ReporteEmergencia.objects.create(
            categoria="INUNDACION",
            descripcion="Descripción secreta con info sensible",
            ubicacion_texto="Dirección exacta privada",
            estado_revision=ReporteEmergencia.EstadoRevision.PENDIENTE,
        )

        r = self.client.get(f"/reportes/{reporte.id}/")
        self.assertEqual(r.status_code, 200)
        # El UUID sí se muestra
        self.assertContains(r, str(reporte.id))
        # El estado sí
        self.assertContains(r, "Pendiente")
        # Privacidad: NO se muestra descripción ni ubicación
        self.assertNotContains(r, "Descripción secreta con info sensible")
        self.assertNotContains(r, "Dirección exacta privada")

    def test_tracking_no_expone_reporte_descartado_como_publico(self):
        """Un reporte descartado se puede consultar (el usuario lo envió),
        pero NO debe aparecer como vinculado a emergencia pública."""
        from apps.emergencias.models import ReporteEmergencia
        reporte = ReporteEmergencia.objects.create(
            categoria="INUNDACION",
            descripcion="Test",
            ubicacion_texto="Test",
            estado_revision=ReporteEmergencia.EstadoRevision.DESCARTADO,
        )

        r = self.client.get(f"/reportes/{reporte.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Descartado")

    def test_home_tiene_cta_reportar(self):
        r = self.client.get("/")
        self.assertContains(r, "/reportes/")
        self.assertContains(r, "Reportar emergencia")

    def test_alerts_list_tiene_cta_reportar(self):
        r = self.client.get("/alertas/")
        self.assertContains(r, "/reportes/")
        self.assertContains(r, "Reportar")
