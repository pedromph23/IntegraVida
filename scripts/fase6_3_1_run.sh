#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 6.3.1 — Fix estructural de email"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/5: Parchear modelo"
python3 scripts/fase6_3_1_fix.py

echo ""
echo "▶ 2/5: Tests + docs"
python3 scripts/fase6_3_1_tests_docs.py

echo ""
echo "▶ 3/5: Generar migración"
python3 manage.py makemigrations usuarios

echo ""
echo "▶ 4/5: Aplicar migración"
python3 manage.py migrate usuarios

echo ""
echo "▶ Verificación: check + makemigrations --check"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ 5/5: Tests usuarios + regresión global"
python3 manage.py test apps.usuarios -v 2
python3 manage.py test apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 6.3.1 completada"
