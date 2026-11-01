"""Vistas de ocultamiento del admin (F4.a).

- not_found_404: devuelve 404 silencioso para /admin/ y subpaths
  (NO usa raise Http404 para evitar revelar que la ruta existe).
- robots_txt: sirve /robots.txt con Disallow del slug del admin y
  de rutas internas.
"""
from django.conf import settings
from django.http import HttpResponse


def not_found_404(request, rest=""):
    """404 directo sin redirect, sin login, sin información."""
    return HttpResponse(
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
        "<title>No encontrado</title></head><body>"
        "<h1>404</h1><p>La página solicitada no existe.</p>"
        "</body></html>",
        status=404,
        content_type="text/html; charset=utf-8",
    )


def robots_txt(request):
    slug = settings.INTEGRAVIDA_ADMIN_SLUG
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        f"Disallow: /{slug}/",
        "Disallow: /panel/",
        "Disallow: /api/",
        "Disallow: /health/",
        "Allow: /",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
        "",
    ]
    return HttpResponse(
        "\n".join(lines), content_type="text/plain; charset=utf-8",
    )
