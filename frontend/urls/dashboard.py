"""URLs del panel institucional (F3.a)."""
from django.urls import path

from frontend.views import dashboard as dash_views

app_name = "dashboard"

urlpatterns = [
    path("", dash_views.home, name="home"),
]
