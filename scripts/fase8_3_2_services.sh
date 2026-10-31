#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> apps/inventario/services.py << 'EOF'


# ══════════════════════════════════════════════════════════════════
# ENTREGAS (Fase 8.3.2)
# ══════════════════════════════════════════════════════════════════

def _init_transiciones_entrega():
    from apps.inventario.models import Entrega as E
    return {
        E.Estado.BORRADOR: {E.Estado.ENVIADA, E.Estado.CANCELADA},
        E.Estado.ENVIADA: {E.Estado.RECIBIDA, E.Estado.CANCELADA},
        E.Estado.RECIBIDA: set(),
        E.Estado.CANCELADA: set(),
    }


def _validar_transicion_entrega(estado_actual, nuevo_estado):
    from django.core.exceptions import ValidationError
    permitidas = _init_transiciones_entrega().get(estado_actual, set())
    if nuevo_estado not in permitidas:
        raise ValidationError(
            {"estado": f"Transición inválida: {estado_actual} -> {nuevo_estado}."}
        )


@transaction.atomic
def crear_entrega(
    *, codigo, almacen_origen, motivo, detalles,
    refugio=None, hospital=None, destinatario_texto="",
    notas="", usuario, request=None,
):
    """Crea una entrega en BORRADOR con sus detalles."""
    from apps.inventario.models import (
        DetalleEntrega, Entrega, TransicionEntrega,
    )
    from django.core.exceptions import ValidationError

    if not motivo or not motivo.strip():
        raise ValidationError({"motivo": "El motivo es obligatorio."})

    if not detalles:
        raise ValidationError({"detalles": "Debe incluir al menos un insumo."})

    # Al menos un destino
    if not (refugio or hospital or destinatario_texto.strip()):
        raise ValidationError(
            {"destino": "Debe indicar refugio, hospital o destinatario."}
        )

    # No ambos
    if refugio and hospital:
        raise ValidationError(
            {"destino": "No puede ser refugio y hospital a la vez."}
        )

    entrega = Entrega.objects.create(
        codigo=codigo,
        almacen_origen=almacen_origen,
        refugio=refugio,
        hospital=hospital,
        destinatario_texto=destinatario_texto.strip(),
        motivo=motivo.strip(),
        solicitada_por=usuario,
        notas=notas,
    )

    for det in detalles:
        DetalleEntrega.objects.create(
            entrega=entrega,
            insumo=det["insumo"],
            lote=det["lote"],
            cantidad=det["cantidad"],
        )

    TransicionEntrega.objects.create(
        entrega=entrega,
        estado_anterior="",
        estado_nuevo=Entrega.Estado.BORRADOR,
        usuario=usuario,
        motivo="Creación de entrega.",
    )

    _auditar_entrega(
        entrega, usuario, request, "entrega.creada",
        f"Entrega {codigo} creada.",
    )
    return entrega


def _auditar_entrega(entrega, usuario, request, accion, justif):
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion=accion,
        tipo_objeto="Entrega",
        objeto_id=entrega.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=justif,
        direccion_ip=ip,
        agente_usuario=ua,
        organizacion_id=entrega.almacen_origen.organizacion_id,
        metadatos={
            "estado": entrega.estado,
            "codigo": entrega.codigo,
        },
    )


