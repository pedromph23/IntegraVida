import { test, expect } from '@playwright/test';

/**
 * Verifica modo claro/oscuro/sistema (§4.2).
 *
 * Nota técnica: NO usamos `addInitScript` para limpiar localStorage en
 * el beforeEach, porque se dispararía también en el `page.reload()` del
 * test 9, borrando el valor que el test está tratando de verificar.
 * En su lugar, limpiamos explícitamente al inicio de cada test con una
 * navegación + evaluate + reload.
 */
test.describe('Theme toggle — claro / oscuro / sistema', () => {
  test.beforeEach(async ({ page }) => {
    // Estado limpio al inicio de cada test:
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('iv-theme'));
    await page.reload();
    // Esperar a que el script anti-FOUC haya aplicado data-theme
    await page.waitForFunction(() => {
      return document.documentElement.getAttribute('data-theme') !== null;
    });
  });

  test('data-theme existe en <html> al cargar (anti-FOUC)', async ({ page }) => {
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(['light', 'dark']).toContain(theme);
  });

  test('ciclo light → dark → system persiste en localStorage', async ({ page }) => {
    const toggle = page.locator('[title*="Cambiar tema"]');
    await expect(toggle).toBeVisible();

    // Estado inicial: null → system
    let stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect([null, 'system']).toContain(stored);

    // Click 1: system → light
    await toggle.click();
    stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(stored).toBe('light');

    // Click 2: light → dark
    await toggle.click();
    stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(stored).toBe('dark');

    // Click 3: dark → system
    await toggle.click();
    stored = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(stored).toBe('system');
  });

  test('tema persiste tras recarga', async ({ page }) => {
    const toggle = page.locator('[title*="Cambiar tema"]');

    // Ciclo: system → light → dark
    await toggle.click();
    await toggle.click();

    // Verificar localStorage antes de recargar
    const before = await page.evaluate(() => localStorage.getItem('iv-theme'));
    expect(before).toBe('dark');

    // Verificar data-theme antes de recargar
    const dataThemeBefore = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(dataThemeBefore).toBe('dark');

    // Recargar
    await page.reload();

    // Esperar a que el anti-FOUC aplique el tema guardado
    await page.waitForFunction(() => {
      return document.documentElement.getAttribute('data-theme') === 'dark';
    });

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
