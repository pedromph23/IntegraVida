#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ Rebuild CSS+JS"
NODE_ENV=production npx tailwindcss -i ./static/css/src/main.css -o ./static/css/dist/main.css --minify >/dev/null
npx esbuild ./static/js/src/main.js --bundle --outfile=./static/js/dist/main.js --minify --sourcemap >/dev/null
echo "  CSS gzip: $(gzip -c static/css/dist/main.css | wc -c | tr -d ' ') B"
echo "  JS  gzip: $(gzip -c static/js/dist/main.js | wc -c | tr -d ' ') B"

echo "▶ Anti-CDN"
bash scripts/check-no-cdn.sh
echo "▶ Django check"
python3 manage.py check

echo "▶ Tests F3.e.2"
python3 manage.py test frontend.tests.test_dashboard_pacientes -v 1 2>&1 | tail -6

echo "▶ Tests globales"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
echo "$TEST_OUT" | grep -q "^OK" || { echo "❌ Tests rojos"; exit 1; }
echo "✅ Tests OK"

echo "▶ Smoke"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload > /tmp/rs_f3e2.log 2>&1 &
RS_PID=$!
sleep 3
for p in / /hospitales/ /refugios/ /alertas/ /panel/login/ /admin/; do
    echo "  $p → $(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:8000$p)"
done
echo "  /panel/pacientes/ (sin sesión, -L) → $(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:8000/panel/pacientes/)"
echo "  /pacientes/ (URL pública — debe ser 404) → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/pacientes/)"
kill "$RS_PID" 2>/dev/null
wait "$RS_PID" 2>/dev/null || true

echo ""
echo "✅ F3.e.2 — módulo Pacientes"
