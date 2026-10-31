#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 6.2 — Pacientes, Episodios, Contactos"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/6: Crear app pacientes"
python3 scripts/fase6_2_pacientes.py

echo ""
echo "▶ 2/6: Añadir a INSTALLED_APPS"
python3 - <<'PYEOF'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
needle = "    'apps.hospitales.apps.HospitalesConfig',\n"
addition = needle + "    'apps.pacientes.apps.PacientesConfig',\n"
if "'apps.pacientes.apps.PacientesConfig'" in text:
    print("ya aplicado")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: pacientes añadido a INSTALLED_APPS")
else:
    raise SystemExit("ERROR: no se encontró HospitalesConfig")
PYEOF

echo ""
echo "▶ 3/6: Tests + docs"
python3 scripts/fase6_2_tests_docs.py

echo ""
echo "▶ 4/6: Generar migración"
python3 manage.py makemigrations pacientes

echo ""
echo "▶ 5/6: Aplicar migración"
python3 manage.py migrate pacientes

echo ""
echo "▶ Verificación: check + makemigrations --check"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ 6/6: Tests pacientes + regresión global"
python3 manage.py test apps.pacientes -v 2
python3 manage.py test apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 6.2 completada"
