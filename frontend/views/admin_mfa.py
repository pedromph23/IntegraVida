"""Vistas de MFA del admin (F4.b).

Flujo:
  /<slug>/mfa/          → si verificado: redirect a /<slug>/
                          si sin secret: redirect a /<slug>/mfa/setup/
                          si con secret: form de código
  /<slug>/mfa/setup/    → genera secret, muestra URI + form
  /<slug>/mfa/verify/   → POST: valida código, marca sesión, redirect /<slug>/
  /<slug>/mfa/cancel/   → limpia sesión y vuelve al login

Namespaced bajo admin_custom:* (no dashboard:*).
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.usuarios.services import (
    check_rate_limit,
    clear_rate_limit,
    enroll_admin_mfa,
    register_failed_attempt,
    verify_admin_mfa,
)


User = get_user_model()


def _admin_root_url() -> str:
    """URL base del Django admin (para redirect post-MFA)."""
    return f"/{settings.INTEGRAVIDA_ADMIN_SLUG}/"


def _verify_url() -> str:
    return reverse("admin_custom:admin_mfa_verify")


def _setup_url() -> str:
    return reverse("admin_custom:admin_mfa_setup")


def _submit_url() -> str:
    return reverse("admin_custom:admin_mfa_submit")


def _cancel_url() -> str:
    return reverse("admin_custom:admin_mfa_cancel")


def _require_admin_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


# Los anónimos que toquen /<slug>/mfa/* deben ir al login del ADMIN,
# no al del panel institucional (settings.LOGIN_URL = /panel/login/).
# reverse_lazy("admin:login") → /<slug>/login/ (prefijo del admin.site.urls).
_admin_login_required = login_required(login_url=reverse_lazy("admin:login"))


def _audit_mfa_event(request, *, accion, justificacion, metadatos=None):
    """Auditoría best-effort: nunca debe romper el flujo de autenticación.

    registrar_evento() puede fallar por advisory lock, cadena rota, o
    problemas transitorios de BD. Si eso ocurre, lo loggeamos pero
    dejamos que el usuario continúe su intento de auth.
    """
    import logging
    _logger = logging.getLogger(__name__)
    ip = (request.META.get("REMOTE_ADDR") or "")[:64] or None
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
    try:
        registrar_evento(
            actor=request.user,
            accion=accion,
            tipo_objeto="AdminMFA",
            objeto_id=str(request.user.pk),
            resultado=EventoAuditoria.Resultado.DENEGADO,
            justificacion=justificacion,
            direccion_ip=ip,
            agente_usuario=ua,
            metadatos=metadatos or {},
        )
    except Exception:
        _logger.exception(
            "No se pudo registrar evento de auditoría MFA: %s", accion,
        )


@_admin_login_required
@require_GET
def mfa_verify_view(request):
    if not _require_admin_staff(request.user):
        return HttpResponseForbidden("Solo personal del admin.")

    # Ya verificado en esta sesión → ir al admin
    if request.session.get("admin_mfa_verified_at"):
        return redirect(_admin_root_url())

    # Sin secret → setup
    if not request.user.admin_mfa_secret:
        return redirect(_setup_url())

    return render(request, "admin_custom/mfa_verify.html", {
        "page_title": "Verificación MFA",
    })


@_admin_login_required
@require_GET
def mfa_setup_view(request):
    if not _require_admin_staff(request.user):
        return HttpResponseForbidden("Solo personal del admin.")

    if request.user.admin_mfa_secret:
        # Ya enrolado → ir a verificar
        return redirect(_verify_url())

    secret, uri = enroll_admin_mfa(request.user)

    return render(request, "admin_custom/mfa_setup.html", {
        "page_title": "Configurar MFA",
        "secret_base32": secret,
        "provisioning_uri": uri,
    })


@_admin_login_required
@require_POST
def mfa_verify_submit(request):
    if not _require_admin_staff(request.user):
        return HttpResponseForbidden("Solo personal del admin.")

    code = request.POST.get("code", "").strip()
    ip = request.META.get("REMOTE_ADDR", "") or "0.0.0.0"

    permitido, intentos, maximo = check_rate_limit(ip, request.user.username)
    if not permitido:
        _audit_mfa_event(
            request,
            accion="admin.mfa.rate_limited",
            justificacion=f"Rate limit excedido ({intentos}/{maximo}).",
            metadatos={"intentos": intentos, "maximo": maximo},
        )
        messages.error(
            request,
            f"Demasiados intentos ({intentos}/{maximo}). "
            "Espera 15 minutos antes de reintentar.",
        )
        return redirect(_verify_url())

    if not verify_admin_mfa(request.user, code):
        register_failed_attempt(ip, request.user.username)
        _audit_mfa_event(
            request,
            accion="admin.mfa.invalid_code",
            justificacion="Código TOTP inválido.",
            metadatos={"intentos_previos": intentos},
        )
        messages.error(request, "Código inválido. Intenta de nuevo.")
        return redirect(_verify_url())

    # Éxito
    clear_rate_limit(ip, request.user.username)
    request.session["admin_mfa_verified_at"] = timezone.now().timestamp()
    request.session["admin_mfa_user_id"] = str(request.user.pk)

    return redirect(_admin_root_url())


@_admin_login_required
@require_GET
def mfa_cancel_view(request):
    request.session.pop("admin_mfa_verified_at", None)
    request.session.pop("admin_mfa_user_id", None)
    return redirect(_verify_url())
