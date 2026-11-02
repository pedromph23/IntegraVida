"""Decoradores de autorización del panel institucional.

Envuelven `login_required` + verificación de permiso del sistema de
permisos (`apps.usuarios.permisos`).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy

from apps.usuarios.permisos import tiene_permiso


def permiso_requerido(modulo, accion, redirect_to=None):
    """Exige un permiso específico para ejecutar la vista.

    Uso:
        @permiso_requerido("refugios", "crear")
        def refugio_create(request):
            ...

    - Si no está autenticado → login_required redirige a LOGIN_URL.
    - Si autenticado pero sin permiso:
      * Si `redirect_to` es None → 403.
      * Si `redirect_to` es una URL name → redirect + mensaje flash.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not tiene_permiso(request.user, modulo, accion):
                if redirect_to:
                    messages.error(
                        request,
                        "No tienes permiso para realizar esta acción.",
                    )
                    return redirect(reverse_lazy(redirect_to))
                raise PermissionDenied(
                    "No tienes permiso para realizar esta acción.",
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
