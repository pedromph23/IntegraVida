"""Tests de Fase 8.3.1 — Transferencias entre almacenes."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import Hospital
from apps.inventario.models import (
    Almacen, DetalleTransferencia, Insumo, Lote, Movimiento,
    Stock, Transferencia, TransicionTransferencia,
)
from apps.inventario.services import (
    cancelar_transferencia, crear_transferencia,
    despachar_transferencia, recibir_transferencia,
    transicionar_transferencia,
)
from apps.organizaciones.models import Membresia, Organizacion

Usuario = get_user_model()


def _setup(slug):
    org = Organizacion.objects.create(
        nombre=f"Org {slug}", tipo=Organizacion.Tipo.ONG,
        codigo=f"org-{slug}", estado=Organizacion.Estado.ACTIVA,
    )
    h1 = Hospital.objects.create(
        codigo=f"h1-{slug}", nombre="H1",
        tipo=Hospital.Tipo.HOSPITAL, nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org, direccion="x",
    )
    h2 = Hospital.objects.create(
        codigo=f"h2-{slug}", nombre="H2",
        tipo=Hospital.Tipo.HOSPITAL, nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org, direccion="y",
    )
    a1 = Almacen.objects.create(
        codigo=f"a1-{slug}", nombre="A1", organizacion=org, hospital=h1,
    )
    a2 = Almacen.objects.create(
        codigo=f"a2-{slug}", nombre="A2", organizacion=org, hospital=h2,
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
    stock1 = Stock.objects.create(
        almacen=a1, lote=lote, cantidad=Decimal("100"),
    )
    return {
        "org": org, "a1": a1, "a2": a2,
        "user": user, "insumo": insumo, "lote": lote, "stock1": stock1,
    }


class CrearTransferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = _setup("ct")

    def test_crear_valida(self):
        t = crear_transferencia(
            codigo="t-001",
            almacen_origen=self.s["a1"],
            almacen_destino=self.s["a2"],
            motivo="Rebalanceo",
            detalles=[{
                "insumo": self.s["insumo"],
                "lote_origen": self.s["lote"],
                "cantidad": Decimal("10"),
            }],
            usuario=self.s["user"],
        )
        self.assertEqual(t.estado, Transferencia.Estado.BORRADOR)
        self.assertEqual(t.detalles.count(), 1)
        self.assertEqual(TransicionTransferencia.objects.count(), 1)

    def test_origen_igual_destino_falla(self):
        with self.assertRaises(ValidationError):
            crear_transferencia(
                codigo="t-002",
                almacen_origen=self.s["a1"],
                almacen_destino=self.s["a1"],
                motivo="x",
                detalles=[{
                    "insumo": self.s["insumo"],
                    "lote_origen": self.s["lote"],
                    "cantidad": Decimal("5"),
                }],
                usuario=self.s["user"],
            )

    def test_sin_detalles_falla(self):
        with self.assertRaises(ValidationError):
            crear_transferencia(
                codigo="t-003",
                almacen_origen=self.s["a1"],
                almacen_destino=self.s["a2"],
                motivo="x",
                detalles=[],
                usuario=self.s["user"],
            )

    def test_audita_creacion(self):
        crear_transferencia(
            codigo="t-004",
            almacen_origen=self.s["a1"],
            almacen_destino=self.s["a2"],
            motivo="x",
            detalles=[{
                "insumo": self.s["insumo"],
                "lote_origen": self.s["lote"],
                "cantidad": Decimal("5"),
            }],
            usuario=self.s["user"],
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="transferencia.creada"
            ).count(), 1,
        )


class FlujoTransferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s = _setup("fl")

    def _crear(self):
        return crear_transferencia(
            codigo="t-flujo",
            almacen_origen=self.s["a1"],
            almacen_destino=self.s["a2"],
            motivo="Test",
            detalles=[{
                "insumo": self.s["insumo"],
                "lote_origen": self.s["lote"],
                "cantidad": Decimal("10"),
            }],
            usuario=self.s["user"],
        )

    def test_flujo_completo(self):
        t = self._crear()
        transicionar_transferencia(
            transferencia_id=t.pk,
            nuevo_estado=Transferencia.Estado.APROBADA,
            usuario=self.s["user"],
        )
        despachar_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
        )
        recibir_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
        )
        t.refresh_from_db()
        self.assertEqual(t.estado, Transferencia.Estado.RECIBIDA)
        # Stock origen: 100 - 10 = 90
        self.s["stock1"].refresh_from_db()
        self.assertEqual(self.s["stock1"].cantidad, Decimal("90.000"))
        # Stock destino: se creó con 10
        stock2 = Stock.objects.get(
            almacen=self.s["a2"], lote=self.s["lote"],
        )
        self.assertEqual(stock2.cantidad, Decimal("10.000"))

    def test_despacho_sin_stock_falla(self):
        t = self._crear()
        transicionar_transferencia(
            transferencia_id=t.pk,
            nuevo_estado=Transferencia.Estado.APROBADA,
            usuario=self.s["user"],
        )
        self.s["stock1"].cantidad = Decimal("5")
        self.s["stock1"].save()
        with self.assertRaises(ValidationError):
            despachar_transferencia(
                transferencia_id=t.pk, usuario=self.s["user"],
            )
        self.s["stock1"].refresh_from_db()
        self.assertEqual(self.s["stock1"].cantidad, Decimal("5.000"))

    def test_salto_invalido_falla(self):
        t = self._crear()
        with self.assertRaises(ValidationError):
            despachar_transferencia(
                transferencia_id=t.pk, usuario=self.s["user"],
            )

    def test_cancelar_borrador_sin_movimientos(self):
        t = self._crear()
        cancelar_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
            motivo="No requerido",
        )
        t.refresh_from_db()
        self.assertEqual(t.estado, Transferencia.Estado.CANCELADA)
        self.s["stock1"].refresh_from_db()
        self.assertEqual(self.s["stock1"].cantidad, Decimal("100.000"))

    def test_cancelar_en_transito_restaura_stock(self):
        t = self._crear()
        transicionar_transferencia(
            transferencia_id=t.pk,
            nuevo_estado=Transferencia.Estado.APROBADA,
            usuario=self.s["user"],
        )
        despachar_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
        )
        self.s["stock1"].refresh_from_db()
        self.assertEqual(self.s["stock1"].cantidad, Decimal("90.000"))
        cancelar_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
            motivo="Cancelada en tránsito",
        )
        self.s["stock1"].refresh_from_db()
        self.assertEqual(self.s["stock1"].cantidad, Decimal("100.000"))

    def test_recibir_cancelada_falla(self):
        t = self._crear()
        cancelar_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
        )
        with self.assertRaises(ValidationError):
            recibir_transferencia(
                transferencia_id=t.pk, usuario=self.s["user"],
            )

    def test_multiples_transiciones_auditadas(self):
        t = self._crear()
        transicionar_transferencia(
            transferencia_id=t.pk,
            nuevo_estado=Transferencia.Estado.APROBADA,
            usuario=self.s["user"],
        )
        despachar_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
        )
        recibir_transferencia(
            transferencia_id=t.pk, usuario=self.s["user"],
        )
        self.assertEqual(
            TransicionTransferencia.objects.filter(transferencia=t).count(),
            4,  # BORRADOR inicial + APROBADA + EN_TRANSITO + RECIBIDA
        )
        self.assertGreaterEqual(
            EventoAuditoria.objects.filter(
                tipo_objeto="Transferencia", objeto_id=str(t.id),
            ).count(),
            4,
        )