@transaction.atomic
def enviar_entrega(
    *, entrega_id, usuario, motivo="", request=None,
):
    """BORRADOR -> ENVIADA. Genera SALIDA por cada lote en origen."""
    from apps.inventario.models import (
        Entrega, Movimiento, Stock, TransicionEntrega,
    )
    from django.core.exceptions import ValidationError

    try:
        e = (
            Entrega.objects
            .select_for_update(of=("self",))
            .select_related("almacen_origen")
            .get(pk=entrega_id)
        )
    except Entrega.DoesNotExist:
        raise ValidationError({"entrega": "No existe."})

    _validar_transicion_entrega(e.estado, Entrega.Estado.ENVIADA)

    detalles = list(e.detalles.select_related("insumo", "lote"))
    if not detalles:
        raise ValidationError({"detalles": "Sin líneas que enviar."})

    # Fail-fast: validar stock de todas las líneas
    for det in detalles:
        stock = (
            Stock.objects
            .select_for_update(of=("self",))
            .filter(almacen=e.almacen_origen, lote=det.lote)
            .first()
        )
        if stock is None or stock.cantidad < det.cantidad:
            raise ValidationError(
                {"detalles": (
                    f"Stock insuficiente de {det.lote.codigo}. "
                    f"Disponible: {stock.cantidad if stock else 0}, "
                    f"solicitado: {det.cantidad}."
                )}
            )

    # Ejecutar salidas
    for det in detalles:
        stock = Stock.objects.select_for_update(of=("self",)).get(
            almacen=e.almacen_origen, lote=det.lote,
        )
        registrar_movimiento(
            stock_id=stock.pk,
            tipo=Movimiento.Tipo.SALIDA,
            cantidad=float(det.cantidad),
            referencia_tipo="Entrega",
            referencia_id=str(e.id),
            notas=motivo,
            usuario=usuario,
            request=request,
        )
        det.cantidad_entregada = det.cantidad
        det.save(update_fields=["cantidad_entregada"])

    anterior = e.estado
    e.estado = Entrega.Estado.ENVIADA
    e.enviada_por = usuario
    e.enviada_en = timezone.now()
    e.save()

    TransicionEntrega.objects.create(
        entrega=e, estado_anterior=anterior,
        estado_nuevo=Entrega.Estado.ENVIADA,
        usuario=usuario, motivo=motivo,
    )
    _auditar_entrega(
        e, usuario, request,
        "entrega.enviada",
        f"{anterior} -> ENVIADA. {len(detalles)} líneas.",
    )
    return e


@transaction.atomic
def recibir_entrega(
    *, entrega_id, usuario, motivo="", request=None,
):
    """ENVIADA -> RECIBIDA. Sin movimientos: el destino consume."""
    from apps.inventario.models import (
        Entrega, TransicionEntrega,
    )
    from django.core.exceptions import ValidationError

    try:
        e = (
            Entrega.objects
            .select_for_update(of=("self",))
            .get(pk=entrega_id)
        )
    except Entrega.DoesNotExist:
        raise ValidationError({"entrega": "No existe."})

    _validar_transicion_entrega(e.estado, Entrega.Estado.RECIBIDA)

    anterior = e.estado
    e.estado = Entrega.Estado.RECIBIDA
    e.recibida_por = usuario
    e.recibida_en = timezone.now()
    e.save()

    TransicionEntrega.objects.create(
        entrega=e, estado_anterior=anterior,
        estado_nuevo=Entrega.Estado.RECIBIDA,
        usuario=usuario, motivo=motivo,
    )
    _auditar_entrega(
        e, usuario, request,
        "entrega.recibida",
        f"{anterior} -> RECIBIDA.",
    )
    return e


@transaction.atomic
def cancelar_entrega(
    *, entrega_id, usuario, motivo="", request=None,
):
    """BORRADOR -> CANCELADA (sin movimientos).
    ENVIADA -> CANCELADA con restauración al origen."""
    from apps.inventario.models import (
        Entrega, Movimiento, Stock, TransicionEntrega,
    )
    from django.core.exceptions import ValidationError

    try:
        e = (
            Entrega.objects
            .select_for_update(of=("self",))
            .select_related("almacen_origen")
            .get(pk=entrega_id)
        )
    except Entrega.DoesNotExist:
        raise ValidationError({"entrega": "No existe."})

    if e.estado == Entrega.Estado.ENVIADA:
        for det in e.detalles.select_related("lote"):
            if det.cantidad_entregada <= 0:
                continue
            stock = Stock.objects.select_for_update(of=("self",)).get(
                almacen=e.almacen_origen, lote=det.lote,
            )
            registrar_movimiento(
                stock_id=stock.pk,
                tipo=Movimiento.Tipo.ENTRADA,
                cantidad=float(det.cantidad_entregada),
                referencia_tipo="Entrega_cancelacion",
                referencia_id=str(e.id),
                notas=f"Cancelación: {motivo}",
                usuario=usuario,
                request=request,
            )

    _validar_transicion_entrega(e.estado, Entrega.Estado.CANCELADA)

    anterior = e.estado
    e.estado = Entrega.Estado.CANCELADA
    e.save()

    TransicionEntrega.objects.create(
        entrega=e, estado_anterior=anterior,
        estado_nuevo=Entrega.Estado.CANCELADA,
        usuario=usuario, motivo=motivo,
    )
    _auditar_entrega(
        e, usuario, request,
        "entrega.cancelada",
        f"{anterior} -> CANCELADA. Motivo: {motivo}",
    )
    return e
EOF

echo "OK: servicios de entrega añadidos"

# Verificación imports
python3 manage.py shell -c "from apps.inventario import services; print('OK: services importan')"
