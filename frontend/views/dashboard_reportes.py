"""Vistas del panel para el módulo Reportes (F3.h.1).

Los 2 reportes existentes (inventario crítico, capacidad operativa) viven
en apps.reportes.services, que ya validan, generan, y registran la
exportación en RegistroExportacion. F3.h.1 es solo la UI.

No se genera CSV/XLSX todavía (no hay openpyxl/xlsxwriter en deps).
El resultado JSON se muestra formateado; descarga real → F4.
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from apps.organizaciones.models import Membresia, Organizacion
from apps.organizaciones.services import puede_administrar_plataforma
from apps.reportes.models import RegistroExportacion
from apps.reportes.services import (
    generar_reporte_capacidad_operativa,
    generar_reporte_inventario_critico,
)

PAGE_SIZE_HISTORIAL = 30

REPORTES_DISPONIBLES = {
    "inventario-critico": {
        "nombre": "Inventario crítico",
        "descripcion": (
            "Insumos bajo stock mínimo global y lotes vencidos o próximos "
            "a vencer en los almacenes visibles para tu organización."
        ),
        "contenido_enum": "INVENTARIO_CRITICO",
        "servicio": generar_reporte_inventario_critico,
    },
    "capacidad-operativa": {
        "nombre": "Capacidad operativa",
        "descripcion": (
            "Refugios y hospitales con su estado operativo agregado, "
            "para evaluar cobertura y detectar zonas sin capacidad."
        ),
        "contenido_enum": "CAPACIDAD_OPERATIVA",
        "servicio": generar_reporte_capacidad_operativa,
    },
}


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _orgs_visibles(user):
    if puede_administrar_plataforma(user):
        return Organizacion.objects.filter(
            estado="ACTIVA",
        ).order_by("nombre")
    org_ids = _org_ids_del_usuario(user)
    return Organizacion.objects.filter(
        id__in=org_ids, estado="ACTIVA",
    ).order_by("nombre")


def _historial_visible(user):
    qs = RegistroExportacion.objects.select_related("usuario", "organizacion")
    if puede_administrar_plataforma(user):
        return qs
    org_ids = _org_ids_del_usuario(user)
    return qs.filter(
        Q(organizacion_id__in=org_ids)
        | Q(organizacion__isnull=True, usuario=user)
    )


@login_required
@require_GET
def reportes_index(request):
    return render(request, "dashboard/reportes/index.html", {
        "page_title": "Reportes",
        "reportes": REPORTES_DISPONIBLES,
    })


@login_required
def reporte_ejecutar(request, slug):
    meta = REPORTES_DISPONIBLES.get(slug)
    if meta is None:
        raise Http404("Reporte desconocido.")

    orgs = _orgs_visibles(request.user)
    resultado_str = None

    if not orgs.exists():
        messages.warning(
            request,
            "No hay organizaciones visibles para generar reportes. "
            "Contacta al administrador para que te asigne una membresía.",
        )

    if request.method == "POST":
        org_id = request.POST.get("organizacion", "").strip()
        organizacion = None
        if org_id:
            try:
                organizacion = orgs.get(id=org_id)
            except (Organizacion.DoesNotExist, ValueError):
                messages.error(request, "Organización inválida.")
                return redirect(
                    "dashboard:reporte_ejecutar", slug=slug,
                )
        # Los servicios validan que organizacion no sea None; si no se
        # selecciona, usamos la primera visible.
        if organizacion is None:
            organizacion = orgs.first()

        try:
            resultado = meta["servicio"](
                usuario=request.user,
                organizacion=organizacion,
                request=request,
            )
            resultado_str = json.dumps(
                resultado, indent=2, ensure_ascii=False, default=str,
            )
            messages.success(
                request, "Reporte generado y exportación registrada.",
            )
        except PermissionDenied:
            messages.error(request, "No tienes acceso a esa organización.")
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                detalle = "; ".join(
                    f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()
                )
            else:
                detalle = "; ".join(e.messages)
            messages.error(request, detalle)

    return render(request, "dashboard/reportes/detalle.html", {
        "page_title": meta["nombre"],
        "slug": slug,
        "meta": meta,
        "organizaciones": orgs,
        "resultado": resultado_str,
    })


@login_required
@require_GET
def reportes_historial(request):
    qs = _historial_visible(request.user).order_by("-creado_en")

    contenido = request.GET.get("contenido", "")
    contenidos_validos = {v for v, _ in RegistroExportacion._meta.get_field("contenido").choices}
    if contenido not in contenidos_validos:
        contenido = ""
    if contenido:
        qs = qs.filter(contenido=contenido)

    resultado = request.GET.get("resultado", "")
    resultados_validos = {v for v, _ in RegistroExportacion._meta.get_field("resultado").choices}
    if resultado not in resultados_validos:
        resultado = ""
    if resultado:
        qs = qs.filter(resultado=resultado)

    paginator = Paginator(qs, PAGE_SIZE_HISTORIAL)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/reportes/historial.html", {
        "page_title": "Historial de exportaciones",
        "page_obj": page,
        "total": paginator.count,
        "filters": {"contenido": contenido, "resultado": resultado},
        "contenidos": RegistroExportacion._meta.get_field("contenido").choices,
        "resultados": RegistroExportacion._meta.get_field("resultado").choices,
    })
