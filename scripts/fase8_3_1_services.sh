#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> apps/inventario/services.py << 'EOF'


# ══════════════════════════════════════════════════════════════════
# TRANSFERENCIAS (Fase 8.3.1)
# ══════════════════════════════════════════════════════════════════

TRANSICIONES_TRANSFERENCIA = None  # Se inicializa abajo


def _init_transiciones():
    from apps.inventario.models import Transferencia as T
    return {
        T.Estado.BORRADOR: {T.Estado.APROBADA, T.Estado.RECHAZADA, T.Estado.CANCELADA},
        T.Estado.APROBADA: {T.Estado.EN_TRANSITO, T.Estado.CANCELADA},
        T.Estado.EN_TRANSITO: {T.Estado.RECIBIDA, T.Estado.CANCELADA},
        T.Estado.RECIBIDA: set(),
        T.Estado.RECHAZADA: set(),
        T.Estado.CANCELADA: set(),
    }


def _validar_transicion_transferencia(estado_actual, nuevo_estado):
    from apps.inventario.models import Transferencia
    from django.core.exceptions import ValidationError
    trans = _init_transiciones()
    permitidas = trans.get(estado_actual, set())
    if nuevo_estado not in permitidas:
        raise ValidationError(
            {"estado": f"Transición inválida: {estado_actual} -> {nuevo_estado}."}
        )


@transaction.atomic
def crear_transferencia(
    *, codigo, almacen_origen, almacen_destino, motivo, detalles,
    prioridad="MEDIA", notas="", usuario, request=None,
):
    """Crea una transferencia en BORRADOR con sus detalles."""
    from apps.inventario.models import (
        DetalleTransferencia, Transferencia, TransicionTransferencia,
    )
    from django.core.exceptions import ValidationError
    from apps.organizaciones.services import tiene_acceso_a_organizacion

    if almacen_origen.pk == almacen_destino.pk:
        raise ValidationError(
            {"almacen_destino": "El destino no puede ser el origen."}
        )

    if not tiene_acceso_a_organizacion(usuario, almacen_origen.organizacion):
        raise PermissionDenied("No tienes acceso al almacén de origen.")

    if not detalles:
        raise ValidationError({"detalles": "Debe incluir al menos un insumo."})

    transferencia = Transferencia.objects.create(
        codigo=codigo,
        almacen_origen=almacen_origen,
        almacen_destino=almacen_destino,
        prioridad=prioridad,
        motivo=motivo.strip(),
        solicitada_por=usuario,
        notas=notas,
    )

    for det in detalles:
        DetalleTransferencia.objects.create(
            transferencia=transferencia,
            insumo=det["insumo"],
            lote_origen=det["lote_origen"],
            cantidad=det["cantidad"],
        )

    TransicionTransferencia.objects.create(
        transferencia=transferencia,
        estado_anterior="",
        estado_nuevo=Transferencia.Estado.BORRADOR,
        usuario=usuario,
        motivo="Creación de transferencia.",
    )

    _auditar_transferencia(
        transferencia, usuario, request,
        "transferencia.creada",
        f"Transferencia {codigo} creada.",
    )
    return transferencia


def _auditar_transferencia(transferencia, usuario, request, accion, justif):
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion=accion,
        tipo_objeto="Transferencia",
        objeto_id=transferencia.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=justif,
        direccion_ip=ip,
        agente_usuario=ua,
        organizacion_id=transferencia.almacen_origen.organizacion_id,
        metadatos={
            "estado": transferencia.estado,
            "codigo": transferencia.codigo,
        },
    )


