"""Vistas de usuarios staff/superuser del admin custom (F4.c).

Por ahora: listado de staff + superusers. Acciones (revocar sesiones,
resetear MFA) llegan en F4.d.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.shortcuts import render
from django.views.decorators.http import require_GET


User = get_user_model()


_admin_login_required = login_required(login_url=reverse_lazy("admin:login"))


def _require_admin_access(request):
    u = request.user
    return u.is_authenticated and (u.is_superuser or u.is_staff)


@_admin_login_required
@require_GET
def users_list(request):
    if not _require_admin_access(request):
        return HttpResponseForbidden("Solo staff/superuser.")

    qs = (
        User.objects
        .filter(Q(is_staff=True) | Q(is_superuser=True))
        .order_by("-is_superuser", "-is_staff", "username")
    )

    return render(request, "admin_custom/users_list.html", {
        "page_title": "Admin · Usuarios",
        "usuarios": qs,
    })
