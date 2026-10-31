#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Estado actual de STATIC_* en settings.py"
grep -E "^STATIC_(URL|ROOT|FILES_DIRS)" config/settings.py

echo ""
echo "▶ 2. Activar STATICFILES_DIRS"
python3 - << 'PY'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")

# Caso 1: línea comentada con texto original
commented = "# STATICFILES_DIRS = [BASE_DIR / 'static']   # descomentar si existe static/ común"
if commented in text:
    text = text.replace(commented, "STATICFILES_DIRS = [BASE_DIR / 'static']", 1)
    p.write_text(text, encoding="utf-8")
    print("OK: STATICFILES_DIRS activado (comentario removido)")
    raise SystemExit(0)

# Caso 2: ya activo
if "STATICFILES_DIRS = [BASE_DIR / 'static']" in text:
    print("ya aplicado: STATICFILES_DIRS")
    raise SystemExit(0)

# Caso 3: no existe — insertar tras STATIC_URL
needle = "STATIC_URL = 'static/'"
if needle in text:
    text = text.replace(
        needle,
        needle + "\nSTATICFILES_DIRS = [BASE_DIR / 'static']",
        1,
    )
    p.write_text(text, encoding="utf-8")
    print("OK: STATICFILES_DIRS insertado tras STATIC_URL")
    raise SystemExit(0)

raise SystemExit("ERROR: no se encontró STATIC_URL en settings.py")
PY

echo ""
echo "▶ 3. Verificar STATICFILES_DIRS desde Django"
python3 manage.py shell -c "
from django.conf import settings
print('STATIC_URL        =', settings.STATIC_URL)
print('STATIC_ROOT       =', settings.STATIC_ROOT)
print('STATICFILES_DIRS  =', settings.STATICFILES_DIRS)
"

echo ""
echo "▶ 4. Verificar resolución del archivo"
python3 manage.py shell -c "
from django.contrib.staticfiles import finders
css_path = finders.find('css/dist/main.css')
js_path = finders.find('js/dist/main.js')
print('CSS resuelve a:', css_path)
print('JS  resuelve a:', js_path)
assert css_path is not None, 'CSS NO se resuelve'
assert js_path is not None, 'JS NO se resuelve'
print('OK: ambos archivos se resuelven')
"

echo ""
echo "▶ 5. Test HTTP real (arranca servidor, consulta, mata)"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_static_check.log &
RS_PID=$!
sleep 3
CSS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/css/dist/main.css)
JS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/js/dist/main.js)
CSS_SIZE=$(curl -s http://localhost:8000/static/css/dist/main.css | wc -c)
JS_SIZE=$(curl -s http://localhost:8000/static/js/dist/main.js | wc -c)
kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo "CSS: HTTP $CSS_CODE ($CSS_SIZE bytes)"
echo "JS:  HTTP $JS_CODE ($JS_SIZE bytes)"

if [ "$CSS_CODE" != "200" ] || [ "$JS_CODE" != "200" ]; then
    echo "ERROR: STATICFILES no funciona"
    exit 1
fi

echo ""
echo "▶ 6. Borrar snapshots incorrectos (fueron capturados sin CSS)"
rm -rf tests/e2e/snapshots.spec.ts-snapshots
echo "OK: snapshots borrados"

echo ""
echo "▶ 7. Regenerar snapshots con CSS correcto"
npx playwright test --update-snapshots 2>&1 | tail -20

echo ""
echo "▶ 8. Confirmar que los 9 tests pasan sin --update"
npx playwright test 2>&1 | tail -15

echo ""
echo "▶ 9. Verificar archivos de baseline creados"
ls -la tests/e2e/snapshots.spec.ts-snapshots/

echo ""
echo "✅ FIX STATICFILES COMPLETADO"
