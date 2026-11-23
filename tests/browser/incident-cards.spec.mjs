import { expect, test } from '@playwright/test';

for (const width of [320, 360, 375, 390, 430, 1440]) {
  test(`incident card stays readable and interactive at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/ai-incidents/');
    const card = page.locator('.oof-incident-row').first();
    await expect(card).toBeVisible();
    await expect(card.getByRole('heading', { name: 'Analytical Insight' })).toBeVisible();
    await expect(card.getByRole('heading', { name: 'Relevant Architecture' })).toBeVisible();
    const geometry = await card.evaluate((node) => {
      const status = node.querySelector('.oof-incident-card-status').getBoundingClientRect();
      const architecture = node.querySelector('.oof-card-architecture-block').getBoundingClientRect();
      return { statusBottom: status.bottom, architectureTop: architecture.top,
        pageWidth: document.documentElement.scrollWidth, viewportWidth: innerWidth };
    });
    expect(geometry.statusBottom).toBeLessThanOrEqual(geometry.architectureTop);
    expect(geometry.pageWidth).toBeLessThanOrEqual(geometry.viewportWidth);
    const analysis = card.getByRole('button', { name: 'Analysis' });
    await analysis.focus();
    await page.keyboard.press('Enter');
    await expect(analysis).toHaveAttribute('aria-expanded', 'true');
    await expect(card.getByText('Observed event', { exact: true })).toBeVisible();
    const prevention = card.getByRole('button', { name: 'Prevention' });
    await prevention.click();
    await expect(analysis).toHaveAttribute('aria-expanded', 'false');
    await expect(card.getByText('Preventive control', { exact: true })).toBeVisible();
    const verification = card.getByRole('button', { name: 'Verification' });
    await verification.click();
    await expect(card.getByRole('link', { name: 'Help verify / Submit evidence' })).toBeVisible();
    await verification.click();
    await expect(verification).toHaveAttribute('aria-expanded', 'false');
    await expect(card.getByRole('link', { name: 'Full Case' })).toHaveAttribute('href', /\/ai-incidents\/incidents\//);
  });
}

test('an unavailable analysis is neutral and does not claim an architecture', async ({ page }) => {
  await page.goto('/ai-incidents/?q=OOF-AII-233233');
  const card = page.locator('.oof-incident-row').first();
  await expect(card).toContainText('OOF-AII-233233');
  await expect(card).toContainText('Analysis is not available for this record.');
  await expect(card).not.toContainText('Candidate applicability');
});
