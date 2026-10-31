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
