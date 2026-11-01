"""URLs custom del admin (F4.b + F4.c).

Se montan bajo /<slug>/... ANTES que admin.site.urls en config/urls.py.
- F4.b: mfa/*
- F4.c: custom/ (dashboard) + custom/users/ (gestión staff)

Django admin nativo sigue en /<slug>/ (root).
"""
from django.urls import path

from frontend.views import admin_mfa as mfa_views
from frontend.views import admin_dashboard as dash_views
from frontend.views import admin_users as users_views
from frontend.views import admin_audit as audit_views
from frontend.views import admin_config as config_views

app_name = "admin_custom"

urlpatterns = [
    # ── F4.b — MFA ──
    path("mfa/", mfa_views.mfa_verify_view, name="admin_mfa_verify"),
    path("mfa/setup/", mfa_views.mfa_setup_view, name="admin_mfa_setup"),
    path("mfa/verify/", mfa_views.mfa_verify_submit, name="admin_mfa_submit"),
    path("mfa/cancel/", mfa_views.mfa_cancel_view, name="admin_mfa_cancel"),

    # ── F4.c — Dashboard custom + usuarios ──
    path("custom/", dash_views.dashboard_view, name="admin_dashboard"),
    path("custom/users/", users_views.users_list, name="admin_users_list"),

    # ── F4.d — Auditoría + Configuración ──
    path("custom/audit/", audit_views.audit_list, name="admin_audit_list"),
    path("custom/audit/<uuid:evento_id>/", audit_views.audit_detail, name="admin_audit_detail"),
    path("custom/config/", config_views.config_view, name="admin_config"),
]
