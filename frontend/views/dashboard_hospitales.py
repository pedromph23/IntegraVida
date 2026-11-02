"""Vistas del panel para el módulo Hospitales (F3.e.1 + F5.b).

F3.e.1: lista + detalle + cambiar estado.
F5.b: CRUD completo (create, update, inactivar [soft], reactivar)
      con permisos granulares y scoping por organización.

Soft delete: NO_OPERATIVO (no hay INACTIVO en el modelo). "Inactivar"
marca el hospital como NO_OPERATIVO. "Reactivar" vuelve a DISPONIBLE.
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
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from apps.usuarios.permisos import (
    ACCION_CAMBIAR_ESTADO,
    ACCION_CREAR,
    ACCION_EDITAR,
    ACCION_ELIMINAR,
    orgs_donde_puede,
    tiene_permiso,
)

from frontend.decorators import permiso_requerido
from frontend.forms.hospitales import HospitalForm


PAGE_SIZE = 25


def _base_queryset(user):
    """Hospitales visibles por el user según Membresias ACTIVAS."""
    qs = Hospital.objects.select_related(
        "organizacion", "responsable", "municipio", "parroquia",
    )
    if puede_administrar_plataforma(user):
        return qs
    org_ids = (
        Membresia.objects
        .filter(usuario=user, estado="ACTIVA")
        .values_list("organizacion_id", flat=True)
    )
    return qs.filter(organizacion_id__in=org_ids)


# ── Lista ─────────────────────────────────────────────────────────────
@login_required
@require_GET
def hospitales_list(request):
    qs = _base_queryset(request.user)

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
        "can_write": tiene_permiso(request.user, "hospitales", ACCION_CAMBIAR_ESTADO),
        "can_create": tiene_permiso(request.user, "hospitales", ACCION_CREAR),
        "can_edit": tiene_permiso(request.user, "hospitales", ACCION_EDITAR),
        "can_delete": tiene_permiso(request.user, "hospitales", ACCION_ELIMINAR),
    })


# ── Detalle ───────────────────────────────────────────────────────────
@login_required
@require_GET
def hospital_detail(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    servicios = hospital.servicios_through.select_related(
        "servicio",
    ).order_by("servicio__nombre")[:50]
    recursos = hospital.recursos.order_by("tipo")[:20]

    return render(request, "dashboard/hospitales/detail.html", {
        "page_title": f"Hospital · {hospital.nombre}",
        "hospital": hospital,
        "servicios": servicios,
        "recursos": recursos,
        "estados_permitidos": _transiciones(hospital.estado_operativo, request.user),
        "can_write": tiene_permiso(request.user, "hospitales", ACCION_CAMBIAR_ESTADO, hospital.organizacion),
        "can_edit": tiene_permiso(request.user, "hospitales", ACCION_EDITAR, hospital.organizacion),
        "can_delete": tiene_permiso(request.user, "hospitales", ACCION_ELIMINAR, hospital.organizacion),
    })


def _transiciones(estado_actual, user):
    """Transiciones válidas de EstadoOperativo."""
    if user.is_superuser or user.is_staff:
        todos = {c[0] for c in Hospital.EstadoOperativo.choices}
        return todos - {estado_actual}
    TRANS = {
        "DISPONIBLE":   {"SATURADO", "COLAPSADO", "NO_OPERATIVO"},
        "SATURADO":     {"DISPONIBLE", "COLAPSADO", "NO_OPERATIVO"},
        "COLAPSADO":    {"SATURADO", "NO_OPERATIVO"},
        "NO_OPERATIVO": {"DISPONIBLE", "SATURADO"},
    }
    return TRANS.get(estado_actual, set())


# ── Cambiar estado ────────────────────────────────────────────────────
@login_required
@require_POST
def hospital_cambiar_estado(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "hospitales", ACCION_CAMBIAR_ESTADO, hospital.organizacion):
        return HttpResponseForbidden("Sin permiso para cambiar el estado.")

    nuevo = request.POST.get("estado_operativo", "").strip()
    validos = {c[0] for c in Hospital.EstadoOperativo.choices}
    if nuevo not in validos:
        messages.error(request, "Estado operativo inválido.")
        return redirect("dashboard:hospital_detail", codigo=codigo)

    anterior = hospital.estado_operativo
    if anterior == nuevo:
        messages.info(request, f"El estado ya era {nuevo}.")
        return redirect("dashboard:hospital_detail", codigo=codigo)

    permitidas = _transiciones(anterior, request.user)
    if nuevo not in permitidas:
        messages.error(request, f"Transición no permitida: {anterior} → {nuevo}.")
        return redirect("dashboard:hospital_detail", codigo=codigo)

    with transaction.atomic():
        hospital.estado_operativo = nuevo
        hospital.save(update_fields=["estado_operativo", "actualizado_en"])

    messages.success(request, f"Estado actualizado: {anterior} → {nuevo}.")
    return redirect("dashboard:hospital_detail", codigo=codigo)


# ── Crear ─────────────────────────────────────────────────────────────
@permiso_requerido("hospitales", ACCION_CREAR, redirect_to="dashboard:hospitales_list")
@require_GET
def hospital_create_form(request):
    form = HospitalForm(user=request.user)
    return render(request, "dashboard/hospitales/form.html", {
        "page_title": "Nuevo hospital",
        "form": form,
        "is_create": True,
    })


@permiso_requerido("hospitales", ACCION_CREAR, redirect_to="dashboard:hospitales_list")
@require_POST
def hospital_create_submit(request):
    data = request.POST.copy()
    if not data.get("organizacion"):
        orgs = orgs_donde_puede(request.user, "hospitales", ACCION_CREAR)
        if orgs.count() == 1:
            data["organizacion"] = str(orgs.first().pk)

    form = HospitalForm(data, user=request.user)
    if not form.is_valid():
        return render(request, "dashboard/hospitales/form.html", {
            "page_title": "Nuevo hospital",
            "form": form,
            "is_create": True,
        })

    with transaction.atomic():
        hospital = form.save(commit=False)
        if not hospital.estado_operativo:
            hospital.estado_operativo = Hospital.EstadoOperativo.DISPONIBLE
        hospital.save()

    messages.success(request, f"Hospital '{hospital.nombre}' creado.")
    return redirect("dashboard:hospital_detail", codigo=hospital.codigo)


# ── Editar ────────────────────────────────────────────────────────────
@login_required
@require_GET
def hospital_update_form(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "hospitales", ACCION_EDITAR, hospital.organizacion):
        return HttpResponseForbidden("Sin permiso para editar este hospital.")

    form = HospitalForm(instance=hospital, user=request.user)
    return render(request, "dashboard/hospitales/form.html", {
        "page_title": f"Editar · {hospital.nombre}",
        "form": form,
        "is_create": False,
        "hospital": hospital,
    })


@login_required
@require_POST
def hospital_update_submit(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "hospitales", ACCION_EDITAR, hospital.organizacion):
        return HttpResponseForbidden("Sin permiso para editar este hospital.")

    form = HospitalForm(request.POST, instance=hospital, user=request.user)
    if not form.is_valid():
        return render(request, "dashboard/hospitales/form.html", {
            "page_title": f"Editar · {hospital.nombre}",
            "form": form,
            "is_create": False,
            "hospital": hospital,
        })

    with transaction.atomic():
        hospital = form.save()

    messages.success(request, "Hospital actualizado.")
    return redirect("dashboard:hospital_detail", codigo=hospital.codigo)


# ── Inactivar (soft: NO_OPERATIVO) ────────────────────────────────────
@login_required
@require_GET
def hospital_inactivar_confirm(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "hospitales", ACCION_ELIMINAR, hospital.organizacion):
        return HttpResponseForbidden("Sin permiso para inactivar este hospital.")
    return render(request, "dashboard/hospitales/confirm_inactivar.html", {
        "page_title": f"Inactivar · {hospital.nombre}",
        "hospital": hospital,
    })


@login_required
@require_POST
def hospital_inactivar_submit(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "hospitales", ACCION_ELIMINAR, hospital.organizacion):
        return HttpResponseForbidden("Sin permiso para inactivar este hospital.")

    if hospital.estado_operativo == Hospital.EstadoOperativo.NO_OPERATIVO:
        messages.info(request, "El hospital ya está NO_OPERATIVO.")
        return redirect("dashboard:hospital_detail", codigo=hospital.codigo)

    with transaction.atomic():
        hospital.estado_operativo = Hospital.EstadoOperativo.NO_OPERATIVO
        hospital.save(update_fields=["estado_operativo", "actualizado_en"])

    messages.success(
        request,
        "Hospital marcado como NO_OPERATIVO. No aparece en el portal público.",
    )
    return redirect("dashboard:hospitales_list")


# ── Reactivar ─────────────────────────────────────────────────────────
@login_required
@require_POST
def hospital_reactivar(request, codigo):
    hospital = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "hospitales", ACCION_ELIMINAR, hospital.organizacion):
        return HttpResponseForbidden("Sin permiso para reactivar este hospital.")

    if hospital.estado_operativo != Hospital.EstadoOperativo.NO_OPERATIVO:
        messages.info(request, "El hospital no está NO_OPERATIVO.")
        return redirect("dashboard:hospital_detail", codigo=hospital.codigo)

    with transaction.atomic():
        hospital.estado_operativo = Hospital.EstadoOperativo.DISPONIBLE
        hospital.save(update_fields=["estado_operativo", "actualizado_en"])

    messages.success(request, "Hospital reactivado (DISPONIBLE).")
    return redirect("dashboard:hospital_detail", codigo=hospital.codigo)
