"""Filtros y tags de presentación (sin lógica de negocio)."""

from django import template

register = template.Library()


@register.filter
def badge_class(estado: str) -> str:
    """Mapea un estado a clase CSS de badge."""
    mapping = {
        "CONFIRMADA": "badge-danger",
        "EN_ATENCION": "badge-warning",
        "RESUELTA": "badge-success",
        "ACTIVO": "badge-success",
        "LLENO": "badge-warning",
        "DISPONIBLE": "badge-success",
        "SATURADO": "badge-warning",
    }
    return mapping.get(estado, "badge-info")
