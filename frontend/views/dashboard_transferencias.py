"""Vistas del panel para el módulo Transferencias (F3.g.2).

Lógica de estados y side effects de stock vive en apps.inventario.services:
- transicionar_transferencia: BORRADOR/APROBADA -> APROBADA/RECHAZADA
- despachar_transferencia: APROBADA -> EN_TRANSITO (SALIDA origen)
- recibir_transferencia: EN_TRANSITO -> RECIBIDA (ENTRADA destino)
- cancelar_transferencia: desde no-terminal -> CANCELADA
El POST dispatcher enruta por acción al servicio específico.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.inventario.models import Transferencia
from apps.inventario.services import (
    _init_transiciones,
    cancelar_transferencia,
    despachar_transferencia,
    recibir_transferencia,
    transicionar_transferencia,
)
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma

PAGE_SIZE = 25

ACCIONES_POR_ESTADO = {
    "BORRADOR":    ["aprobar", "rechazar", "cancelar"],
    "APROBADA":    ["despachar", "cancelar"],
    "EN_TRANSITO": ["recibir", "cancelar"],
    "RECIBIDA":    [],
    "RECHAZADA":   [],
    "CANCELADA":   [],
}


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _transferencias_visibles(user):
    qs = Transferencia.objects.all()
    if puede_administrar_plataforma(user):
        return qs
    org_ids = _org_ids_del_usuario(user)
    if not org_ids:
        return qs.none()
    return qs.filter(
        Q(almacen_origen__organizacion_id__in=org_ids)
        | Q(almacen_destino__organizacion_id__in=org_ids)
    )


def _can_write_transferencias(user, transferencia):
    if puede_administrar_plataforma(user):
        return True
    org_ids = _org_ids_del_usuario(user)
    return (
        transferencia.almacen_origen.organizacion_id in org_ids
        or transferencia.almacen_destino.organizacion_id in org_ids
    )


@login_required
@require_GET
def transferencias_list(request):
    qs = _transferencias_visibles(request.user).select_related(
        "almacen_origen", "almacen_destino",
    )

    estado = request.GET.get("estado", "")
    estados_validos = {v for v, _ in Transferencia.Estado.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado=estado)

    prioridad = request.GET.get("prioridad", "")
    prioridades_validas = {v for v, _ in Transferencia.Prioridad.choices}
    if prioridad not in prioridades_validas:
        prioridad = ""
    if prioridad:
        qs = qs.filter(prioridad=prioridad)

    qs = qs.order_by("-solicitada_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/transferencias/list.html", {
        "page_title": "Transferencias",
        "page_obj": page,
        "total": paginator.count,
        "filters": {"estado": estado, "prioridad": prioridad},
        "estados": Transferencia.Estado.choices,
        "prioridades": Transferencia.Prioridad.choices,
    })


@login_required
@require_GET
def transferencia_detail(request, transferencia_id):
    t = get_object_or_404(
        _transferencias_visibles(request.user).select_related(
            "almacen_origen__organizacion",
            "almacen_destino__organizacion",
            "solicitada_por", "aprobada_por",
            "despachada_por", "recibida_por",
        ),
        id=transferencia_id,
    )
    detalles = t.detalles.select_related(
        "insumo", "lote_origen",
    ).order_by("insumo__nombre")
    transiciones = t.transiciones.select_related("usuario").order_by("-creado_en")

    can_write = _can_write_transferencias(request.user, t)
    acciones = ACCIONES_POR_ESTADO.get(t.estado, []) if can_write else []

    return render(request, "dashboard/transferencias/detail.html", {
        "page_title": f"Transferencia · {t.get_estado_display()}",
        "transferencia": t,
        "detalles": detalles,
        "transiciones": transiciones,
        "acciones_disponibles": acciones,
    })


@login_required
@require_POST
def transferencia_accion(request, transferencia_id):
    t = get_object_or_404(
        _transferencias_visibles(request.user).select_related(
            "almacen_origen__organizacion",
            "almacen_destino__organizacion",
        ),
        id=transferencia_id,
    )
    if not _can_write_transferencias(request.user, t):
        return HttpResponseForbidden("Sin permiso para operar esta transferencia.")

    accion = request.POST.get("accion", "").strip()
    motivo = request.POST.get("motivo", "").strip()

    try:
        if accion == "aprobar":
            transicionar_transferencia(
                transferencia_id=transferencia_id,
                nuevo_estado="APROBADA",
                usuario=request.user, motivo=motivo, request=request,
            )
        elif accion == "rechazar":
            transicionar_transferencia(
                transferencia_id=transferencia_id,
                nuevo_estado="RECHAZADA",
                usuario=request.user, motivo=motivo, request=request,
            )
        elif accion == "despachar":
            despachar_transferencia(
                transferencia_id=transferencia_id,
                usuario=request.user, motivo=motivo, request=request,
            )
        elif accion == "recibir":
            recibir_transferencia(
                transferencia_id=transferencia_id,
                usuario=request.user, motivo=motivo, request=request,
            )
        elif accion == "cancelar":
            cancelar_transferencia(
                transferencia_id=transferencia_id,
                usuario=request.user, motivo=motivo, request=request,
            )
        else:
            messages.error(request, f"Acción inválida: {accion}.")
            return redirect(
                "dashboard:transferencia_detail",
                transferencia_id=transferencia_id,
            )

        messages.success(request, f"Acción '{accion}' aplicada.")

    except PermissionDenied:
        return HttpResponseForbidden("Sin permiso sobre esta transferencia.")
    except ValidationError as e:
        if hasattr(e, "message_dict"):
            textos = [
                f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()
            ]
            detalle = "; ".join(textos)
        else:
            detalle = "; ".join(e.messages)
        messages.error(request, detalle)

    return redirect(
        "dashboard:transferencia_detail",
        transferencia_id=transferencia_id,
    )
