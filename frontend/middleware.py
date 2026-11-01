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


class AdminMFARequiredMiddleware:
    """Fuerza MFA en el admin personalizado (F4.b).

    Aplica SOLO a /<slug>/*, excluyendo rutas de auth y estáticos
    (login, logout, password_reset, mfa, jsi18n, static).

    Si el usuario autenticado no tiene `admin_mfa_verified_at`
    reciente (< 8 h) en la sesión, redirige a /<slug>/mfa/.

    No actúa sobre anónimos: deja que Django admin redirija a /login/.
    """
    MFA_SESSION_KEY = "admin_mfa_verified_at"
    MFA_USER_KEY = "admin_mfa_user_id"
    MFA_VALID_SECONDS = 8 * 3600  # 8 h

    # Sufijos (relativos a /<slug>) que NO requieren MFA.
    ALLOWLIST_PREFIXES = (
        "/login/",
        "/logout/",
        "/password_reset/",
        "/reset/",            # cubre /reset/<uidb64>/<token>/
        "/mfa/",              # cubre /mfa/ y /mfa/setup/
        "/jsi18n/",
        "/static/",
        "/favicon.ico",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        slug = getattr(settings, "INTEGRAVIDA_ADMIN_SLUG", "")
        self.slug = slug
        self.prefix = f"/{slug}/" if slug else None
        self.mfa_url = f"/{slug}/mfa/" if slug else None

    def __call__(self, request):
        if self._aplica(request):
            redir = self._check_mfa(request)
            if redir is not None:
                return redir
        return self.get_response(request)

    def _aplica(self, request):
        if not self.prefix:
            return False
        if not request.path.startswith(self.prefix):
            return False
        # Ruta relativa al slug, con "/" inicial
        resto = "/" + request.path[len(self.prefix):]
        for pref in self.ALLOWLIST_PREFIXES:
            if resto.startswith(pref):
                return False
        return True

    def _check_mfa(self, request):
        from django.shortcuts import redirect
        from django.utils import timezone

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if not (user.is_superuser or user.is_staff):
            return None

        mfa_user_id = request.session.get(self.MFA_USER_KEY)
        mfa_verified_at = request.session.get(self.MFA_SESSION_KEY)

        if str(mfa_user_id) != str(user.pk) or not mfa_verified_at:
            return redirect(self.mfa_url)

        try:
            verified_ts = float(mfa_verified_at)
        except (TypeError, ValueError):
            return redirect(self.mfa_url)

        if timezone.now().timestamp() - verified_ts > self.MFA_VALID_SECONDS:
            return redirect(self.mfa_url)

        return None


class SecurityHeadersMiddleware:
    """Añade CSP + headers de seguridad modernos a TODAS las respuestas.

    - Content-Security-Policy (restrictiva, con deuda documentada)
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation/microphone/camera bloqueados

    Nota sobre CSP:
    - script-src 'unsafe-inline' por script anti-FOUC inline en base_*.html.
    - script-src 'unsafe-eval' por Alpine.js (compila expresiones x-data).
    - style-src 'unsafe-inline' por Tailwind (vars CSS dinámicas).
    - img-src https: por tiles de Leaflet (TILE_SERVER_URL configurable).
    Refactor a nonce/hash → F5.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._set_headers(response)
        return response

    def _set_headers(self, response):
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.setdefault("Content-Security-Policy", csp)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin",
        )
        response.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
