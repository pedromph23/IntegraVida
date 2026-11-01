"""URLs del panel (F3.a home + F3.c refugios + F3.d emergencias + F3.e.1 hospitales)."""
from django.urls import path

from frontend.views import dashboard as dash_views
from frontend.views import dashboard_refugios as refugio_views
from frontend.views import dashboard_emergencias as emergencia_views
from frontend.views import dashboard_hospitales as hospital_views

app_name = "dashboard"

urlpatterns = [
    path("", dash_views.home, name="home"),

    # F3.c — Refugios
    path("refugios/", refugio_views.refugios_list, name="refugios_list"),
    path(
        "refugios/<slug:codigo>/",
        refugio_views.refugio_detail,
        name="refugio_detail",
    ),
    path(
        "refugios/<slug:codigo>/estado/",
        refugio_views.refugio_cambiar_estado,
        name="refugio_cambiar_estado",
    ),

    # F3.d — Emergencias
    path(
        "emergencias/",
        emergencia_views.emergencias_list,
        name="emergencias_list",
    ),
    path(
        "emergencias/<uuid:emergencia_id>/",
        emergencia_views.emergencia_detail,
        name="emergencia_detail",
    ),
    path(
        "emergencias/<uuid:emergencia_id>/estado/",
        emergencia_views.emergencia_cambiar_estado,
        name="emergencia_cambiar_estado",
    ),

    # F3.e.1 — Hospitales
    path(
        "hospitales/",
        hospital_views.hospitales_list,
        name="hospitales_list",
    ),
    path(
        "hospitales/<slug:codigo>/",
        hospital_views.hospital_detail,
        name="hospital_detail",
    ),
    path(
        "hospitales/<slug:codigo>/estado/",
        hospital_views.hospital_cambiar_estado,
        name="hospital_cambiar_estado",
    ),
]
