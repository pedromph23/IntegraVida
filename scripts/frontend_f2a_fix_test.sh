#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Ajustar test_home_enlaza_a_api_publica"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/tests/test_public_views.py")
text = p.read_text(encoding="utf-8")

old = '''    def test_home_enlaza_a_api_publica(self):
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        self.assertContains(r, "/api/publico/hospitales/")'''

new = '''    def test_home_enlaza_a_api_publica(self):
        """Home enlaza a la API pública (emergencias, refugios) y al
        portal HTML de hospitales. Los tres coexisten porque la API
        sigue siendo el contrato (§api.md) y el portal HTML es UX."""
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/api/publico/refugios/")
        # Hospitales migró a portal HTML en F2.a
        self.assertContains(r, "/hospitales/")'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: test_home_enlaza_a_api_publica ajustado")
elif 'self.assertContains(r, "/hospitales/")' in text:
    print("ya aplicado: test_home_enlaza_a_api_publica")
else:
    raise SystemExit("ERROR: bloque no encontrado en test_public_views.py")
PY

echo ""
echo "▶ 2. Tests frontend (deben pasar los 22)"
python3 manage.py test frontend -v 1 2>&1 | tail -4

echo ""
echo "▶ 3. Suite backend completa para confirmar 55 verdes"
python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4

echo ""
echo "▶ 4. Anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "✅ Test fix completado"
