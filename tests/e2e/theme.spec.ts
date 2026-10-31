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
