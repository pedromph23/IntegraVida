"""Vistas del panel para el módulo Refugios (F3.c + F5.a).

F3.c: lista + detalle + cambiar estado (lectura + acción de flujo).
F5.a: agregadas refugio_create / refugio_update / refugio_inactivar
      con permisos granulares y scoping por organización.

Reglas de permisos (Membresia.rol + compatibilidad con auth.Group):
- ADMIN_ORGANIZACION: ver, crear, editar, eliminar (inactivar), cambiar estado.
- COORDINADOR:       ver, crear, editar, cambiar estado.
- OPERADOR:          ver, cambiar estado.
- SANITARIO/LOGISTICA/CONSULTA: ver solo.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from apps.refugios.models import Refugio
from apps.usuarios.permisos import (
    ACCION_CAMBIAR_ESTADO,
    ACCION_CREAR,
    ACCION_EDITAR,
    ACCION_ELIMINAR,
    ACCION_VER,
    tiene_permiso,
)

from frontend.decorators import permiso_requerido
from frontend.forms.refugios import RefugioForm


PAGE_SIZE = 25


# ── Helpers de scoping y permisos ─────────────────────────────────────
def _base_queryset(user):
    """Refugios visibles por el user según sus Membresías ACTIVAS."""
    qs = Refugio.objects.select_related(
        "organizacion", "responsable", "municipio", "parroquia"
    )
    if puede_administrar_plataforma(user):
        return qs
    org_ids = (
        Membresia.objects
        .filter(usuario=user, estado="ACTIVA")
        .values_list("organizacion_id", flat=True)
    )
    return qs.filter(organizacion_id__in=org_ids)


def _can_write_refugios(user, refugio=None, accion=ACCION_CAMBIAR_ESTADO):
    """Compat con F3.c: determinar si el user puede editar el refugio."""
    if refugio is None:
        return tiene_permiso(user, "refugios", accion)
    return tiene_permiso(user, "refugios", accion, refugio.organizacion)


# ── Lista ─────────────────────────────────────────────────────────────
@login_required
@require_GET
def refugios_list(request):
    qs = _base_queryset(request.user)

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(direccion__icontains=q)
            | Q(codigo__icontains=q)
        )

    estado = request.GET.get("estado_operativo", "")
    estados_validos = {c[0] for c in Refugio.EstadoOperativo.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado_operativo=estado)

    tipo = request.GET.get("tipo", "")
    tipos_validos = {c[0] for c in Refugio.Tipo.choices}
    if tipo not in tipos_validos:
        tipo = ""
    if tipo:
        qs = qs.filter(tipo=tipo)

    qs = qs.order_by("-creado_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/refugios/list.html", {
        "page_title": "Refugios",
        "page_obj": page,
        "total": paginator.count,
        "filters": {"q": q, "estado_operativo": estado, "tipo": tipo},
        "estados": Refugio.EstadoOperativo.choices,
        "tipos": Refugio.Tipo.choices,
        "can_write": _can_write_refugios(request.user),
        "can_create": tiene_permiso(request.user, "refugios", ACCION_CREAR),
        "can_edit": tiene_permiso(request.user, "refugios", ACCION_EDITAR),
        "can_delete": tiene_permiso(request.user, "refugios", ACCION_ELIMINAR),
    })


# ── Detalle ───────────────────────────────────────────────────────────
@login_required
@require_GET
def refugio_detail(request, codigo):
    refugio = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    necesidades = refugio.necesidades.all().order_by(
        "-prioridad", "-creada_en",
    )[:50]
    registros = refugio.registros_ocupacion.select_related(
        "registrado_por",
    ).order_by("-creado_en")[:20]

    return render(request, "dashboard/refugios/detail.html", {
        "page_title": f"Refugio · {refugio.nombre}",
        "refugio": refugio,
        "necesidades": necesidades,
        "registros": registros,
        "estados": Refugio.EstadoOperativo.choices,
        "can_write": _can_write_refugios(request.user, refugio, ACCION_CAMBIAR_ESTADO),
        "can_edit": tiene_permiso(request.user, "refugios", ACCION_EDITAR, refugio.organizacion),
        "can_delete": tiene_permiso(request.user, "refugios", ACCION_ELIMINAR, refugio.organizacion),
    })


# ── Crear ─────────────────────────────────────────────────────────────
@permiso_requerido("refugios", ACCION_CREAR, redirect_to="dashboard:refugios_list")
@require_GET
def refugio_create_form(request):
    form = RefugioForm(user=request.user)
    return render(request, "dashboard/refugios/form.html", {
        "page_title": "Nuevo refugio",
        "form": form,
        "is_create": True,
    })


@permiso_requerido("refugios", ACCION_CREAR, redirect_to="dashboard:refugios_list")
@require_POST
def refugio_create_submit(request):
    data = request.POST.copy()
    if not data.get("organizacion"):
        from apps.usuarios.permisos import orgs_donde_puede
        orgs = orgs_donde_puede(request.user, "refugios", ACCION_CREAR)
        if orgs.count() == 1:
            data["organizacion"] = str(orgs.first().pk)

    form = RefugioForm(data, user=request.user)
    if not form.is_valid():
        # DEBUG: qué falla exactamente
        return render(request, "dashboard/refugios/form.html", {
            "page_title": "Nuevo refugio",
            "form": form,
            "is_create": True,
        })

    with transaction.atomic():
        refugio = form.save(commit=False)
        if refugio.ocupacion_actual is None:
            refugio.ocupacion_actual = 0
        if not refugio.estado_operativo:
            refugio.estado_operativo = Refugio.EstadoOperativo.ACTIVO
        refugio.save()

    messages.success(request, f"Refugio '{refugio.nombre}' creado.")
    return redirect("dashboard:refugio_detail", codigo=refugio.codigo)


@login_required
@require_GET
def refugio_update_form(request, codigo):
    refugio = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "refugios", ACCION_EDITAR, refugio.organizacion):
        return HttpResponseForbidden("Sin permiso para editar este refugio.")

    form = RefugioForm(instance=refugio, user=request.user)
    return render(request, "dashboard/refugios/form.html", {
        "page_title": f"Editar · {refugio.nombre}",
        "form": form,
        "is_create": False,
        "refugio": refugio,
    })


@login_required
@require_POST
def refugio_update_submit(request, codigo):
    refugio = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "refugios", ACCION_EDITAR, refugio.organizacion):
        return HttpResponseForbidden("Sin permiso para editar este refugio.")

    form = RefugioForm(request.POST, instance=refugio, user=request.user)
    if not form.is_valid():
        # DEBUG: qué está fallando
        return render(request, "dashboard/refugios/form.html", {
            "page_title": f"Editar · {refugio.nombre}",
            "form": form,
            "is_create": False,
            "refugio": refugio,
        })

    with transaction.atomic():
        refugio = form.save()

    messages.success(request, "Refugio actualizado.")
    return redirect("dashboard:refugio_detail", codigo=refugio.codigo)


# ── Inactivar (soft delete) ───────────────────────────────────────────
@login_required
@require_GET
def refugio_inactivar_confirm(request, codigo):
    refugio = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "refugios", ACCION_ELIMINAR, refugio.organizacion):
        return HttpResponseForbidden("Sin permiso para inactivar este refugio.")
    return render(request, "dashboard/refugios/confirm_inactivar.html", {
        "page_title": f"Inactivar · {refugio.nombre}",
        "refugio": refugio,
    })


@login_required
@require_POST
def refugio_inactivar_submit(request, codigo):
    refugio = get_object_or_404(_base_queryset(request.user), codigo=codigo)
    if not tiene_permiso(request.user, "refugios", ACCION_ELIMINAR, refugio.organizacion):
        return HttpResponseForbidden("Sin permiso para inactivar este refugio.")

    if refugio.estado_operativo == Refugio.EstadoOperativo.INACTIVO:
        messages.info(request, "El refugio ya está inactivo.")
        return redirect("dashboard:refugio_detail", codigo=refugio.codigo)

    with transaction.atomic():
        refugio.estado_operativo = Refugio.EstadoOperativo.INACTIVO
        refugio.save(update_fields=["estado_operativo", "actualizado_en"])

    messages.success(
        request,
        "Refugio marcado como INACTIVO. No aparecerá en el portal público.",
    )
    return redirect("dashboard:refugios_list")


# ── Cambiar estado (F3.c refactorizado con permisos) ──────────────────
@login_required
@require_POST
def refugio_cambiar_estado(request, codigo):
    refugio = get_object_or_404(_base_queryset(request.user), codigo=codigo)

    if not tiene_permiso(
        request.user, "refugios", ACCION_CAMBIAR_ESTADO, refugio.organizacion,
    ):
        return HttpResponseForbidden("Sin permiso para cambiar el estado.")

    nuevo = request.POST.get("estado_operativo", "").strip()
    validos = {c[0] for c in Refugio.EstadoOperativo.choices}
    if nuevo not in validos:
        messages.error(request, "Estado operativo inválido.")
        return redirect("dashboard:refugio_detail", codigo=codigo)

    anterior = refugio.estado_operativo
    if anterior == nuevo:
        messages.info(request, f"El estado ya era {nuevo}.")
        return redirect("dashboard:refugio_detail", codigo=codigo)

    with transaction.atomic():
        refugio.estado_operativo = nuevo
        refugio.save(update_fields=["estado_operativo", "actualizado_en"])

    messages.success(request, f"Estado actualizado: {anterior} → {nuevo}.")
    return redirect("dashboard:refugio_detail", codigo=codigo)
