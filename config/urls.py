"""Enrutamiento raíz.

§7.1: /admin/ devuelve 404 (no 403, no redirect). El admin real vive
bajo /<INTEGRAVIDA_ADMIN_SLUG>/, configurado por env.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.configuracion import views as config_views
from frontend.views.admin_hidden import not_found_404, robots_txt

urlpatterns = [
    # ── Anti-enumeración del admin (§7.1) ────────────────────────────
    # Captura /admin/ y cualquier sub-path ANTES que nada.
    path("admin/", not_found_404),
    path("admin/<path:rest>", not_found_404),

    # ── robots.txt ───────────────────────────────────────────────────
    path("robots.txt", robots_txt, name="robots_txt"),

    # ── Portal público + panel institucional ─────────────────────────
    path("", include("frontend.urls")),

    # ── Health ───────────────────────────────────────────────────────
    path("health/", config_views.health, name="health"),

    # ── Admin personalizado (URL oculta, configurable por env) ───────
    # ── Admin: MFA custom ANTES de admin.site.urls ──────────────
    path(
        f"{settings.INTEGRAVIDA_ADMIN_SLUG}/",
        include("frontend.urls.admin_custom"),
    ),
    path(f"{settings.INTEGRAVIDA_ADMIN_SLUG}/", admin.site.urls),

    # ── API interna / pública ────────────────────────────────────────
    path(
        "api/interno/organizaciones/",
        include("apps.organizaciones.urls"),
    ),
    path(
        "api/interno/emergencias/",
        include("apps.emergencias.urls_internas"),
    ),
    path(
        "api/publico/emergencias/",
        include("apps.emergencias.urls"),
    ),
    path(
        "api/publico/refugios/",
        include("apps.refugios.urls"),
    ),
    path(
        "api/publico/hospitales/",
        include("apps.hospitales.urls"),
    ),
    path(
        "api/interno/reportes/",
        include("apps.reportes.urls"),
    ),
]
