#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Cambiar '__all__' → 'general' en el view"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

old = '                errors = {"__all__": list(exc.messages)}'
new = '                errors = {"general": list(exc.messages)}'

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: view usa errors['general']")
elif '"general"' in text:
    print("ya aplicado: view")
else:
    raise SystemExit("ERROR: bloque no encontrado en views")
PY

echo ""
echo "▶ 2. Cambiar errors.__all__ → errors.general en el template"
python3 - << 'PY'
from pathlib import Path
p = Path("templates/public/report_form.html")
text = p.read_text(encoding="utf-8")

old_block = '''  {% if errors.__all__ %}
    <div class="mt-4">
      {% include "components/alert.html" with variant="danger" title="Error al enviar" body=errors.__all__.0 dismissible=True %}
    </div>
  {% endif %}'''

new_block = '''  {% if errors.general %}
    <div class="mt-4">
      {% include "components/alert.html" with variant="danger" title="Error al enviar" body=errors.general.0 dismissible=True %}
    </div>
  {% endif %}'''

if old_block in text:
    text = text.replace(old_block, new_block, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: template usa errors.general")
elif "errors.general" in text:
    print("ya aplicado: template")
else:
    raise SystemExit("ERROR: bloque no encontrado en template")
PY

echo ""
echo "▶ 3. Verificar que ya no queda '__all__' en template"
if grep -n "__all__" templates/public/report_form.html; then
    echo "ERROR: queda '__all__' en el template"
    exit 1
fi
echo "OK: sin '__all__' residual"

echo ""
echo "▶ 4. Tests de reportes (los 3 que fallaban + los 6 que ya pasaban)"
python3 manage.py test frontend.tests.test_public_views.ReportesPublicosTests -v 2 2>&1 | tail -20

echo ""
echo "▶ 5. Suite completa con bloqueo (§3.8)"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
if ! echo "$TEST_OUT" | grep -q "^OK"; then
    echo ""
    echo "❌ ERROR: tests rojos. NO COMMITEAR."
    exit 1
fi
echo "✅ Tests OK, seguro para commit"

echo ""
echo "▶ 6. Smoke final"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_f2d_fix.log &
RS_PID=$!
sleep 3

CODE_FORM=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/reportes/)
CODE_404=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/reportes/00000000-0000-0000-0000-000000000000/)
HOME_CTA=$(curl -s http://localhost:8000/ | grep -c 'href="/reportes/"' || true)
ALERTS_CTA=$(curl -s http://localhost:8000/alertas/ | grep -c 'href="/reportes/"' || true)

kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo "GET /reportes/              → $CODE_FORM (esperado 200)"
echo "GET /reportes/<uuid>/        → $CODE_404 (esperado 404)"
echo "CTA en home:                 $HOME_CTA (esperado ≥1)"
echo "CTA en /alertas/:            $ALERTS_CTA (esperado ≥1)"

echo ""
echo "✅ F2.d — Reportes implementados (DTL fix aplicado)"
