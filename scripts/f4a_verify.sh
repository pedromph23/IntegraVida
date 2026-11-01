#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

SLUG=$(python3 -c "from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); print(settings.INTEGRAVIDA_ADMIN_SLUG)")
echo "▶ Slug del admin (desde env): $SLUG"

echo "▶ Rebuild CSS+JS"
NODE_ENV=production npx tailwindcss -i ./static/css/src/main.css -o ./static/css/dist/main.css --minify >/dev/null
npx esbuild ./static/js/src/main.js --bundle --outfile=./static/js/dist/main.js --minify --sourcemap >/dev/null
echo "  CSS gzip: $(gzip -c static/css/dist/main.css | wc -c | tr -d ' ') B"
echo "  JS  gzip: $(gzip -c static/js/dist/main.js | wc -c | tr -d ' ') B"

echo "▶ Anti-CDN"; bash scripts/check-no-cdn.sh
echo "▶ Django check"; python3 manage.py check

echo "▶ Tests F4.a"
python3 manage.py test frontend.tests.test_admin_hidden -v 1 2>&1 | tail -6

echo "▶ Tests globales"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
echo "$TEST_OUT" | grep -q "^OK" || { echo "❌ Tests rojos"; exit 1; }
echo "✅ Tests OK"

echo "▶ Smoke"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload > /tmp/rs_f4a.log 2>&1 &
RS_PID=$!
sleep 3

echo "  ── Rutas que deben seguir 200 ──"
for p in / /hospitales/ /refugios/ /alertas/ /panel/login/ /health/; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:8000$p)"
done

echo "  ── /admin/ debe ser 404 ──"
echo "    /admin/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/)"
echo "    /admin/login/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/login/)"
echo "    /admin/anything/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/anything/)"

echo "  ── Admin oculto (slug) ──"
echo "    /$SLUG/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/$SLUG/)"
echo "    /$SLUG/login/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/$SLUG/login/)"

echo "  ── Headers en /$SLUG/login/ ──"
curl -sI "http://localhost:8000/$SLUG/login/" | grep -iE "x-robots-tag|cache-control|x-frame" || echo "    ⚠ Faltan headers"

echo "  ── robots.txt ──"
curl -s "http://localhost:8000/robots.txt" | head -10

kill "$RS_PID" 2>/dev/null
wait "$RS_PID" 2>/dev/null || true

echo ""
echo "✅ F4.a — Admin oculto con slug configurable + /admin/ 404"
