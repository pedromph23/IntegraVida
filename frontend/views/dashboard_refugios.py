"""Vistas del panel para el módulo Refugios (F3.c).

Separado de dashboard.py para que las métricas (F3.b) y los módulos
operativos no se mezclen. Las vistas de F3.d..h seguirán este patrón:
un módulo por archivo, importados desde frontend/urls/dashboard.py.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.refugios.models import Refugio


REFUGIO_WRITE_GROUPS = {"ADMIN", "COORDINADOR", "OPERADOR_REFUGIO"}
PAGE_SIZE = 25


def _can_write_refugios(user):
    if user.is_superuser or user.is_staff:
        return True
    groups = set(user.groups.values_list("name", flat=True))
    return bool(groups & REFUGIO_WRITE_GROUPS)


def _base_queryset():
    return Refugio.objects.select_related(
        "organizacion", "responsable", "municipio", "parroquia"
    )


@login_required
@require_GET
def refugios_list(request):
    qs = _base_queryset()

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
    })


@login_required
@require_GET
def refugio_detail(request, codigo):
    refugio = get_object_or_404(_base_queryset(), codigo=codigo)
    necesidades = refugio.necesidades.all().order_by(
        "-prioridad", "-creada_en"
    )[:50]
    registros = refugio.registros_ocupacion.select_related(
        "registrado_por"
    ).order_by("-creado_en")[:20]

    return render(request, "dashboard/refugios/detail.html", {
        "page_title": f"Refugio · {refugio.nombre}",
        "refugio": refugio,
        "necesidades": necesidades,
        "registros": registros,
        "estados": Refugio.EstadoOperativo.choices,
        "can_write": _can_write_refugios(request.user),
    })


@login_required
@require_POST
def refugio_cambiar_estado(request, codigo):
    if not _can_write_refugios(request.user):
        return HttpResponseForbidden(
            "No tienes permiso para modificar refugios."
        )

    refugio = get_object_or_404(Refugio, codigo=codigo)

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
