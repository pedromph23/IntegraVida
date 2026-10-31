"""Servicios de refugios — operaciones transaccionales y auditadas."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.refugios.models import Refugio, RegistroOcupacion


@transaction.atomic
def registrar_ocupacion(
    *,
    refugio_id,
    cantidad_nueva,
    fuente=RegistroOcupacion.Fuente.MANUAL,
    notas="",
    usuario,
    request=None,
):
    """
    Registra un cambio de ocupación en un refugio.

    - Bloquea la fila con select_for_update para evitar race conditions (§10).
    - Valida 0 <= cantidad_nueva <= capacidad_total.
    - Crea un RegistroOcupacion (historial inmutable).
    - Audita el cambio con hash encadenado.
    - Si cantidad_nueva == ocupacion_actual, no hace nada (idempotente).
    """
    if cantidad_nueva < 0:
        raise ValidationError(
            {"cantidad_nueva": "La cantidad no puede ser negativa."}
        )

    try:
        refugio = (
            Refugio.objects.select_for_update().get(pk=refugio_id)
        )
    except Refugio.DoesNotExist:
        raise ValidationError({"refugio": "El refugio no existe."})

    if cantidad_nueva > refugio.capacidad_total:
        raise ValidationError(
            {
                "cantidad_nueva": (
                    f"Excede la capacidad total ({refugio.capacidad_total})."
                )
            }
        )

    anterior = refugio.ocupacion_actual
    diferencia = cantidad_nueva - anterior

    if diferencia == 0:
        return refugio

    refugio.ocupacion_actual = cantidad_nueva
    refugio.save(update_fields=["ocupacion_actual", "actualizado_en"])

    RegistroOcupacion.objects.create(
        refugio=refugio,
        cantidad_anterior=anterior,
        cantidad_nueva=cantidad_nueva,
        diferencia=diferencia,
        fuente=fuente,
        notas=notas,
        registrado_por=usuario,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="refugio.ocupacion_actualizada",
        tipo_objeto="Refugio",
        objeto_id=refugio.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=f"Ocupación: {anterior} → {cantidad_nueva}",
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=refugio.organizacion_id,
        metadatos={
            "cantidad_anterior": anterior,
            "cantidad_nueva": cantidad_nueva,
            "diferencia": diferencia,
            "fuente": str(fuente),
        },
    )

    return refugio
