"""Vista del mapa navegador (/panel/mapa/)."""
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.emergencias.models import Emergencia
from apps.hospitales.models import Hospital
from apps.organizaciones.models import Membresia
from apps.organizaciones.services import puede_administrar_plataforma
from apps.refugios.models import PuntoReferencia, Refugio


def _org_ids_del_usuario(user):
    return list(
        Membresia.objects
        .filter(usuario=user, estado=Membresia.Estado.ACTIVA)
        .values_list("organizacion_id", flat=True)
    )


def _construir_puntos(user):
    if puede_administrar_plataforma(user):
        org_ids = None
    else:
        org_ids = _org_ids_del_usuario(user)

    puntos = []

    # Hospitales
    h_qs = Hospital.objects.filter(estado_operativo="DISPONIBLE")
    if org_ids is not None:
        h_qs = h_qs.filter(organizacion_id__in=org_ids)
    for h in h_qs:
        if h.ubicacion:
            puntos.append({
                "id": str(h.id),
                "tipo": "hospital",
                "categoria": "HOSPITAL",
                "lat": h.ubicacion.y,
                "lng": h.ubicacion.x,
                "titulo": h.nombre,
                "subtitulo": h.direccion,
                "url": f"/panel/hospitales/{h.codigo}/",
            })

    # Refugios
    r_qs = Refugio.objects.filter(estado_operativo="DISPONIBLE")
    if org_ids is not None:
        r_qs = r_qs.filter(organizacion_id__in=org_ids)
    for r in r_qs:
        if r.ubicacion:
            puntos.append({
                "id": str(r.id),
                "tipo": "refugio",
                "categoria": "REFUGIO",
                "lat": r.ubicacion.y,
                "lng": r.ubicacion.x,
                "titulo": r.nombre,
                "subtitulo": r.direccion,
                "url": f"/panel/refugios/{r.codigo}/",
            })

    # Emergencias (con coordenadas)
    e_qs = Emergencia.objects.exclude(punto__isnull=True)
    if org_ids is not None:
        e_qs = e_qs.filter(organizacion_id__in=org_ids)
    for e in e_qs:
        puntos.append({
            "id": str(e.id),
            "tipo": "emergencia",
            "categoria": "emergencia",
            "lat": e.punto.y,
            "lng": e.punto.x,
            "titulo": getattr(e, "titulo", "Emergencia"),
            "subtitulo": getattr(e, "ubicacion_texto", ""),
            "url": f"/panel/emergencias/{e.id}/",
        })

    # Puntos de referencia
    p_qs = PuntoReferencia.objects.filter(activo=True)
    if org_ids is not None:
        p_qs = p_qs.filter(organizacion_id__in=org_ids)
    for p in p_qs:
        if p.ubicacion:
            puntos.append({
                "id": str(p.id),
                "tipo": "punto",
                "categoria": "punto",
                "lat": p.ubicacion.y,
                "lng": p.ubicacion.x,
                "titulo": p.nombre,
                "subtitulo": p.direccion,
                "url": f"/panel/puntos/{p.id}/",
            })

    return puntos


@login_required
@require_GET
def mapa_view(request):
    puntos = _construir_puntos(request.user)
    return render(request, "dashboard/mapa/index.html", {
        "page_title": "Mapa operativo",
        "puntos_json": json.dumps(puntos),
        "total_puntos": len(puntos),
    })
