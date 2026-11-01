"""Vistas del panel para el módulo Hospitales (F3.e.1).

Patrón espejo de dashboard_refugios.py (F3.c) y dashboard_emergencias.py
(F3.d): un módulo por archivo, transiciones whitelist, staff puede forzar.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.hospitales.models import Hospital


HOSPITAL_WRITE_GROUPS = {"ADMIN", "COORDINADOR", "OPERADOR_HOSPITAL"}
PAGE_SIZE = 25

TRANSICIONES_VALIDAS = {
    "DISPONIBLE":   {"SATURADO", "COLAPSADO", "NO_OPERATIVO"},
    "SATURADO":     {"DISPONIBLE", "COLAPSADO", "NO_OPERATIVO"},
    "COLAPSADO":    {"SATURADO", "NO_OPERATIVO"},
    "NO_OPERATIVO": {"DISPONIBLE", "SATURADO"},
}


def _can_write_hospitales(user):
    if user.is_superuser or user.is_staff:
        return True
    groups = set(user.groups.values_list("name", flat=True))
    return bool(groups & HOSPITAL_WRITE_GROUPS)


def _transiciones_permitidas(estado_actual, user):
    if user.is_superuser or user.is_staff:
        todos = {c[0] for c in Hospital.EstadoOperativo.choices}
        return todos - {estado_actual}
    return TRANSICIONES_VALIDAS.get(estado_actual, set())


def _base_queryset():
    return Hospital.objects.select_related(
        "organizacion", "responsable", "municipio", "parroquia",
    )


@login_required
@require_GET
def hospitales_list(request):
    qs = _base_queryset()

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(direccion__icontains=q)
            | Q(codigo__icontains=q)
        )

    estado = request.GET.get("estado_operativo", "")
    estados_validos = {c[0] for c in Hospital.EstadoOperativo.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado_operativo=estado)

    tipo = request.GET.get("tipo", "")
    tipos_validos = {c[0] for c in Hospital.Tipo.choices}
    if tipo not in tipos_validos:
        tipo = ""
    if tipo:
        qs = qs.filter(tipo=tipo)

    nivel = request.GET.get("nivel", "")
    niveles_validos = {c[0] for c in Hospital.Nivel.choices}
    if nivel not in niveles_validos:
        nivel = ""
    if nivel:
        qs = qs.filter(nivel=nivel)

    qs = qs.order_by("-creado_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/hospitales/list.html", {
        "page_title": "Hospitales",
        "page_obj": page,
        "total": paginator.count,
        "filters": {
            "q": q, "estado_operativo": estado, "tipo": tipo, "nivel": nivel,
        },
        "estados": Hospital.EstadoOperativo.choices,
        "tipos": Hospital.Tipo.choices,
        "niveles": Hospital.Nivel.choices,
        "can_write": _can_write_hospitales(request.user),
    })


@login_required
@require_GET
def hospital_detail(request, codigo):
    hospital = get_object_or_404(_base_queryset(), codigo=codigo)
    servicios = hospital.servicios_through.select_related(
        "servicio",
    ).order_by("servicio__nombre")[:50]
    recursos = hospital.recursos.order_by("tipo")[:20]

    return render(request, "dashboard/hospitales/detail.html", {
        "page_title": f"Hospital · {hospital.nombre}",
        "hospital": hospital,
        "servicios": servicios,
        "recursos": recursos,
        "estados_permitidos": _transiciones_permitidas(
            hospital.estado_operativo, request.user,
        ),
        "can_write": _can_write_hospitales(request.user),
    })


@login_required
@require_POST
def hospital_cambiar_estado(request, codigo):
    if not _can_write_hospitales(request.user):
        return HttpResponseForbidden(
            "No tienes permiso para modificar hospitales."
        )

    hospital = get_object_or_404(Hospital, codigo=codigo)

    nuevo = request.POST.get("estado_operativo", "").strip()
    validos = {c[0] for c in Hospital.EstadoOperativo.choices}
    if nuevo not in validos:
        messages.error(request, "Estado operativo inválido.")
        return redirect("dashboard:hospital_detail", codigo=codigo)

    anterior = hospital.estado_operativo
    if anterior == nuevo:
        messages.info(request, f"El estado ya era {nuevo}.")
        return redirect("dashboard:hospital_detail", codigo=codigo)

    permitidas = _transiciones_permitidas(anterior, request.user)
    if nuevo not in permitidas:
        messages.error(
            request,
            f"Transición no permitida: {anterior} → {nuevo}.",
        )
        return redirect("dashboard:hospital_detail", codigo=codigo)

    with transaction.atomic():
        hospital.estado_operativo = nuevo
        hospital.save(update_fields=["estado_operativo", "actualizado_en"])

    messages.success(request, f"Estado actualizado: {anterior} → {nuevo}.")
    return redirect("dashboard:hospital_detail", codigo=codigo)
