"""Servicio centralizado para registrar eventos de auditoría."""

import math
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address

from apps.auditoria.models import EventoAuditoria


CLAVES_METADATOS_PERMITIDAS = {
    "origen",
    "cantidad",
    "tipo_operacion",
    "codigo",
    "estado",
    "metodo",
    "resultado_operacion",
}

MAX_LONGITUD_VALOR = 200


def _validar_metadatos(metadatos):
    if metadatos is None:
        return {}

    if not isinstance(metadatos, dict):
        raise ValidationError("Los metadatos deben ser un diccionario.")

    if len(metadatos) > len(CLAVES_METADATOS_PERMITIDAS):
        raise ValidationError("Demasiados campos en los metadatos.")

    for clave, valor in metadatos.items():
        if not isinstance(clave, str) or clave not in CLAVES_METADATOS_PERMITIDAS:
            raise ValidationError(
                f"Clave de metadatos no autorizada: {clave}."
            )

        if valor is not None and type(valor) not in (str, int, float, bool):
            raise ValidationError(
                f"Tipo de valor no permitido para el metadato {clave}."
            )

        if isinstance(valor, str) and len(valor) > MAX_LONGITUD_VALOR:
            raise ValidationError(
                f"El metadato {clave} supera el límite de longitud."
            )

        if isinstance(valor, float) and not math.isfinite(valor):
            raise ValidationError(
                f"El metadato {clave} debe ser un número finito."
            )

    return metadatos


def registrar_evento(
    *,
    accion,
    actor=None,
    organizacion_id=None,
    tipo_objeto="",
    objeto_id="",
    resultado=EventoAuditoria.Resultado.EXITOSO,
    justificacion="",
    ip=None,
    agente_usuario="",
    correlation_id=None,
    metadatos=None,
):
    """Valida y guarda un evento de auditoría."""

    if not isinstance(accion, str) or not accion.strip():
        raise ValidationError("La acción de auditoría es obligatoria.")

    accion = accion.strip()
    if len(accion) > 100:
        raise ValidationError("La acción supera los 100 caracteres.")

    if resultado not in EventoAuditoria.Resultado.values:
        raise ValidationError("El resultado de auditoría no es válido.")

    if not isinstance(tipo_objeto, str) or len(tipo_objeto) > 100:
        raise ValidationError("El tipo de objeto no es válido.")

    if not isinstance(justificacion, str) or len(justificacion) > 500:
        raise ValidationError("La justificación no es válida.")

    if not isinstance(agente_usuario, str) or len(agente_usuario) > 500:
        raise ValidationError("El agente de usuario no es válido.")

    if type(objeto_id) not in (str, int, UUID):
        raise ValidationError("El identificador del objeto no es válido.")

    objeto_id = str(objeto_id)
    if len(objeto_id) > 100:
        raise ValidationError(
            "El identificador del objeto supera los 100 caracteres."
        )

    if organizacion_id is not None:
        try:
            organizacion_id = UUID(str(organizacion_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError(
                "El identificador de organización debe ser un UUID válido."
            ) from exc

    if ip is not None:
        if not isinstance(ip, str):
            raise ValidationError("La dirección IP debe ser texto.")

        try:
            validate_ipv46_address(ip)
        except ValidationError as exc:
            raise ValidationError("La dirección IP no es válida.") from exc

    if correlation_id is None:
        correlation_id = ""
    elif isinstance(correlation_id, (str, UUID)):
        correlation_id = str(correlation_id)
    else:
        raise ValidationError(
            "El identificador de correlación no es válido."
        )

    if len(correlation_id) > 100:
        raise ValidationError(
            "El identificador de correlación supera los 100 caracteres."
        )

    metadatos_validados = _validar_metadatos(metadatos)

    evento = EventoAuditoria(
        actor=actor,
        organizacion_id=organizacion_id,
        accion=accion,
        tipo_objeto=tipo_objeto,
        objeto_id=objeto_id,
        resultado=resultado,
        justificacion=justificacion,
        direccion_ip=ip,
        agente_usuario=agente_usuario,
        id_correlacion=correlation_id,
        metadatos=metadatos_validados,
    )

    evento.full_clean()
    evento.save()
    return evento
