"""Vista de configuración del admin custom (F4.d). Solo lectura.

No hay catálogos editables en apps.configuracion (ReferenciaMigracion es
interno). F4.d expone estado del sistema y enlaza a Django admin para
CRUD de catálogos nativos (User, Group, Organización).

Edición de catálogos propios → F5.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET

from apps.auditoria.models import EventoAuditoria
from apps.organizaciones.models import Membresia, Organizacion


User = get_user_model()


_admin_login_required = login_required(login_url=reverse_lazy("admin:login"))


def _require_admin_access(request):
    u = request.user
    return u.is_authenticated and (u.is_superuser or u.is_staff)


@_admin_login_required
@require_GET
def config_view(request):
    if not _require_admin_access(request):
        return HttpResponseForbidden("Solo staff/superuser.")

    slug = settings.INTEGRAVIDA_ADMIN_SLUG

    # Métricas mínimas
    total_usuarios = User.objects.count()
    total_orgs = Organizacion.objects.count()
    total_membresias = Membresia.objects.count()
    total_eventos = EventoAuditoria.objects.count()
    total_grupos = Group.objects.count()

    # Settings relevantes (sin filtrar secretos)
    import django
    return render(request, "admin_custom/config.html", {
        "page_title": "Admin · Configuración",
        "info": {
            "django_version": django.get_version(),
            "debug": settings.DEBUG,
            "admin_slug_length": len(slug),
            "mfa_valid_hours": 8,
            "session_age_seconds": getattr(settings, "SESSION_COOKIE_AGE", 1209600),
        },
        "counts": {
            "usuarios": total_usuarios,
            "organizaciones": total_orgs,
            "membresias": total_membresias,
            "eventos_auditoria": total_eventos,
            "grupos_auth": total_grupos,
        },
    })
