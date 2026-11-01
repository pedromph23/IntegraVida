"""Middleware de seguridad para el admin personalizado (F4.a).

Añade headers anti-indexación y anti-cacheo a todas las respuestas
cuyo path empieza por `/<INTEGRAVIDA_ADMIN_SLUG>/`. No toca el portal
público ni el panel institucional.
"""
from django.conf import settings


class AdminSecurityMiddleware:
    """Fuerza headers de ocultamiento en el admin.

    §7.1:
    - X-Robots-Tag: noindex, nofollow, noarchive
    - Cache-Control: no-store

    Se aplica DESPUÉS de AuthenticationMiddleware para no interferir
    con la auth normal; solo modifica `response` en process_response.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        slug = getattr(settings, "INTEGRAVIDA_ADMIN_SLUG", "")
        self.prefix = f"/{slug}/" if slug else None

    def __call__(self, request):
        response = self.get_response(request)
        return self._endurecer(request, response)

    def _endurecer(self, request, response):
        if not self.prefix:
            return response
        if not request.path.startswith(self.prefix):
            return response

        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response["Pragma"] = "no-cache"
        response["X-Frame-Options"] = "DENY"
        return response
