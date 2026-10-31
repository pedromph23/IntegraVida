"""Vista raíz — landing informativa + health check (§14).

No es el portal público real; es un punto de entrada que informa
el estado del sistema y enlaza a los endpoints disponibles.
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.auditoria.models import EventoAuditoria
from apps.emergencias.models import Emergencia
from apps.hospitales.models import Hospital
from apps.refugios.models import Refugio


@require_GET
def index(request):
    """Landing HTML en /."""
    contexto = {
        "nombre": "IntegraVida",
        "version": "0.11.0",
        "entorno": "desarrollo" if __import__("django.conf").conf.settings.DEBUG else "producción",
        "stats": {
            "emergencias_publicas": Emergencia.objects.filter(
                estado__in=[
                    Emergencia.Estado.CONFIRMADA,
                    Emergencia.Estado.EN_ATENCION,
                    Emergencia.Estado.RESUELTA,
                ]
            ).count(),
            "refugios_activos": Refugio.objects.filter(
                estado_operativo__in=[
                    Refugio.EstadoOperativo.ACTIVO,
                    Refugio.EstadoOperativo.LLENO,
                ]
            ).count(),
            "hospitales_activos": Hospital.objects.filter(
                estado_operativo__in=[
                    Hospital.EstadoOperativo.DISPONIBLE,
                    Hospital.EstadoOperativo.SATURADO,
                ]
            ).count(),
            "eventos_auditoria": EventoAuditoria.objects.count(),
        },
        "endpoints_publicos": [
            ("/api/publico/emergencias/", "Emergencias"),
            ("/api/publico/refugios/", "Refugios"),
            ("/api/publico/hospitales/", "Hospitales"),
        ],
    }
    return render(request, "index.html", contexto)


@require_GET
def health(request):
    """Health check JSON para load balancers."""
    return JsonResponse({
        "status": "ok",
        "service": "integravida",
        "version": "0.11.0",
    })
