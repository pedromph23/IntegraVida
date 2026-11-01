"""Vista de dashboard del admin custom (F4.c).

Métricas reales de usuarios + eventos de auditoría recientes + salud
del sistema. Solo staff/superuser. El MFA lo garantiza el middleware
(AdminMFARequiredMiddleware); aquí no re-verificamos MFA.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.auditoria.models import EventoAuditoria


User = get_user_model()


_admin_login_required = login_required(login_url=reverse_lazy("admin:login"))


def _require_admin_access(request):
    u = request.user
    return u.is_authenticated and (u.is_superuser or u.is_staff)


@_admin_login_required
@require_GET
def dashboard_view(request):
    if not _require_admin_access(request):
        return HttpResponseForbidden("Solo staff/superuser.")

    # ── Métricas de usuarios ──
    usuarios_total = User.objects.count()
    usuarios_staff = User.objects.filter(is_staff=True).count()
    usuarios_superusers = User.objects.filter(is_superuser=True).count()
    usuarios_activos = User.objects.filter(is_active=True).count()
    usuarios_mfa = User.objects.filter(admin_mfa_secret__isnull=False).count()
    usuarios_sin_mfa = max(usuarios_staff - usuarios_mfa, 0)

    # ── Auditoría reciente ──
    eventos = list(
        EventoAuditoria.objects
        .select_related("actor")
        .order_by("-ocurrido_en")[:10]
    )
    total_eventos = EventoAuditoria.objects.count()

    # ── Salud del sistema ──
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    return render(request, "admin_custom/dashboard.html", {
        "page_title": "Admin · Dashboard",
        "usuarios_total": usuarios_total,
        "usuarios_staff": usuarios_staff,
        "usuarios_superusers": usuarios_superusers,
        "usuarios_activos": usuarios_activos,
        "usuarios_mfa": usuarios_mfa,
        "usuarios_sin_mfa": usuarios_sin_mfa,
        "eventos": eventos,
        "total_eventos": total_eventos,
        "db_ok": db_ok,
    })
