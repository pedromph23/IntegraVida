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

echo "▶ Tests F4.b"
python3 manage.py test frontend.tests.test_admin_mfa -v 1 2>&1 | tail -6

echo "▶ Tests globales"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
echo "$TEST_OUT" | grep -q "^OK" || { echo "❌ Tests rojos"; exit 1; }
echo "✅ Tests OK"

echo "▶ Smoke"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload > /tmp/rs_f4b.log 2>&1 &
RS_PID=$!
sleep 3

echo "  ── /admin/ sigue 404 ──"
for p in /admin/ /admin/login/ /admin/anything/; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000$p)"
done

echo "  ── Admin oculto MFA ──"
echo "    /$SLUG/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/$SLUG/)"
echo "    /$SLUG/login/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/$SLUG/login/)"
echo "    /$SLUG/mfa/ (anónimo, sin -L) → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/$SLUG/mfa/)"
echo "    /$SLUG/mfa/setup/ (anónimo, sin -L) → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/$SLUG/mfa/setup/)"

echo "  ── Redirect MFA anónimo (debe ir a /<slug>/login/) ──"
MFA_REDIR=$(curl -s -o /dev/null -w '%{redirect_url}' http://localhost:8000/$SLUG/mfa/)
echo "    → $MFA_REDIR"
if echo "$MFA_REDIR" | grep -q "/panel/login/"; then
    echo "    ❌ redirect a /panel/login/ (FALLO F4.b)"
    kill "$RS_PID" 2>/dev/null
    wait "$RS_PID" 2>/dev/null || true
    exit 1
fi

echo "  ── Portal y panel intactos ──"
for p in / /hospitales/ /refugios/ /alertas/ /panel/login/ /health/ /robots.txt; do
    echo "    $p → $(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:8000$p)"
done

echo "  ── Headers MFA endpoint ──"
curl -sI "http://localhost:8000/$SLUG/mfa/" | grep -iE "x-robots-tag|cache-control|x-frame" || echo "    ⚠ Faltan headers"

kill "$RS_PID" 2>/dev/null
wait "$RS_PID" 2>/dev/null || true

echo ""
echo "✅ F4.b — MFA TOTP + rate limit + login admin oculto"
