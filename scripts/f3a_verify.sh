#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ Rebuild CSS"
NODE_ENV=production npx tailwindcss -i ./static/css/src/main.css -o ./static/css/dist/main.css --minify
echo "  CSS gzip: $(gzip -c static/css/dist/main.css | wc -c | tr -d ' ') bytes"

echo "▶ Rebuild JS"
npx esbuild ./static/js/src/main.js --bundle --outfile=./static/js/dist/main.js --minify --sourcemap
echo "  JS gzip:  $(gzip -c static/js/dist/main.js | wc -c | tr -d ' ') bytes"

echo "▶ Anti-CDN"
bash scripts/check-no-cdn.sh

echo "▶ Django check"
python3 manage.py check

echo "▶ Tests"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
if ! echo "$TEST_OUT" | grep -q "^OK"; then
    echo "❌ Tests rojos. NO COMMITEAR."
    exit 1
fi
echo "✅ Tests OK"

echo "▶ Smoke"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload > /tmp/rs_f3a.log 2>&1 &
RS_PID=$!
sleep 3

for p in /panel/ /panel/login/ /admin/ / /hospitales/ /refugios/; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -L "http://localhost:8000$p")
    echo "  $p → $code"
done

echo ""
echo "--- Anti-FOUC en login (esperado: 1) ---"
grep -c "data-theme" templates/auth/login.html

echo "--- CDNs en templates nuevos (esperado: 0) ---"
grep -rE "https?://(cdn|unpkg|jsdelivr|fonts\.googleapis)" \
  templates/auth templates/dashboard templates/layouts templates/base 2>/dev/null \
  && echo "❌ Encontrado CDN" || echo "OK: sin CDNs"

kill "$RS_PID" 2>/dev/null || true
wait "$RS_PID" 2>/dev/null || true

echo ""
echo "✅ F3.a verificación completa"
