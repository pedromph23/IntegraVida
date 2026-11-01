"""Vistas del panel para el módulo Derivaciones (F3.f.2).

La lógica de transiciones, validación de prioridad, verificación de
acceso y auditoría vive en apps.derivaciones.services. Aquí solo:
  - Lectura de lista/detalle con ámbito del usuario
  - POST de transición que delega en services.transicionar_derivacion()
    capturando PermissionDenied y ValidationError.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.derivaciones.models import Derivacion
from apps.derivaciones.services import (
    TRANSICIONES_PERMITIDAS,
    transicionar_derivacion,
)
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import (
    puede_administrar_plataforma,
    tiene_acceso_a_organizacion,
)

from .dashboard_pacientes import (
    _can_see_full_names,
    _can_see_sensitive_pii,
    _mask_cedula,
    _mask_nombre,
)

PAGE_SIZE = 25


def _org_ids_del_usuario(user):
    return (
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _base_queryset(user):
    qs = Derivacion.objects.select_related(
        "episodio__paciente",
        "hospital_origen__organizacion",
        "hospital_destino__organizacion",
        "solicitada_por", "aceptada_por",
    )
    if puede_administrar_plataforma(user):
        return qs
    org_ids = list(_org_ids_del_usuario(user))
    if not org_ids:
        return qs.none()
    return qs.filter(
        Q(hospital_origen__organizacion_id__in=org_ids)
        | Q(hospital_destino__organizacion_id__in=org_ids)
    )


def _can_write_derivaciones(user, derivacion):
    """Replica _usuario_puede_operar de services.py (para template)."""
    return (
        tiene_acceso_a_organizacion(
            user, derivacion.hospital_origen.organizacion,
        )
        or tiene_acceso_a_organizacion(
            user, derivacion.hospital_destino.organizacion,
        )
    )


@login_required
@require_GET
def derivaciones_list(request):
    qs = _base_queryset(request.user)

    estado = request.GET.get("estado", "")
    estados_validos = {v for v, _ in Derivacion.Estado.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado=estado)

    prioridad = request.GET.get("prioridad", "")
    prioridades_validas = {v for v, _ in Derivacion.Prioridad.choices}
    if prioridad not in prioridades_validas:
        prioridad = ""
    if prioridad:
        qs = qs.filter(prioridad=prioridad)

    qs = qs.order_by("-solicitada_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    filas = []
    for d in page:
        p = d.episodio.paciente
        filas.append({
            "id": d.id,
            "paciente_masked": _mask_nombre(p.nombres, p.apellidos),
            "cedula_masked": _mask_cedula(p.cedula),
            "hospital_origen": d.hospital_origen.nombre,
            "hospital_destino": d.hospital_destino.nombre,
            "prioridad": d.prioridad,
            "prioridad_display": d.get_prioridad_display(),
            "estado": d.estado,
            "estado_display": d.get_estado_display(),
            "solicitada_en": d.solicitada_en,
        })

    return render(request, "dashboard/derivaciones/list.html", {
        "page_title": "Derivaciones",
        "page_obj": page,
        "filas": filas,
        "total": paginator.count,
        "filters": {"estado": estado, "prioridad": prioridad},
        "estados": Derivacion.Estado.choices,
        "prioridades": Derivacion.Prioridad.choices,
    })


@login_required
@require_GET
def derivacion_detail(request, derivacion_id):
    derivacion = get_object_or_404(
        _base_queryset(request.user), id=derivacion_id,
    )
    paciente = derivacion.episodio.paciente
    transiciones = derivacion.transiciones.select_related(
        "usuario",
    ).order_by("-creado_en")[:30]
    permitidas = TRANSICIONES_PERMITIDAS.get(derivacion.estado, set())

    return render(request, "dashboard/derivaciones/detail.html", {
        "page_title": f"Derivación · {derivacion.get_estado_display()}",
        "derivacion": derivacion,
        "paciente": paciente,
        "transiciones": transiciones,
        "estados_permitidos": sorted(permitidas),
        "can_write": _can_write_derivaciones(request.user, derivacion),
        "can_see_full_names": _can_see_full_names(request.user),
        "can_see_sensitive_pii": _can_see_sensitive_pii(request.user),
    })


@login_required
@require_POST
def derivacion_transicionar(request, derivacion_id):
    # get_object_or_404 con _base_queryset asegura ámbito de lectura.
    # La autorización de escritura y la transición válida las decide
    # services.transicionar_derivacion.
    get_object_or_404(_base_queryset(request.user), id=derivacion_id)

    nuevo = request.POST.get("estado", "").strip()
    motivo = request.POST.get("motivo", "").strip()

    try:
        transicionar_derivacion(
            derivacion_id=derivacion_id,
            nuevo_estado=nuevo,
            usuario=request.user,
            motivo=motivo,
            request=request,
        )
        messages.success(request, "Estado actualizado.")
    except PermissionDenied:
        return HttpResponseForbidden(
            "No tienes permiso para operar esta derivación."
        )
    except ValidationError as e:
        if hasattr(e, "message_dict"):
            textos = [
                f"{campo}: {', '.join(msgs)}"
                for campo, msgs in e.message_dict.items()
            ]
            detalle = "; ".join(textos)
        else:
            detalle = "; ".join(e.messages)
        messages.error(request, detalle)

    return redirect(
        "dashboard:derivacion_detail", derivacion_id=derivacion_id,
    )
