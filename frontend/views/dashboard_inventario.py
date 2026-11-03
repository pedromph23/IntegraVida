"""Vistas del panel para el módulo Inventario (F3.g.1). Solo lectura.

Modelos cubiertos: Insumo, Almacen, Lote, Stock, Movimiento.
Las operaciones transaccionales (registrar_movimiento, FEFO, transferencias,
entregas) viven en apps.inventario.services y se abordan en F3.g.2.

Ámbito: usuario solo ve almacenes de sus orgs con Membresia ACTIVA.
Superuser (puede_administrar_plataforma) ve todo.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import (
    BooleanField, Case, DecimalField, F, Q, Sum, Value, When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.inventario.models import Almacen, Insumo, Lote, Movimiento, Stock
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma

PAGE_SIZE = 25
KARDEX_PAGE_SIZE = 50
VENCIMIENTO_PROXIMO_DIAS = 30


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _almacenes_visibles(user):
    if puede_administrar_plataforma(user):
        return Almacen.objects.all()
    org_ids = _org_ids_del_usuario(user)
    if not org_ids:
        return Almacen.objects.none()
    return Almacen.objects.filter(organizacion_id__in=org_ids)


@login_required
@require_GET
def insumos_list(request):
    qs = Insumo.objects.all()
    almacenes = _almacenes_visibles(request.user)

    # Anotación stock_total por almacenes visibles (subquery con subselect)
    qs = qs.annotate(
        stock_total=Coalesce(
            Sum(
                "lotes__stocks__cantidad",
                filter=Q(lotes__stocks__almacen__in=almacenes),
            ),
            Value(0, output_field=DecimalField()),
        ),
    ).annotate(
        bajo_stock=Case(
            When(
                stock_total__lt=F("stock_minimo_global"),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )

    categoria = request.GET.get("categoria", "")
    categorias_validas = {v for v, _ in Insumo._meta.get_field("categoria").choices}
    if categoria not in categorias_validas:
        categoria = ""
    if categoria:
        qs = qs.filter(categoria=categoria)

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))

    solo_activos = request.GET.get("activo", "true") == "true"
    if solo_activos:
        qs = qs.filter(activo=True)

    solo_bajo = request.GET.get("bajo_stock", "") == "true"
    if solo_bajo:
        qs = qs.filter(bajo_stock=True)

    qs = qs.order_by("categoria", "nombre")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/inventario/insumos_list.html", {
        "page_title": "Insumos",
        "page_obj": page,
        "total": paginator.count,
        "filters": {
            "q": q, "categoria": categoria,
            "activo": "true" if solo_activos else "false",
            "bajo_stock": "true" if solo_bajo else "",
        },
        "categorias": Insumo._meta.get_field("categoria").choices,
        "can_edit": _can_edit_insumos(request.user),
    })


@login_required
@require_GET
def stock_list(request):
    almacenes = _almacenes_visibles(request.user)
    qs = (
        Stock.objects
        .filter(almacen__in=almacenes)
        .select_related("almacen", "lote__insumo")
        .annotate(
            stock_minimo=F("lote__insumo__stock_minimo_global"),
        )
    )

    # Filtro por almacén (validando que sea visible)
    almacen_id = request.GET.get("almacen", "")
    almacenes_disponibles = almacenes.order_by("nombre")
    if almacen_id:
        try:
            qs = qs.filter(almacen_id=almacen_id)
        except (ValueError, TypeError):
            almacen_id = ""

    # Búsqueda por insumo (nombre o código)
    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(lote__insumo__nombre__icontains=q)
            | Q(lote__insumo__codigo__icontains=q)
        )

    bajo_stock = request.GET.get("bajo_stock", "") == "true"
    if bajo_stock:
        qs = qs.filter(cantidad__lt=F("lote__insumo__stock_minimo_global"))

    solo_con_stock = request.GET.get("con_stock", "true") == "true"
    if solo_con_stock:
        qs = qs.filter(cantidad__gt=0)

    qs = qs.order_by("almacen__nombre", "lote__insumo__nombre", "lote__fecha_vencimiento")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    hoy = timezone.now().date()
    filas = []
    for s in page:
        v = s.lote.fecha_vencimiento
        filas.append({
            "id": s.id,
            "almacen_nombre": s.almacen.nombre,
            "insumo_codigo": s.lote.insumo.codigo,
            "insumo_nombre": s.lote.insumo.nombre,
            "insumo_unidad": s.lote.insumo.get_unidad_medida_display(),
            "lote_codigo": s.lote.codigo,
            "fecha_vencimiento": v,
            "vencido": bool(v and v < hoy),
            "cantidad": s.cantidad,
            "stock_minimo": s.stock_minimo,
            "bajo_minimo": s.cantidad < s.stock_minimo,
        })

    return render(request, "dashboard/inventario/stock_list.html", {
        "page_title": "Stock por almacén",
        "page_obj": page,
        "filas": filas,
        "total": paginator.count,
        "filters": {
            "almacen": almacen_id,
            "q": q,
            "bajo_stock": "true" if bajo_stock else "",
            "con_stock": "true" if solo_con_stock else "false",
        },
        "almacenes": almacenes_disponibles,
    })


@login_required
@require_GET
def stock_detail(request, stock_id):
    almacenes = _almacenes_visibles(request.user)
    stock = get_object_or_404(
        Stock.objects
        .select_related("almacen", "lote__insumo"),
        id=stock_id, almacen__in=almacenes,
    )
    movimientos_qs = (
        Movimiento.objects
        .filter(stock=stock)
        .select_related("registrado_por")
        .order_by("-creado_en")
    )
    paginator = Paginator(movimientos_qs, KARDEX_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    insumo = stock.lote.insumo
    return render(request, "dashboard/inventario/stock_detail.html", {
        "page_title": f"Kardex · {insumo.nombre}",
        "stock": stock,
        "insumo": insumo,
        "page_obj": page,
        "total_movimientos": paginator.count,
        "bajo_minimo": stock.cantidad < insumo.stock_minimo_global,
    })


@login_required
@require_GET
def insumo_detail(request, codigo):
    insumo = get_object_or_404(Insumo, codigo=codigo)
    almacenes = _almacenes_visibles(request.user)

    stocks = (
        Stock.objects
        .filter(
            almacen__in=almacenes,
            lote__insumo=insumo,
            cantidad__gt=0,
        )
        .select_related("almacen", "lote")
        .order_by("almacen__nombre", "lote__fecha_vencimiento")
    )
    total_cantidad = stocks.aggregate(t=Sum("cantidad"))["t"] or 0

    # Marcar lotes próximos a vencer (<30 días) para el template
    hoy = timezone.now().date()
    limite = hoy + timedelta(days=VENCIMIENTO_PROXIMO_DIAS)
    stocks_lista = list(stocks)
    for s in stocks_lista:
        v = s.lote.fecha_vencimiento
        s.vence_proximo = bool(v and v <= limite)
        s.vencido = bool(v and v < hoy)
        s.bajo_minimo = s.cantidad < insumo.stock_minimo_global

    return render(request, "dashboard/inventario/insumo_detail.html", {
        "page_title": f"Insumo · {insumo.nombre}",
        "insumo": insumo,
        "stocks": stocks_lista,
        "total_cantidad": total_cantidad,
        "can_edit": _can_edit_insumos(request.user),
    })


from frontend.forms.insumos import InsumoForm


def _can_edit_insumos(user):
    """Insumo es catálogo global: solo admin de plataforma puede editarlo."""
    return puede_administrar_plataforma(user)


@login_required
@require_GET
def insumo_create_form(request):
    if not _can_edit_insumos(request.user):
        return HttpResponseForbidden("Sin permiso para crear insumos.")
    form = InsumoForm()
    return render(request, "dashboard/inventario/form.html", {
        "form": form, "page_title": "Nuevo insumo",
    })


@login_required
@require_POST
def insumo_create_submit(request):
    if not _can_edit_insumos(request.user):
        return HttpResponseForbidden("Sin permiso para crear insumos.")
    form = InsumoForm(request.POST)
    if form.is_valid():
        insumo = form.save()
        messages.success(request, f"Insumo '{insumo.nombre}' creado.")
        return redirect("dashboard:insumo_detail", codigo=insumo.codigo)
    return render(request, "dashboard/inventario/form.html", {
        "form": form, "page_title": "Nuevo insumo",
    })


@login_required
@require_GET
def insumo_update_form(request, codigo):
    if not _can_edit_insumos(request.user):
        return HttpResponseForbidden("Sin permiso para editar insumos.")
    insumo = get_object_or_404(Insumo, codigo=codigo)
    form = InsumoForm(instance=insumo)
    return render(request, "dashboard/inventario/form.html", {
        "form": form, "page_title": f"Editar insumo: {insumo.nombre}",
        "insumo": insumo,
    })


@login_required
@require_POST
def insumo_update_submit(request, codigo):
    if not _can_edit_insumos(request.user):
        return HttpResponseForbidden("Sin permiso para editar insumos.")
    insumo = get_object_or_404(Insumo, codigo=codigo)
    form = InsumoForm(request.POST, instance=insumo)
    if form.is_valid():
        form.save()
        messages.success(request, "Insumo actualizado.")
        return redirect("dashboard:insumo_detail", codigo=insumo.codigo)
    return render(request, "dashboard/inventario/form.html", {
        "form": form, "page_title": f"Editar insumo: {insumo.nombre}",
        "insumo": insumo,
    })


@login_required
@require_POST
def insumo_inactivar_submit(request, codigo):
    if not _can_edit_insumos(request.user):
        return HttpResponseForbidden("Sin permiso para inactivar insumos.")
    insumo = get_object_or_404(Insumo, codigo=codigo)
    insumo.activo = not insumo.activo
    insumo.save(update_fields=["activo", "actualizado_en"])
    estado = "activado" if insumo.activo else "inactivado"
    messages.success(request, f"Insumo {estado}.")
    return redirect("dashboard:insumo_detail", codigo=insumo.codigo)
