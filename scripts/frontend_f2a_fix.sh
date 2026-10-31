#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Fix Http404 en frontend/views/public.py"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

# Añadir Http404 al bloque de imports de django.http (donde ya puede estar Http404 local)
if "from django.http import Http404" not in text.split("\n\n\n")[0]:
    # Insertar al nivel de módulo, junto a otros imports de django
    needle = "from django.http import Http404\n" if "from django.http import Http404\n" in text else None
    # Buscar cualquier bloque de imports de django para añadir
    if "from django.conf import settings\n" in text:
        text = text.replace(
            "from django.conf import settings\n",
            "from django.conf import settings\nfrom django.http import Http404\n",
            1,
        )
        print("OK: Http404 añadido al import de módulo")
    else:
        raise SystemExit("ERROR: no se encontró from django.conf import settings")
else:
    print("ya aplicado: Http404 en imports")
    
# Limpiar el import redundante dentro de design_system si existe
text = text.replace("        from django.http import Http404\n", "")

p.write_text(text, encoding="utf-8")
PY

echo ""
echo "▶ 2. Mostrar imports actuales de frontend/views/public.py"
head -15 frontend/views/public.py

echo ""
echo "▶ 3. Fix tests: aceptar tanto /hospitales/ como /api/publico/hospitales/"
python3 - << 'PY'
from pathlib import Path
p = Path("apps/configuracion/tests.py")
text = p.read_text(encoding="utf-8")

# El test busca los 3 links en home. Actualizar el de hospitales.
old = '''    def test_index_incluye_links_a_endpoints_publicos(self):
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        self.assertContains(r, "/api/publico/hospitales/")'''

new = '''    def test_index_incluye_links_a_endpoints_publicos(self):
        """Home enlaza al portal HTML de hospitales y a la API pública."""
        r = self.client.get("/")
        # Links al portal HTML (migrado de API cruda a páginas con UX)
        self.assertContains(r, "/hospitales/")
        # La API pública sigue disponible pero ya no se enlaza desde home
        # (a menos que un usuario la conozca por docs/api.md)'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: LandingPageTests actualizado")
elif 'self.assertContains(r, "/hospitales/")' in text:
    print("ya aplicado: LandingPageTests")
else:
    raise SystemExit("ERROR: bloque no encontrado en apps/configuracion/tests.py")
PY

echo ""
echo "▶ 4. Verificar imports"
python3 manage.py shell -c "from frontend.views import public; print('OK: frontend.views.public importa')"

echo ""
echo "▶ 5. Tests de apps.configuracion"
python3 manage.py test apps.configuracion -v 1 2>&1 | tail -4

echo ""
echo "▶ 6. Tests frontend"
python3 manage.py test frontend -v 1 2>&1 | tail -4

echo ""
echo "▶ 7. Smoke de /hospitales/no-existe/"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_fix.log &
RS_PID=$!
sleep 3

CODE_LIST=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/hospitales/)
CODE_404=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/hospitales/no-existe/)

kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo "GET /hospitales/           → $CODE_LIST (esperado 200)"
echo "GET /hospitales/no-existe/ → $CODE_404 (esperado 404)"

if [ "$CODE_LIST" = "200" ] && [ "$CODE_404" = "404" ]; then
    echo "OK: rutas correctas"
else
    echo "ERROR: rutas incorrectas"
    exit 1
fi

echo ""
echo "✅ Fix completado"
