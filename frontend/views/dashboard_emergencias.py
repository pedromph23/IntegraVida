"""Vistas del panel para el módulo Emergencias (F3.d + F5.c).

F3.d: lista + detalle + cambiar estado (transiciones whitelist).
F5.c: agregado create + update con permisos granulares y scoping.

NO hay acción "eliminar": una emergencia es un evento que ocurrió.
"Cerrar" = cambiar estado a RESUELTA (completada) o DESCARTADA (falsa
alarma). El modelo no tiene campo soft_delete.

Reglas de permisos:
- ADMIN_ORG, COORDINADOR: ver, crear, editar, cambiar estado.
- OPERADOR, SANITARIO: ver, cambiar estado.
- LOGISTICA, CONSULTA: ver solo.
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
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from apps.usuarios.permisos import (
    ACCION_CAMBIAR_ESTADO,
    ACCION_CREAR,
    ACCION_EDITAR,
    orgs_donde_puede,
    tiene_permiso,
)

from frontend.decorators import permiso_requerido
from frontend.forms.emergencias import EmergenciaForm


PAGE_SIZE = 25

# Transiciones válidas (el modelo no las define; whitelist explícita)
TRANSICIONES_VALIDAS = {
    "RECIBIDA":        {"EN_VERIFICACION", "DESCARTADA"},
    "EN_VERIFICACION": {"CONFIRMADA", "DESCARTADA"},
    "CONFIRMADA":      {"EN_ATENCION", "DESCARTADA"},
    "EN_ATENCION":     {"RESUELTA", "DESCARTADA"},
    "RESUELTA":        set(),
    "DESCARTADA":      set(),
}


def _base_queryset(user):
    """Emergencias visibles por el user según Membresias ACTIVAS.

    Si la emergencia no tiene organizacion (null), solo superuser la ve.
    """
    qs = Emergencia.objects.select_related(
        "municipio", "parroquia", "organizacion", "reportada_por",
    )
    if puede_administrar_plataforma(user):
        return qs
    org_ids = (
        Membresia.objects
        .filter(usuario=user, estado="ACTIVA")
        .values_list("organizacion_id", flat=True)
    )
    return qs.filter(organizacion_id__in=org_ids)


def _transiciones_permitidas(estado_actual, user):
    if user.is_superuser or user.is_staff:
        todos = {c[0] for c in Emergencia.Estado.choices}
        return todos - {estado_actual}
    return TRANSICIONES_VALIDAS.get(estado_actual, set())


# ── Lista ─────────────────────────────────────────────────────────────
@login_required
@require_GET
def emergencias_list(request):
    qs = _base_queryset(request.user)

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
        "can_write": tiene_permiso(request.user, "emergencias", ACCION_CAMBIAR_ESTADO),
        "can_create": tiene_permiso(request.user, "emergencias", ACCION_CREAR),
        "can_edit": tiene_permiso(request.user, "emergencias", ACCION_EDITAR),
    })


# ── Detalle ───────────────────────────────────────────────────────────
@login_required
@require_GET
def emergencia_detail(request, emergencia_id):
    emergencia = get_object_or_404(
        _base_queryset(request.user), id=emergencia_id,
    )
    reportes = emergencia.reportes.select_related(
        "reportante",
    ).order_by("-recibido_en")[:20]

    return render(request, "dashboard/emergencias/detail.html", {
        "page_title": f"Emergencia · {emergencia.titulo}",
        "emergencia": emergencia,
        "reportes": reportes,
        "estados_permitidos": _transiciones_permitidas(
            emergencia.estado, request.user,
        ),
        "can_write": tiene_permiso(
            request.user, "emergencias", ACCION_CAMBIAR_ESTADO,
            emergencia.organizacion,
        ),
        "can_edit": tiene_permiso(
            request.user, "emergencias", ACCION_EDITAR,
            emergencia.organizacion,
        ),
    })


# ── Cambiar estado ────────────────────────────────────────────────────
@login_required
@require_POST
def emergencia_cambiar_estado(request, emergencia_id):
    emergencia = get_object_or_404(_base_queryset(request.user), id=emergencia_id)

    if not tiene_permiso(
        request.user, "emergencias", ACCION_CAMBIAR_ESTADO,
        emergencia.organizacion,
    ):
        return HttpResponseForbidden("Sin permiso para modificar emergencias.")

    nuevo = request.POST.get("estado", "").strip()
    validos = {c[0] for c in Emergencia.Estado.choices}
    if nuevo not in validos:
        messages.error(request, "Estado inválido.")
        return redirect("dashboard:emergencia_detail", emergencia_id=emergencia.id)

    anterior = emergencia.estado
    if anterior == nuevo:
        messages.info(request, f"La emergencia ya estaba en {nuevo}.")
        return redirect("dashboard:emergencia_detail", emergencia_id=emergencia.id)

    permitidas = _transiciones_permitidas(anterior, request.user)
    if nuevo not in permitidas:
        messages.error(
            request, f"Transición no permitida: {anterior} → {nuevo}.",
        )
        return redirect("dashboard:emergencia_detail", emergencia_id=emergencia.id)

    with transaction.atomic():
        emergencia.estado = nuevo
        emergencia.save(update_fields=["estado", "actualizada_en"])

    messages.success(request, f"Estado actualizado: {anterior} → {nuevo}.")
    return redirect("dashboard:emergencia_detail", emergencia_id=emergencia.id)


# ── Crear ─────────────────────────────────────────────────────────────
@permiso_requerido("emergencias", ACCION_CREAR, redirect_to="dashboard:emergencias_list")
@require_GET
def emergencia_create_form(request):
    form = EmergenciaForm(user=request.user)
    return render(request, "dashboard/emergencias/form.html", {
        "page_title": "Nueva emergencia",
        "form": form,
        "is_create": True,
    })


@permiso_requerido("emergencias", ACCION_CREAR, redirect_to="dashboard:emergencias_list")
@require_POST
def emergencia_create_submit(request):
    data = request.POST.copy()
    if not data.get("organizacion"):
        orgs = orgs_donde_puede(request.user, "emergencias", ACCION_CREAR)
        if orgs.count() == 1:
            data["organizacion"] = str(orgs.first().pk)

    form = EmergenciaForm(data, user=request.user)
    if not form.is_valid():
        return render(request, "dashboard/emergencias/form.html", {
            "page_title": "Nueva emergencia",
            "form": form,
            "is_create": True,
        })

    with transaction.atomic():
        emergencia = form.save(commit=False)
        emergencia.estado = Emergencia.Estado.RECIBIDA
        if not emergencia.reportada_por_id:
            emergencia.reportada_por = request.user
        emergencia.save()

    messages.success(request, f"Emergencia '{emergencia.titulo}' creada.")
    return redirect("dashboard:emergencia_detail", emergencia_id=emergencia.id)


# ── Editar ────────────────────────────────────────────────────────────
@login_required
@require_GET
def emergencia_update_form(request, emergencia_id):
    emergencia = get_object_or_404(_base_queryset(request.user), id=emergencia_id)
    if not tiene_permiso(
        request.user, "emergencias", ACCION_EDITAR, emergencia.organizacion,
    ):
        return HttpResponseForbidden("Sin permiso para editar esta emergencia.")

    form = EmergenciaForm(instance=emergencia, user=request.user)
    return render(request, "dashboard/emergencias/form.html", {
        "page_title": f"Editar · {emergencia.titulo}",
        "form": form,
        "is_create": False,
        "emergencia": emergencia,
    })


@login_required
@require_POST
def emergencia_update_submit(request, emergencia_id):
    emergencia = get_object_or_404(_base_queryset(request.user), id=emergencia_id)
    if not tiene_permiso(
        request.user, "emergencias", ACCION_EDITAR, emergencia.organizacion,
    ):
        return HttpResponseForbidden("Sin permiso para editar esta emergencia.")

    form = EmergenciaForm(request.POST, instance=emergencia, user=request.user)
    if not form.is_valid():
        return render(request, "dashboard/emergencias/form.html", {
            "page_title": f"Editar · {emergencia.titulo}",
            "form": form,
            "is_create": False,
            "emergencia": emergencia,
        })

    with transaction.atomic():
        emergencia = form.save()

    messages.success(request, "Emergencia actualizada.")
    return redirect("dashboard:emergencia_detail", emergencia_id=emergencia.id)
