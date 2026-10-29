"""
Servicio de registro de auditoría con cadena criptográfica (§7.3).

registrar_evento() es la única vía sancionada para insertar eventos.
Usa pg_advisory_xact_lock para serializar inserciones concurrentes y
garantizar que la cadena nunca se bifurque (§7.4, §10).
"""

from django.db import connection, transaction

from .models import HASH_GENESIS, EventoAuditoria, calcular_hash


# Clave global del advisory lock. Liberada al cerrar la transacción.
_ADVISORY_LOCK_KEY = 0x41554449  # "AUDI" en hex


def registrar_evento(
    *,
    actor,
    accion,
    tipo_objeto="",
    objeto_id="",
    resultado=EventoAuditoria.Resultado.EXITOSO,
    justificacion="",
    agente_usuario="",
    id_correlacion="",
    organizacion_id=None,
    direccion_ip=None,
    metadatos=None,
):
    """
    Registra un evento de auditoría de forma atómica y encadenada.

    Returns:
        El EventoAuditoria persistido, con hash_actual calculado.
    """
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_ADVISORY_LOCK_KEY])

        ultimo_hash = (
            EventoAuditoria.objects
            .order_by("-ocurrido_en")
            .values_list("hash_actual", flat=True)
            .first()
        )
        hash_anterior = ultimo_hash if ultimo_hash else HASH_GENESIS

        evento = EventoAuditoria(
            actor=actor,
            organizacion_id=organizacion_id,
            accion=accion,
            tipo_objeto=tipo_objeto,
            objeto_id=objeto_id,
            resultado=resultado,
            justificacion=justificacion,
            agente_usuario=agente_usuario,
            id_correlacion=id_correlacion,
            direccion_ip=direccion_ip,
            metadatos=metadatos or {},
            hash_anterior=hash_anterior,
        )
        evento.hash_actual = calcular_hash(evento)
        evento.save()
        return evento