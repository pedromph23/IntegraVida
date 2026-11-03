"""API proxy hacia OSRM local (localhost:5000)."""
import json
import urllib.request
import urllib.error

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET


OSRM_BASE = "http://localhost:5000"


@login_required
@require_GET
def calcular_ruta(request):
    """Proxy: /panel/api/ruta/?origin_lat=..&origin_lng=..&dest_lat=..&dest_lng=.."""
    try:
        o_lat = float(request.GET["origin_lat"])
        o_lng = float(request.GET["origin_lng"])
        d_lat = float(request.GET["dest_lat"])
        d_lng = float(request.GET["dest_lng"])
    except (KeyError, ValueError):
        return JsonResponse({"error": "Coordenadas inválidas"}, status=400)

    url = (
        f"{OSRM_BASE}/route/v1/driving/"
        f"{o_lng},{o_lat};{d_lng},{d_lat}"
        f"?overview=full&steps=true&geometries=geojson"
    )

    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read())
        return JsonResponse(data)
    except urllib.error.URLError as e:
        return JsonResponse(
            {"error": "Motor de rutas no disponible (OSRM offline)", "detail": str(e)},
            status=503,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
