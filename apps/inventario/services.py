"""Servicios de inventario — movimientos transaccionales con FEFO."""

from django.core.exceptions import PermissionDenied, ValidationError
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
