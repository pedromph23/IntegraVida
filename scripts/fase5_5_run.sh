#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 5.5 — Portal público de refugios"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/3: Escribir código (views, urls, config)"
python3 scripts/fase5_5_refugios.py

echo ""
echo "▶ 2/3: Tests + docs"
python3 scripts/fase5_5_tests_docs.py

echo ""
echo "▶ 3/3: Verificar y testear"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ Tests de refugios"
python3 manage.py test apps.refugios -v 2

echo ""
echo "▶ Regresión: emergencias + auditoría"
python3 manage.py test apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 5.5 completada"
