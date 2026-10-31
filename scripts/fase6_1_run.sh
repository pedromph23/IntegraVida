#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 6.1 — Hospitales"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/6: Crear app hospitales"
python3 scripts/fase6_1_hospitales.py

echo ""
echo "▶ 2/6: Añadir a INSTALLED_APPS"
python3 - <<'PYEOF'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
needle = "    'apps.refugios.apps.RefugiosConfig',\n"
addition = needle + "    'apps.hospitales.apps.HospitalesConfig',\n"
if "'apps.hospitales.apps.HospitalesConfig'" in text:
    print("ya aplicado")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: hospitales añadido a INSTALLED_APPS")
else:
    raise SystemExit("ERROR: no se encontró RefugiosConfig")
PYEOF

echo ""
echo "▶ 3/6: Tests + docs"
python3 scripts/fase6_1_tests_docs.py

echo ""
echo "▶ 4/6: Generar migración"
python3 manage.py makemigrations hospitales

echo ""
echo "▶ 5/6: Aplicar migración"
python3 manage.py migrate hospitales

echo ""
echo "▶ Verificación: django check + makemigrations --check"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ 6/6: Tests hospitales + regresión"
python3 manage.py test apps.hospitales -v 2
python3 manage.py test apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 6.1 completada"
