"""Vistas del portal público — sin registro (§6.1)."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods

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


@require_GET
def alerts_list(request):
    """Lista pública de alertas (emergencias verificadas)."""
    from django.db.models import Q
    from apps.emergencias.views import (
        ESTADOS_PUBLICOS, _serializar_emergencia,
    )

    queryset = (
        Emergencia.objects
        .filter(estado__in=ESTADOS_PUBLICOS)
        .select_related("municipio", "parroquia")
    )

    categoria = request.GET.get("categoria", "").strip()
    if categoria:
        queryset = queryset.filter(categoria=categoria)

    gravedad = request.GET.get("gravedad", "").strip()
    if gravedad:
        try:
            queryset = queryset.filter(gravedad=int(gravedad))
        except (TypeError, ValueError):
            pass

    estado = request.GET.get("estado", "").strip()
    if estado and estado in ESTADOS_PUBLICOS:
        queryset = queryset.filter(estado=estado)

    municipio = request.GET.get("municipio", "").strip()
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio)

    q = request.GET.get("q", "").strip()[:100]
    if q:
        queryset = queryset.filter(
            Q(ubicacion_texto__icontains=q) | Q(titulo__icontains=q)
        )

    queryset = queryset.order_by("-ocurrida_en", "-creada_en")[:60]

    alertas = [_serializar_emergencia(e) for e in queryset]

    from apps.emergencias.models import Emergencia as EmergenciaModel
    return render(request, "public/alerts_list.html", {
        "alertas": alertas,
        "total": len(alertas),
        "filtros": {
            "categoria": categoria,
            "gravedad": gravedad,
            "estado": estado,
            "municipio": municipio,
            "q": q,
        },
        "opciones_categoria": [
            (v, l) for v, l in EmergenciaModel.Categoria.choices
        ],
        "opciones_gravedad": [
            ("1", "Baja"),
            ("2", "Moderada"),
            ("3", "Alta"),
            ("4", "Crítica"),
        ],
        "opciones_estado": [
            ("CONFIRMADA", "Confirmada"),
            ("EN_ATENCION", "En atención"),
            ("RESUELTA", "Resuelta"),
        ],
    })


@require_GET
def alert_detail(request, emergencia_id):
    """Detalle público de una alerta por UUID."""
    from apps.emergencias.views import (
        ESTADOS_PUBLICOS, _serializar_emergencia,
    )

    try:
        emergencia = (
            Emergencia.objects
            .select_related("municipio", "parroquia")
            .get(id=emergencia_id, estado__in=ESTADOS_PUBLICOS)
        )
    except Emergencia.DoesNotExist:
        raise Http404("Alerta no encontrada")

    return render(request, "public/alert_detail.html", {
        "alerta": _serializar_emergencia(emergencia),
    })


@require_http_methods(["GET", "POST"])
def report_create(request):
    """Formulario HTML de reporte ciudadano + submit."""
    from django.core.exceptions import ValidationError
    from apps.emergencias.models import Emergencia
    from apps.emergencias.services import recibir_reporte_publico

    form_data = {
        "categoria": "",
        "descripcion": "",
        "ubicacion_texto": "",
        "referencia_lugar": "",
    }
    errors = {}
    limitado = False

    if request.method == "POST":
        form_data = {
            "categoria": request.POST.get("categoria", "").strip(),
            "descripcion": request.POST.get("descripcion", "").strip(),
            "ubicacion_texto": request.POST.get("ubicacion_texto", "").strip(),
            "referencia_lugar": request.POST.get("referencia_lugar", "").strip(),
        }

        try:
            reporte, limitado = recibir_reporte_publico(
                datos=form_data,
                request=request,
            )
            if not limitado and reporte is not None:
                return redirect(
                    "public:report-tracking",
                    reporte_id=reporte.id,
                )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                errors = exc.message_dict
            else:
                errors = {"general": list(exc.messages)}

    categorias = [(v, l) for v, l in Emergencia.Categoria.choices]

    status = 200
    if limitado:
        status = 429

    return render(
        request,
        "public/report_form.html",
        {
            "form_data": form_data,
            "errors": errors,
            "limitado": limitado,
            "categorias": categorias,
        },
        status=status,
    )


@require_GET
def report_tracking(request, reporte_id):
    """Seguimiento público de un reporte por UUID (magic link)."""
    from apps.emergencias.models import ReporteEmergencia

    try:
        reporte = ReporteEmergencia.objects.get(id=reporte_id)
    except ReporteEmergencia.DoesNotExist:
        raise Http404("Reporte no encontrado")

    # Privacidad: solo exponer campos NO sensibles.
    # NO se expone: descripcion, ubicacion_texto, referencia_lugar,
    # reportante, punto. El UUID actúa como "magic link".
    vinculado_publico = False
    emergencia_publica = None

    if reporte.emergencia_id is not None:
        try:
            emergencia = reporte.emergencia
            if emergencia.estado in ESTADOS_EMERGENCIA_PUBLICOS:
                vinculado_publico = True
                emergencia_publica = {
                    "id": str(emergencia.id),
                    "titulo": emergencia.titulo,
                }
        except Emergencia.DoesNotExist:
            pass

    data = {
        "id": str(reporte.id),
        "categoria": reporte.categoria,
        "categoria_texto": reporte.get_categoria_display(),
        "estado_revision": reporte.estado_revision,
        "estado_revision_texto": reporte.get_estado_revision_display(),
        "recibido_en": reporte.recibido_en,
        "vinculado": reporte.emergencia_id is not None,
        "vinculado_publico": vinculado_publico,
        "emergencia_publica": emergencia_publica,
    }

    return render(
        request,
        "public/report_tracking.html",
        {"reporte": data},
    )
