#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/reportes/services.py << 'EOF'
"""Servicios de reportes — agregaciones operativas sin PII."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.derivaciones.models import Derivacion
from apps.hospitales.models import Hospital
from apps.inventario.models import (
    Almacen, Insumo, Lote, Stock,
)
from apps.organizaciones.models import Membresia, Organizacion
from apps.organizaciones.services import (
    puede_administrar_plataforma, tiene_acceso_a_organizacion,
)
from apps.reportes.models import RegistroExportacion
from apps.refugios.models import Refugio


UMBRAL_VENCIMIENTO_DIAS = 30


def _organizaciones_visibles(usuario):
    """Devuelve las organizaciones que el usuario puede consultar."""
    if puede_administrar_plataforma(usuario):
        return Organizacion.objects.filter(
            estado=Organizacion.Estado.ACTIVA
        )
    return Organizacion.objects.filter(
        membresias__usuario=usuario,
        membresias__estado=Membresia.Estado.ACTIVA,
        estado=Organizacion.Estado.ACTIVA,
    ).distinct()


def _validar_organizacion(usuario, organizacion):
    if organizacion is None:
        if puede_administrar_plataforma(usuario):
            return
        raise ValidationError(
            {"organizacion": "Debes especificar una organización."}
        )
    if not tiene_acceso_a_organizacion(usuario, organizacion):
        raise PermissionDenied(
            "No tienes acceso a esa organización."
        )


def _registrar_exportacion(
    *, usuario, organizacion, contenido, parametros,
    filas, resultado="EXITOSO", detalle="",
):
    return RegistroExportacion.objects.create(
        usuario=usuario,
        organizacion=organizacion,
        tipo=RegistroExportacion.Tipo.JSON,
        contenido=contenido,
        parametros=parametros,
        filas_incluidas=filas,
        resultado=resultado,
        detalle=detalle[:500] if detalle else "",
    )


def _auditar(usuario, contenido, organizacion, request):
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]
    registrar_evento(
        actor=usuario,
        accion=f"reporte.{contenido.lower()}",
        tipo_objeto="RegistroExportacion",
        objeto_id="",
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=f"Generación de reporte {contenido}.",
        direccion_ip=ip,
        agente_usuario=ua,
        organizacion_id=organizacion.id if organizacion else None,
        metadatos={"contenido": contenido},
    )


def generar_reporte_inventario_critico(*, usuario, organizacion=None, request=None):
    """
    Inventario crítico por organización.

    Devuelve:
    - insumos_bajo_minimo: insumos cuyo stock total en la org está
      por debajo de stock_minimo_global.
    - lotes_por_vencer: lotes con fecha_vencimiento <= hoy+30d y con
      stock > 0 en algún almacén de la org.
    - lotes_vencidos: ya vencidos pero aún con stock (alerta).

    Sin PII. Solo cantidades y referencias de catálogo.
    """
    _validar_organizacion(usuario, organizacion)
    ahora = timezone.now()
    limite = ahora.date() + timedelta(days=UMBRAL_VENCIMIENTO_DIAS)

    orgs = [organizacion] if organizacion else list(
        _organizaciones_visibles(usuario)
    )

    stocks_base = Stock.objects.filter(
        almacen__organizacion__in=orgs,
    ).select_related("almacen", "lote__insumo")

    # Stock total por insumo (agregado en la org)
    stock_por_insumo = (
        stocks_base
        .values("lote__insumo_id", "lote__insumo__codigo",
                "lote__insumo__nombre", "lote__insumo__stock_minimo_global")
        .annotate(
            total=Coalesce(
                Sum("cantidad"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
        )
    )

    insumos_bajo_minimo = []
    for row in stock_por_insumo:
        if row["total"] < row["lote__insumo__stock_minimo_global"]:
            insumos_bajo_minimo.append({
                "insumo_codigo": row["lote__insumo__codigo"],
                "insumo_nombre": row["lote__insumo__nombre"],
                "stock_actual": float(row["total"]),
                "stock_minimo": float(row["lote__insumo__stock_minimo_global"]),
                "deficit": float(
                    row["lote__insumo__stock_minimo_global"] - row["total"]
                ),
            })

    lotes_por_vencer_qs = stocks_base.filter(
        cantidad__gt=0,
        lote__fecha_vencimiento__isnull=False,
        lote__fecha_vencimiento__lte=limite,
        lote__fecha_vencimiento__gte=ahora.date(),
    ).order_by("lote__fecha_vencimiento")

    lotes_por_vencer = []
    for s in lotes_por_vencer_qs:
        lotes_por_vencer.append({
            "almacen_codigo": s.almacen.codigo,
            "insumo_codigo": s.lote.insumo.codigo,
            "lote_codigo": s.lote.codigo,
            "fecha_vencimiento": s.lote.fecha_vencimiento.isoformat(),
            "cantidad": float(s.cantidad),
            "dias_restantes": (s.lote.fecha_vencimiento - ahora.date()).days,
        })

    lotes_vencidos_qs = stocks_base.filter(
        cantidad__gt=0,
        lote__fecha_vencimiento__isnull=False,
        lote__fecha_vencimiento__lt=ahora.date(),
    ).order_by("lote__fecha_vencimiento")

    lotes_vencidos = []
    for s in lotes_vencidos_qs:
        lotes_vencidos.append({
            "almacen_codigo": s.almacen.codigo,
            "insumo_codigo": s.lote.insumo.codigo,
            "lote_codigo": s.lote.codigo,
            "fecha_vencimiento": s.lote.fecha_vencimiento.isoformat(),
            "cantidad": float(s.cantidad),
            "dias_vencido": (ahora.date() - s.lote.fecha_vencimiento).days,
        })

    filas = (
        len(insumos_bajo_minimo) + len(lotes_por_vencer) + len(lotes_vencidos)
    )
    _registrar_exportacion(
        usuario=usuario,
        organizacion=organizacion,
        contenido=RegistroExportacion.Contenido.INVENTARIO_CRITICO,
        parametros={"umbral_vencimiento_dias": UMBRAL_VENCIMIENTO_DIAS},
        filas=filas,
        resultado=(
            "EXITOSO" if filas > 0 else "SIN_DATOS"
        ),
    )
    _auditar(
        usuario, RegistroExportacion.Contenido.INVENTARIO_CRITICO,
        organizacion, request,
    )

    return {
        "generado_en": ahora.isoformat(),
        "umbral_vencimiento_dias": UMBRAL_VENCIMIENTO_DIAS,
        "insumos_bajo_minimo": insumos_bajo_minimo,
        "lotes_por_vencer": lotes_por_vencer,
        "lotes_vencidos": lotes_vencidos,
        "total_alertas": filas,
    }


def generar_reporte_capacidad_operativa(*, usuario, organizacion=None, request=None):
    """
    Capacidad operativa: refugios + derivaciones pendientes.

    - refugios: capacidad_total, ocupacion_actual, disponible,
      estado_operativo, porcentaje.
    - derivaciones_pendientes: conteo por estado.
    - hospitales_por_estado: conteo por estado operativo.

    Sin PII. Solo agregados.
    """
    _validar_organizacion(usuario, organizacion)
    ahora = timezone.now()

    orgs = [organizacion] if organizacion else list(
        _organizaciones_visibles(usuario)
    )

    refugios_qs = Refugio.objects.filter(
        organizacion__in=orgs,
    ).values(
        "codigo", "nombre", "estado_operativo",
        "capacidad_total", "ocupacion_actual",
    ).order_by("nombre")

    refugios = []
    for r in refugios_qs:
        disponible = max(0, r["capacidad_total"] - r["ocupacion_actual"])
        porcentaje = (
            round((r["ocupacion_actual"] / r["capacidad_total"]) * 100, 1)
            if r["capacidad_total"] > 0 else 0.0
        )
        refugios.append({
            "codigo": r["codigo"],
            "nombre": r["nombre"],
            "estado_operativo": r["estado_operativo"],
            "capacidad_total": r["capacidad_total"],
            "ocupacion_actual": r["ocupacion_actual"],
            "capacidad_disponible": disponible,
            "porcentaje_ocupacion": porcentaje,
        })

    derivaciones_qs = Derivacion.objects.filter(
        Q(hospital_origen__organizacion__in=orgs)
        | Q(hospital_destino__organizacion__in=orgs)
    ).values("estado").annotate(total=Count("id"))

    derivaciones_por_estado = {
        row["estado"]: row["total"] for row in derivaciones_qs
    }

    hospitales_qs = Hospital.objects.filter(
        organizacion__in=orgs,
    ).values("estado_operativo").annotate(total=Count("id"))

    hospitales_por_estado = {
        row["estado_operativo"]: row["total"] for row in hospitales_qs
    }

    filas = len(refugios) + sum(derivaciones_por_estado.values())
    _registrar_exportacion(
        usuario=usuario,
        organizacion=organizacion,
        contenido=RegistroExportacion.Contenido.CAPACIDAD_OPERATIVA,
        parametros={"incluye": ["refugios", "derivaciones", "hospitales"]},
        filas=filas,
        resultado="EXITOSO" if filas > 0 else "SIN_DATOS",
    )
    _auditar(
        usuario, RegistroExportacion.Contenido.CAPACIDAD_OPERATIVA,
        organizacion, request,
    )

    return {
        "generado_en": ahora.isoformat(),
        "refugios": refugios,
        "derivaciones_por_estado": derivaciones_por_estado,
        "hospitales_por_estado": hospitales_por_estado,
        "total_elementos": filas,
    }
EOF

python3 manage.py shell -c "from apps.reportes import services; print('OK: services importan')"
