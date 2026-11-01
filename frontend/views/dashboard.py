"""Vistas del panel institucional (F3.b: métricas reales en home).

Las tarjetas se filtran por grupo del usuario. Si el usuario no tiene
grupos (o no coincide con GROUP_TO_CARDS), ve todas. Ajustar el mapeo
aquí cuando F3.h cree los grupos reales.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.refugios.models import Refugio
from apps.emergencias.models import Emergencia, ReporteEmergencia
from apps.hospitales.models import Hospital


GROUP_TO_CARDS = {
    "ADMIN":               {"refugios", "emergencias", "hospitales", "reportes"},
    "COORDINADOR":         {"refugios", "emergencias", "hospitales", "reportes"},
    "OPERADOR_REFUGIO":    {"refugios"},
    "OPERADOR_EMERGENCIA": {"emergencias"},
    "OPERADOR_HOSPITAL":   {"hospitales"},
    "ANALISTA":            {"reportes"},
}
ALL_CARDS = {"refugios", "emergencias", "hospitales", "reportes"}


def _visible_from_groups(groups):
    if not groups:
        return ALL_CARDS
    visible = set()
    for g in groups:
        visible |= GROUP_TO_CARDS.get(g, set())
    return visible or ALL_CARDS


def _visible_cards(user):
    """Wrapper usado por tests y por código que solo tiene user."""
    return _visible_from_groups(
        list(user.groups.values_list("name", flat=True))
    )


def _first_existing_field(model, candidates):
    names = {f.name for f in model._meta.get_fields()}
    for c in candidates:
        if c in names:
            return c
    return None


def _build_cards(visible):
    now = timezone.now()
    cutoff = now - timedelta(days=7)
    cards = []

    if "refugios" in visible:
        agg = Refugio.objects.aggregate(
            total=Count("id"),
            activos=Count("id", filter=Q(estado_operativo="ACTIVO")),
        )
        cards.append({
            "key": "refugios", "label": "Refugios activos",
            "count": agg["activos"], "total": agg["total"],
            "url": "/panel/refugios/",
        })

    if "emergencias" in visible:
        agg = Emergencia.objects.aggregate(
            total=Count("id"),
            abiertas=Count("id", filter=Q(
                estado__in=["CONFIRMADA", "EN_ATENCION"]
            )),
        )
        cards.append({
            "key": "emergencias", "label": "Emergencias abiertas",
            "count": agg["abiertas"], "total": agg["total"],
            "url": "/panel/emergencias/",
        })

    if "hospitales" in visible:
        agg = Hospital.objects.aggregate(
            total=Count("id"),
            disponibles=Count("id", filter=Q(
                estado_operativo="DISPONIBLE"
            )),
        )
        cards.append({
            "key": "hospitales", "label": "Hospitales disponibles",
            "count": agg["disponibles"], "total": agg["total"],
            "url": "/panel/hospitales/",
        })

    if "reportes" in visible:
        fecha_field = _first_existing_field(
            ReporteEmergencia,
            ["creado_en", "created_at", "fecha_creacion", "fecha_reporte"],
        )
        rep_qs = ReporteEmergencia.objects.all()
        if fecha_field:
            rep_qs = rep_qs.filter(**{f"{fecha_field}__gte": cutoff})
        agg = rep_qs.aggregate(
            total=Count("id"),
            pendientes=Count("id", filter=Q(
                estado_revision="PENDIENTE"
            )),
        )
        cards.append({
            "key": "reportes", "label": "Reportes pendientes (7d)",
            "count": agg["pendientes"], "total": agg["total"],
            "url": "/panel/reportes/",
        })

    return cards


@login_required
def home(request):
    user = request.user
    groups = list(user.groups.values_list("name", flat=True))
    visible = _visible_from_groups(groups)
    cards = _build_cards(visible)
    return render(request, "dashboard/home.html", {
        "page_title": "Panel institucional",
        "user_groups": groups,
        "last_login": user.last_login,
        "cards": cards,
    })
