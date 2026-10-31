#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 5 — Refugios"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/4: Crear app refugios"
python3 scripts/fase5_refugios.py

echo ""
echo "▶ 2/4: Añadir app a INSTALLED_APPS"
python3 - <<'PYEOF'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
needle = "    'apps.emergencias.apps.EmergenciasConfig',\n"
addition = needle + "    'apps.refugios.apps.RefugiosConfig',\n"
if "'apps.refugios.apps.RefugiosConfig'" in text:
    print("ya aplicado")
elif needle in text:
    text = text.replace(needle, addition, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: refugios añadido a INSTALLED_APPS")
else:
    raise SystemExit("ERROR: no se encontró EmergenciasConfig en settings")
PYEOF

echo ""
echo "▶ 3/4: Generar migración"
python3 manage.py makemigrations refugios

echo ""
echo "▶ 4/4: Aplicar migración"
python3 manage.py migrate refugios

echo ""
echo "▶ Verificación: django check"
python3 manage.py check

echo ""
echo "▶ Ejecutando 13 tests de refugios"
python3 manage.py test apps.refugios -v 2

echo ""
echo "▶ Tests de auditoría (regresión)"
python3 manage.py test apps.auditoria -v 1

echo ""
echo "✅ FASE 5 completada"
echo ""
echo "Revisa:"
echo "  git status --short"
echo "  python manage.py shell -c 'from apps.refugios.models import Refugio; print(Refugio.objects.count())'"
