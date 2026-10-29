from django.urls import path

from apps.emergencias import vistas_internas

app_name = "emergencias_internas"

urlpatterns = [
    path(
        "reportes/",
        vistas_internas.lista_reportes_internos,
        name="lista-reportes",
    ),
    path(
        "reportes/<uuid:reporte_id>/revision/",
        vistas_internas.revisar_reporte_interno,
        name="revisar-reporte",
    ),
    path(
        "reportes/<uuid:reporte_id>/vincular/",
        vistas_internas.vincular_reporte_interno,
        name="vincular-reporte",
    ),
]
