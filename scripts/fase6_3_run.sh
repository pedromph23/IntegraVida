#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 6.3 — Triaje + Ámbito de Membresía"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/7: Escribir código (organizaciones + triaje)"
python3 scripts/fase6_3_codigo.py

echo ""
echo "▶ 2/7: Añadir triaje a INSTALLED_APPS"
python3 - <<'PYEOF'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
needle = "    'apps.pacientes.apps.PacientesConfig',\n"
addition = needle + "    'apps.triaje.apps.TriajeConfig',\n"
if "'apps.triaje.apps.TriajeConfig'" in text:
    print("ya aplicado")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: triaje añadido a INSTALLED_APPS")
else:
    raise SystemExit("ERROR: no se encontró PacientesConfig")
PYEOF

echo ""
echo "▶ 3/7: Tests + docs"
python3 scripts/fase6_3_tests_docs.py

echo ""
echo "▶ 4/7: Generar migración Membresia"
python3 manage.py makemigrations organizaciones

echo ""
echo "▶ 5/7: Generar migración Triaje"
python3 manage.py makemigrations triaje

echo ""
echo "▶ 6/7: Aplicar migraciones"
python3 manage.py migrate organizaciones
python3 manage.py migrate triaje

echo ""
echo "▶ Verificación: check + makemigrations --check"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ 7/7: Tests + regresión global"
python3 manage.py test apps.triaje apps.organizaciones apps.pacientes -v 2
python3 manage.py test apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 6.3 completada"
