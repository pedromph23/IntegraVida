"""Servicios de MFA del admin (F4.b).

- enroll_admin_mfa: genera secret TOTP, lo cifra, devuelve URI otpauth
  + secret en Base32 (para que el usuario lo añada a su app).
- verify_admin_mfa: valida código TOTP contra el secret del usuario.
- reset_admin_mfa: borra el secret (requiere acceso al management command).
- Rate limiting: helpers de cache (LocMem en dev, Redis en prod).

Referencia: RFC 6238 (TOTP). pyotp con digest SHA1, 6 dígitos, 30 s.
"""
from __future__ import annotations

import pyotp
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone


User = get_user_model()

# ── Rate limiting ────────────────────────────────────────────────────
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 15 * 60  # 15 min


def _rl_key(ip: str, username: str) -> str:
    return f"mfa_rl:{ip}:{username}"


def check_rate_limit(ip: str, username: str) -> tuple[bool, int, int]:
    """Devuelve (permitido, intentos_actuales, max)."""
    key = _rl_key(ip, username)
    attempts = cache.get(key, [])
    now = timezone.now().timestamp()
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]
    return len(attempts) < RATE_LIMIT_MAX_ATTEMPTS, len(attempts), RATE_LIMIT_MAX_ATTEMPTS


def register_failed_attempt(ip: str, username: str) -> None:
    key = _rl_key(ip, username)
    attempts = cache.get(key, [])
    now = timezone.now().timestamp()
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]
    attempts.append(now)
    cache.set(key, attempts, RATE_LIMIT_WINDOW_SECONDS + 60)


def clear_rate_limit(ip: str, username: str) -> None:
    cache.delete(_rl_key(ip, username))


# ── MFA ──────────────────────────────────────────────────────────────
def enroll_admin_mfa(user, *, force: bool = False) -> tuple[str, str]:
    """Genera un secret TOTP nuevo para el usuario y lo guarda cifrado.

    Devuelve (secret_base32, provisioning_uri).
    Si force=False y el usuario ya tiene secret, regenera igual (el
    caller decide; usado por crear_admin_inicial).
    """
    secret = pyotp.random_base32()
    user.admin_mfa_secret = secret
    user.admin_mfa_enrolled_at = timezone.now()
    user.save(update_fields=["admin_mfa_secret", "admin_mfa_enrolled_at"])

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=user.get_username(),
        issuer_name="IntegraVida Admin",
    )
    return secret, uri


def verify_admin_mfa(user, code: str, *, valid_window: int = 1) -> bool:
    """Verifica un código TOTP. valid_window=1 permite ±30 s de desfase."""
    secret = user.admin_mfa_secret
    if not secret:
        return False
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)


def reset_admin_mfa(user) -> None:
    """Borra el secret. El usuario deberá re-enrolarse."""
    user.admin_mfa_secret = None
    user.admin_mfa_enrolled_at = None
    user.save(update_fields=["admin_mfa_secret", "admin_mfa_enrolled_at"])
