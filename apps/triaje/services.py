"""Servicios de triaje — creación transaccional y auditada."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.pacientes.models import Episodio
from apps.pacientes.services import filtrar_episodios_por_ambito
from apps.triaje.models import Triaje


@transaction.atomic
def registrar_triaje(
    *,
    episodio_id,
    clasificacion,
    signos_vitales=None,
    observaciones="",
    es_reevaluacion=False,
    motivo_reevaluacion="",
    usuario,
    request=None,
):
    """
    Registra un nuevo triaje para un episodio.

    - Bloquea el episodio con select_for_update (§10).
    - Verifica que el usuario tenga acceso al episodio (§8, §11).
    - Marca el triaje anterior vigente como histórico.
    - Crea el nuevo Triaje con vigente=True.
    - Audita la operación con hash encadenado.
    """
    clasificaciones_validas = {v for v, _ in Triaje.Clasificacion.choices}
    if clasificacion not in clasificaciones_validas:
        raise ValidationError(
            {"clasificacion": "La clasificación no es válida."}
        )

    if es_reevaluacion and not motivo_reevaluacion.strip():
        raise ValidationError(
            {"motivo_reevaluacion": "Debes justificar la reevaluación."}
        )

    try:
        episodio = (
            Episodio.objects
            .select_for_update(of=("self",))
            .get(pk=episodio_id)
        )
    except Episodio.DoesNotExist:
        raise ValidationError({"episodio": "El episodio no existe."})

    # Verificación de ámbito (§8, §11): el usuario debe poder ver este episodio
    episodios_visibles = filtrar_episodios_por_ambito(
        Episodio.objects.filter(pk=episodio_id), usuario
    )
    if not episodios_visibles.exists():
        raise PermissionDenied(
            "No tienes acceso a este episodio (ámbito o organización)."
        )

    if episodio.estado in {Episodio.Estado.CERRADO, Episodio.Estado.FALLECIDO}:
        raise ValidationError(
            {"episodio": "No se puede triajar un episodio cerrado o fallecido."}
        )

    # Marca el anterior como histórico (respeta UniqueConstraint parcial)
    Triaje.objects.filter(episodio=episodio, vigente=True).update(vigente=False)

    triaje = Triaje.objects.create(
        episodio=episodio,
        clasificacion=clasificacion,
        signos_vitales=signos_vitales or {},
        observaciones=observaciones,
        evaluado_por=usuario,
        es_reevaluacion=es_reevaluacion,
        motivo_reevaluacion=motivo_reevaluacion,
        vigente=True,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion=(
            "triaje.reevaluacion_registrada"
            if es_reevaluacion
            else "triaje.registrado"
        ),
        tipo_objeto="Triaje",
        objeto_id=triaje.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=(
            f"Triaje {triaje.get_clasificacion_display()} "
            f"para episodio {episodio.pk}."
        ),
        direccion_ip=ip,
        agente_usuario=user_agent,
        metadatos={
            "episodio_id": str(episodio.pk),
            "clasificacion": clasificacion,
            "es_reevaluacion": es_reevaluacion,
            "tiene_signos_vitales": bool(triaje.signos_vitales),
        },
    )

    return triaje
