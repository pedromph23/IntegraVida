"""Vistas del panel para el módulo Pacientes (F3.e.2 + F5.d).

F3.e.2: lista + detalle con masking PII (masking.py).
F5.d: scoping por organización (vía episodios) + edición de PII
      restringida a ADMIN_ORGANIZACION o COORDINADOR.

Scoping por org: un Paciente no tiene organizacion directa. Se asocia
vía sus Episodios (hospital o refugio). Solo se ven pacientes con al
menos 1 episodio en una org donde el user tiene Membresia ACTIVA.

Crear paciente NO se hace aquí (se hace en F5.f "Nuevo episodio"):
un paciente sin episodio no tiene scope y sería invisible.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from apps.pacientes.models import Episodio, Paciente
from apps.usuarios.permisos import (
    ACCION_EDITAR,
    ACCION_VER,
    tiene_permiso,
)

from frontend.forms.pacientes import PacienteForm


PAGE_SIZE = 25

PII_SENSITIVE_GROUPS = {"ADMIN", "COORDINADOR", "ADMIN_ORGANIZACION"}
FULL_NAMES_GROUPS = {"ADMIN", "COORDINADOR", "OPERADOR_HOSPITAL", "ADMIN_ORGANIZACION", "SANITARIO"}


def _groups_of(user):
    if not user.is_authenticated:
        return set()
    return set(user.groups.values_list("name", flat=True))


def _can_see_sensitive_pii(user):
    if user.is_superuser or user.is_staff:
        return True
    return bool(_groups_of(user) & PII_SENSITIVE_GROUPS)


def _can_see_full_names(user):
    if user.is_superuser or user.is_staff:
        return True
    return bool(_groups_of(user) & FULL_NAMES_GROUPS)


def _mask_cedula(cedula):
    digits = "".join(ch for ch in (cedula or "") if ch.isdigit())
    if len(digits) < 4:
        return "—"
    return f"***-**-{digits[-4:]}"


def _mask_nombre(nombres, apellidos):
    partes = f"{nombres or ''} {apellidos or ''}".split()
    if not partes:
        return "—"
    return " ".join(f"{p[0].upper()}***" for p in partes)


def _calc_edad(fecha_nacimiento):
    if not fecha_nacimiento:
        return "—"
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


def _base_queryset(user):
    """Pacientes visibles por episodios en orgs del user.

    Si el user es superuser/staff → todos.
    Si tiene Membresia ACTIVA → solo los que tengan al menos 1 episodio
    en una de sus orgs.
    Si no tiene Membresia → ninguno.
    """
    qs = Paciente.objects.all()

    # Anotación del último estado de episodio para la lista
    ultimo_ep = (
        Episodio.objects
        .filter(paciente=OuterRef("pk"))
        .order_by("-fecha_ingreso")
        .values("estado")[:1]
    )
    qs = qs.annotate(
        episodios_count=Count("episodios", distinct=True),
        ultimo_episodio_estado=Subquery(ultimo_ep),
    )

    if puede_administrar_plataforma(user):
        return qs

    org_ids = list(
        Membresia.objects
        .filter(usuario=user, estado="ACTIVA")
        .values_list("organizacion_id", flat=True)
    )
    if not org_ids:
        return qs.none()

    return qs.filter(
        Q(episodios__hospital__organizacion_id__in=org_ids)
        | Q(episodios__refugio__organizacion_id__in=org_ids)
    ).distinct()


@login_required
@require_GET
def pacientes_list(request):
    # Si el user no tiene ACCION_VER sobre pacientes → 403
    if not tiene_permiso(request.user, "pacientes", ACCION_VER):
        return HttpResponseForbidden(
            "No tienes permiso para ver pacientes."
        )

    qs = _base_queryset(request.user)

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(
            Q(nombres__icontains=q) | Q(apellidos__icontains=q)
        )

    qs = qs.order_by("-creado_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    # Enmascaramiento SIEMPRE en lista
    filas = [
        {
            "id": p.id,
            "nombre_masked": _mask_nombre(p.nombres, p.apellidos),
            "cedula_masked": _mask_cedula(p.cedula),
            "edad": _calc_edad(p.fecha_nacimiento),
            "sexo_display": p.get_sexo_biologico_display(),
            "episodios_count": p.episodios_count,
            "ultimo_episodio_estado": p.ultimo_episodio_estado or "—",
        }
        for p in page
    ]

    return render(request, "dashboard/pacientes/list.html", {
        "page_title": "Pacientes",
        "page_obj": page,
        "filas": filas,
        "total": paginator.count,
        "filters": {"q": q},
    })


@login_required
@require_GET
def paciente_detail(request, paciente_id):
    if not tiene_permiso(request.user, "pacientes", ACCION_VER):
        return HttpResponseForbidden(
            "No tienes permiso para ver pacientes."
        )

    paciente = get_object_or_404(_base_queryset(request.user), id=paciente_id)
    contactos = paciente.contactos.order_by("-es_principal", "nombre")[:20]
    episodios = paciente.episodios.select_related(
        "hospital", "refugio", "registrado_por",
    ).order_by("-fecha_ingreso")[:30]

    can_edit = tiene_permiso(
        request.user, "pacientes", ACCION_EDITAR,
    )

    return render(request, "dashboard/pacientes/detail.html", {
        "page_title": f"Paciente · {_mask_nombre(paciente.nombres, paciente.apellidos)}",
        "paciente": paciente,
        "contactos": contactos,
        "episodios": episodios,
        "can_see_full_names": _can_see_full_names(request.user),
        "can_see_sensitive_pii": _can_see_sensitive_pii(request.user),
        "can_edit": can_edit,
    })


# ── Editar ────────────────────────────────────────────────────────────
@login_required
@require_GET
def paciente_update_form(request, paciente_id):
    if not tiene_permiso(request.user, "pacientes", ACCION_EDITAR):
        return HttpResponseForbidden(
            "No tienes permiso para editar pacientes."
        )

    paciente = get_object_or_404(_base_queryset(request.user), id=paciente_id)
    form = PacienteForm(instance=paciente)
    return render(request, "dashboard/pacientes/form.html", {
        "page_title": f"Editar · {_mask_nombre(paciente.nombres, paciente.apellidos)}",
        "form": form,
        "paciente": paciente,
    })


@login_required
@require_POST
def paciente_update_submit(request, paciente_id):
    if not tiene_permiso(request.user, "pacientes", ACCION_EDITAR):
        return HttpResponseForbidden(
            "No tienes permiso para editar pacientes."
        )

    paciente = get_object_or_404(_base_queryset(request.user), id=paciente_id)
    form = PacienteForm(request.POST, instance=paciente)
    if not form.is_valid():
        return render(request, "dashboard/pacientes/form.html", {
            "page_title": f"Editar · {_mask_nombre(paciente.nombres, paciente.apellidos)}",
            "form": form,
            "paciente": paciente,
        })

    with transaction.atomic():
        paciente = form.save()

    messages.success(request, "Datos del paciente actualizados.")
    return redirect("dashboard:paciente_detail", paciente_id=paciente.id)
