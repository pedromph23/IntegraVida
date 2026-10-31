#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/derivaciones/services.py << 'EOF'
"""Servicios de derivación — flujo con transiciones controladas."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.derivaciones.models import Derivacion, TransicionEstado
from apps.organizaciones.services import tiene_acceso_a_organizacion
from apps.pacientes.models import Episodio
from apps.pacientes.services import filtrar_episodios_por_ambito
from apps.triaje.models import Triaje


TRANSICIONES_PERMITIDAS = {
    Derivacion.Estado.SOLICITADA: {
        Derivacion.Estado.ACEPTADA,
        Derivacion.Estado.RECHAZADA,
        Derivacion.Estado.CANCELADA,
    },
    Derivacion.Estado.ACEPTADA: {
        Derivacion.Estado.ASIGNADA,
        Derivacion.Estado.CANCELADA,
    },
    Derivacion.Estado.ASIGNADA: {
        Derivacion.Estado.EN_CAMINO,
        Derivacion.Estado.CANCELADA,
    },
    Derivacion.Estado.EN_CAMINO: {
        Derivacion.Estado.COMPLETADA,
        Derivacion.Estado.CANCELADA,
    },
    Derivacion.Estado.RECHAZADA: set(),
    Derivacion.Estado.COMPLETADA: set(),
    Derivacion.Estado.CANCELADA: set(),
}


PRIORIDAD_ORDEN = {
    Derivacion.Prioridad.BAJA: 1,
    Derivacion.Prioridad.MEDIA: 2,
    Derivacion.Prioridad.ALTA: 3,
    Derivacion.Prioridad.CRITICA: 4,
}


TRIAGE_A_PRIORIDAD_MINIMA = {
    Triaje.Clasificacion.ROJO: Derivacion.Prioridad.ALTA,
    Triaje.Clasificacion.AMARILLO: Derivacion.Prioridad.MEDIA,
    Triaje.Clasificacion.VERDE: Derivacion.Prioridad.BAJA,
}


def _prioridad_minima(episodio):
    triaje = Triaje.objects.filter(episodio=episodio, vigente=True).first()
    if triaje is None:
        return Derivacion.Prioridad.BAJA
    return TRIAGE_A_PRIORIDAD_MINIMA[triaje.clasificacion]


def _validar_prioridad(prioridad, episodio):
    if prioridad not in PRIORIDAD_ORDEN:
        raise ValidationError({"prioridad": "Prioridad inválida."})
    minima = _prioridad_minima(episodio)
    if PRIORIDAD_ORDEN[prioridad] < PRIORIDAD_ORDEN[minima]:
        raise ValidationError(
            {
                "prioridad": (
                    f"La prioridad no puede ser menor que {minima} "
                    f"(dictada por el triaje clínico vigente)."
                )
            }
        )


def _usuario_puede_operar(usuario, derivacion):
    return (
        tiene_acceso_a_organizacion(
            usuario, derivacion.hospital_origen.organizacion
        )
        or tiene_acceso_a_organizacion(
            usuario, derivacion.hospital_destino.organizacion
        )
    )


@transaction.atomic
def solicitar_derivacion(
    *,
    episodio_id,
    hospital_destino,
    motivo,
    prioridad=Derivacion.Prioridad.MEDIA,
    notas="",
    usuario,
    request=None,
):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "El motivo es obligatorio."})

    try:
        episodio = Episodio.objects.get(pk=episodio_id)
    except Episodio.DoesNotExist:
        raise ValidationError({"episodio": "El episodio no existe."})

    if episodio.hospital_id is None:
        raise ValidationError(
            {"episodio": "Solo se derivan episodios con hospital de origen."}
        )

    if episodio.hospital_id == hospital_destino.pk:
        raise ValidationError(
            {"hospital_destino": "El destino no puede ser el origen."}
        )

    visibles = filtrar_episodios_por_ambito(
        Episodio.objects.filter(pk=episodio_id), usuario
    )
    if not visibles.exists():
        raise PermissionDenied("No tienes acceso a este episodio.")

    _validar_prioridad(prioridad, episodio)

    derivacion = Derivacion.objects.create(
        episodio=episodio,
        hospital_origen=episodio.hospital,
        hospital_destino=hospital_destino,
        prioridad=prioridad,
        estado=Derivacion.Estado.SOLICITADA,
        motivo=motivo,
        solicitada_por=usuario,
        notas=notas,
    )

    TransicionEstado.objects.create(
        derivacion=derivacion,
        estado_anterior="",
        estado_nuevo=Derivacion.Estado.SOLICITADA,
        usuario=usuario,
        motivo="Creación de derivación.",
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="derivacion.solicitada",
        tipo_objeto="Derivacion",
        objeto_id=derivacion.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=(
            f"Derivación: {episodio.hospital.codigo} -> "
            f"{hospital_destino.codigo}."
        ),
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=episodio.hospital.organizacion_id,
        metadatos={
            "prioridad": prioridad,
            "estado": Derivacion.Estado.SOLICITADA,
        },
    )
    return derivacion


@transaction.atomic
def transicionar_derivacion(
    *,
    derivacion_id,
    nuevo_estado,
    usuario,
    motivo="",
    request=None,
):
    if nuevo_estado not in {v for v, _ in Derivacion.Estado.choices}:
        raise ValidationError({"estado": "Estado inválido."})

    try:
        derivacion = (
            Derivacion.objects
            .select_for_update(of=("self",))
            .select_related(
                "hospital_origen__organizacion",
                "hospital_destino__organizacion",
            )
            .get(pk=derivacion_id)
        )
    except Derivacion.DoesNotExist:
        raise ValidationError({"derivacion": "La derivación no existe."})

    if not _usuario_puede_operar(usuario, derivacion):
        raise PermissionDenied("No tienes acceso a esta derivación.")

    permitidas = TRANSICIONES_PERMITIDAS.get(derivacion.estado, set())
    if nuevo_estado not in permitidas:
        raise ValidationError(
            {
                "estado": (
                    f"Transición inválida: {derivacion.estado} -> "
                    f"{nuevo_estado}."
                )
            }
        )

    estado_anterior = derivacion.estado
    derivacion.estado = nuevo_estado

    ahora = timezone.now()
    if nuevo_estado == Derivacion.Estado.ACEPTADA:
        derivacion.aceptada_por = usuario
        derivacion.aceptada_en = ahora
    elif nuevo_estado == Derivacion.Estado.EN_CAMINO:
        derivacion.iniciada_en = ahora
    elif nuevo_estado == Derivacion.Estado.COMPLETADA:
        derivacion.completada_en = ahora

    derivacion.save()

    TransicionEstado.objects.create(
        derivacion=derivacion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        usuario=usuario,
        motivo=(motivo or "").strip(),
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="derivacion.transicion",
        tipo_objeto="Derivacion",
        objeto_id=derivacion.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=f"Transición: {estado_anterior} -> {nuevo_estado}.",
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=derivacion.hospital_origen.organizacion_id,
        metadatos={
            "estado_anterior": estado_anterior,
            "estado_nuevo": nuevo_estado,
        },
    )
    return derivacion
EOF

echo "OK: Fase 7.2 completada (services.py)"
