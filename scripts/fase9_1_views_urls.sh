#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/reportes/views.py << 'EOF'
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


def _manejar(handler):
    def wrapper(request):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Autenticación requerida."}, status=401
            )
        try:
            organizacion = _resolver_organizacion(request)
            data = handler(
                usuario=request.user,
                organizacion=organizacion,
                request=request,
            )
        except PermissionDenied as exc:
            return JsonResponse({"error": str(exc)}, status=403)
        except ValidationError as exc:
            detalles = (
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            )
            return JsonResponse(
                {"error": "Solicitud inválida.", "detalles": detalles},
                status=400,
            )
        return JsonResponse(data)
    return wrapper


@require_GET
@_manejar
def reporte_inventario_critico(request, *, usuario, organizacion, request_):
    return generar_reporte_inventario_critico(
        usuario=usuario, organizacion=organizacion, request=request_,
    )


@require_GET
@_manejar
def reporte_capacidad_operativa(request, *, usuario, organizacion, request_):
    return generar_reporte_capacidad_operativa(
        usuario=usuario, organizacion=organizacion, request=request_,
    )
EOF

# Corregir el decorador: la firma _manejar no pasa request correctamente.
# Rehacer views.py más simple.
cat > apps/reportes/views.py << 'EOF'
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
EOF

cat > apps/reportes/urls.py << 'EOF'
from django.urls import path

from apps.reportes import views

app_name = "reportes"

urlpatterns = [
    path(
        "inventario-critico/",
        views.reporte_inventario_critico,
        name="inventario-critico",
    ),
    path(
        "capacidad-operativa/",
        views.reporte_capacidad_operativa,
        name="capacidad-operativa",
    ),
]
EOF

# Registrar en config/urls.py
python3 - << 'PY'
from pathlib import Path
p = Path("config/urls.py")
text = p.read_text(encoding="utf-8")
needle = (
    '    path(\n'
    '        "api/publico/hospitales/",\n'
    '        include("apps.hospitales.urls"),\n'
    '    ),\n'
)
addition = needle + (
    '    path(\n'
    '        "api/interno/reportes/",\n'
    '        include("apps.reportes.urls"),\n'
    '    ),\n'
)
if '"api/interno/reportes/"' in text:
    print("ya aplicado")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: reportes en config/urls.py")
else:
    raise SystemExit("ERROR: marker no encontrado en config/urls.py")
PY

python3 manage.py shell -c "from apps.reportes import views, urls; print('OK: views y urls')"
