"""Vistas del panel para el CRUD de Usuarios."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from frontend.forms.usuarios import UsuarioCreateForm, UsuarioUpdateForm

User = get_user_model()
PAGE_SIZE = 25


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _orgs_administrables(user):
    """Organizaciones en las que el user puede crear/asignar usuarios."""
    if puede_administrar_plataforma(user):
        from apps.organizaciones.models import Organizacion
        return Organizacion.objects.filter(estado="ACTIVA").order_by("nombre")
    org_ids = list(
        Membresia.objects
        .filter(
            usuario=user, estado=Membresia.Estado.ACTIVA,
            rol="ADMIN_ORGANIZACION",
        )
        .values_list("organizacion_id", flat=True)
    )
    from apps.organizaciones.models import Organizacion
    return Organizacion.objects.filter(id__in=org_ids, estado="ACTIVA").order_by("nombre")


def _usuarios_visibles(user):
    qs = User.objects.all().select_related("membresias__organizacion")
    if puede_administrar_plataforma(user):
        return qs
    org_ids = _org_ids_del_usuario(user)
    if not org_ids:
        return qs.none()
    return qs.filter(membresias__organizacion_id__in=org_ids).distinct()


def _can_manage_user(admin_user, target_user):
    if puede_administrar_plataforma(admin_user):
        return True
    org_ids = list(
        Membresia.objects
        .filter(
            usuario=admin_user, estado=Membresia.Estado.ACTIVA,
            rol="ADMIN_ORGANIZACION",
        )
        .values_list("organizacion_id", flat=True)
    )
    if not org_ids:
        return False
    return Membresia.objects.filter(
        usuario=target_user, organizacion_id__in=org_ids, estado=Membresia.Estado.ACTIVA,
    ).exists()


@login_required
@require_GET
def usuarios_list(request):
    qs = _usuarios_visibles(request.user).order_by("first_name", "last_name", "username")
    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/usuarios/list.html", {
        "page_title": "Usuarios",
        "page_obj": page,
        "total": paginator.count,
        "filters": {"q": q},
        "can_create": _orgs_administrables(request.user).exists(),
    })


@login_required
@require_GET
def usuario_detail(request, user_id):
    user = get_object_or_404(_usuarios_visibles(request.user), id=user_id)
    membresias = user.membresias.select_related("organizacion").order_by("organizacion__nombre")
    return render(request, "dashboard/usuarios/detail.html", {
        "page_title": f"Usuario · {user.get_full_name() or user.username}",
        "usuario": user,
        "membresias": membresias,
        "can_edit": _can_manage_user(request.user, user),
    })


@login_required
@require_GET
def usuario_create_form(request):
    orgs_qs = _orgs_administrables(request.user)
    if not orgs_qs.exists():
        return HttpResponseForbidden("Sin permiso para crear usuarios.")
    form = UsuarioCreateForm(orgs_qs=orgs_qs)
    return render(request, "dashboard/usuarios/form.html", {
        "form": form, "page_title": "Nuevo usuario",
    })


@login_required
@require_POST
def usuario_create_submit(request):
    orgs_qs = _orgs_administrables(request.user)
    if not orgs_qs.exists():
        return HttpResponseForbidden("Sin permiso para crear usuarios.")

    form = UsuarioCreateForm(request.POST, orgs_qs=orgs_qs)
    if form.is_valid():
        with transaction.atomic():
            user = form.save()
            Membresia.objects.create(
                usuario=user,
                organizacion=form.cleaned_data["organizacion"],
                rol=form.cleaned_data["rol"],
                estado=Membresia.Estado.ACTIVA,
            )
        messages.success(request, f"Usuario '{user.username}' creado correctamente.")
        return redirect("dashboard:usuario_detail", user_id=user.id)

    return render(request, "dashboard/usuarios/form.html", {
        "form": form, "page_title": "Nuevo usuario",
    })


@login_required
@require_GET
def usuario_update_form(request, user_id):
    user = get_object_or_404(_usuarios_visibles(request.user), id=user_id)
    if not _can_manage_user(request.user, user):
        return HttpResponseForbidden("Sin permiso para editar este usuario.")
    form = UsuarioUpdateForm(instance=user)
    return render(request, "dashboard/usuarios/form.html", {
        "form": form, "page_title": f"Editar usuario: {user.username}",
        "usuario": user,
    })


@login_required
@require_POST
def usuario_update_submit(request, user_id):
    user = get_object_or_404(_usuarios_visibles(request.user), id=user_id)
    if not _can_manage_user(request.user, user):
        return HttpResponseForbidden("Sin permiso para editar este usuario.")
    form = UsuarioUpdateForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        messages.success(request, "Datos del usuario actualizados.")
        return redirect("dashboard:usuario_detail", user_id=user.id)
    return render(request, "dashboard/usuarios/form.html", {
        "form": form, "page_title": f"Editar usuario: {user.username}",
        "usuario": user,
    })


@login_required
@require_POST
def usuario_toggle_active(request, user_id):
    user = get_object_or_404(_usuarios_visibles(request.user), id=user_id)
    if not _can_manage_user(request.user, user):
        return HttpResponseForbidden("Sin permiso para inactivar este usuario.")
    if user == request.user:
        messages.error(request, "No puedes inactivar tu propia cuenta desde aquí.")
        return redirect("dashboard:usuario_detail", user_id=user.id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    estado = "activado" if user.is_active else "inactivado"
    messages.success(request, f"Usuario {estado}.")
    return redirect("dashboard:usuario_detail", user_id=user.id)
