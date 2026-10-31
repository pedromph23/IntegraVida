"""Endpoints de reportes operativos — requieren autenticación."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.organizaciones.models import Organizacion
from apps.reportes.services import (
    generar_reporte_capacidad_operativa,
    generar_reporte_inventario_critico,
)


def _resolver_organizacion(request):
    org_id = request.GET.get("organizacion")
    if not org_id:
        return None
    try:
        return Organizacion.objects.get(pk=org_id)
    except Organizacion.DoesNotExist:
        raise ValidationError({"organizacion": "No existe."})


def _respuesta_error(exc):
    if isinstance(exc, PermissionDenied):
        return JsonResponse({"error": str(exc)}, status=403)
    if isinstance(exc, ValidationError):
        detalles = (
            exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        )
        return JsonResponse(
            {"error": "Solicitud inválida.", "detalles": detalles},
            status=400,
        )
    return JsonResponse({"error": "Error inesperado."}, status=500)


@require_GET
def reporte_inventario_critico(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autenticación requerida."}, status=401)
    try:
        organizacion = _resolver_organizacion(request)
        data = generar_reporte_inventario_critico(
            usuario=request.user,
            organizacion=organizacion,
            request=request,
        )
    except (PermissionDenied, ValidationError) as exc:
        return _respuesta_error(exc)
    return JsonResponse(data)


@require_GET
def reporte_capacidad_operativa(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autenticación requerida."}, status=401)
    try:
        organizacion = _resolver_organizacion(request)
        data = generar_reporte_capacidad_operativa(
            usuario=request.user,
            organizacion=organizacion,
            request=request,
        )
    except (PermissionDenied, ValidationError) as exc:
        return _respuesta_error(exc)
    return JsonResponse(data)
