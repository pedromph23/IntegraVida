"""Vistas de autenticación del panel institucional (F3.a)."""
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy


class PanelLoginView(auth_views.LoginView):
    template_name = "auth/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Acceso al panel institucional"
        ctx["mfa_enabled"] = False  # True cuando backend lo soporte
        return ctx


class PanelLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("auth:login")
