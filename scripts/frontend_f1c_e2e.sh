#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Fix .gitignore — versionar static/*/dist/"
if ! grep -q '^!static/css/dist/' .gitignore 2>/dev/null; then
    cat >> .gitignore << 'EOF'

# Frontend — dist SÍ se versiona (deployment sin npm)
!static/css/dist/
!static/js/dist/
EOF
    echo "OK: .gitignore — dist versionado"
else
    echo "ya aplicado"
fi

echo ""
echo "▶ 2. Verificar que dist se puede versionar"
git add -n static/css/dist/main.css static/js/dist/main.js 2>&1 | head -3

echo ""
echo "▶ 3. Crear playwright.config.ts"
mkdir -p tests/e2e
cat > playwright.config.ts << 'EOF'
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: false,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'python3 manage.py runserver 0.0.0.0:8000 --noreload',
    url: 'http://localhost:8000/health/',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    stdout: 'pipe',
    stderr: 'pipe',
  },

  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      animations: 'disabled',
    },
  },
});
EOF

echo "OK: playwright.config.ts"

echo ""
echo "▶ 4. tests/e2e/offline.spec.ts (4 tests)"
cat > tests/e2e/offline.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';

/**
 * Verifica que el portal funciona SIN red externa (§11.5, §16).
 * Bloquea cualquier request fuera de localhost:8000 y 127.0.0.1:8000.
 * Si aparece un CDN, un font externo, un analytics, este test falla.
 */
test.describe('Portal público — offline (sin red externa)', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
        return route.continue();
      }
      // Bloquear cualquier dominio externo
      return route.abort();
    });
  });

  test('home renderiza offline con hero y conteos', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/IntegraVida/);
    await expect(page.locator('h1')).toContainText('Encuentra ayuda ahora');
    // Los 3 contadores aparecen (incluso si son 0)
    await expect(page.locator('text=Emergencias públicas')).toBeVisible();
    await expect(page.locator('text=Refugios activos')).toBeVisible();
    await expect(page.locator('text=Hospitales activos')).toBeVisible();
  });

  test('design-system renderiza offline con todos los componentes', async ({ page }) => {
    await page.goto('/design-system/');
    // Verifica que al menos un ejemplo de cada componente se renderiza
    await expect(page.locator('text=1. Botones')).toBeVisible();
    await expect(page.locator('text=5. Alerts')).toBeVisible();
    await expect(page.locator('.btn-primary').first()).toBeVisible();
    await expect(page.locator('.badge-success').first()).toBeVisible();
  });

  test('CSS y JS cargan desde /static/ local', async ({ page, request }) => {
    await page.goto('/');
    const cssResponse = await request.get('/static/css/dist/main.css');
    expect(cssResponse.status()).toBe(200);
    const jsResponse = await request.get('/static/js/dist/main.js');
    expect(jsResponse.status()).toBe(200);
    // El CSS no debe estar vacío
    const cssBody = await cssResponse.text();
    expect(cssBody.length).toBeGreaterThan(1000);
  });

  test('no hay requests externos en home', async ({ page }) => {
    const externalRequests: string[] = [];
    page.on('request', (req) => {
      const url = new URL(req.url());
      if (
        !url.hostname.includes('localhost') &&
        !url.hostname.includes('127.0.0.1') &&
        !url.protocol.startsWith('data:') &&
        !url.protocol.startsWith('blob:')
      ) {
        externalRequests.push(req.url());
      }
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    expect(externalRequests).toEqual([]);
  });
});
EOF

echo "OK: tests/e2e/offline.spec.ts"

echo ""
echo "▶ 5. tests/e2e/theme.spec.ts (3 tests)"
cat > tests/e2e/theme.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';

/**
 * Verifica modo claro/oscuro/sistema (§4.2).
 */
