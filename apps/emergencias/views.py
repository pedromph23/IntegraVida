import json

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from apps.emergencias.models import Emergencia


ESTADOS_PUBLICOS = [
    Emergencia.Estado.CONFIRMADA,
    Emergencia.Estado.EN_ATENCION,
    Emergencia.Estado.RESUELTA,
]


def _serializar_emergencia(emergencia):
    punto = None

    if emergencia.punto:
        punto = {
            "latitud": emergencia.punto.y,
            "longitud": emergencia.punto.x,
        }

    return {
        "id": str(emergencia.id),
        "titulo": emergencia.titulo,
        "descripcion": emergencia.descripcion,
        "categoria": emergencia.categoria,
        "categoria_texto": emergencia.get_categoria_display(),
        "gravedad": emergencia.gravedad,
        "gravedad_texto": emergencia.get_gravedad_display(),
        "estado": emergencia.estado,
        "estado_texto": emergencia.get_estado_display(),
        "ubicacion": emergencia.ubicacion_texto,
        "referencia_lugar": emergencia.referencia_lugar,
        "punto": punto,
        "municipio": (
            emergencia.municipio.nombre
            if emergencia.municipio_id
            else None
        ),
        "parroquia": (
            emergencia.parroquia.nombre
            if emergencia.parroquia_id
            else None
        ),
        "ocurrida_en": (
            emergencia.ocurrida_en.isoformat()
            if emergencia.ocurrida_en
            else None
        ),
        "creada_en": emergencia.creada_en.isoformat(),
        "actualizada_en": emergencia.actualizada_en.isoformat(),
    }


@require_GET
def lista_emergencias(request):
    queryset = (
        Emergencia.objects
        .filter(estado__in=ESTADOS_PUBLICOS)
        .select_related("municipio", "parroquia")
    )

    categoria = request.GET.get("categoria")
    gravedad = request.GET.get("gravedad")
    municipio = request.GET.get("municipio")
    busqueda = request.GET.get("q")

    if categoria:
        categorias_validas = {
            valor for valor, _ in Emergencia.Categoria.choices
        }
        if categoria not in categorias_validas:
            return JsonResponse(
                {"error": "La categoría indicada no es válida."},
                status=400,
            )
        queryset = queryset.filter(categoria=categoria)

    if gravedad:
        try:
            gravedad_numero = int(gravedad)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "La gravedad debe ser un número entre 1 y 4."},
                status=400,
            )

        if gravedad_numero not in Emergencia.Gravedad.values:
            return JsonResponse(
                {"error": "La gravedad debe ser un número entre 1 y 4."},
                status=400,
            )

        queryset = queryset.filter(gravedad=gravedad_numero)

    if municipio:
        queryset = queryset.filter(
            municipio__nombre__icontains=municipio.strip()
        )

    if busqueda:
        termino = busqueda.strip()
        queryset = queryset.filter(
            Q(ubicacion_texto__icontains=termino)
            | Q(titulo__icontains=termino)
        )

    try:
        limite = int(request.GET.get("limite", "50"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El límite debe ser un número entre 1 y 100."},
            status=400,
        )

    if not 1 <= limite <= 100:
        return JsonResponse(
            {"error": "El límite debe ser un número entre 1 y 100."},
            status=400,
        )

    try:
        offset = int(request.GET.get("offset", "0"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El offset debe ser un entero mayor o igual a 0."},
            status=400,
        )

    if offset < 0:
        return JsonResponse(
            {"error": "El offset debe ser un entero mayor o igual a 0."},
            status=400,
        )

    total = queryset.count()
    resultados = queryset.order_by("-creada_en")[offset:offset + limite]

    return JsonResponse({
        "total": total,
        "limite": limite,
        "offset": offset,
        "resultados": [
            _serializar_emergencia(emergencia)
            for emergencia in resultados
        ],
    })


@require_GET
def detalle_emergencia(request, emergencia_id):
    try:
        emergencia = (
            Emergencia.objects
            .select_related("municipio", "parroquia")
            .get(
                id=emergencia_id,
                estado__in=ESTADOS_PUBLICOS,
            )
        )
    except Emergencia.DoesNotExist:
        return JsonResponse(
            {"error": "La emergencia no existe o no está disponible públicamente."},
            status=404,
        )

    return JsonResponse({
        "emergencia": _serializar_emergencia(emergencia),
    })


@require_GET
def estado_servicio_reportes(request):
    """
    Comprueba que el endpoint de recepción está disponible.
    No expone datos de reportes.
    """
    return JsonResponse({
        "servicio": "recepcion_reportes",
        "disponible": True,
    })


@csrf_exempt
@require_POST
def crear_reporte_publico(request):
    """Recibe un reporte ciudadano sin exigir autenticación."""
    from django.core.exceptions import ValidationError

    from apps.emergencias.services import recibir_reporte_publico

    if not (request.content_type or "").startswith("application/json"):
        return JsonResponse(
            {"error": "El contenido debe enviarse como application/json."},
            status=415,
        )

    try:
        datos = json.loads(request.body.decode("utf-8"))
        reporte, limitado = recibir_reporte_publico(
            datos=datos,
            request=request,
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no contiene JSON válido."},
            status=400,
        )
    except ValidationError as exc:
        return JsonResponse(
            {"error": "No se pudo validar el reporte.", "detalles": exc.message_dict
             if hasattr(exc, "message_dict") else exc.messages},
            status=400,
        )

    if limitado:
        return JsonResponse(
            {"error": "Has enviado demasiados reportes. Inténtalo más tarde."},
            status=429,
        )

    return JsonResponse(
        {
            "mensaje": "Reporte recibido. Quedará pendiente de verificación.",
            "reporte_id": str(reporte.id),
            "estado_revision": reporte.estado_revision,
        },
        status=201,
    )
