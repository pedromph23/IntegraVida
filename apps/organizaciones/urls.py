from django.urls import path

from apps.organizaciones.views import organizaciones_internas

app_name = "organizaciones"

urlpatterns = [
    path(
        "",
        organizaciones_internas,
        name="organizaciones-internas",
    ),
]
