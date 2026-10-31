"""Tests de Fase 10.1 — ReferenciaMigracion."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.configuracion.models import ReferenciaMigracion

Usuario = get_user_model()


class ReferenciaMigracionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Usuario.objects.create_user(
            username="mig-u", email="mig-u@test.local", password="x",
        )

    def _crear(self, sistema="COBIJO_VZLA", entidad="refugios", ident="REF-001"):
        return ReferenciaMigracion.objects.create(
            sistema_origen=sistema,
            entidad_origen=entidad,
            identificador_origen=ident,
            entidad_destino="refugios.Refugio",
            migrado_por=self.user,
        )

    def test_crear_valida(self):
        r = self._crear()
        self.assertEqual(
            r.resultado_validacion,
            ReferenciaMigracion.ResultadoValidacion.PENDIENTE,
        )
        self.assertEqual(
            r.sistema_origen,
            ReferenciaMigracion.SistemaOrigen.COBIJO_VZLA,
        )

    def test_unique_sistema_entidad_identificador(self):
        self._crear()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._crear()

    def test_mismo_ident_distinto_sistema_ok(self):
        self._crear(sistema="COBIJO_VZLA", entidad="refugios", ident="REF-1")
        r2 = self._crear(sistema="NUTRILINK", entidad="refugios", ident="REF-1")
        self.assertIsNotNone(r2.pk)

    def test_mismo_ident_distinta_entidad_ok(self):
        self._crear(entidad="refugios", ident="X-1")
        r2 = self._crear(entidad="insumos", ident="X-1")
        self.assertIsNotNone(r2.pk)

    def test_identificador_destino_nullable(self):
        r = self._crear()
        self.assertIsNone(r.identificador_destino)

    def test_resultado_pendiente_por_defecto(self):
        r = self._crear()
        self.assertEqual(r.resultado_validacion, "PENDIENTE")

    def test_actualizar_validacion(self):
        r = self._crear()
        r.resultado_validacion = (
            ReferenciaMigracion.ResultadoValidacion.VALIDADO
        )
        r.identificador_destino = "00000000-0000-0000-0000-000000000001"
        r.save()
        r.refresh_from_db()
        self.assertEqual(r.resultado_validacion, "VALIDADO")
        self.assertIsNotNone(r.identificador_destino)


# ══════════════════════════════════════════════════════════════════
# Landing page + health check (Fase 11.4)
# ══════════════════════════════════════════════════════════════════

from django.test import TestCase as DjangoTestCase
from django.urls import reverse


class LandingPageTests(DjangoTestCase):
    def test_index_devuelve_200(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "IntegraVida")
        self.assertContains(r, "API pública")

    def test_index_incluye_links_a_endpoints_publicos(self):
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        self.assertContains(r, "/api/publico/hospitales/")

    def test_health_check_devuelve_ok(self):
        r = self.client.get("/health/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "integravida")
