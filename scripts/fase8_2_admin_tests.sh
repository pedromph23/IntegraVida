#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> apps/inventario/admin.py << 'EOF'


# ── Lote, Stock, Movimiento ──────────────────────────────────────

from apps.inventario.models import Lote, Movimiento, Stock


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ("almacen", "cantidad", "actualizado_en")
    readonly_fields = ("actualizado_en",)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        "insumo", "codigo", "fecha_vencimiento", "proveedor", "creado_en",
    )
    list_filter = ("insumo__categoria",)
    search_fields = ("insumo__nombre", "codigo", "proveedor")
    readonly_fields = ("id", "creado_en", "actualizado_en")
    inlines = [StockInline]


class MovimientoInline(admin.TabularInline):
    model = Movimiento
    extra = 0
    can_delete = False
    fields = (
        "tipo", "cantidad", "cantidad_anterior", "cantidad_nueva",
        "diferencia", "registrado_por", "creado_en",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("almacen", "lote", "cantidad", "actualizado_en")
    list_filter = ("almacen",)
    search_fields = ("almacen__nombre", "lote__codigo", "lote__insumo__nombre")
    readonly_fields = ("id", "actualizado_en")
    inlines = [MovimientoInline]


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        "stock", "tipo", "cantidad", "cantidad_anterior", "cantidad_nueva",
        "registrado_por", "creado_en",
    )
    list_filter = ("tipo",)
    search_fields = ("stock__lote__insumo__nombre", "referencia_id")
    readonly_fields = (
        "id", "stock", "tipo", "cantidad", "cantidad_anterior",
        "cantidad_nueva", "diferencia", "referencia_tipo", "referencia_id",
        "registrado_por", "notas", "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
EOF

cat > apps/inventario/tests_inventario.py << 'EOF'
"""Tests de Fase 8.2 — Lote, Stock, Movimiento, FEFO."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import Hospital
from apps.inventario.models import (
    Almacen, Insumo, Lote, Movimiento, NotAllowed, Stock,
)
from apps.inventario.services import (
    registrar_movimiento, seleccionar_stock_fefo,
)
from apps.organizaciones.models import Organizacion

Usuario = get_user_model()


def _setup(slug):
    org = Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.ONG,
        codigo=f"org-{slug}",
        estado=Organizacion.Estado.ACTIVA,
    )
    hospital = Hospital.objects.create(
        codigo=f"h-{slug}",
        nombre=f"H {slug}",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="x",
    )
    almacen = Almacen.objects.create(
        codigo=f"alm-{slug}",
        nombre=f"Almacén {slug}",
        organizacion=org,
        hospital=hospital,
    )
    usuario = Usuario.objects.create_user(
        username=f"u-{slug}", email=f"u-{slug}@test.local", password="x"
    )
    return org, almacen, usuario


class LoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.almacen, cls.usuario = _setup("lote")
        cls.insumo_a = Insumo.objects.create(
            codigo="ins-a", nombre="A",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True, requiere_vencimiento=True,
        )
        cls.insumo_b = Insumo.objects.create(
            codigo="ins-b", nombre="B",
            categoria=Insumo.Categoria.ALIMENTO,
            unidad_medida=Insumo.UnidadMedida.KILOGRAMO,
            requiere_lote=True, requiere_vencimiento=True,
        )

    def test_crear_valido(self):
        lote = Lote.objects.create(
            insumo=self.insumo_a, codigo="L-2024-001",
            fecha_vencimiento=date(2027, 1, 1),
        )
        self.assertEqual(lote.codigo, "L-2024-001")

    def test_unique_insumo_codigo(self):
        Lote.objects.create(insumo=self.insumo_a, codigo="L-UNICO")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Lote.objects.create(insumo=self.insumo_a, codigo="L-UNICO")

    def test_mismo_codigo_distinto_insumo_ok(self):
        Lote.objects.create(insumo=self.insumo_a, codigo="L-SHARED")
        lote_b = Lote.objects.create(insumo=self.insumo_b, codigo="L-SHARED")
        self.assertIsNotNone(lote_b.pk)


class StockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.almacen, cls.usuario = _setup("stock")
        cls.insumo = Insumo.objects.create(
            codigo="ins-s", nombre="S",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True,
        )
        cls.lote = Lote.objects.create(insumo=cls.insumo, codigo="L-S")

    def test_crear_stock_inicial(self):
        s = Stock.objects.create(
            almacen=self.almacen, lote=self.lote, cantidad=Decimal("0"),
        )
        self.assertEqual(s.cantidad, Decimal("0"))

    def test_unique_almacen_lote(self):
        Stock.objects.create(
            almacen=self.almacen, lote=self.lote, cantidad=Decimal("5"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Stock.objects.create(
                    almacen=self.almacen, lote=self.lote,
                    cantidad=Decimal("10"),
                )

    def test_cantidad_negativa_falla_db(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Stock.objects.create(
                    almacen=self.almacen, lote=self.lote,
                    cantidad=Decimal("-1"),
                )


class MovimientoInmutabilidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.almacen, cls.usuario = _setup("inm")
        cls.insumo = Insumo.objects.create(
            codigo="ins-i", nombre="I",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True,
        )
        cls.lote = Lote.objects.create(insumo=cls.insumo, codigo="L-I")
        cls.stock = Stock.objects.create(
            almacen=cls.almacen, lote=cls.lote, cantidad=Decimal("10"),
        )

    def test_movimiento_inmutable_update(self):
        mov = registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.SALIDA,
            cantidad=2,
            usuario=self.usuario,
        )
        mov.notas = "modificado"
        with self.assertRaises(NotAllowed):
            mov.save()

    def test_movimiento_inmutable_delete(self):
        mov = registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.SALIDA,
            cantidad=2,
            usuario=self.usuario,
        )
        with self.assertRaises(NotAllowed):
            mov.delete()


class RegistrarMovimientoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.almacen, cls.usuario = _setup("reg")
        cls.insumo = Insumo.objects.create(
            codigo="ins-r", nombre="R",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True,
        )
        cls.lote = Lote.objects.create(insumo=cls.insumo, codigo="L-R")
        cls.stock = Stock.objects.create(
            almacen=cls.almacen, lote=cls.lote, cantidad=Decimal("0"),
        )

    def test_entrada(self):
        mov = registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.ENTRADA,
            cantidad=10,
            usuario=self.usuario,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, Decimal("10.000"))
        self.assertEqual(mov.cantidad_anterior, Decimal("0.000"))
        self.assertEqual(mov.cantidad_nueva, Decimal("10.000"))
        self.assertEqual(mov.diferencia, Decimal("10.000"))

    def test_salida(self):
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.ENTRADA,
            cantidad=10,
            usuario=self.usuario,
        )
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.SALIDA,
            cantidad=3,
            usuario=self.usuario,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, Decimal("7.000"))

    def test_salida_sin_stock_falla(self):
        with self.assertRaises(ValidationError):
            registrar_movimiento(
                stock_id=self.stock.pk,
                tipo=Movimiento.Tipo.SALIDA,
                cantidad=5,
                usuario=self.usuario,
            )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, Decimal("0"))

    def test_ajuste_positivo(self):
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.ENTRADA,
            cantidad=10,
            usuario=self.usuario,
        )
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.AJUSTE,
            cantidad=2,
            usuario=self.usuario,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, Decimal("12.000"))

    def test_ajuste_negativo(self):
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.ENTRADA,
            cantidad=10,
            usuario=self.usuario,
        )
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.AJUSTE,
            cantidad=-3,
            usuario=self.usuario,
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, Decimal("7.000"))

    def test_audita_movimiento(self):
        registrar_movimiento(
            stock_id=self.stock.pk,
            tipo=Movimiento.Tipo.ENTRADA,
            cantidad=5,
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="inventario.movimiento_entrada"
            ).count(),
            1,
        )


class FEFOTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.almacen, cls.usuario = _setup("fefo")
        cls.insumo_perecedero = Insumo.objects.create(
            codigo="ins-per", nombre="Perecedero",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True, requiere_vencimiento=True,
        )
        cls.insumo_durable = Insumo.objects.create(
            codigo="ins-dur", nombre="Durable",
            categoria=Insumo.Categoria.AGUA,
            unidad_medida=Insumo.UnidadMedida.LITRO,
            requiere_lote=False, requiere_vencimiento=False,
        )
        hoy = date.today()
        cls.lote_vencido = Lote.objects.create(
            insumo=cls.insumo_perecedero, codigo="L-VENCIDO",
            fecha_vencimiento=hoy - timedelta(days=10),
        )
        cls.lote_cercano = Lote.objects.create(
            insumo=cls.insumo_perecedero, codigo="L-CERCA",
            fecha_vencimiento=hoy + timedelta(days=15),
        )
        cls.lote_lejano = Lote.objects.create(
            insumo=cls.insumo_perecedero, codigo="L-LEJOS",
            fecha_vencimiento=hoy + timedelta(days=180),
        )
        for lote, cant in [
            (cls.lote_vencido, "10"),
            (cls.lote_cercano, "10"),
            (cls.lote_lejano, "10"),
        ]:
            Stock.objects.create(
                almacen=cls.almacen, lote=lote, cantidad=Decimal(cant),
            )

    def test_fefo_elige_el_mas_cercano_a_vencer(self):
        stock = seleccionar_stock_fefo(
            insumo=self.insumo_perecedero,
            almacen=self.almacen,
            cantidad=5,
        )
        self.assertEqual(stock.lote, self.lote_cercano)

    def test_fefo_excluye_vencidos(self):
        stock = seleccionar_stock_fefo(
            insumo=self.insumo_perecedero,
            almacen=self.almacen,
            cantidad=5,
        )
        self.assertNotEqual(stock.lote, self.lote_vencido)

    def test_fefo_sin_stock_suficiente_devuelve_none(self):
        stock = seleccionar_stock_fefo(
            insumo=self.insumo_perecedero,
            almacen=self.almacen,
            cantidad=100,
        )
        self.assertIsNone(stock)

    def test_fefo_insumo_sin_vencimiento(self):
        lote_dur = Lote.objects.create(
            insumo=self.insumo_durable, codigo="L-DUR",
        )
        Stock.objects.create(
            almacen=self.almacen, lote=lote_dur, cantidad=Decimal("50"),
        )
        stock = seleccionar_stock_fefo(
            insumo=self.insumo_durable,
            almacen=self.almacen,
            cantidad=10,
        )
        self.assertEqual(stock.lote, lote_dur)
EOF

echo "OK: admin + 17 tests nuevos"
