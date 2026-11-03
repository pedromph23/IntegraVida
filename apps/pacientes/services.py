"""Servicios de pacientes — normalización, hash y creación controlada."""

import hashlib
import hmac
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.pacientes.models import Paciente


def _hmac_key():
    """
    Clave HMAC para `cedula_hash`.

    Prioridad:
    1. PACIENTE_CEDULA_HMAC_KEY (independiente, para producción)
    2. Derivada de SECRET_KEY (desarrollo, migrable)

    En Fase 11 se migrará a variable independiente y se documentará
    la rotación.
    """
    raw = getattr(settings, "PACIENTE_CEDULA_HMAC_KEY", None) or settings.SECRET_KEY
    return hashlib.sha256(f"integravida:cedula:{raw}".encode("utf-8")).digest()


def normalizar_cedula(cedula):
    """Normaliza a mayúsculas alfanuméricas: 'V-12.345.678' -> 'V12345678'."""
    if not cedula:
        return ""
    return "".join(c for c in str(cedula).upper() if c.isalnum())


def calcular_cedula_hash(cedula):
    """Calcula HMAC-SHA256 de la cédula normalizada."""
    normalizada = normalizar_cedula(cedula)
    if not normalizada:
        return None
    return hmac.new(
        _hmac_key(), normalizada.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@transaction.atomic
def crear_paciente(
    *,
    cedula="",
    nombres,
    apellidos,
    fecha_nacimiento=None,
    sexo_biologico=Paciente.SexoBiologico.NO_ESPECIFICADO,
    telefono="",
    email="",
    cuenta_vinculada=None,
    notas_internas="",
    usuario,
    request=None,
):
    """
    Crea un paciente calculando automáticamente su `cedula_hash`.

    - Si la cédula está vacía, `cedula_hash` queda NULL.
    - Si la cédula ya existe (mismo hash), lanza ValidationError.
    - Audita la creación con hash encadenado.
    """
    nombres = (nombres or "").strip()
    apellidos = (apellidos or "").strip()

    if not nombres:
        raise ValidationError({"nombres": "Los nombres son obligatorios."})
    if not apellidos:
        raise ValidationError({"apellidos": "Los apellidos son obligatorios."})

    cedula_hash = calcular_cedula_hash(cedula)

    if cedula_hash and Paciente.objects.filter(cedula_hash=cedula_hash).exists():
        raise ValidationError(
            {"cedula": "Ya existe un paciente registrado con esta cédula."}
        )

    paciente = Paciente.objects.create(
        cedula=(cedula or "").strip(),
        cedula_hash=cedula_hash,
        nombres=nombres,
        apellidos=apellidos,
        fecha_nacimiento=fecha_nacimiento,
        sexo_biologico=sexo_biologico,
        telefono=(telefono or "").strip(),
        email=(email or "").strip(),
        cuenta_vinculada=cuenta_vinculada,
        notas_internas=notas_internas,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="paciente.creado",
        tipo_objeto="Paciente",
        objeto_id=paciente.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion="Creación de expediente de paciente.",
        direccion_ip=ip,
        agente_usuario=user_agent,
        metadatos={
            "tiene_cedula": bool(cedula_hash),
            "sexo_biologico": paciente.sexo_biologico,
        },
    )

    return paciente


def buscar_paciente_por_cedula(cedula):
    """Busca un paciente por cédula normalizada. Devuelve None si no existe."""
    hash_busqueda = calcular_cedula_hash(cedula)
    if not hash_busqueda:
        return None
    return Paciente.objects.filter(cedula_hash=hash_busqueda).first()

def filtrar_episodios_por_ambito(queryset, usuario):
    """
    Limita episodios a las membresías activas del usuario.

    - Superusuario activo: acceso global de plataforma.
    - Membresía sin municipio: todos los centros de su organización.
    - Membresía con municipio: solo centros de esa organización
      ubicados en ese municipio.
    - Se respeta cada pareja organización/municipio sin cruzar ámbitos.
    - Las organizaciones suspendidas o inactivas no conceden acceso.
    """
    from django.db.models import Q

    from apps.organizaciones.models import Membresia, Organizacion
    from apps.organizaciones.services import puede_administrar_plataforma

    if puede_administrar_plataforma(usuario):
        return queryset

    if not getattr(usuario, "is_authenticated", False):
        return queryset.none()

    membresias = list(
        Membresia.objects.filter(
            usuario=usuario,
            estado=Membresia.Estado.ACTIVA,
            organizacion__estado=Organizacion.Estado.ACTIVA,
        ).values_list(
            "organizacion_id",
            "ambito_municipio_id",
        )
    )

    if not membresias:
        return queryset.none()

    filtros = Q(pk__in=[])

    for organizacion_id, municipio_id in membresias:
        if municipio_id is None:
            filtros |= (
                Q(hospital__organizacion_id=organizacion_id)
                | Q(refugio__organizacion_id=organizacion_id)
            )
        else:
            filtros |= (
                Q(
                    hospital__organizacion_id=organizacion_id,
                    hospital__municipio_id=municipio_id,
                )
                | Q(
                    refugio__organizacion_id=organizacion_id,
                    refugio__municipio_id=municipio_id,
                )
            )

    return queryset.filter(filtros).distinct()
