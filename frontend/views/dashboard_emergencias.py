"""Vistas del panel para el módulo Emergencias (F3.d).

El modelo no define transiciones de estado ni historial. F3.d usa una
whitelist explícita en TRANSICIONES_VALIDAS; el superuser/is_staff puede
forzar cualquier transición.

Patrón espejo de dashboard_refugios.py (F3.c).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.emergencias.models import Emergencia


EMERGENCIA_WRITE_GROUPS = {"ADMIN", "COORDINADOR", "OPERADOR_EMERGENCIA"}
PAGE_SIZE = 25

# Transiciones válidas (el modelo no las define; ver docstring)
TRANSICIONES_VALIDAS = {
    "RECIBIDA":        {"EN_VERIFICACION", "DESCARTADA"},
    "EN_VERIFICACION": {"CONFIRMADA", "DESCARTADA"},
    "CONFIRMADA":      {"EN_ATENCION", "DESCARTADA"},
    "EN_ATENCION":     {"RESUELTA", "DESCARTADA"},
    "RESUELTA":        set(),
    "DESCARTADA":      set(),
}


def _can_write_emergencias(user):
    if user.is_superuser or user.is_staff:
        return True
    groups = set(user.groups.values_list("name", flat=True))
    return bool(groups & EMERGENCIA_WRITE_GROUPS)


def _transiciones_permitidas(estado_actual, user):
    if user.is_superuser or user.is_staff:
        todos = {c[0] for c in Emergencia.Estado.choices}
        return todos - {estado_actual}
    return TRANSICIONES_VALIDAS.get(estado_actual, set())


def _base_queryset():
    return Emergencia.objects.select_related(
        "municipio", "parroquia", "organizacion", "reportada_por",
    )


@login_required
@require_GET
def emergencias_list(request):
    qs = _base_queryset()

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(titulo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(ubicacion_texto__icontains=q)
        )

    estado = request.GET.get("estado", "")
    estados_validos = {c[0] for c in Emergencia.Estado.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado=estado)

    categoria = request.GET.get("categoria", "")
    categorias_validas = {c[0] for c in Emergencia.Categoria.choices}
    if categoria not in categorias_validas:
        categoria = ""
    if categoria:
        qs = qs.filter(categoria=categoria)

    qs = qs.order_by("-creada_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/emergencias/list.html", {
        "page_title": "Emergencias",
        "page_obj": page,
        "total": paginator.count,
        "filters": {"q": q, "estado": estado, "categoria": categoria},
        "estados": Emergencia.Estado.choices,
        "categorias": Emergencia.Categoria.choices,
        "can_write": _can_write_emergencias(request.user),
    })


@login_required
@require_GET
def emergencia_detail(request, emergencia_id):
    emergencia = get_object_or_404(
        _base_queryset(), id=emergencia_id,
    )
    reportes = emergencia.reportes.select_related(
        "reportante"
    ).order_by("-recibido_en")[:20]

    return render(request, "dashboard/emergencias/detail.html", {
        "page_title": f"Emergencia · {emergencia.titulo}",
        "emergencia": emergencia,
        "reportes": reportes,
        "estados_permitidos": _transiciones_permitidas(
            emergencia.estado, request.user,
        ),
        "can_write": _can_write_emergencias(request.user),
    })


@login_required
@require_POST
def emergencia_cambiar_estado(request, emergencia_id):
    if not _can_write_emergencias(request.user):
        return HttpResponseForbidden(
            "No tienes permiso para modificar emergencias."
        )

    emergencia = get_object_or_404(Emergencia, id=emergencia_id)

    nuevo = request.POST.get("estado", "").strip()
    validos = {c[0] for c in Emergencia.Estado.choices}
    if nuevo not in validos:
        messages.error(request, "Estado inválido.")
        return redirect(
            "dashboard:emergencia_detail", emergencia_id=emergencia.id,
        )

    anterior = emergencia.estado
    if anterior == nuevo:
        messages.info(request, f"La emergencia ya estaba en {nuevo}.")
        return redirect(
            "dashboard:emergencia_detail", emergencia_id=emergencia.id,
        )

    permitidas = _transiciones_permitidas(anterior, request.user)
    if nuevo not in permitidas:
        messages.error(
            request,
            f"Transición no permitida: {anterior} → {nuevo}.",
        )
        return redirect(
            "dashboard:emergencia_detail", emergencia_id=emergencia.id,
        )

    with transaction.atomic():
        emergencia.estado = nuevo
        emergencia.save(update_fields=["estado", "actualizada_en"])

    messages.success(request, f"Estado actualizado: {anterior} → {nuevo}.")
    return redirect(
        "dashboard:emergencia_detail", emergencia_id=emergencia.id,
    )
