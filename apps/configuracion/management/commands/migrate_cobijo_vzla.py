"""Migra Refugios desde un fixture de Cobijo VZLA (§16.1)."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.configuracion.models import ReferenciaMigracion
from apps.refugios.models import Refugio

from ._migracion_utils import (
    cargar_fixture, crear_referencia, hash_registro,
    resolver_admin, resolver_organizacion, ya_migrado,
)

SISTEMA = ReferenciaMigracion.SistemaOrigen.COBIJO_VZLA
ENTIDAD_ORIGEN = "refugios"
ENTIDAD_DESTINO = "refugios.Refugio"


class Command(BaseCommand):
    help = "Migra Refugios desde un fixture de Cobijo VZLA."

    def add_arguments(self, parser):
        parser.add_argument("--fixture", required=True)
        parser.add_argument("--organizacion", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        org = resolver_organizacion(options["organizacion"])
        admin = resolver_admin()
        records = cargar_fixture(options["fixture"])

        creados = omitidos = errores = 0
        for record in records:
            origin_id = record.get("id")
            if not origin_id:
                self.stderr.write(f"Registro sin id: {record}")
                errores += 1
                continue

            if ya_migrado(SISTEMA, ENTIDAD_ORIGEN, origin_id):
                omitidos += 1
                continue

            try:
                capacidad = int(record.get("capacidad_total", 0))
                disponible = int(record.get("capacidad_disponible", 0))
                ocupacion = max(0, capacidad - disponible)

                estado = (
                    Refugio.EstadoOperativo.ACTIVO
                    if record.get("operativo")
                    else Refugio.EstadoOperativo.INACTIVO
                )
                refugio = Refugio.objects.create(
                    codigo=f"cobijo-{origin_id.lower()}",
                    nombre=record.get("nombre", f"Refugio {origin_id}"),
                    tipo=Refugio.Tipo.REFUGIO,
                    organizacion=org,
                    direccion=record.get("direccion", ""),
                    capacidad_total=capacidad,
                    ocupacion_actual=ocupacion,
                    servicios=record.get("servicios", []),
                    estado_operativo=estado,
                    telefono_publico=record.get("telefono", ""),
                )
            except Exception as exc:
                self.stderr.write(f"Error {origin_id}: {exc}")
                errores += 1
                continue

            crear_referencia(
                sistema=SISTEMA, entidad_origen=ENTIDAD_ORIGEN,
                identificador_origen=origin_id,
                entidad_destino=ENTIDAD_DESTINO,
                identificador_destino=refugio.pk,
                hash_origen=hash_registro(record),
                admin=admin,
            )
            creados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Cobijo VZLA -> Refugio: "
            f"creados={creados} omitidos={omitidos} errores={errores}"
        ))
