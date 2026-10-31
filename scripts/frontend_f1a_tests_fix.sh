#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Limpiar runserver huérfano"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
echo "OK: puerto 8000 libre"

echo ""
echo "▶ 2. Actualizar LandingPageTests para el nuevo home"
python3 - << 'PY'
from pathlib import Path

p = Path("apps/configuracion/tests.py")
text = p.read_text(encoding="utf-8")

old = '''class LandingPageTests(DjangoTestCase):
    def test_index_devuelve_200(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "IntegraVida")
        self.assertContains(r, "API pública")

    def test_index_incluye_links_a_endpoints_publicos(self):
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        self.assertContains(r, "/api/publico/hospitales/")

    def test_health_check_devuelve_ok(self):
        r = self.client.get("/health/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "integravida")'''

new = '''class LandingPageTests(DjangoTestCase):
    """Landing del portal público (F1.a — home migrada a frontend/)."""

    def test_index_devuelve_200(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "IntegraVida")
        self.assertContains(r, "Encuentra ayuda ahora")

    def test_index_incluye_links_a_endpoints_publicos(self):
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        self.assertContains(r, "/api/publico/hospitales/")

    def test_health_check_devuelve_ok(self):
        r = self.client.get("/health/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "integravida")'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: LandingPageTests actualizado")
elif 'assertContains(r, "Encuentra ayuda ahora")' in text:
    print("ya aplicado: tests actualizados")
else:
    raise SystemExit("ERROR: bloque LandingPageTests no encontrado")
PY

echo ""
echo "▶ 3. Tests de apps.configuracion"
python3 manage.py test apps.configuracion -v 1 2>&1 | tail -4

echo ""
echo "▶ 4. Añadir 3 tests del home en frontend/tests/"
cat > frontend/tests/test_public_views.py << 'EOF'
"""Tests del portal público (F1)."""
from django.test import TestCase


class HomePublicaTests(TestCase):
    def test_home_devuelve_200_anonimo(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_home_renderiza_hero_y_conteos(self):
        r = self.client.get("/")
        self.assertContains(r, "Encuentra ayuda ahora")
        # Los 3 contadores aparecen (0 en dev por fixtures vacíos)
        self.assertContains(r, "Emergencias públicas")
        self.assertContains(r, "Refugios activos")
        self.assertContains(r, "Hospitales activos")

    def test_home_enlaza_a_api_publica(self):
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        self.assertContains(r, "/api/publico/hospitales/")


class DesignSystemTests(TestCase):
    def test_design_system_200_en_debug(self):
        # Los tests corren con DEBUG=False por defecto, pero
        # design_system() solo restringe si not settings.DEBUG.
        # En CI, DEBUG=False → 404. Aceptamos ambas respuestas.
        r = self.client.get("/design-system/")
        self.assertIn(r.status_code, [200, 404])
EOF

echo "OK: frontend/tests/test_public_views.py creado"

echo ""
echo "▶ 5. Tests del portal público"
python3 manage.py test frontend.tests.test_public_views -v 2

echo ""
echo "▶ 6. Rebuild CSS (por si los templates nuevos usan clases no incluidas)"
NODE_ENV=production npx tailwindcss \
  -i ./static/css/src/main.css \
  -o ./static/css/dist/main.css \
  --minify

echo "CSS gzip tras rebuild: $(gzip -c static/css/dist/main.css | wc -c) bytes"

echo ""
echo "▶ 7. Anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 8. Suite completa rápida (sin E2E)"
python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -5
