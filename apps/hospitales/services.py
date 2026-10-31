"""Servicios de hospitales — operaciones transaccionales y auditadas."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.hospitales.models import RecursoHospitalario, RegistroDisponibilidad


@transaction.atomic
def registrar_disponibilidad(
    *,
    recurso_id,
    cantidad_nueva,
    usuario,
    notas="",
    request=None,
):
    """
    Registra un cambio de disponibilidad en un recurso hospitalario.

    - select_for_update para concurrencia (§10).
    - Valida 0 <= cantidad_nueva <= capacidad_total.
    - Crea un RegistroDisponibilidad (historial inmutable).
    - Audita con hash encadenado.
    - Idempotente si cantidad_nueva == disponible.
    """
    if cantidad_nueva < 0:
        raise ValidationError(
            {"cantidad_nueva": "La cantidad no puede ser negativa."}
        )

    try:
        recurso = (
            RecursoHospitalario.objects
            .select_for_update()
            .select_related("hospital")
            .get(pk=recurso_id)
        )
    except RecursoHospitalario.DoesNotExist:
        raise ValidationError({"recurso": "El recurso no existe."})

    if recurso.capacidad_total == 0:
        raise ValidationError(
            {"recurso": "El recurso no tiene capacidad total definida."}
        )

    if cantidad_nueva > recurso.capacidad_total:
        raise ValidationError(
            {
                "cantidad_nueva": (
                    f"Excede la capacidad total ({recurso.capacidad_total})."
                )
            }
        )

    anterior = recurso.disponible
    diferencia = cantidad_nueva - anterior

    if diferencia == 0:
        return recurso

    recurso.disponible = cantidad_nueva
    recurso.save(update_fields=["disponible", "actualizado_en"])

    RegistroDisponibilidad.objects.create(
        recurso=recurso,
        cantidad_anterior=anterior,
        cantidad_nueva=cantidad_nueva,
        diferencia=diferencia,
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
        accion="hospital.disponibilidad_actualizada",
        tipo_objeto="RecursoHospitalario",
        objeto_id=recurso.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=(
            f"Disponibilidad de {recurso.get_tipo_display()}: "
            f"{anterior} -> {cantidad_nueva}"
        ),
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=recurso.hospital.organizacion_id,
        metadatos={
            "tipo": recurso.tipo,
            "cantidad_anterior": anterior,
            "cantidad_nueva": cantidad_nueva,
            "diferencia": diferencia,
        },
    )

    return recurso
