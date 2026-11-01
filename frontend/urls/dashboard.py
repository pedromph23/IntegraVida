"""URLs del panel institucional (F3.a home + F3.c refugios)."""
from django.urls import path

from frontend.views import dashboard as dash_views
from frontend.views import dashboard_refugios as refugio_views

app_name = "dashboard"

urlpatterns = [
    path("", dash_views.home, name="home"),
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
]
