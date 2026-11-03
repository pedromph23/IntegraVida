"""Vistas del panel institucional (F3.b: métricas reales en home).

Las tarjetas se filtran por grupo del usuario. Si el usuario no tiene
grupos (o no coincide con GROUP_TO_CARDS), ve todas. Ajustar el mapeo
aquí cuando F3.h cree los grupos reales.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from apps.organizaciones.services import puede_administrar_plataforma
from apps.organizaciones.models import Membresia
from django.urls import reverse
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

    # ── Datos para el mapa ──
    mapa_puntos = []
    try:
        if puede_administrar_plataforma(user):
            org_ids = None
        else:
            org_ids = list(
                Membresia.objects.filter(
                    usuario=user, estado=Membresia.Estado.ACTIVA,
                ).values_list("organizacion_id", flat=True)
            )

        h_qs = Hospital.objects.filter(estado_operativo="DISPONIBLE")
        if org_ids is not None:
            h_qs = h_qs.filter(organizacion_id__in=org_ids)
        for h in h_qs:
            if h.ubicacion:
                mapa_puntos.append({
                    "lat": h.ubicacion.y,
                    "lng": h.ubicacion.x,
                    "titulo": h.nombre,
                    "categoria": "HOSPITAL",
                    "subtitulo": h.direccion,
                    "url": reverse("dashboard:hospital_detail", args=[h.codigo]),
                })

        r_qs = Refugio.objects.filter(estado_operativo="DISPONIBLE")
        if org_ids is not None:
            r_qs = r_qs.filter(organizacion_id__in=org_ids)
        for r in r_qs:
            if r.ubicacion:
                mapa_puntos.append({
                    "lat": r.ubicacion.y,
                    "lng": r.ubicacion.x,
                    "titulo": r.nombre,
                    "categoria": "REFUGIO",
                    "subtitulo": r.direccion,
                    "url": reverse("dashboard:refugio_detail", args=[r.codigo]),
                })
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Error construyendo mapa del panel")
        mapa_puntos = []

    import json
    context = {
        "page_title": "Panel institucional",
        "cards": cards,
        "user_groups": groups,
        "mapa_puntos": mapa_puntos,
        "mapa_puntos_json": json.dumps(mapa_puntos),
    }
    return render(request, "dashboard/home.html", context)
