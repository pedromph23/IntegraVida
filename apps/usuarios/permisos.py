"""Sistema de permisos de IntegraVida.

Fuente de verdad para autorización granular a nivel de módulo + acción.

- Coherencia relacional: los permisos van atados a la Membresia del
  usuario (rol + organización). Un usuario con Membresia ACTIVA en
  múltiples orgs tiene la unión de permisos de sus roles en cada una.
- Compatibilidad con F3: los 12 módulos de F3 usan auth.Group para
  permisos. Este módulo acepta AMBOS sistemas (Membresia.rol y Group).
  Unificación → F5.g.

Uso:
    from apps.usuarios.permisos import (
        ACCION_VER, ACCION_CREAR, ACCION_EDITAR, ACCION_ELIMINAR,
        ACCION_CAMBIAR_ESTADO, tiene_permiso,
    )

    if tiene_permiso(user, "refugios", ACCION_CREAR, org):
        ...
"""
from __future__ import annotations


# ── Acciones atómicas ─────────────────────────────────────────────────
ACCION_VER = "ver"
ACCION_CREAR = "crear"
ACCION_EDITAR = "editar"
ACCION_ELIMINAR = "eliminar"           # Semánticamente = "inactivar" (soft delete)
ACCION_CAMBIAR_ESTADO = "cambiar_estado"


# ── Mapa de permisos por rol de Membresia (sistema nuevo) ─────────────
# Estructura: {rol: {modulo: set(acciones)}}
ROL_PERMISOS: dict[str, dict[str, set[str]]] = {
    "ADMIN_ORGANIZACION": {
        "refugios": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_ELIMINAR, ACCION_CAMBIAR_ESTADO,
        },
        "hospitales": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_ELIMINAR, ACCION_CAMBIAR_ESTADO,
        },
        "emergencias": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR, ACCION_CAMBIAR_ESTADO,
        },
        "pacientes": {
            ACCION_VER, ACCION_EDITAR,
        },
    },
    "COORDINADOR": {
        "refugios": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_CAMBIAR_ESTADO,
        },
        "hospitales": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_CAMBIAR_ESTADO,
        },
        "emergencias": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR, ACCION_CAMBIAR_ESTADO,
        },
        "pacientes": {
            ACCION_VER, ACCION_EDITAR,
        },
    },
    "OPERADOR": {
        "refugios": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
        "hospitales": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
        "emergencias": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
        "pacientes": {ACCION_VER},
    },
    "SANITARIO": {
        "refugios": {ACCION_VER},
        "hospitales": {ACCION_VER},
        "emergencias": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
        "pacientes": {ACCION_VER},
    },
    "LOGISTICA": {
        "refugios": {ACCION_VER},
        "hospitales": {ACCION_VER},
        "emergencias": {ACCION_VER},
    },
    "CONSULTA": {
        "refugios": {ACCION_VER},
        "hospitales": {ACCION_VER},
        "emergencias": {ACCION_VER},
    },
}


# ── Mapa de permisos por auth.Group (legacy F3) ───────────────────────
# Solo para compatibilidad con los módulos F3 que usan groups.
GROUP_PERMISOS: dict[str, dict[str, set[str]]] = {
    "ADMIN": {
        "refugios": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_ELIMINAR, ACCION_CAMBIAR_ESTADO,
        },
        "hospitales": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_ELIMINAR, ACCION_CAMBIAR_ESTADO,
        },
        "emergencias": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR, ACCION_CAMBIAR_ESTADO,
        },
        "pacientes": {
            ACCION_VER, ACCION_EDITAR,
        },
    },
    "COORDINADOR": {
        "refugios": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_CAMBIAR_ESTADO,
        },
        "hospitales": {
            ACCION_VER, ACCION_CREAR, ACCION_EDITAR,
            ACCION_CAMBIAR_ESTADO,
        },
    },
    "OPERADOR_REFUGIO": {
        "refugios": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
    },
    "OPERADOR_HOSPITAL": {
        "hospitales": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
        "pacientes": {ACCION_VER},
    },
    "OPERADOR_EMERGENCIA": {
        "emergencias": {ACCION_VER, ACCION_CAMBIAR_ESTADO},
    },
}


def _membresias_activas(user, organizacion=None):
    """Queryset de Membresia ACTIVA del usuario (opcionalmente filtrado)."""
    if not user.is_authenticated:
        return None
    qs = user.membresias.filter(estado="ACTIVA")
    if organizacion is not None:
        qs = qs.filter(organizacion=organizacion)
    return qs


def tiene_permiso(user, modulo, accion, organizacion=None):
    """Verifica si `user` puede ejecutar `accion` en `modulo`.

    - Si organizacion es None → chequea en CUALQUIER org del usuario.
    - Si organizacion se pasa → chequea SOLO en esa org.
    - Superuser / staff → True siempre.
    - Acepta Membresia.rol (nuevo) y auth.Group (legacy F3).
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    # 1. Membresia.rol (nuevo)
    qs = _membresias_activas(user, organizacion)
    if qs is not None:
        for m in qs:
            if accion in ROL_PERMISOS.get(m.rol, {}).get(modulo, set()):
                return True

    # 2. auth.Group (legacy F3)
    groups = set(user.groups.values_list("name", flat=True))
    for g in groups:
        if accion in GROUP_PERMISOS.get(g, {}).get(modulo, set()):
            return True

    return False


def orgs_donde_puede(user, modulo, accion):
    """Devuelve queryset de Organizacion ACTIVA donde el user tiene `accion`."""
    from apps.organizaciones.models import Organizacion

    if not user.is_authenticated:
        return Organizacion.objects.none()
    if user.is_superuser or user.is_staff:
        return Organizacion.objects.filter(estado="ACTIVA")

    org_ids = set()
    for m in _membresias_activas(user) or []:
        if accion in ROL_PERMISOS.get(m.rol, {}).get(modulo, set()):
            org_ids.add(m.organizacion_id)

    return Organizacion.objects.filter(id__in=org_ids, estado="ACTIVA")
