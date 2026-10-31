"""Context processors del frontend."""
from django.conf import settings


def map_config(request):
    """Expone la config de Leaflet a los templates (F2.e)."""
    return {
        "TILE_SERVER_URL": settings.TILE_SERVER_URL,
        "TILE_SERVER_ATTRIBUTION": settings.TILE_SERVER_ATTRIBUTION,
    }
