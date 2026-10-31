"""Tests de Fase 10.3 — migración piloto con fixtures."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.configuracion.models import ReferenciaMigracion
from apps.inventario.models import Insumo
from apps.organizaciones.models import Organizacion
from apps.refugios.models import Refugio

Usuario = get_user_model()

FIXTURE_COBIJO = "data/fixtures/cobijo_vzla_refugios.json"
FIXTURE_NUTRI = "data/fixtures/nutrilink_supplies.json"


def _org(slug="mig-org"):
    return Organizacion.objects.create(
        nombre=f"Org {slug}", tipo=Organizacion.Tipo.ONG,
        codigo=slug, estado=Organizacion.Estado.ACTIVA,
    )


def _admin():
    return Usuario.objects.create_user(
        username="mig-admin", email="mig-admin@test.local",
        password="x", is_superuser=True,
    )


class CobijoVzlaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = _admin()
        cls.org = _org("cob")

    def _ejecutar(self):
        out = StringIO()
        call_command(
            "migrate_cobijo_vzla",
            fixture=FIXTURE_COBIJO,
            organizacion=str(self.org.pk),
            stdout=out,
        )
        return out.getvalue()

    def test_migracion_crea_refugios(self):
        self._ejecutar()
        self.assertEqual(Refugio.objects.count(), 3)

    def test_migracion_crea_referencias(self):
        self._ejecutar()
        self.assertEqual(
            ReferenciaMigracion.objects.filter(
                sistema_origen=ReferenciaMigracion.SistemaOrigen.COBIJO_VZLA,
            ).count(),
            3,
        )

    def test_migracion_mapea_capacidad_correctamente(self):
        self._ejecutar()
        r = Refugio.objects.get(codigo="cobijo-ref-001")
        self.assertEqual(r.capacidad_total, 120)
        self.assertEqual(r.ocupacion_actual, 90)
        self.assertEqual(r.estado_operativo, Refugio.EstadoOperativo.ACTIVO)

    def test_migracion_marca_inactivo_si_operativo_false(self):
        self._ejecutar()
        r = Refugio.objects.get(codigo="cobijo-ref-003")
        self.assertEqual(r.estado_operativo, Refugio.EstadoOperativo.INACTIVO)

    def test_idempotencia_no_duplica(self):
        self._ejecutar()
        self._ejecutar()
        self.assertEqual(Refugio.objects.count(), 3)
        self.assertEqual(ReferenciaMigracion.objects.count(), 3)

    def test_hash_origen_se_guarda(self):
        self._ejecutar()
        ref = ReferenciaMigracion.objects.first()
        self.assertEqual(len(ref.hash_origen), 64)
        self.assertEqual(ref.resultado_validacion, "VALIDADO")
        self.assertIsNotNone(ref.identificador_destino)


class NutrilinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = _admin()
        cls.org = _org("nut")

    def _ejecutar(self):
        out = StringIO()
        call_command(
            "migrate_nutrilink",
            fixture=FIXTURE_NUTRI,
            organizacion=str(self.org.pk),
            stdout=out,
        )
        return out.getvalue()

    def test_migracion_crea_insumos(self):
        self._ejecutar()
        self.assertEqual(Insumo.objects.count(), 5)

    def test_mapeo_alimento_a_alimento(self):
        self._ejecutar()
        r = Insumo.objects.get(codigo="nutrilink-ali-001")
        self.assertEqual(r.categoria, Insumo.Categoria.ALIMENTO)
        self.assertEqual(r.unidad_medida, Insumo.UnidadMedida.KILOGRAMO)
        self.assertFalse(r.requiere_vencimiento)

    def test_mapeo_medico_a_medicina_con_vencimiento(self):
        self._ejecutar()
        r = Insumo.objects.get(codigo="nutrilink-med-001")
        self.assertEqual(r.categoria, Insumo.Categoria.MEDICINA)
        self.assertTrue(r.requiere_vencimiento)
        self.assertTrue(r.requiere_lote)
        self.assertEqual(r.vida_util_dias, 1095)

    def test_idempotencia(self):
        self._ejecutar()
        self._ejecutar()
        self.assertEqual(Insumo.objects.count(), 5)
        self.assertEqual(
            ReferenciaMigracion.objects.filter(
                sistema_origen=ReferenciaMigracion.SistemaOrigen.NUTRILINK,
            ).count(),
            5,
        )

    def test_todos_validados_sin_advertencias(self):
        self._ejecutar()
        self.assertEqual(
            ReferenciaMigracion.objects.filter(
                resultado_validacion="CON_ADVERTENCIA",
            ).count(),
            0,
        )
