#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/inventario/tests_entregas.py << 'EOF'
"""Tests de Fase 8.3.2 — Entregas a refugios/hospitales."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import Hospital
from apps.inventario.models import (
    Almacen, DetalleEntrega, Entrega, Insumo, Lote, Movimiento,
    Stock, TransicionEntrega,
)
from apps.inventario.services import (
    cancelar_entrega, crear_entrega, enviar_entrega, recibir_entrega,
)
from apps.organizaciones.models import Membresia, Organizacion
from apps.refugios.models import Refugio

Usuario = get_user_model()


def _setup(slug):
    org = Organizacion.objects.create(
        nombre=f"Org {slug}", tipo=Organizacion.Tipo.ONG,
        codigo=f"org-{slug}", estado=Organizacion.Estado.ACTIVA,
    )
    h = Hospital.objects.create(
        codigo=f"h-{slug}", nombre="H",
        tipo=Hospital.Tipo.HOSPITAL, nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org, direccion="x",
    )
    almacen = Almacen.objects.create(
        codigo=f"alm-{slug}", nombre="Almacén", organizacion=org, hospital=h,
    )
    refugio = Refugio.objects.create(
        codigo=f"ref-{slug}", nombre="Refugio destino",
        organizacion=org, direccion="y", capacidad_total=50,
    )
    user = Usuario.objects.create_user(
        username=f"u-{slug}", email=f"u-{slug}@test.local", password="x",
    )
    Membresia.objects.create(
        usuario=user, organizacion=org,
        rol=Membresia.Rol.LOGISTICA, estado=Membresia.Estado.ACTIVA,
    )
    insumo = Insumo.objects.create(
        codigo=f"ins-{slug}", nombre="Med",
        categoria=Insumo.Categoria.MEDICINA,
        unidad_medida=Insumo.UnidadMedida.UNIDAD,
        requiere_lote=True, requiere_vencimiento=True,
    )
    lote = Lote.objects.create(
        insumo=insumo, codigo=f"L-{slug}",
        fecha_vencimiento=date.today() + timedelta(days=180),
    )
    stock = Stock.objects.create(
        almacen=almacen, lote=lote, cantidad=Decimal("50"),
    )
    return {
        "org": org, "almacen": almacen, "refugio": refugio,
        "user": user, "insumo": insumo, "lote": lote, "stock": stock,
    }


class CrearEntregaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = _setup("ce")

    def test_crear_a_refugio(self):
        e = crear_entrega(
            codigo="e-001",
            almacen_origen=self.s["almacen"],
            refugio=self.s["refugio"],
            motivo="Dotación mensual",
            detalles=[{
                "insumo": self.s["insumo"],
                "lote": self.s["lote"],
                "cantidad": Decimal("10"),
            }],
            usuario=self.s["user"],
        )
        self.assertEqual(e.estado, Entrega.Estado.BORRADOR)
        self.assertEqual(e.refugio, self.s["refugio"])
        self.assertEqual(e.detalles.count(), 1)

    def test_crear_a_texto_externo(self):
        e = crear_entrega(
            codigo="e-002",
            almacen_origen=self.s["almacen"],
            destinatario_texto="Comunidad El Valle",
            motivo="Ayuda directa",
            detalles=[{
                "insumo": self.s["insumo"],
                "lote": self.s["lote"],
                "cantidad": Decimal("5"),
            }],
            usuario=self.s["user"],
        )
        self.assertEqual(e.destinatario_texto, "Comunidad El Valle")

    def test_sin_destino_falla(self):
        with self.assertRaises(ValidationError):
            crear_entrega(
                codigo="e-003",
                almacen_origen=self.s["almacen"],
                motivo="x",
                detalles=[{
                    "insumo": self.s["insumo"],
                    "lote": self.s["lote"],
                    "cantidad": Decimal("5"),
                }],
                usuario=self.s["user"],
            )

    def test_refugio_y_hospital_falla(self):
        from apps.hospitales.models import Hospital as H
        h = H.objects.filter(codigo="h-ce").first()
        with self.assertRaises(ValidationError):
            crear_entrega(
                codigo="e-004",
                almacen_origen=self.s["almacen"],
                refugio=self.s["refugio"],
                hospital=h,
                motivo="x",
                detalles=[{
                    "insumo": self.s["insumo"],
                    "lote": self.s["lote"],
                    "cantidad": Decimal("5"),
                }],
                usuario=self.s["user"],
            )

    def test_sin_motivo_falla(self):
        with self.assertRaises(ValidationError):
            crear_entrega(
                codigo="e-005",
                almacen_origen=self.s["almacen"],
                refugio=self.s["refugio"],
                motivo="",
                detalles=[{
                    "insumo": self.s["insumo"],
                    "lote": self.s["lote"],
                    "cantidad": Decimal("5"),
                }],
                usuario=self.s["user"],
            )


class FlujoEntregaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = _setup("fe")

    def _crear(self):
        return crear_entrega(
            codigo="e-flujo",
            almacen_origen=self.s["almacen"],
            refugio=self.s["refugio"],
            motivo="Test",
            detalles=[{
                "insumo": self.s["insumo"],
                "lote": self.s["lote"],
                "cantidad": Decimal("10"),
            }],
            usuario=self.s["user"],
        )

    def test_flujo_completo(self):
        e = self._crear()
        enviar_entrega(entrega_id=e.pk, usuario=self.s["user"])
        self.s["stock"].refresh_from_db()
        self.assertEqual(self.s["stock"].cantidad, Decimal("40.000"))
        recibir_entrega(entrega_id=e.pk, usuario=self.s["user"])
        e.refresh_from_db()
        self.assertEqual(e.estado, Entrega.Estado.RECIBIDA)

    def test_envio_sin_stock_falla(self):
        e = self._crear()
        self.s["stock"].cantidad = Decimal("5")
        self.s["stock"].save()
        with self.assertRaises(ValidationError):
            enviar_entrega(entrega_id=e.pk, usuario=self.s["user"])
        self.s["stock"].refresh_from_db()
        self.assertEqual(self.s["stock"].cantidad, Decimal("5.000"))

    def test_recibir_borrador_falla(self):
        e = self._crear()
        with self.assertRaises(ValidationError):
            recibir_entrega(entrega_id=e.pk, usuario=self.s["user"])

    def test_cancelar_borrador_sin_movimiento(self):
        e = self._crear()
        cancelar_entrega(
            entrega_id=e.pk, usuario=self.s["user"], motivo="No requerido",
        )
        self.s["stock"].refresh_from_db()
        self.assertEqual(self.s["stock"].cantidad, Decimal("50.000"))
        e.refresh_from_db()
        self.assertEqual(e.estado, Entrega.Estado.CANCELADA)

    def test_cancelar_enviada_restaura_stock(self):
        e = self._crear()
        enviar_entrega(entrega_id=e.pk, usuario=self.s["user"])
        self.s["stock"].refresh_from_db()
        self.assertEqual(self.s["stock"].cantidad, Decimal("40.000"))
        cancelar_entrega(
            entrega_id=e.pk, usuario=self.s["user"],
            motivo="Devuelto por destinatario",
        )
        self.s["stock"].refresh_from_db()
        self.assertEqual(self.s["stock"].cantidad, Decimal("50.000"))

    def test_recibir_cancelada_falla(self):
        e = self._crear()
        cancelar_entrega(entrega_id=e.pk, usuario=self.s["user"])
        with self.assertRaises(ValidationError):
            recibir_entrega(entrega_id=e.pk, usuario=self.s["user"])

    def test_recibida_es_terminal(self):
        e = self._crear()
        enviar_entrega(entrega_id=e.pk, usuario=self.s["user"])
        recibir_entrega(entrega_id=e.pk, usuario=self.s["user"])
        with self.assertRaises(ValidationError):
            cancelar_entrega(entrega_id=e.pk, usuario=self.s["user"])

    def test_transiciones_auditadas(self):
        e = self._crear()
        enviar_entrega(entrega_id=e.pk, usuario=self.s["user"])
        recibir_entrega(entrega_id=e.pk, usuario=self.s["user"])
        self.assertEqual(
            TransicionEntrega.objects.filter(entrega=e).count(),
            3,  # BORRADOR inicial + ENVIADA + RECIBIDA
        )
        self.assertGreaterEqual(
            EventoAuditoria.objects.filter(
                tipo_objeto="Entrega", objeto_id=str(e.id),
            ).count(),
            3,
        )
EOF

# Admin
cat >> apps/inventario/admin.py << 'EOF'


# ── Entregas ──────────────────────────────────────────────────────

from apps.inventario.models import (
    DetalleEntrega, Entrega, TransicionEntrega,
)


class DetalleEntregaInline(admin.TabularInline):
    model = DetalleEntrega
    extra = 0
    autocomplete_fields = ("insumo", "lote")
    fields = ("insumo", "lote", "cantidad", "cantidad_entregada")
    readonly_fields = ("cantidad_entregada",)


class TransicionEntregaInline(admin.TabularInline):
    model = TransicionEntrega
    extra = 0
    can_delete = False
    fields = ("estado_anterior", "estado_nuevo", "usuario", "motivo", "creado_en")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "almacen_origen", "refugio", "hospital",
        "destinatario_texto", "estado", "solicitada_en",
    )
    list_filter = ("estado", "almacen_origen")
    search_fields = ("codigo", "motivo", "destinatario_texto")
    readonly_fields = (
        "id", "solicitada_en", "enviada_en", "recibida_en",
        "creado_en", "actualizado_en",
    )
    inlines = [DetalleEntregaInline, TransicionEntregaInline]
    date_hierarchy = "solicitada_en"

    def has_add_permission(self, request):
        return False


@admin.register(TransicionEntrega)
class TransicionEntregaAdmin(admin.ModelAdmin):
    list_display = (
        "entrega", "estado_anterior", "estado_nuevo", "usuario", "creado_en",
    )
    readonly_fields = (
        "id", "entrega", "estado_anterior", "estado_nuevo",
        "usuario", "motivo", "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
EOF

echo "OK: admin + tests_entregas.py (13 tests)"
