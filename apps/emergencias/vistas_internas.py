"""Endpoints internos para la revisión de reportes ciudadanos."""

import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.emergencias.models import Emergencia, ReporteEmergencia
from apps.emergencias.servicios_revision import (
    cambiar_estado_reporte,
    puede_revisar_reportes,
    vincular_reporte_emergencia,
)


def _error_validacion(exc):
    detalles = (
        exc.message_dict
        if hasattr(exc, "message_dict")
        else exc.messages
    )
    return JsonResponse(
        {"error": "La solicitud no es válida.", "detalles": detalles},
        status=400,
    )


def _autorizar(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Debes iniciar sesión."},
            status=401,
        )

    if not puede_revisar_reportes(request.user):
        return JsonResponse(
            {"error": "No tienes permiso para revisar reportes."},
            status=403,
        )

    return None


def _leer_json(request):
    if request.content_type != "application/json":
        return None, JsonResponse(
            {"error": "El contenido debe ser application/json."},
            status=415,
        )

    try:
        datos = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse(
            {"error": "El cuerpo de la solicitud no contiene JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return None, JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    return datos, None


def _serializar_reporte(reporte):
    return {
        "id": str(reporte.id),
        "categoria": reporte.categoria,
        "categoria_texto": reporte.get_categoria_display(),
        "descripcion": reporte.descripcion,
        "ubicacion_texto": reporte.ubicacion_texto,
        "referencia_lugar": reporte.referencia_lugar,
        "canal": reporte.canal,
        "estado_revision": reporte.estado_revision,
        "estado_revision_texto": reporte.get_estado_revision_display(),
        "recibido_en": reporte.recibido_en.isoformat(),
        "emergencia_id": (
            str(reporte.emergencia_id) if reporte.emergencia_id else None
        ),
        "municipio": (
            reporte.municipio.nombre if reporte.municipio_id else None
        ),
        "parroquia": (
            reporte.parroquia.nombre if reporte.parroquia_id else None
        ),
    }


@require_GET
def lista_reportes_internos(request):
    denegacion = _autorizar(request)
    if denegacion:
        return denegacion

    queryset = ReporteEmergencia.objects.select_related(
        "emergencia", "municipio", "parroquia"
    )

    estado = request.GET.get("estado_revision")
    if estado:
        if estado not in ReporteEmergencia.EstadoRevision.values:
            return JsonResponse(
                {"error": "El estado de revisión no es válido."},
                status=400,
            )
        queryset = queryset.filter(estado_revision=estado)
    else:
        queryset = queryset.filter(
            estado_revision__in=[
                ReporteEmergencia.EstadoRevision.PENDIENTE,
                ReporteEmergencia.EstadoRevision.EN_REVISION,
            ]
        )

    categoria = request.GET.get("categoria")
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

    try:
        limite = int(request.GET.get("limite", "50"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El límite debe estar entre 1 y 100."},
            status=400,
        )

    if not 1 <= limite <= 100:
        return JsonResponse(
            {"error": "El límite debe estar entre 1 y 100."},
            status=400,
        )

    total = queryset.count()
    resultados = queryset.order_by("-recibido_en")[:limite]

    return JsonResponse({
        "total": total,
        "limite": limite,
        "resultados": [_serializar_reporte(r) for r in resultados],
    })


@require_POST
def revisar_reporte_interno(request, reporte_id):
    denegacion = _autorizar(request)
    if denegacion:
        return denegacion

    datos, error = _leer_json(request)
    if error:
        return error

    campos_permitidos = {"estado_revision", "justificacion"}
    if set(datos) - campos_permitidos:
        return JsonResponse(
            {"error": "La solicitud contiene campos no permitidos."},
            status=400,
        )

    try:
        reporte = cambiar_estado_reporte(
            reporte_id=reporte_id,
            estado_nuevo=datos.get("estado_revision"),
            justificacion=datos.get("justificacion", ""),
            usuario=request.user,
            request=request,
        )
    except ReporteEmergencia.DoesNotExist:
        return JsonResponse({"error": "El reporte no existe."}, status=404)
    except PermissionDenied:
        return JsonResponse({"error": "No tienes permiso para revisar reportes."}, status=403)
    except ValidationError as exc:
        return _error_validacion(exc)

    return JsonResponse({
        "mensaje": "El estado del reporte fue actualizado.",
        "reporte": _serializar_reporte(reporte),
    })


@require_POST
def vincular_reporte_interno(request, reporte_id):
    denegacion = _autorizar(request)
    if denegacion:
        return denegacion

    datos, error = _leer_json(request)
    if error:
        return error

    campos_permitidos = {"emergencia_id", "justificacion"}
    if set(datos) - campos_permitidos:
        return JsonResponse(
            {"error": "La solicitud contiene campos no permitidos."},
            status=400,
        )

    emergencia_id = datos.get("emergencia_id")
    if not isinstance(emergencia_id, str) or not emergencia_id.strip():
        return JsonResponse(
            {"error": "Debes proporcionar el identificador de la emergencia."},
            status=400,
        )

    try:
        reporte = vincular_reporte_emergencia(
            reporte_id=reporte_id,
            emergencia_id=emergencia_id,
            justificacion=datos.get("justificacion", ""),
            usuario=request.user,
            request=request,
        )
    except ReporteEmergencia.DoesNotExist:
        return JsonResponse({"error": "El reporte no existe."}, status=404)
    except Emergencia.DoesNotExist:
        return JsonResponse({"error": "La emergencia no existe."}, status=404)
    except PermissionDenied:
        return JsonResponse({"error": "No tienes permiso para revisar reportes."}, status=403)
    except ValidationError as exc:
        return _error_validacion(exc)

    return JsonResponse({
        "mensaje": "El reporte fue vinculado a la emergencia.",
        "reporte": _serializar_reporte(reporte),
    })