@transaction.atomic
def transicionar_transferencia(
    *, transferencia_id, nuevo_estado, usuario, motivo="", request=None,
):
    """Máquina de estados de Transferencia. Efectos por estado se manejan
    en funciones específicas (despachar, recibir, cancelar)."""
    from apps.inventario.models import (
        Transferencia, TransicionTransferencia,
    )
    from django.core.exceptions import ValidationError

    try:
        t = (
            Transferencia.objects
            .select_for_update(of=("self",))
            .get(pk=transferencia_id)
        )
    except Transferencia.DoesNotExist:
        raise ValidationError({"transferencia": "No existe."})

    _validar_transicion_transferencia(t.estado, nuevo_estado)

    anterior = t.estado
    t.estado = nuevo_estado
    ahora = timezone.now()

    if nuevo_estado == Transferencia.Estado.APROBADA:
        t.aprobada_por = usuario
        t.aprobada_en = ahora

    t.save()

    TransicionTransferencia.objects.create(
        transferencia=t, estado_anterior=anterior,
        estado_nuevo=nuevo_estado, usuario=usuario, motivo=motivo,
    )
    _auditar_transferencia(
        t, usuario, request,
        f"transferencia.{nuevo_estado.lower()}",
        f"{anterior} -> {nuevo_estado}",
    )
    return t


@transaction.atomic
def despachar_transferencia(
    *, transferencia_id, usuario, motivo="", request=None,
):
    """APROBADA -> EN_TRANSITO. Genera SALIDA de cada lote en origen."""
    from apps.inventario.models import (
        Movimiento, Stock, Transferencia, TransicionTransferencia,
    )
    from django.core.exceptions import ValidationError

    try:
        t = (
            Transferencia.objects
            .select_for_update(of=("self",))
            .select_related("almacen_origen")
            .get(pk=transferencia_id)
        )
    except Transferencia.DoesNotExist:
        raise ValidationError({"transferencia": "No existe."})

    _validar_transicion_transferencia(t.estado, Transferencia.Estado.EN_TRANSITO)

    # Primero validar stock de todas las líneas
    detalles = list(t.detalles.select_related("insumo", "lote_origen"))
    if not detalles:
        raise ValidationError({"detalles": "Sin líneas que despachar."})

    for det in detalles:
        stock = (
            Stock.objects
            .select_for_update(of=("self",))
            .filter(
                almacen=t.almacen_origen,
                lote=det.lote_origen,
            )
            .first()
        )
        if stock is None or stock.cantidad < det.cantidad:
            raise ValidationError(
                {"detalles": (
                    f"Stock insuficiente de {det.lote_origen.codigo}. "
                    f"Disponible: {stock.cantidad if stock else 0}, "
                    f"solicitado: {det.cantidad}."
                )}
            )

    # Ejecutar salidas
    for det in detalles:
        stock = Stock.objects.select_for_update(of=("self",)).get(
            almacen=t.almacen_origen, lote=det.lote_origen,
        )
        registrar_movimiento(
            stock_id=stock.pk,
            tipo=Movimiento.Tipo.TRANSFERENCIA_SALIDA,
            cantidad=float(det.cantidad),
            referencia_tipo="Transferencia",
            referencia_id=str(t.id),
            notas=motivo,
            usuario=usuario,
            request=request,
        )
        det.cantidad_despachada = det.cantidad
        det.save(update_fields=["cantidad_despachada"])

    anterior = t.estado
    t.estado = Transferencia.Estado.EN_TRANSITO
    t.despachada_por = usuario
    t.despachada_en = timezone.now()
    t.save()

    TransicionTransferencia.objects.create(
        transferencia=t, estado_anterior=anterior,
        estado_nuevo=Transferencia.Estado.EN_TRANSITO,
        usuario=usuario, motivo=motivo,
    )
    _auditar_transferencia(
        t, usuario, request,
        "transferencia.despachada",
        f"{anterior} -> EN_TRANSITO. {len(detalles)} líneas despachadas.",
    )
    return t


