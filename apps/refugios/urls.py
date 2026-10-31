from django.urls import path

from apps.refugios import views

app_name = "refugios"

urlpatterns = [
    path("", views.lista_refugios, name="lista"),
    path("<slug:codigo>/", views.detalle_refugio, name="detalle"),
]
