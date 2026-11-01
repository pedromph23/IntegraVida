"""Vistas del panel para el módulo Entregas (F3.g.3).

Lógica de estados + side effects de stock vive en apps.inventario.services:
- enviar_entrega: BORRADOR -> ENVIADA (SALIDA en origen)
- recibir_entrega: ENVIADA -> RECIBIDA (ENTRADA en destino)
- cancelar_entrega: BORRADOR/ENVIADA -> CANCELADA (restaura si ENVIADA)
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

from apps.inventario.models import Entrega
from apps.inventario.services import (
    cancelar_entrega,
    enviar_entrega,
    recibir_entrega,
)
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma

PAGE_SIZE = 25

ACCIONES_POR_ESTADO = {
    "BORRADOR": ["enviar", "cancelar"],
    "ENVIADA":  ["recibir", "cancelar"],
    "RECIBIDA": [],
    "CANCELADA": [],
}


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _entregas_visibles(user):
    qs = Entrega.objects.all()
    if puede_administrar_plataforma(user):
        return qs
    org_ids = _org_ids_del_usuario(user)
    if not org_ids:
        return qs.none()
    return qs.filter(
        Q(almacen_origen__organizacion_id__in=org_ids)
        | Q(hospital__organizacion_id__in=org_ids)
        | Q(refugio__organizacion_id__in=org_ids)
    )


def _can_write_entregas(user, entrega):
    if puede_administrar_plataforma(user):
        return True
    org_ids = _org_ids_del_usuario(user)
    if entrega.almacen_origen.organizacion_id in org_ids:
        return True
    if entrega.hospital and entrega.hospital.organizacion_id in org_ids:
        return True
    if entrega.refugio and entrega.refugio.organizacion_id in org_ids:
        return True
    return False


@login_required
@require_GET
def entregas_list(request):
    qs = _entregas_visibles(request.user).select_related(
        "almacen_origen", "hospital", "refugio",
    )

    estado = request.GET.get("estado", "")
    estados_validos = {v for v, _ in Entrega.Estado.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado=estado)

    qs = qs.order_by("-solicitada_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/entregas/list.html", {
        "page_title": "Entregas",
        "page_obj": page,
        "total": paginator.count,
        "filters": {"estado": estado},
        "estados": Entrega.Estado.choices,
    })


@login_required
@require_GET
def entrega_detail(request, entrega_id):
    e = get_object_or_404(
        _entregas_visibles(request.user).select_related(
            "almacen_origen__organizacion",
            "hospital__organizacion",
            "refugio__organizacion",
            "solicitada_por", "enviada_por", "recibida_por",
        ),
        id=entrega_id,
    )
    detalles = e.detalles.select_related("insumo", "lote").order_by("insumo__nombre")
    transiciones = e.transiciones.select_related("usuario").order_by("-creado_en")

    can_write = _can_write_entregas(request.user, e)
    acciones = ACCIONES_POR_ESTADO.get(e.estado, []) if can_write else []

    return render(request, "dashboard/entregas/detail.html", {
        "page_title": f"Entrega · {e.get_estado_display()}",
        "entrega": e,
        "detalles": detalles,
        "transiciones": transiciones,
        "acciones_disponibles": acciones,
    })


@login_required
@require_POST
def entrega_accion(request, entrega_id):
    e = get_object_or_404(
        _entregas_visibles(request.user).select_related(
            "almacen_origen__organizacion",
            "hospital__organizacion",
            "refugio__organizacion",
        ),
        id=entrega_id,
    )
    if not _can_write_entregas(request.user, e):
        return HttpResponseForbidden("Sin permiso para operar esta entrega.")

    accion = request.POST.get("accion", "").strip()
    motivo = request.POST.get("motivo", "").strip()

    try:
        if accion == "enviar":
            enviar_entrega(
                entrega_id=entrega_id,
                usuario=request.user, motivo=motivo, request=request,
            )
        elif accion == "recibir":
            recibir_entrega(
                entrega_id=entrega_id,
                usuario=request.user, motivo=motivo, request=request,
            )
        elif accion == "cancelar":
            cancelar_entrega(
                entrega_id=entrega_id,
                usuario=request.user, motivo=motivo, request=request,
            )
        else:
            messages.error(request, f"Acción inválida: {accion}.")
            return redirect(
                "dashboard:entrega_detail", entrega_id=entrega_id,
            )

        messages.success(request, f"Acción '{accion}' aplicada.")

    except PermissionDenied:
        return HttpResponseForbidden("Sin permiso sobre esta entrega.")
    except ValidationError as ex:
        if hasattr(ex, "message_dict"):
            textos = [f"{k}: {', '.join(v)}" for k, v in ex.message_dict.items()]
            detalle = "; ".join(textos)
        else:
            detalle = "; ".join(ex.messages)
        messages.error(request, detalle)

    return redirect(
        "dashboard:entrega_detail", entrega_id=entrega_id,
    )
