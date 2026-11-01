"""URLs custom del admin (F4.b): MFA.

Se montan bajo /<slug>/mfa/... ANTES que admin.site.urls en
config/urls.py. Sin esto, Django admin capturaría /mfa/ como intento
de acceso a modelo "mfa" y devolvería 404 confuso.
"""
from django.urls import path

from frontend.views import admin_mfa as views

app_name = "admin_custom"

urlpatterns = [
    path("mfa/", views.mfa_verify_view, name="admin_mfa_verify"),
    path("mfa/setup/", views.mfa_setup_view, name="admin_mfa_setup"),
    path("mfa/verify/", views.mfa_verify_submit, name="admin_mfa_submit"),
    path("mfa/cancel/", views.mfa_cancel_view, name="admin_mfa_cancel"),
]
