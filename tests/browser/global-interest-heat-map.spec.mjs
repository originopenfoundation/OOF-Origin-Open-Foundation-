import { expect, test } from "@playwright/test";

const dataset = {
  schemaVersion: "1.1",
  algorithmVersion: "3.0",
  windowStart: "2026-09-16T09:40:24Z",
  windowEnd: "2026-09-30T09:40:24Z",
  generatedAt: "2026-09-30T09:40:24Z",
  lastCheckedAt: "2026-09-30T09:40:24Z",
  source: "Cloudflare Web Analytics",
  countries: [
    { iso: "SG", status: "very-high" },
    { iso: "SK", status: "high" },
    { iso: "US", status: "moderate" },
    { iso: "BR", status: "emerging" }
  ]
};

async function mockDataset(page, overrides = {}) {
  await page.route("**/data/oof-global-interest-heat-map.json", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ...dataset, ...overrides })
  }));
  await page.route("https://api.github.com/**", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ workflow_runs: [] })
  }));
}

test("desktop map supports all states, selection, zoom, reset and small countries", async ({ page }) => {
  const consoleErrors = [];
  page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
  await mockDataset(page);
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-globe.leaflet-container")).toBeVisible();
  await expect(page.getByText("Very High Interest", { exact: true })).toBeVisible();

  for (const [iso, status] of [["SG", "Very High Interest"], ["SK", "High Interest"], ["US", "Moderate Interest"], ["BR", "Emerging Interest"], ["CA", "Insufficient Signal"]]) {
    await page.locator("#global-interest-country-select").selectOption(iso);
    await expect(page.locator("#global-interest-country-status")).toContainText(status);
  }

  const zoomIn = page.getByRole("button", { name: "Zoom in" });
  await zoomIn.focus();
  await zoomIn.press("Enter");
  await page.getByRole("button", { name: "Reset map view" }).click();
  await expect(page.locator("#global-interest-country-name")).toHaveText("Select a country");
  expect(consoleErrors).toEqual([]);
});

test("mobile map has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockDataset(page);
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-globe.leaflet-container")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  await page.locator("#global-interest-country-select").selectOption("SG");
  await expect(page.locator("#global-interest-country-status")).toContainText("Very High Interest");
});

test("stale warning and geometry fallback remain non-destructive", async ({ page }) => {
  await mockDataset(page, { lastCheckedAt: "2020-01-01T00:00:00Z", generatedAt: "2020-01-01T00:00:00Z" });
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-stale-warning")).toBeVisible();

  const fallbackPage = await page.context().newPage();
  await mockDataset(fallbackPage);
  await fallbackPage.route("**/assets/data/ne_50m_admin_0_countries.geojson", route => route.abort());
  await fallbackPage.goto("/global-interest-heat-map.html");
  await expect(fallbackPage.locator("#global-interest-fallback")).toBeVisible();
  await expect(fallbackPage.locator("#global-interest-country-select")).toBeVisible();
});
