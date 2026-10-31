from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.hospitales.models import Hospital
from apps.inventario.models import Almacen, Insumo
from apps.organizaciones.models import Organizacion
from apps.refugios.models import Refugio

Usuario = get_user_model()


def _org(slug="inv-org"):
    return Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.ONG,
        codigo=slug,
        estado=Organizacion.Estado.ACTIVA,
    )


class InsumoModeloTests(TestCase):
    def test_crear_valido(self):
        i = Insumo.objects.create(
            codigo="med-001",
            nombre="Paracetamol 500mg",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True,
            requiere_vencimiento=True,
            vida_util_dias=365,
        )
        self.assertTrue(i.requiere_lote)
        self.assertTrue(i.requiere_vencimiento)
        self.assertTrue(i.activo)

    def test_codigo_unico(self):
        Insumo.objects.create(
            codigo="ali-001",
            nombre="Arroz",
            categoria=Insumo.Categoria.ALIMENTO,
            unidad_medida=Insumo.UnidadMedida.KILOGRAMO,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Insumo.objects.create(
                    codigo="ali-001",
                    nombre="Arroz duplicado",
                    categoria=Insumo.Categoria.ALIMENTO,
                    unidad_medida=Insumo.UnidadMedida.KILOGRAMO,
                )

    def test_vencimiento_requiere_lote(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Insumo.objects.create(
                    codigo="bad-001",
                    nombre="Sin lote pero vence",
                    categoria=Insumo.Categoria.MEDICINA,
                    unidad_medida=Insumo.UnidadMedida.UNIDAD,
                    requiere_lote=False,
                    requiere_vencimiento=True,
                )

    def test_sin_vencimiento_sin_lote_ok(self):
        i = Insumo.objects.create(
            codigo="agua-001",
            nombre="Agua embotellada",
            categoria=Insumo.Categoria.AGUA,
            unidad_medida=Insumo.UnidadMedida.LITRO,
            requiere_lote=False,
            requiere_vencimiento=False,
        )
        self.assertEqual(i.stock_minimo_global, Decimal("0"))

    def test_stock_minimo_decimal(self):
        i = Insumo.objects.create(
            codigo="dec-001",
            nombre="Test decimal",
            categoria=Insumo.Categoria.OTRO,
            unidad_medida=Insumo.UnidadMedida.GRAMO,
            stock_minimo_global=Decimal("12.345"),
        )
        self.assertEqual(i.stock_minimo_global, Decimal("12.345"))


class AlmacenModeloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("alm")
        cls.hospital = Hospital.objects.create(
            codigo="h-alm",
            nombre="H Almacen",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III,
            organizacion=cls.org,
            direccion="x",
        )
        cls.refugio = Refugio.objects.create(
            codigo="r-alm",
            nombre="R Almacen",
            organizacion=cls.org,
            direccion="y",
            capacidad_total=10,
        )

    def test_almacen_en_hospital(self):
        a = Almacen.objects.create(
            codigo="alm-h-1",
            nombre="Almacén H",
            organizacion=self.org,
            hospital=self.hospital,
        )
        self.assertEqual(a.tipo_ubicacion, "HOSPITAL")

    def test_almacen_en_refugio(self):
        a = Almacen.objects.create(
            codigo="alm-r-1",
            nombre="Almacén R",
            organizacion=self.org,
            refugio=self.refugio,
        )
        self.assertEqual(a.tipo_ubicacion, "REFUGIO")

    def test_almacen_independiente(self):
        a = Almacen.objects.create(
            codigo="alm-i-1",
            nombre="Centro de acopio",
            organizacion=self.org,
        )
        self.assertEqual(a.tipo_ubicacion, "INDEPENDIENTE")

    def test_almacen_con_ambos_falla(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Almacen.objects.create(
                    codigo="alm-bad",
                    nombre="Mal",
                    organizacion=self.org,
                    hospital=self.hospital,
                    refugio=self.refugio,
                )

    def test_codigo_unico(self):
        Almacen.objects.create(
            codigo="alm-u",
            nombre="Uno",
            organizacion=self.org,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Almacen.objects.create(
                    codigo="alm-u",
                    nombre="Dos",
                    organizacion=self.org,
                )
