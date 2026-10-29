from django.urls import path

from apps.emergencias import views

app_name = "emergencias"

urlpatterns = [
    path("", views.lista_emergencias, name="lista"),
    path(
        "reportes/estado/",
        views.estado_servicio_reportes,
        name="estado-servicio",
    ),
    path(
        "reportes/",
        views.crear_reporte_publico,
        name="crear-reporte",
    ),
    path(
        "<uuid:emergencia_id>/",
        views.detalle_emergencia,
        name="detalle",
    ),
]
