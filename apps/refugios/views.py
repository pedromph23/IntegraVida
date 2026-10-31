"""Endpoints públicos de refugios — solo lectura, sin autenticación."""

from django.db.models import Q, Subquery, OuterRef
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.refugios.models import Refugio, RegistroOcupacion


ESTADOS_PUBLICOS = [
    Refugio.EstadoOperativo.ACTIVO,
    Refugio.EstadoOperativo.LLENO,
]


def _serializar_refugio(refugio):
    punto = None
    if refugio.ubicacion:
        punto = {"latitud": refugio.ubicacion.y, "longitud": refugio.ubicacion.x}

    return {
        "id": str(refugio.id),
        "codigo": refugio.codigo,
        "nombre": refugio.nombre,
        "tipo": refugio.tipo,
        "tipo_texto": refugio.get_tipo_display(),
        "direccion": refugio.direccion,
        "referencia_lugar": refugio.referencia_lugar,
        "punto": punto,
        "municipio": refugio.municipio.nombre if refugio.municipio_id else None,
        "parroquia": refugio.parroquia.nombre if refugio.parroquia_id else None,
        "capacidad_total": refugio.capacidad_total,
        "capacidad_disponible": refugio.capacidad_disponible,
        "porcentaje_ocupacion": refugio.porcentaje_ocupacion,
        "esta_lleno": refugio.esta_lleno,
        "servicios": refugio.servicios,
        "estado_operativo": refugio.estado_operativo,
        "estado_operativo_texto": refugio.get_estado_operativo_display(),
        "telefono_publico": refugio.telefono_publico,
        "correo_publico": refugio.correo_publico,
        "ocupacion_actualizada_en": (
            refugio.ultima_ocupacion_en.isoformat()
            if getattr(refugio, "ultima_ocupacion_en", None)
            else None
        ),
    }


def _queryset_publico():
    ultima = (
        RegistroOcupacion.objects
        .filter(refugio=OuterRef("pk"))
        .order_by("-creado_en")
        .values("creado_en")[:1]
    )
    return (
        Refugio.objects
        .filter(estado_operativo__in=ESTADOS_PUBLICOS)
        .select_related("municipio", "parroquia")
        .annotate(ultima_ocupacion_en=Subquery(ultima))
    )


@require_GET
def lista_refugios(request):
    queryset = _queryset_publico()

    tipo = request.GET.get("tipo")
    if tipo:
        tipos_validos = {v for v, _ in Refugio.Tipo.choices}
        if tipo not in tipos_validos:
            return JsonResponse(
                {"error": "El tipo indicado no es válido."}, status=400
            )
        queryset = queryset.filter(tipo=tipo)

    estado = request.GET.get("estado_operativo")
    if estado:
        if estado not in ESTADOS_PUBLICOS:
            return JsonResponse(
                {"error": "El estado solicitado no está disponible públicamente."},
                status=400,
            )
        queryset = queryset.filter(estado_operativo=estado)

    municipio = request.GET.get("municipio")
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio.strip())

    parroquia = request.GET.get("parroquia")
    if parroquia:
        queryset = queryset.filter(parroquia__nombre__icontains=parroquia.strip())

    q = request.GET.get("q")
    if q:
        termino = q.strip()[:100]
        queryset = queryset.filter(
            Q(nombre__icontains=termino) | Q(direccion__icontains=termino)
        )

    try:
        limite = int(request.GET.get("limite", "50"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El límite debe ser un número entre 1 y 100."}, status=400
        )
    if not 1 <= limite <= 100:
        return JsonResponse(
            {"error": "El límite debe ser un número entre 1 y 100."}, status=400
        )

    try:
        offset = int(request.GET.get("offset", "0"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El offset debe ser un entero mayor o igual a 0."}, status=400
        )
    if offset < 0:
        return JsonResponse(
            {"error": "El offset debe ser un entero mayor o igual a 0."}, status=400
        )

    total = queryset.count()
    resultados = queryset.order_by("-creado_en")[offset:offset + limite]

    return JsonResponse({
        "total": total,
        "limite": limite,
        "offset": offset,
        "resultados": [_serializar_refugio(r) for r in resultados],
    })


@require_GET
def detalle_refugio(request, codigo):
    try:
        refugio = _queryset_publico().get(codigo=codigo)
    except Refugio.DoesNotExist:
        return JsonResponse(
            {"error": "El refugio no existe o no está disponible públicamente."},
            status=404,
        )
    return JsonResponse({"refugio": _serializar_refugio(refugio)})
