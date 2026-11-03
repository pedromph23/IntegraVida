"""CRUD de Puntos de Referencia."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from apps.refugios.models import PuntoReferencia
from frontend.forms.puntos_referencia import PuntoReferenciaForm


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _puntos_visibles(user):
    qs = PuntoReferencia.objects.all()
    if puede_administrar_plataforma(user):
        return qs
    org_ids = _org_ids_del_usuario(user)
    if not org_ids:
        return qs.none()
    return qs.filter(organizacion_id__in=org_ids)


def _org_del_usuario_para_crear(user):
    m = Membresia.objects.filter(
        usuario=user, estado=Membresia.Estado.ACTIVA,
    ).select_related("organizacion").first()
    return m.organizacion if m else None


@login_required
@require_GET
def puntos_list(request):
    qs = _puntos_visibles(request.user).order_by("categoria", "nombre")
    return render(request, "dashboard/puntos/list.html", {
        "page_title": "Puntos de referencia",
        "puntos": qs,
        "can_create": _org_del_usuario_para_crear(request.user) is not None,
    })


@login_required
@require_GET
def punto_create_form(request):
    org = _org_del_usuario_para_crear(request.user)
    if not org:
        return HttpResponseForbidden("No perteneces a ninguna organización.")
    return render(request, "dashboard/puntos/form.html", {
        "form": PuntoReferenciaForm(),
        "page_title": "Nuevo punto de referencia",
    })


@login_required
@require_POST
def punto_create_submit(request):
    org = _org_del_usuario_para_crear(request.user)
    if not org:
        return HttpResponseForbidden("No perteneces a ninguna organización.")
    form = PuntoReferenciaForm(request.POST)
    if form.is_valid():
        p = form.save(commit=False)
        p.organizacion = org
        p.save()
        messages.success(request, f"Punto '{p.nombre}' creado.")
        return redirect("dashboard:puntos_list")
    return render(request, "dashboard/puntos/form.html", {
        "form": form, "page_title": "Nuevo punto de referencia",
    })


@login_required
@require_GET
def punto_detail(request, punto_id):
    p = get_object_or_404(_puntos_visibles(request.user), id=punto_id)
    return render(request, "dashboard/puntos/detail.html", {
        "page_title": f"Punto: {p.nombre}",
        "punto": p,
    })


@login_required
@require_GET
def punto_update_form(request, punto_id):
    p = get_object_or_404(_puntos_visibles(request.user), id=punto_id)
    return render(request, "dashboard/puntos/form.html", {
        "form": PuntoReferenciaForm(instance=p),
        "page_title": f"Editar: {p.nombre}",
        "punto": p,
    })


@login_required
@require_POST
def punto_update_submit(request, punto_id):
    p = get_object_or_404(_puntos_visibles(request.user), id=punto_id)
    form = PuntoReferenciaForm(request.POST, instance=p)
    if form.is_valid():
        form.save()
        messages.success(request, "Punto actualizado.")
        return redirect("dashboard:puntos_list")
    return render(request, "dashboard/puntos/form.html", {
        "form": form, "page_title": f"Editar: {p.nombre}", "punto": p,
    })


@login_required
@require_POST
def punto_toggle(request, punto_id):
    p = get_object_or_404(_puntos_visibles(request.user), id=punto_id)
    p.activo = not p.activo
    p.save(update_fields=["activo", "actualizado_en"])
    estado = "activado" if p.activo else "inactivado"
    messages.success(request, f"Punto {estado}.")
    return redirect("dashboard:puntos_list")