@transaction.atomic
def recibir_transferencia(
    *, transferencia_id, usuario, motivo="", request=None,
):
    """EN_TRANSITO -> RECIBIDA. Genera ENTRADA de cada lote en destino."""
    from apps.inventario.models import (
        Movimiento, Stock, Transferencia, TransicionTransferencia,
    )
    from django.core.exceptions import ValidationError

    try:
        t = (
            Transferencia.objects
            .select_for_update(of=("self",))
            .select_related("almacen_destino")
            .get(pk=transferencia_id)
        )
    except Transferencia.DoesNotExist:
        raise ValidationError({"transferencia": "No existe."})

    _validar_transicion_transferencia(t.estado, Transferencia.Estado.RECIBIDA)

    detalles = list(t.detalles.select_related("lote_origen", "insumo"))
    for det in detalles:
        stock, _ = Stock.objects.get_or_create(
            almacen=t.almacen_destino,
            lote=det.lote_origen,
            defaults={"cantidad": 0},
        )
        registrar_movimiento(
            stock_id=stock.pk,
            tipo=Movimiento.Tipo.TRANSFERENCIA_ENTRADA,
            cantidad=float(det.cantidad_despachada or det.cantidad),
            referencia_tipo="Transferencia",
            referencia_id=str(t.id),
            notas=motivo,
            usuario=usuario,
            request=request,
        )
        det.cantidad_recibida = det.cantidad_despachada or det.cantidad
        det.save(update_fields=["cantidad_recibida"])

    anterior = t.estado
    t.estado = Transferencia.Estado.RECIBIDA
    t.recibida_por = usuario
    t.recibida_en = timezone.now()
    t.save()

    TransicionTransferencia.objects.create(
        transferencia=t, estado_anterior=anterior,
        estado_nuevo=Transferencia.Estado.RECIBIDA,
        usuario=usuario, motivo=motivo,
    )
    _auditar_transferencia(
        t, usuario, request,
        "transferencia.recibida",
        f"{anterior} -> RECIBIDA. {len(detalles)} líneas recibidas.",
    )
    return t


@transaction.atomic
def cancelar_transferencia(
    *, transferencia_id, usuario, motivo="", request=None,
):
    """BORRADOR/APROBADA -> CANCELADA sin movimientos.
    EN_TRANSITO -> CANCELADA con restauración al origen."""
    from apps.inventario.models import (
        Movimiento, Stock, Transferencia, TransicionTransferencia,
    )
    from django.core.exceptions import ValidationError

    try:
        t = (
            Transferencia.objects
            .select_for_update(of=("self",))
            .select_related("almacen_origen")
            .get(pk=transferencia_id)
        )
    except Transferencia.DoesNotExist:
        raise ValidationError({"transferencia": "No existe."})

    if t.estado == Transferencia.Estado.EN_TRANSITO:
        # Restaurar al origen
        for det in t.detalles.select_related("lote_origen"):
            if det.cantidad_despachada <= 0:
                continue
            stock = Stock.objects.select_for_update(of=("self",)).get(
                almacen=t.almacen_origen, lote=det.lote_origen,
            )
            registrar_movimiento(
                stock_id=stock.pk,
                tipo=Movimiento.Tipo.ENTRADA,
                cantidad=float(det.cantidad_despachada),
                referencia_tipo="Transferencia_cancelacion",
                referencia_id=str(t.id),
                notas=f"Cancelación: {motivo}",
                usuario=usuario,
                request=request,
            )

    _validar_transicion_transferencia(t.estado, Transferencia.Estado.CANCELADA)

    anterior = t.estado
    t.estado = Transferencia.Estado.CANCELADA
    t.save()

    TransicionTransferencia.objects.create(
        transferencia=t, estado_anterior=anterior,
        estado_nuevo=Transferencia.Estado.CANCELADA,
        usuario=usuario, motivo=motivo,
    )
    _auditar_transferencia(
        t, usuario, request,
        "transferencia.cancelada",
        f"{anterior} -> CANCELADA. Motivo: {motivo}",
    )
    return t
EOF

echo "OK: servicios de transferencia añadidos"
