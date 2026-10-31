"""Utilidades compartidas por los comandos de migración (§16.1)."""
import hashlib
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

from apps.configuracion.models import ReferenciaMigracion
from apps.organizaciones.models import Organizacion


def cargar_fixture(fixture_path):
    p = Path(fixture_path)
    if not p.exists():
        raise CommandError(f"Fixture no existe: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolver_organizacion(org_id):
    try:
        return Organizacion.objects.get(pk=org_id)
    except Organizacion.DoesNotExist:
        raise CommandError(f"Organización no existe: {org_id}")


def resolver_admin():
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True, is_active=True).first()
    if not admin:
        raise CommandError(
            "Necesitas un superusuario activo para ejecutar la migración."
        )
    return admin


def hash_registro(record):
    serialized = json.dumps(
        record, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def ya_migrado(sistema, entidad, identificador):
    return ReferenciaMigracion.objects.filter(
        sistema_origen=sistema,
        entidad_origen=entidad,
        identificador_origen=str(identificador),
    ).exists()


def crear_referencia(
    *, sistema, entidad_origen, identificador_origen,
    entidad_destino, identificador_destino, hash_origen, admin,
    resultado=ReferenciaMigracion.ResultadoValidacion.VALIDADO,
    detalle="",
):
    return ReferenciaMigracion.objects.create(
        sistema_origen=sistema,
        entidad_origen=entidad_origen,
        identificador_origen=str(identificador_origen),
        entidad_destino=entidad_destino,
        identificador_destino=identificador_destino,
        hash_origen=hash_origen,
        resultado_validacion=resultado,
        detalle_validacion=detalle,
        migrado_por=admin,
    )
