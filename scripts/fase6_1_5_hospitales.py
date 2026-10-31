#!/usr/bin/env python3
"""Fase 6.1.5 — Portal público de hospitales + precarga de servicios."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  escrito: {rel}")

def patch(rel, old, new, label=""):
    p = BASE / rel
    text = p.read_text(encoding="utf-8")
    if old not in text and new in text:
        print(f"  ya aplicado: {label or rel}")
        return
    if text.count(old) != 1:
        sys.exit(f"ERROR: {rel} — patrón no único")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK: {label or rel}")

# ══════════════════════════════════════════════════════════════════
# 1) apps/hospitales/views.py
# ══════════════════════════════════════════════════════════════════
print("== 1/4 views.py ==")
views = '''"""Endpoints públicos de hospitales — solo lectura, sin autenticación."""

from datetime import timedelta

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.hospitales.models import Hospital, RecursoHospitalario


ESTADOS_PUBLICOS = [
    Hospital.EstadoOperativo.DISPONIBLE,
    Hospital.EstadoOperativo.SATURADO,
]

UMBRAL_DESACTUALIZADO = timedelta(hours=2)


def _estado_recurso(recurso, ahora):
    if recurso is None:
        return {"estado": "sin_datos", "actualizado_en": None}
    if recurso.capacidad_total == 0:
        return {
            "estado": "sin_datos",
            "actualizado_en": (
                recurso.actualizado_en.isoformat()
                if recurso.actualizado_en
                else None
            ),
        }
    if recurso.actualizado_en is None:
        return {"estado": "sin_datos", "actualizado_en": None}
    if (ahora - recurso.actualizado_en) > UMBRAL_DESACTUALIZADO:
        return {
            "estado": "sin_datos",
            "actualizado_en": recurso.actualizado_en.isoformat(),
        }
    estado = "disponible" if recurso.disponible > 0 else "no_disponible"
    return {
        "estado": estado,
        "actualizado_en": recurso.actualizado_en.isoformat(),
    }


def _serializar_hospital(hospital, ahora):
    punto = None
    if hospital.ubicacion:
        punto = {
            "latitud": hospital.ubicacion.y,
            "longitud": hospital.ubicacion.x,
        }

    existentes = {r.tipo: r for r in hospital.recursos.all()}
    recursos = {}
    for tipo in RecursoHospitalario.Tipo.values:
        recursos[tipo.lower()] = _estado_recurso(existentes.get(tipo), ahora)

    servicios = [
        {
            "codigo": hs.servicio.codigo,
            "nombre": hs.servicio.nombre,
            "tipo": hs.servicio.tipo,
            "disponible": hs.disponible,
        }
        for hs in hospital.servicios_through.all()
        if hs.servicio.activo
    ]

    return {
        "id": str(hospital.id),
        "codigo": hospital.codigo,
        "nombre": hospital.nombre,
        "tipo": hospital.tipo,
        "tipo_texto": hospital.get_tipo_display(),
        "nivel": hospital.nivel,
        "nivel_texto": hospital.get_nivel_display(),
        "direccion": hospital.direccion,
        "referencia_lugar": hospital.referencia_lugar,
        "punto": punto,
        "municipio": hospital.municipio.nombre if hospital.municipio_id else None,
        "parroquia": hospital.parroquia.nombre if hospital.parroquia_id else None,
        "telefono_publico": hospital.telefono_publico,
        "correo_publico": hospital.correo_publico,
        "estado_operativo": hospital.estado_operativo,
        "estado_operativo_texto": hospital.get_estado_operativo_display(),
        "servicios": servicios,
        "recursos": recursos,
    }


def _queryset_publico():
    return (
        Hospital.objects
        .filter(estado_operativo__in=ESTADOS_PUBLICOS)
        .select_related("municipio", "parroquia")
        .prefetch_related("recursos", "servicios_through__servicio")
    )


@require_GET
def lista_hospitales(request):
    queryset = _queryset_publico()

    tipo = request.GET.get("tipo")
    if tipo:
        if tipo not in {v for v, _ in Hospital.Tipo.choices}:
            return JsonResponse(
                {"error": "El tipo indicado no es válido."}, status=400
            )
        queryset = queryset.filter(tipo=tipo)

    nivel = request.GET.get("nivel")
    if nivel:
        if nivel not in {v for v, _ in Hospital.Nivel.choices}:
            return JsonResponse(
                {"error": "El nivel indicado no es válido."}, status=400
            )
        queryset = queryset.filter(nivel=nivel)

    estado = request.GET.get("estado_operativo")
    if estado:
        if estado not in ESTADOS_PUBLICOS:
            return JsonResponse(
                {"error": "El estado solicitado no está disponible públicamente."},
                status=400,
            )
        queryset = queryset.filter(estado_operativo=estado)

    municipio = request.GET.get("municipio")
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio.strip())

    parroquia = request.GET.get("parroquia")
    if parroquia:
        queryset = queryset.filter(parroquia__nombre__icontains=parroquia.strip())

    servicio = request.GET.get("servicio")
    if servicio:
        queryset = queryset.filter(
            servicios_through__servicio__codigo=servicio.strip(),
            servicios_through__disponible=True,
            servicios_through__servicio__activo=True,
        ).distinct()

    q = request.GET.get("q")
    if q:
        termino = q.strip()[:100]
        queryset = queryset.filter(
            Q(nombre__icontains=termino) | Q(direccion__icontains=termino)
        )

    try:
        limite = int(request.GET.get("limite", "50"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El límite debe ser un número entre 1 y 100."}, status=400
        )
    if not 1 <= limite <= 100:
        return JsonResponse(
            {"error": "El límite debe ser un número entre 1 y 100."}, status=400
        )

    try:
        offset = int(request.GET.get("offset", "0"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El offset debe ser un entero mayor o igual a 0."}, status=400
        )
    if offset < 0:
        return JsonResponse(
            {"error": "El offset debe ser un entero mayor o igual a 0."}, status=400
        )

    ahora = timezone.now()
    total = queryset.count()
    resultados = queryset.order_by("-creado_en")[offset:offset + limite]

    return JsonResponse({
        "total": total,
        "limite": limite,
        "offset": offset,
        "resultados": [_serializar_hospital(h, ahora) for h in resultados],
    })


@require_GET
def detalle_hospital(request, codigo):
    try:
        hospital = _queryset_publico().get(codigo=codigo)
    except Hospital.DoesNotExist:
        return JsonResponse(
            {"error": "El hospital no existe o no está disponible públicamente."},
            status=404,
        )
    return JsonResponse({
        "hospital": _serializar_hospital(hospital, timezone.now()),
    })
'''
write("apps/hospitales/views.py", views)

# ══════════════════════════════════════════════════════════════════
# 2) apps/hospitales/urls.py
# ══════════════════════════════════════════════════════════════════
print("== 2/4 urls.py ==")
write("apps/hospitales/urls.py", '''from django.urls import path

from apps.hospitales import views

app_name = "hospitales"

urlpatterns = [
    path("", views.lista_hospitales, name="lista"),
    path("<slug:codigo>/", views.detalle_hospital, name="detalle"),
]
''')

# ══════════════════════════════════════════════════════════════════
# 3) config/urls.py
# ══════════════════════════════════════════════════════════════════
print("== 3/4 config/urls.py ==")
patch(
    "config/urls.py",
    '    path(\n'
    '        "api/publico/refugios/",\n'
    '        include("apps.refugios.urls"),\n'
    '    ),\n',
    '    path(\n'
    '        "api/publico/refugios/",\n'
    '        include("apps.refugios.urls"),\n'
    '    ),\n'
    '    path(\n'
    '        "api/publico/hospitales/",\n'
    '        include("apps.hospitales.urls"),\n'
    '    ),\n',
    "config/urls: hospitales públicos"
)

# ══════════════════════════════════════════════════════════════════
# 4) apps/hospitales/migrations/0002_servicios_iniciales.py
# ══════════════════════════════════════════════════════════════════
print("== 4/4 data migration: catálogo de servicios ==")
data_migration = '''from django.db import migrations


SERVICIOS = [
    # codigo, nombre, tipo
    ("emergencia", "Emergencia", "SERVICIO"),
    ("hospitalizacion", "Hospitalización", "SERVICIO"),
    ("uci", "Unidad de Cuidados Intensivos", "SERVICIO"),
    ("quirofano", "Quirófano", "SERVICIO"),
    ("laboratorio", "Laboratorio clínico", "SERVICIO"),
    ("imagenologia", "Imagenología", "SERVICIO"),
    ("farmacia", "Farmacia", "SERVICIO"),
    ("pediatria", "Pediatría", "ESPECIALIDAD"),
    ("ginecologia", "Ginecología y Obstetricia", "ESPECIALIDAD"),
    ("cardiologia", "Cardiología", "ESPECIALIDAD"),
    ("traumatologia", "Traumatología", "ESPECIALIDAD"),
    ("medicina_interna", "Medicina Interna", "ESPECIALIDAD"),
    ("cirugia_general", "Cirugía General", "ESPECIALIDAD"),
    ("oftalmologia", "Oftalmología", "ESPECIALIDAD"),
    ("nefrologia", "Nefrología", "ESPECIALIDAD"),
]


def crear_servicios(apps, schema_editor):
    Servicio = apps.get_model("hospitales", "Servicio")
    for codigo, nombre, tipo in SERVICIOS:
        Servicio.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "tipo": tipo, "activo": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("hospitales", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_servicios, migrations.RunPython.noop),
    ]
'''
write(
    "apps/hospitales/migrations/0002_servicios_iniciales.py",
    data_migration,
)

print("\n✅ Portal público + catálogo escritos. Ejecuta fase6_1_5_tests_docs.py")
