"""Vistas del portal público — sin registro (§6.1)."""

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.emergencias.models import Emergencia
from apps.hospitales.models import Hospital
from apps.refugios.models import Refugio


ESTADOS_EMERGENCIA_PUBLICOS = [
    Emergencia.Estado.CONFIRMADA,
    Emergencia.Estado.EN_ATENCION,
    Emergencia.Estado.RESUELTA,
]

ESTADOS_REFUGIO_PUBLICOS = [
    Refugio.EstadoOperativo.ACTIVO,
    Refugio.EstadoOperativo.LLENO,
]

ESTADOS_HOSPITAL_PUBLICOS = [
    Hospital.EstadoOperativo.DISPONIBLE,
    Hospital.EstadoOperativo.SATURADO,
]


@require_GET
def home(request):
    """Home del portal público con conteos agregados."""
    contexto = {
        "stats": {
            "emergencias_publicas": Emergencia.objects.filter(
                estado__in=ESTADOS_EMERGENCIA_PUBLICOS,
            ).count(),
            "refugios_activos": Refugio.objects.filter(
                estado_operativo__in=ESTADOS_REFUGIO_PUBLICOS,
            ).count(),
            "hospitales_activos": Hospital.objects.filter(
                estado_operativo__in=ESTADOS_HOSPITAL_PUBLICOS,
            ).count(),
        },
    }
    return render(request, "public/home.html", contexto)


@require_GET
def design_system(request):
    """Demo del sistema de diseño. Solo en DEBUG."""
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404()
    return render(request, "public/design_system.html", {
        "estados_demo": [
            ("ACTIVO", "Activo"),
            ("LLENO", "Lleno"),
            ("CERRADO", "Cerrado"),
        ],
    })
