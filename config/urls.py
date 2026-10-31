from django.contrib import admin
from django.urls import include, path
from apps.configuracion import views as config_views

urlpatterns = [
    path("", config_views.index, name="index"),
    path("health/", config_views.health, name="health"),
    path("admin/", admin.site.urls),
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