test.describe('Theme toggle — claro / oscuro / sistema', () => {
  test.beforeEach(async ({ page }) => {
    // Limpiar preferencias entre tests
    await page.addInitScript(() => {
      localStorage.removeItem('iv-theme');
    });
  });

  test('data-theme existe en <html> al cargar (anti-FOUC)', async ({ page }) => {
    await page.goto('/');
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(['light', 'dark']).toContain(theme);
  });

  test('ciclo light → dark → system persiste en localStorage', async ({ page }) => {
    await page.goto('/');

    const toggle = page.locator('[title*="Cambiar tema"]');
    await expect(toggle).toBeVisible();

    // Estado inicial: system (o el que detecte)
    let stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    // Puede ser null (system por defecto) o 'system'
    expect([null, 'system']).toContain(stored);

    // Click 1: pasa a 'light'
    await toggle.click();
    stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(stored).toBe('light');

    // Click 2: pasa a 'dark'
    await toggle.click();
    stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(stored).toBe('dark');

    // Click 3: vuelve a 'system'
    await toggle.click();
    stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(stored).toBe('system');
  });

  test('tema persiste tras recarga', async ({ page }) => {
    await page.goto('/');
    const toggle = page.locator('[title*="Cambiar tema"]');

    // Cambiar a dark
    await toggle.click();
    await toggle.click();

    // Verificar localStorage
    const before = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(before).toBe('dark');

    // Recargar
    await page.reload();

    // localStorage debe mantener 'dark'
    const after = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(after).toBe('dark');

    // data-theme debe ser 'dark'
    const dataTheme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(dataTheme).toBe('dark');
  });
});
EOF

echo "OK: tests/e2e/theme.spec.ts"

echo ""
echo "▶ 6. tests/e2e/snapshots.spec.ts (2 tests, baseline)"
cat > tests/e2e/snapshots.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';

/**
 * Snapshots visuales del portal (baseline).
 * Primera ejecución: crea baseline.
 * Ejecuciones siguientes: comparan con umbral 2% de diferencia.
 */
test.describe('Snapshots visuales — home', () => {
  test('home en tema claro', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('iv-theme', 'light');
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('home-light.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
    });
  });

  test('home en tema oscuro', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('iv-theme', 'dark');
    });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('home-dark.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
    });
  });
});
EOF

echo "OK: tests/e2e/snapshots.spec.ts"

echo ""
echo "▶ 7. scripts/run-e2e.sh (runner)"
cat > scripts/run-e2e.sh << 'EOF'
#!/usr/bin/env bash
# Runner de pruebas E2E. Arranca Django en background si no está,
# ejecuta Playwright, y limpia.
set -e
cd "$(dirname "$0")/.."

echo "▶ Ejecutando Playwright..."
if [ "$1" = "--update-snapshots" ]; then
    npx playwright test --update-snapshots
else
    npx playwright test
fi

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ E2E: TODOS LOS TESTS PASARON"
else
    echo "❌ E2E: ALGUNOS TESTS FALLARON (exit $EXIT_CODE)"
    echo ""
    echo "Ver reporte HTML:"
    echo "  npx playwright show-report"
fi
exit $EXIT_CODE
EOF
chmod +x scripts/run-e2e.sh

echo "OK: scripts/run-e2e.sh"

echo ""
echo "▶ 8. Package.json — añadir scripts de test:e2e"
python3 - << 'PY'
import json
from pathlib import Path
p = Path("package.json")
data = json.loads(p.read_text(encoding="utf-8"))
scripts = data.get("scripts", {})
scripts["test:e2e"] = "playwright test"
scripts["test:e2e:update"] = "playwright test --update-snapshots"
scripts["test:e2e:report"] = "playwright show-report"
data["scripts"] = scripts
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("OK: scripts test:e2e añadidos")
PY

echo ""
echo "▶ 9. Anti-CDN sobre la suite E2E"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 10. Verificar config TypeScript (sintaxis)"
npx tsc --noEmit --project . 2>&1 | head -10 || \
  echo "NOTA: tsc no instalado, Playwright usa transpilación interna"

echo ""
echo "✅ F1.c setup listo."
echo ""
echo "Siguiente paso (manual):"
echo "  bash scripts/run-e2e.sh --update-snapshots   # primera vez (genera baselines)"
echo "  bash scripts/run-e2e.sh                     # siguientes veces (compara)"
