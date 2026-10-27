"""Vistas HTTP para la gestión interna de organizaciones."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.organizaciones.models import Membresia, Organizacion
from apps.organizaciones.services import puede_administrar_plataforma


def _error_json(mensaje, estado):
    return JsonResponse({"error": mensaje}, status=estado)


@require_GET
def organizaciones_internas(request):
    """Lista organizaciones dentro del ámbito autorizado del usuario."""
    usuario = request.user

    if not usuario.is_authenticated:
        return _error_json("Autenticación requerida.", 401)

    if not usuario.is_active:
        return _error_json("Cuenta inactiva.", 403)

    if puede_administrar_plataforma(usuario):
        organizaciones = Organizacion.objects.all()
    else:
        organizaciones = Organizacion.objects.filter(
            estado=Organizacion.Estado.ACTIVA,
            membresias__usuario=usuario,
            membresias__estado=Membresia.Estado.ACTIVA,
        )

    organizaciones = organizaciones.order_by("nombre").distinct()

    resultados = [
        {
            "id": str(organizacion.pk),
            "nombre": organizacion.nombre,
            "tipo": organizacion.tipo,
            "estado": organizacion.estado,
        }
        for organizacion in organizaciones
    ]

    return JsonResponse({"resultados": resultados})
