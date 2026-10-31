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
