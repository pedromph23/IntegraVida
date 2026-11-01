"""Vistas del panel para el módulo Triaje (F3.f.1). Solo lectura.

La CREACIÓN de triajes vive en apps.triaje.services.registrar_triaje()
(transaccional, auditada, con verificación de ámbito). F3.f.1 NO la
duplica: aquí solo se listan y detallan triajes existentes.

Aislamiento por ámbito (§8, §11): se aplica
filtrar_episodios_por_ambito() a los Episodios, y solo se listan los
triajes cuyo episodio sea visible para el usuario.

PII: reusa los helpers de dashboard_pacientes (_mask_nombre,
_can_see_full_names, _can_see_sensitive_pii) para no duplicar reglas.
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.pacientes.models import Episodio
from apps.pacientes.services import filtrar_episodios_por_ambito
from apps.triaje.models import Triaje

from .dashboard_pacientes import (
    _can_see_full_names,
    _can_see_sensitive_pii,
    _mask_cedula,
    _mask_nombre,
)

PAGE_SIZE = 25


def _base_queryset(user):
    """Triajes cuyo episodio sea visible por ámbito del usuario."""
    episodios_visibles = filtrar_episodios_por_ambito(
        Episodio.objects.all(), user,
    )
    return Triaje.objects.filter(
        episodio__in=episodios_visibles,
    ).select_related(
        "episodio", "episodio__paciente", "evaluado_por",
    )


@login_required
@require_GET
def triajes_list(request):
    qs = _base_queryset(request.user)

    clasificacion = request.GET.get("clasificacion", "")
    clasificaciones_validas = {v for v, _ in Triaje.Clasificacion.choices}
    if clasificacion not in clasificaciones_validas:
        clasificacion = ""
    if clasificacion:
        qs = qs.filter(clasificacion=clasificacion)

    vigente_param = request.GET.get("vigente", "true")
    if vigente_param == "true":
        qs = qs.filter(vigente=True)
    elif vigente_param == "false":
        qs = qs.filter(vigente=False)
    # "todos" o cualquier otro valor: sin filtro

    qs = qs.order_by("-evaluado_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    filas = []
    for t in page:
        p = t.episodio.paciente
        filas.append({
            "id": t.id,
            "clasificacion": t.clasificacion,
            "clasificacion_display": t.get_clasificacion_display().split(" — ")[0],
            "paciente_masked": _mask_nombre(p.nombres, p.apellidos),
            "cedula_masked": _mask_cedula(p.cedula),
            "episodio_estado": t.episodio.get_estado_display(),
            "evaluado_por": t.evaluado_por.username,
            "evaluado_en": t.evaluado_en,
            "vigente": t.vigente,
            "es_reevaluacion": t.es_reevaluacion,
        })

    return render(request, "dashboard/triajes/list.html", {
        "page_title": "Triajes",
        "page_obj": page,
        "filas": filas,
        "total": paginator.count,
        "filters": {"clasificacion": clasificacion, "vigente": vigente_param},
        "clasificaciones": Triaje.Clasificacion.choices,
    })


@login_required
@require_GET
def triaje_detail(request, triaje_id):
    triaje = get_object_or_404(
        _base_queryset(request.user), id=triaje_id,
    )
    paciente = triaje.episodio.paciente
    signos_items = list((triaje.signos_vitales or {}).items())
    historial = triaje.episodio.triajes.exclude(
        id=triaje.id,
    ).select_related("evaluado_por").order_by("-evaluado_en")[:20]

    return render(request, "dashboard/triajes/detail.html", {
        "page_title": f"Triaje · {triaje.get_clasificacion_display().split(' — ')[0]}",
        "triaje": triaje,
        "paciente": paciente,
        "signos_items": signos_items,
        "historial": historial,
        "can_see_full_names": _can_see_full_names(request.user),
        "can_see_sensitive_pii": _can_see_sensitive_pii(request.user),
    })
