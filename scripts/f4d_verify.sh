#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

SLUG=$(python3 -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from django.conf import settings; print(settings.INTEGRAVIDA_ADMIN_SLUG)")
echo "▶ Slug del admin: $SLUG"

echo "▶ Rebuild CSS+JS"
NODE_ENV=production npx tailwindcss -i ./static/css/src/main.css -o ./static/css/dist/main.css --minify >/dev/null
npx esbuild ./static/js/src/main.js --bundle --outfile=./static/js/dist/main.js --minify --sourcemap >/dev/null
echo "  CSS gzip: $(gzip -c static/css/dist/main.css | wc -c | tr -d ' ') B"
echo "  JS  gzip: $(gzip -c static/js/dist/main.js | wc -c | tr -d ' ') B"

echo "▶ Anti-CDN"
bash scripts/check-no-cdn.sh
echo "▶ Django check"
python3 manage.py check

echo "▶ Tests F4.d (audit + config)"
python3 manage.py test frontend.tests.test_admin_audit frontend.tests.test_admin_config --noinput -v 1 2>&1 | tail -6

echo "▶ Tests globales"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend --noinput -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
echo "$TEST_OUT" | grep -q "^OK" || { echo "❌ Tests rojos"; exit 1; }
echo "✅ Tests OK"

echo "▶ Smoke"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload > /tmp/rs_f4d.log 2>&1 &
RS_PID=$!
sleep 3

echo "  ── /admin/ sigue 404 ──"
for p in /admin/ /admin/login/; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000$p)"
done

echo "  ── Nuevas rutas F4.d: anónimo → login del admin ──"
for p in "/$SLUG/custom/audit/" "/$SLUG/custom/config/"; do
    CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:8000$p")
    REDIR=$(curl -s -o /dev/null -w '%{redirect_url}' "http://localhost:8000$p")
    echo "    $p → $CODE $REDIR"
    if echo "$REDIR" | grep -q "/panel/login/"; then
        echo "    ❌ redirect a /panel/login/ (FALLO F4.d)"
        kill "$RS_PID" 2>/dev/null
        wait "$RS_PID" 2>/dev/null || true
        exit 1
    fi
done

echo "  ── Rutas F4.c siguen OK ──"
for p in "/$SLUG/custom/" "/$SLUG/custom/users/"; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000$p)"
done

echo "  ── Admin nativo + login + portal y panel ──"
for p in "/$SLUG/" "/$SLUG/login/" / /hospitales/ /refugios/ /alertas/ /panel/login/ /health/ /robots.txt; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:8000$p)"
done

kill "$RS_PID" 2>/dev/null
wait "$RS_PID" 2>/dev/null || true

echo ""
echo "✅ F4.d — audit + config del admin custom"
