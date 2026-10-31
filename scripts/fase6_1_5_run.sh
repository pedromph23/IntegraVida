#!/usr/bin/env bash
set -e

cd ~/proyectos/integravida

echo "═══════════════════════════════════════════"
echo " FASE 6.1.5 — Portal público de hospitales"
echo "═══════════════════════════════════════════"

echo ""
echo "▶ 1/5: Escribir código (views, urls, config, data migration)"
python3 scripts/fase6_1_5_hospitales.py

echo ""
echo "▶ 2/5: Tests + docs"
python3 scripts/fase6_1_5_tests_docs.py

echo ""
echo "▶ 3/5: Aplicar data migration (catálogo de servicios)"
python3 manage.py migrate hospitales

echo ""
echo "▶ Verificación: django check + makemigrations --check"
python3 manage.py check
python3 manage.py makemigrations --check --dry-run

echo ""
echo "▶ 4/5: Tests hospitales"
python3 manage.py test apps.hospitales -v 2

echo ""
echo "▶ 5/5: Regresión global (refugios + emergencias + auditoría)"
python3 manage.py test apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "▶ Verificar precarga de servicios"
python3 manage.py shell -c "from apps.hospitales.models import Servicio; print(f'Servicios precargados: {Servicio.objects.count()}'); print(list(Servicio.objects.values_list('codigo', flat=True)[:5]))"

echo ""
echo "✅ FASE 6.1.5 completada"
