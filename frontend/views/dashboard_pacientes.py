"""Vistas del panel para el módulo Pacientes (F3.e.2).

Solo lectura: pacientes no tienen estados operativos.

Dos niveles de acceso (§12):
- PII_SENSITIVE_GROUPS (ADMIN, COORDINADOR): cédula completa, fecha
  de nacimiento, notas internas.
- FULL_NAMES_GROUPS (ADMIN, COORDINADOR, OPERADOR_HOSPITAL): nombres
  completos, edad numérica, teléfono, email.
- Resto: todo enmascarado.

La LISTA siempre enmascara nombres y cédula para todos los roles.
El DETALLE aplica los dos niveles según el rol del usuario.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.pacientes.models import Episodio, Paciente

PAGE_SIZE = 25

PII_SENSITIVE_GROUPS = {"ADMIN", "COORDINADOR"}
FULL_NAMES_GROUPS = {"ADMIN", "COORDINADOR", "OPERADOR_HOSPITAL"}


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


def _base_queryset():
    ultimo_ep = (
        Episodio.objects
        .filter(paciente=OuterRef("pk"))
        .order_by("-fecha_ingreso")
        .values("estado")[:1]
    )
    return Paciente.objects.annotate(
        episodios_count=Count("episodios", distinct=True),
        ultimo_episodio_estado=Subquery(ultimo_ep),
    )


@login_required
@require_GET
def pacientes_list(request):
    qs = _base_queryset()

    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(nombres__icontains=q) | qs.filter(apellidos__icontains=q)

    qs = qs.order_by("-creado_en")
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

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
    paciente = get_object_or_404(_base_queryset(), id=paciente_id)
    contactos = paciente.contactos.order_by("-es_principal", "nombre")[:20]
    episodios = paciente.episodios.select_related(
        "hospital", "refugio", "registrado_por",
    ).order_by("-fecha_ingreso")[:30]

    return render(request, "dashboard/pacientes/detail.html", {
        "page_title": f"Paciente · {_mask_nombre(paciente.nombres, paciente.apellidos)}",
        "paciente": paciente,
        "contactos": contactos,
        "episodios": episodios,
        "can_see_full_names": _can_see_full_names(request.user),
        "can_see_sensitive_pii": _can_see_sensitive_pii(request.user),
    })
