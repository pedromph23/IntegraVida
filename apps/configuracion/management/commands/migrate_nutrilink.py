"""Migra Insumos desde un fixture de NUTRILINK (§16.1)."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.configuracion.models import ReferenciaMigracion
from apps.inventario.models import Insumo

from ._migracion_utils import (
    cargar_fixture, crear_referencia, hash_registro,
    resolver_admin, resolver_organizacion, ya_migrado,
)

SISTEMA = ReferenciaMigracion.SistemaOrigen.NUTRILINK
ENTIDAD_ORIGEN = "supplies"
ENTIDAD_DESTINO = "inventario.Insumo"

CATEGORIA_MAP = {
    "alimento": Insumo.Categoria.ALIMENTO,
    "medico": Insumo.Categoria.MEDICINA,
}

UNIDAD_MAP = {
    "kg": Insumo.UnidadMedida.KILOGRAMO,
    "kilo": Insumo.UnidadMedida.KILOGRAMO,
    "gramos": Insumo.UnidadMedida.GRAMO,
    "litros": Insumo.UnidadMedida.LITRO,
    "litro": Insumo.UnidadMedida.LITRO,
    "mililitros": Insumo.UnidadMedida.MILILITRO,
    "raciones": Insumo.UnidadMedida.RACION,
    "racion": Insumo.UnidadMedida.RACION,
    "cajas": Insumo.UnidadMedida.CAJA,
    "caja": Insumo.UnidadMedida.CAJA,
    "unidades": Insumo.UnidadMedida.UNIDAD,
    "unidad": Insumo.UnidadMedida.UNIDAD,
    "frascos": Insumo.UnidadMedida.FRASCO,
    "frasco": Insumo.UnidadMedida.FRASCO,
    "paquetes": Insumo.UnidadMedida.PAQUETE,
    "paquete": Insumo.UnidadMedida.PAQUETE,
}


class Command(BaseCommand):
    help = "Migra Insumos desde un fixture de NUTRILINK."

    def add_arguments(self, parser):
        parser.add_argument("--fixture", required=True)
        parser.add_argument(
            "--organizacion", required=True,
            help="Se acepta por simetría aunque Insumo es global.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        resolver_organizacion(options["organizacion"])
        admin = resolver_admin()
        records = cargar_fixture(options["fixture"])

        creados = omitidos = advertidos = errores = 0
        for record in records:
            origin_id = record.get("id")
            if origin_id is None:
                self.stderr.write(f"Registro sin id: {record}")
                errores += 1
                continue

            if ya_migrado(SISTEMA, ENTIDAD_ORIGEN, origin_id):
                omitidos += 1
                continue

            detalle_advertencias = []
            categoria = CATEGORIA_MAP.get(
                str(record.get("categoria", "")).lower()
            )
            if not categoria:
                detalle_advertencias.append(
                    f"categoria origen '{record.get('categoria')}' no mapeada"
                )
                categoria = Insumo.Categoria.OTRO

            unidad = UNIDAD_MAP.get(
                str(record.get("unidad_medida", "")).lower()
            )
            if not unidad:
                detalle_advertencias.append(
                    f"unidad origen '{record.get('unidad_medida')}' no mapeada"
                )
                unidad = Insumo.UnidadMedida.OTRO

            es_perecedero = bool(record.get("es_perecedero", False))
            vida_util = record.get("dias_vida_util_promedio")

            try:
                insumo = Insumo.objects.create(
                    codigo=(
                        f"nutrilink-"
                        f"{record.get('codigo', str(origin_id)).lower()}"
                    ),
                    nombre=record.get("nombre", f"Insumo {origin_id}"),
                    categoria=categoria,
                    subcategoria=record.get("subcategoria", ""),
                    unidad_medida=unidad,
                    requiere_lote=es_perecedero,
                    requiere_vencimiento=es_perecedero,
                    vida_util_dias=int(vida_util) if vida_util else None,
                )
            except Exception as exc:
                self.stderr.write(f"Error {origin_id}: {exc}")
                errores += 1
                continue

            resultado = (
                ReferenciaMigracion.ResultadoValidacion.VALIDADO
                if not detalle_advertencias
                else ReferenciaMigracion.ResultadoValidacion.CON_ADVERTENCIA
            )
            crear_referencia(
                sistema=SISTEMA, entidad_origen=ENTIDAD_ORIGEN,
                identificador_origen=origin_id,
                entidad_destino=ENTIDAD_DESTINO,
                identificador_destino=insumo.pk,
                hash_origen=hash_registro(record),
                admin=admin,
                resultado=resultado,
                detalle="; ".join(detalle_advertencias),
            )
            if (
                resultado
                == ReferenciaMigracion.ResultadoValidacion.CON_ADVERTENCIA
            ):
                advertidos += 1
            creados += 1

        self.stdout.write(self.style.SUCCESS(
            f"NUTRILINK -> Insumo: creados={creados} "
            f"(advertencias={advertidos}) "
            f"omitidos={omitidos} errores={errores}"
        ))
