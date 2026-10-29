from django.contrib import admin
from django.urls import include, path

urlpatterns = [
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
]
