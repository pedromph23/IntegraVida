"""URLs de autenticación del panel (F3.a). Montadas bajo /panel/."""
from django.urls import path

from frontend.views import auth as auth_views

app_name = "auth"

urlpatterns = [
    path("login/", auth_views.PanelLoginView.as_view(), name="login"),
    path("logout/", auth_views.PanelLogoutView.as_view(), name="logout"),
]
