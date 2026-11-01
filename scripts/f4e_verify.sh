#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

SLUG=$(python3 -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from django.conf import settings; print(settings.INTEGRAVIDA_ADMIN_SLUG)")
echo "▶ Slug del admin: $SLUG"

echo "▶ Rebuild CSS+JS"
NODE_ENV=production npx tailwindcss -i ./static/css/src/main.css -o ./static/css/dist/main.css --minify >/dev/null
npx esbuild ./static/js/src/main.js --bundle --outfile=./static/js/dist/main.js --minify --sourcemap >/dev/null

echo "▶ Anti-CDN"
bash scripts/check-no-cdn.sh
echo "▶ Django check"
python3 manage.py check

echo "▶ Tests F4.e"
python3 manage.py test \
    frontend.tests.test_security_headers \
    frontend.tests.test_admin_hidden_grep \
    --noinput -v 1 2>&1 | tail -6

echo "▶ Tests globales (regresión F1–F4 completa)"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend --noinput -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
echo "$TEST_OUT" | grep -q "^OK" || { echo "❌ Tests rojos"; exit 1; }
echo "✅ Tests OK"

echo "▶ Smoke final"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload > /tmp/rs_f4e.log 2>&1 &
RS_PID=$!
sleep 3

echo "  ── Headers en / ──"
curl -sI http://localhost:8000/ | grep -iE "content-security-policy|x-content-type|referrer-policy|permissions-policy|x-frame" | sed 's/^/    /'

echo "  ── Headers en /admin/ (404 + CSP) ──"
curl -sI http://localhost:8000/admin/ | grep -iE "content-security-policy|x-robots" | sed 's/^/    /'

echo "  ── Rutas críticas ──"
for p in / /admin/ /panel/login/ "/$SLUG/login/" /health/ /robots.txt; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000$p)"
done

echo "  ── Portal público NO contiene el slug ──"
for p in / /hospitales/ /refugios/ /alertas/ /panel/login/; do
    BODY=$(curl -s "http://localhost:8000$p")
    if echo "$BODY" | grep -q "$SLUG"; then
        echo "    ❌ $p contiene el slug del admin"
        kill "$RS_PID" 2>/dev/null
        wait "$RS_PID" 2>/dev/null || true
        exit 1
    else
        echo "    ✅ $p limpio"
    fi
done

kill "$RS_PID" 2>/dev/null
wait "$RS_PID" 2>/dev/null || true

echo ""
echo "✅ F4.e — CSP + headers + grep slug. F4 COMPLETA."
