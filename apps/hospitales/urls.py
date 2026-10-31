from django.urls import path

from apps.hospitales import views

app_name = "hospitales"

urlpatterns = [
    path("", views.lista_hospitales, name="lista"),
    path("<slug:codigo>/", views.detalle_hospital, name="detalle"),
]
