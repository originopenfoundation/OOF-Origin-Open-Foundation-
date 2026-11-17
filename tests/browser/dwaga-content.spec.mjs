import { expect, test } from '@playwright/test';

test('DWAGA index links to the canonical module sections', async ({ page }) => {
  await page.goto('/content/dwaga/dwaga-complete-index.html');
  await expect(page.getByRole('heading', { name: 'DWAGA™ Complete Standards & Modules Index', level: 1 })).toBeVisible();
  const link = page.getByRole('link', { name: 'RIBM — Representation & Interpretation Binding Module', exact: true });
  await expect(link).toHaveCount(1);
  await link.click();
  await expect(page).toHaveURL(/dwaga-dwhs\.html#module-ribm$/);
  await expect(page.locator('#module-ribm')).toBeVisible();
});

test('EGA index retains its module links and complete source', async ({ page }) => {
  await page.goto('/content/ega/ega-complete-index.html');
  await expect(page.locator('a[href*="#module-"]')).toHaveCount(65);
  await expect(page.locator('#ega-source-index')).toContainText('EGA™ consists of 13 Parent Standards and 65 Core Modules');
});

test('DWAGA index remains usable on a narrow mobile screen', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto('/content/dwaga/dwaga-complete-index.html');
  await expect(page.getByRole('link', { name: 'RIBM — Representation & Interpretation Binding Module', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});
