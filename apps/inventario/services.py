"""Servicios de inventario — movimientos transaccionales con FEFO."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.inventario.models import Insumo, Movimiento, Stock


# Tipos que SUMAN cantidad al stock
TIPOS_SUMAN = {
    Movimiento.Tipo.ENTRADA,
    Movimiento.Tipo.TRANSFERENCIA_ENTRADA,
}

# Tipos que RESTAN cantidad del stock (cantidad se registra positiva)
TIPOS_RESTAN = {
    Movimiento.Tipo.SALIDA,
    Movimiento.Tipo.TRANSFERENCIA_SALIDA,
    Movimiento.Tipo.MERMA_VENCIMIENTO,
}


def _calcular_nueva_cantidad(tipo, cantidad, cantidad_actual):
    """Calcula la nueva cantidad del stock según tipo."""
    if tipo in TIPOS_SUMAN:
        if cantidad <= 0:
            raise ValidationError(
                {"cantidad": "Debe ser positiva para este tipo."}
            )
        return cantidad_actual + cantidad
    if tipo in TIPOS_RESTAN:
        if cantidad <= 0:
            raise ValidationError(
                {"cantidad": "Debe ser positiva para este tipo."}
            )
        return cantidad_actual - cantidad
    if tipo == Movimiento.Tipo.AJUSTE:
        # AJUSTE admite cantidad positiva o negativa
        if cantidad == 0:
            raise ValidationError(
                {"cantidad": "El ajuste no puede ser cero."}
            )
        return cantidad_actual + cantidad
    raise ValidationError({"tipo": "Tipo de movimiento inválido."})


@transaction.atomic
def registrar_movimiento(
    *,
    stock_id,
    tipo,
    cantidad,
    referencia_tipo="",
    referencia_id="",
    notas="",
    usuario,
    request=None,
):
    """
    Registra un movimiento de kardex sobre un stock.

    - select_for_update(of=("self",)) bloquea el stock (§10).
    - Valida que la cantidad resultante no sea negativa.
    - Actualiza stock.cantidad y crea Movimiento inmutable.
    - Audita con hash encadenado.
    """
    cantidad = round(float(cantidad), 3)

    try:
        stock = (
            Stock.objects
            .select_for_update(of=("self",))
            .select_related("almacen", "lote__insumo")
            .get(pk=stock_id)
        )
    except Stock.DoesNotExist:
        raise ValidationError({"stock": "El stock no existe."})

    cantidad_anterior = float(stock.cantidad)
    nueva = _calcular_nueva_cantidad(tipo, cantidad, cantidad_anterior)

    if nueva < 0:
        raise ValidationError(
            {
                "cantidad": (
                    f"Stock insuficiente. Disponible: {cantidad_anterior}, "
                    f"solicitado: {cantidad}."
                )
            }
        )

    stock.cantidad = nueva
    stock.save(update_fields=["cantidad", "actualizado_en"])

    movimiento = Movimiento.objects.create(
        stock=stock,
        tipo=tipo,
        cantidad=cantidad,
        cantidad_anterior=cantidad_anterior,
        cantidad_nueva=nueva,
        diferencia=nueva - cantidad_anterior,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        registrado_por=usuario,
        notas=notas,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion=f"inventario.movimiento_{tipo.lower()}",
        tipo_objeto="Movimiento",
        objeto_id=movimiento.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=(
            f"Stock {stock.almacen.codigo}/{stock.lote.codigo}: "
            f"{cantidad_anterior} -> {nueva}."
        ),
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=stock.almacen.organizacion_id,
        metadatos={
            "stock_id": str(stock.id),
            "tipo": tipo,
            "cantidad": cantidad,
            "referencia_tipo": referencia_tipo,
            "referencia_id": referencia_id,
        },
    )

    return movimiento


def seleccionar_stock_fefo(*, insumo, almacen, cantidad):
    """
    Devuelve el Stock candidato a despachar según FEFO.

    - Si insumo.requiere_vencimiento=True: ordena por fecha_vencimiento ASC
      (NULLS LAST), excluye vencidos.
    - Si no requiere vencimiento: ordena por lote.codigo.
    - Solo considera stocks con cantidad >= cantidad solicitada.

    NO reserva ni descuenta. La operación real es registrar_movimiento().

    Devuelve None si no hay stock suficiente en un único lote.
    """
    cantidad = round(float(cantidad), 3)

    stocks = Stock.objects.filter(
        almacen=almacen,
        lote__insumo=insumo,
        cantidad__gte=cantidad,
    ).select_related("almacen", "lote__insumo")

    if insumo.requiere_vencimiento:
        hoy = timezone.localdate()
        stocks = stocks.filter(
            Q(lote__fecha_vencimiento__isnull=True)
            | Q(lote__fecha_vencimiento__gte=hoy)
        ).order_by(
            F("lote__fecha_vencimiento").asc(nulls_last=True),
            "lote__codigo",
        )
    else:
        stocks = stocks.order_by("lote__codigo")

    return stocks.first()
