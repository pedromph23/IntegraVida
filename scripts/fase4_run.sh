#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 4 — Aplicar fixes + tests + docs"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ Script 1/2: parchear código"
python3 scripts/fase4_codigo.py

echo ""
echo "▶ Script 2/2: escribir tests + docs"
python3 scripts/fase4_tests_docs.py

echo ""
echo "▶ Verificación: django check"
python3 manage.py check

echo ""
echo "▶ Verificación: makemigrations --check"
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ Ejecutando 12 tests de emergencias"
python3 manage.py test apps.emergencias -v 2

echo ""
echo "✅ FASE 4 completada"
echo ""
echo "Revisa:"
echo "  git status --short"
echo "  git diff --stat"
