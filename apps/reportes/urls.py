from django.urls import path

from apps.reportes import views

app_name = "reportes"

urlpatterns = [
    path(
        "inventario-critico/",
        views.reporte_inventario_critico,
        name="inventario-critico",
    ),
    path(
        "capacidad-operativa/",
        views.reporte_capacidad_operativa,
        name="capacidad-operativa",
    ),
]
