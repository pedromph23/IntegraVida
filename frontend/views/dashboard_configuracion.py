"""Vistas del panel para el módulo Configuración (F3.h.2).

Único modelo administrable: Membresia (rol + estado). No hay catálogos
editables en apps.configuracion (ReferenciaMigracion es interno).
No se crean/borran usuarios ni membresías — eso queda para F4.

Guard de escritura: superuser O usuario con Membresia(ACTIVA,
rol=ADMIN_ORGANIZACION) en esa organización. NO sustituye la política
completa de escalado (auto-degradación, transferir admin, etc.) —
esa validación vive en F4 / próximas fases.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from frontend.forms.membresias import MembresiaForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.organizaciones.models import Organizacion, Membresia
from apps.organizaciones.services import puede_administrar_plataforma

PAGE_SIZE = 30


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _orgs_admin(user):
    """Orgs donde el usuario puede administrar membresías."""
    if puede_administrar_plataforma(user):
        return None  # señal: todas
    return list(
        Membresia.objects
        .filter(
            usuario=user, estado=Membresia.Estado.ACTIVA,
            rol="ADMIN_ORGANIZACION",
        )
        .values_list("organizacion_id", flat=True)
    )


def _can_manage_membership(user, membresia):
    if puede_administrar_plataforma(user):
        return True
    org_ids = _orgs_admin(user) or []
    return membresia.organizacion_id in org_ids


def _membresias_visibles(user):
    qs = Membresia.objects.select_related("usuario", "organizacion")
    if puede_administrar_plataforma(user):
        return qs
    org_ids = _orgs_admin(user) or []
    if not org_ids:
        return qs.none()
    return qs.filter(organizacion_id__in=org_ids)


@login_required
@require_GET
def configuracion_index(request):
    total_membresias = _membresias_visibles(request.user).count()
    return render(request, "dashboard/configuracion/index.html", {
        "page_title": "Configuración",
        "total_membresias": total_membresias,
    })


@login_required
@require_GET
def membresias_list(request):
    qs = _membresias_visibles(request.user)

    estado = request.GET.get("estado", "")
    estados_validos = {v for v, _ in Membresia.Estado.choices}
    if estado not in estados_validos:
        estado = ""
    if estado:
        qs = qs.filter(estado=estado)

    rol = request.GET.get("rol", "")
    roles_validos = {v for v, _ in Membresia._meta.get_field("rol").choices}
    if rol not in roles_validos:
        rol = ""
    if rol:
        qs = qs.filter(rol=rol)

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(usuario__username__icontains=q)
            | Q(organizacion__nombre__icontains=q)
        )

    qs = qs.order_by("organizacion__nombre", "usuario__username")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/configuracion/membresias_list.html", {
        "page_title": "Membresías",
        "page_obj": page,
        "total": paginator.count,
        "can_manage": (puede_administrar_plataforma(request.user) or bool(_orgs_admin(request.user))),
        "filters": {"estado": estado, "rol": rol, "q": q},
        "estados": Membresia.Estado.choices,
        "roles": Membresia._meta.get_field("rol").choices,
    })


@login_required
@require_POST
def membresia_update(request, membresia_id):
    membresia = get_object_or_404(
        Membresia.objects.select_related("usuario", "organizacion"),
        id=membresia_id,
    )
    if not _can_manage_membership(request.user, membresia):
        return HttpResponseForbidden("Sin permiso para gestionar esta membresía.")

    estado = request.POST.get("estado", "").strip()
    rol = request.POST.get("rol", "").strip()

    estados_validos = {v for v, _ in Membresia.Estado.choices}
    roles_validos = {v for v, _ in Membresia._meta.get_field("rol").choices}

    changed = False
    if estado and estado in estados_validos and estado != membresia.estado:
        membresia.estado = estado
        changed = True
    if rol and rol in roles_validos and rol != membresia.rol:
        membresia.rol = rol
        changed = True

    if changed:
        membresia.save()
        messages.success(
            request,
            f"Membresía de {membresia.usuario.username} actualizada.",
        )
    else:
        messages.info(request, "Sin cambios.")

    return redirect("dashboard:membresias_list")


@login_required
@require_GET
def membresia_create_form(request):
    orgs = _orgs_admin(request.user)
    if orgs is None:
        org_qs = Organizacion.objects.all()
    else:
        org_qs = Organizacion.objects.filter(id__in=orgs)
    form = MembresiaForm()
    form.fields["organizacion"].queryset = org_qs.order_by("nombre")
    return render(request, "dashboard/configuracion/form.html", {
        "form": form, "page_title": "Nueva membresía",
    })


@login_required
@require_POST
def membresia_create_submit(request):
    orgs = _orgs_admin(request.user)
    if orgs is None:
        org_qs = Organizacion.objects.all()
    else:
        org_qs = Organizacion.objects.filter(id__in=orgs)
    form = MembresiaForm(request.POST)
    form.fields["organizacion"].queryset = org_qs.order_by("nombre")
    if form.is_valid():
        form.save()
        messages.success(request, "Membresía creada correctamente.")
        return redirect("dashboard:membresias_list")
    return render(request, "dashboard/configuracion/form.html", {
        "form": form, "page_title": "Nueva membresía",
    })
