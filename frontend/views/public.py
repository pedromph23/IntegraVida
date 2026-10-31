"""Vistas del portal público — sin registro (§6.1)."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
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
        raise Http404()
    return render(request, "public/design_system.html", {
        "estados_demo": [
            ("ACTIVO", "Activo"),
            ("LLENO", "Lleno"),
            ("CERRADO", "Cerrado"),
        ],
    })


@require_GET
def hospitals_list(request):
    """Lista pública de hospitales con filtros server-side."""
    from apps.hospitales.views import _queryset_publico

    queryset = _queryset_publico()

    tipo = request.GET.get("tipo", "").strip()
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    nivel = request.GET.get("nivel", "").strip()
    if nivel:
        queryset = queryset.filter(nivel=nivel)

    estado = request.GET.get("estado_operativo", "").strip()
    if estado:
        queryset = queryset.filter(estado_operativo=estado)

    municipio = request.GET.get("municipio", "").strip()
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio)

    servicio = request.GET.get("servicio", "").strip()
    if servicio:
        queryset = queryset.filter(
            servicios_through__servicio__codigo=servicio,
            servicios_through__disponible=True,
            servicios_through__servicio__activo=True,
        ).distinct()

    q = request.GET.get("q", "").strip()[:100]
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(nombre__icontains=q) | Q(direccion__icontains=q)
        )

    queryset = queryset.order_by("nombre")[:60]
    ahora = timezone.now()

    from apps.hospitales.views import _serializar_hospital
    hospitales = [_serializar_hospital(h, ahora) for h in queryset]

    return render(request, "public/hospitals_list.html", {
        "hospitales": hospitales,
        "total": len(hospitales),
        "filtros": {
            "tipo": tipo,
            "nivel": nivel,
            "estado_operativo": estado,
            "municipio": municipio,
            "servicio": servicio,
            "q": q,
        },
        "opciones_tipo": [
            ("HOSPITAL", "Hospital"),
            ("CLINICA", "Clínica"),
            ("CENTRO_SALUD", "Centro de salud"),
            ("AMBULATORIO", "Ambulatorio"),
        ],
        "opciones_nivel": [
            ("NIVEL_I", "Nivel I"),
            ("NIVEL_II", "Nivel II"),
            ("NIVEL_III", "Nivel III"),
            ("NIVEL_IV", "Nivel IV"),
        ],
        "opciones_estado": [
            ("DISPONIBLE", "Disponible"),
            ("SATURADO", "Saturado"),
        ],
    })


@require_GET
def hospital_detail(request, codigo):
    """Detalle público de un hospital por código (slug)."""
    from apps.hospitales.views import _queryset_publico, _serializar_hospital
    try:
        hospital = _queryset_publico().get(codigo=codigo)
    except Hospital.DoesNotExist:
        raise Http404("Hospital no encontrado")

    return render(request, "public/hospital_detail.html", {
        "hospital": _serializar_hospital(hospital, timezone.now()),
    })


@require_GET
def shelters_list(request):
    """Lista pública de refugios con filtros server-side."""
    from apps.refugios.views import _queryset_publico

    queryset = _queryset_publico()

    tipo = request.GET.get("tipo", "").strip()
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    estado = request.GET.get("estado_operativo", "").strip()
    if estado:
        queryset = queryset.filter(estado_operativo=estado)

    municipio = request.GET.get("municipio", "").strip()
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio)

    # Filtro de disponibilidad: refugios con capacidad libre > 0
    solo_con_lugar = request.GET.get("con_lugar") == "1"
    if solo_con_lugar:
        from django.db.models import F
        queryset = queryset.filter(capacidad_total__gt=F("ocupacion_actual"))

    q = request.GET.get("q", "").strip()[:100]
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(nombre__icontains=q) | Q(direccion__icontains=q)
        )

    queryset = queryset.order_by("nombre")[:60]

    from apps.refugios.views import _serializar_refugio
    refugios = [_serializar_refugio(r) for r in queryset]

    return render(request, "public/shelters_list.html", {
        "refugios": refugios,
        "total": len(refugios),
        "filtros": {
            "tipo": tipo,
            "estado_operativo": estado,
            "municipio": municipio,
            "con_lugar": solo_con_lugar,
            "q": q,
        },
        "opciones_tipo": [
            ("REFUGIO", "Refugio"),
            ("CENTRO_ACOPIO", "Centro de acopio"),
            ("ALBERGUE_TEMPORAL", "Albergue temporal"),
            ("OTRO", "Otro"),
        ],
        "opciones_estado": [
            ("ACTIVO", "Activo"),
            ("LLENO", "Lleno"),
        ],
    })


@require_GET
def shelter_detail(request, codigo):
    """Detalle público de un refugio por código (slug)."""
    from apps.refugios.views import _queryset_publico, _serializar_refugio
    try:
        refugio = _queryset_publico().get(codigo=codigo)
    except Refugio.DoesNotExist:
        raise Http404("Refugio no encontrado")

    return render(request, "public/shelter_detail.html", {
        "refugio": _serializar_refugio(refugio),
    })
