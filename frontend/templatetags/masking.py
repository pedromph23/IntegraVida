"""Filtros de enmascaramiento PII para el panel (F3.e.2).

Reglas (§12):
- cédula: conserva últimos 4 dígitos; resto asteriscos
- nombre único: inicial + asteriscos
- nombre completo (nombres + apellidos): inicial de cada uno + asteriscos
- edad: calculada de fecha_nacimiento (0 si nula)
"""
from datetime import date

from django import template

register = template.Library()


def _solo_digitos(s):
    return "".join(ch for ch in (s or "") if ch.isdigit())


@register.filter
def mask_cedula(value):
    """'V-12345678' → '***-**-5678' (últimos 4 dígitos visibles)."""
    if not value:
        return "—"
    digits = _solo_digitos(str(value))
    if len(digits) < 4:
        return "—"
    return f"***-**-{digits[-4:]}"


@register.filter
def mask_nombre(value):
    """'Juan' → 'J***'."""
    if not value:
        return "—"
    s = str(value).strip()
    if not s:
        return "—"
    return f"{s[0].upper()}***"


@register.filter
def mask_nombre_completo(value):
    """'Juan Pérez' → 'J*** P***' (inicial de cada palabra)."""
    if not value:
        return "—"
    partes = str(value).split()
    return " ".join(f"{p[0].upper()}***" for p in partes if p) or "—"


@register.filter
def edad(fecha_nacimiento):
    """Devuelve años cumplidos o '—' si nula."""
    if not fecha_nacimiento:
        return "—"
    try:
        hoy = date.today()
        return hoy.year - fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
    except Exception:
        return "—"
