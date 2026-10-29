#!/usr/bin/env python3
"""Aplica los 4 fixes de código de Fase 4. Idempotente y verificable."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

def patch(path, old, new, label=""):
    p = BASE / path
    if not p.exists():
        sys.exit(f"ERROR: no existe {path}")
    text = p.read_text(encoding="utf-8")
    if old not in text and new in text:
        print(f"  ya aplicado: {label or path}")
        return
    n = text.count(old)
    if n != 1:
        sys.exit(f"ERROR: {path} — '{old[:60]}...' aparece {n} veces (esperaba 1)")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK: {label or path}")

def write(path, content):
    p = BASE / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  escrito: {path}")

# ══════════════════════════════════════════════════════════════════
# 1) apps/emergencias/services.py — actor=None + direccion_ip
# ══════════════════════════════════════════════════════════════════
print("== 1/4 services.py ==")
patch(
    "apps/emergencias/services.py",
    '    registrar_evento(\n'
    '        accion="emergencia.reporte_publico",\n',
    '    registrar_evento(\n'
    '        actor=None,\n'
    '        accion="emergencia.reporte_publico",\n',
    "services: actor=None"
)
patch(
    "apps/emergencias/services.py",
    '        justificacion="Recepción de reporte ciudadano.",\n'
    '        ip=ip,\n',
    '        justificacion="Recepción de reporte ciudadano.",\n'
    '        direccion_ip=ip,\n',
    "services: direccion_ip"
)

# ══════════════════════════════════════════════════════════════════
# 2) apps/emergencias/servicios_revision.py — direccion_ip
# ══════════════════════════════════════════════════════════════════
print("== 2/4 servicios_revision.py ==")
patch(
    "apps/emergencias/servicios_revision.py",
    '        ip=request.META.get("REMOTE_ADDR") or None,\n',
    '        direccion_ip=request.META.get("REMOTE_ADDR") or None,\n',
    "servicios_revision: direccion_ip"
)

# ══════════════════════════════════════════════════════════════════
# 3) apps/emergencias/views.py — 4 fixes
# ══════════════════════════════════════════════════════════════════
print("== 3/4 views.py ==")

# 3.1 Imports
patch(
    "apps/emergencias/views.py",
    "import json\n\n"
    "from django.http import JsonResponse\n"
    "from django.views.decorators.http import require_GET\n"
    "from django.views.decorators.http import require_POST\n",
    "import json\n\n"
    "from django.db.models import Q\n"
    "from django.http import JsonResponse\n"
    "from django.views.decorators.csrf import csrf_exempt\n"
    "from django.views.decorators.http import require_GET\n"
    "from django.views.decorators.http import require_POST\n",
    "views: imports Q + csrf_exempt"
)

# 3.2 Búsqueda con Q()
patch(
    "apps/emergencias/views.py",
    "    if busqueda:\n"
    "        queryset = queryset.filter(\n"
    "            ubicacion_texto__icontains=busqueda.strip()\n"
    "        ) | queryset.filter(\n"
    "            titulo__icontains=busqueda.strip()\n"
    "        )\n",
    "    if busqueda:\n"
    "        termino = busqueda.strip()\n"
    "        queryset = queryset.filter(\n"
    "            Q(ubicacion_texto__icontains=termino)\n"
    "            | Q(titulo__icontains=termino)\n"
    "        )\n",
    "views: Q() en busqueda"
)

# 3.3 Offset + total
patch(
    "apps/emergencias/views.py",
    "    total = queryset.count()\n"
    "    resultados = queryset.order_by(\"-creada_en\")[:limite]\n"
    "\n"
    "    return JsonResponse({\n"
    "        \"total\": total,\n"
    "        \"limite\": limite,\n"
    "        \"resultados\": [\n"
    "            _serializar_emergencia(emergencia)\n"
    "            for emergencia in resultados\n"
    "        ],\n"
    "    })\n",
    "    try:\n"
    "        offset = int(request.GET.get(\"offset\", \"0\"))\n"
    "    except (TypeError, ValueError):\n"
    "        return JsonResponse(\n"
    "            {\"error\": \"El offset debe ser un entero mayor o igual a 0.\"},\n"
    "            status=400,\n"
    "        )\n"
    "\n"
    "    if offset < 0:\n"
    "        return JsonResponse(\n"
    "            {\"error\": \"El offset debe ser un entero mayor o igual a 0.\"},\n"
    "            status=400,\n"
    "        )\n"
    "\n"
    "    total = queryset.count()\n"
    "    resultados = queryset.order_by(\"-creada_en\")[offset:offset + limite]\n"
    "\n"
    "    return JsonResponse({\n"
    "        \"total\": total,\n"
    "        \"limite\": limite,\n"
    "        \"offset\": offset,\n"
    "        \"resultados\": [\n"
    "            _serializar_emergencia(emergencia)\n"
    "            for emergencia in resultados\n"
    "        ],\n"
    "    })\n",
    "views: offset paginación"
)

# 3.4 csrf_exempt + content-type startswith
patch(
    "apps/emergencias/views.py",
    "@require_POST\n"
    "def crear_reporte_publico(request):\n"
    "    \"\"\"Recibe un reporte ciudadano sin exigir autenticación.\"\"\"\n"
    "    from django.core.exceptions import ValidationError\n"
    "\n"
    "    from apps.emergencias.services import recibir_reporte_publico\n"
    "\n"
    "    if request.content_type != \"application/json\":\n",
    "@csrf_exempt\n"
    "@require_POST\n"
    "def crear_reporte_publico(request):\n"
    "    \"\"\"Recibe un reporte ciudadano sin exigir autenticación.\"\"\"\n"
    "    from django.core.exceptions import ValidationError\n"
    "\n"
    "    from apps.emergencias.services import recibir_reporte_publico\n"
    "\n"
    "    if not (request.content_type or \"\").startswith(\"application/json\"):\n",
    "views: csrf_exempt + startswith"
)

# ══════════════════════════════════════════════════════════════════
# 4) apps/emergencias/urls.py — añadir reportes/estado/
# ══════════════════════════════════════════════════════════════════
print("== 4/4 urls.py ==")
write(
    "apps/emergencias/urls.py",
    "from django.urls import path\n\n"
    "from apps.emergencias import views\n\n"
    "app_name = \"emergencias\"\n\n"
    "urlpatterns = [\n"
    "    path(\"\", views.lista_emergencias, name=\"lista\"),\n"
    "    path(\n"
    "        \"reportes/estado/\",\n"
    "        views.estado_servicio_reportes,\n"
    "        name=\"estado-servicio\",\n"
    "    ),\n"
    "    path(\n"
    "        \"reportes/\",\n"
    "        views.crear_reporte_publico,\n"
    "        name=\"crear-reporte\",\n"
    "    ),\n"
    "    path(\n"
    "        \"<uuid:emergencia_id>/\",\n"
    "        views.detalle_emergencia,\n"
    "        name=\"detalle\",\n"
    "    ),\n"
    "]\n"
)

print("\n✅ Código parcheado. Ahora ejecuta scripts/fase4_tests_docs.py")
