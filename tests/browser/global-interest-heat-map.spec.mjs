import { expect, test } from "@playwright/test";

const dataset = {
  schemaVersion: "1.3",
  algorithmVersion: "3.2",
  windowStart: "2026-09-16T09:40:24Z",
  windowEnd: "2026-09-30T09:40:24Z",
  generatedAt: "2026-09-30T09:40:24Z",
  lastCheckedAt: "2026-09-30T09:40:24Z",
  lastSuccessfulCloudflareRetrievalAt: "2026-09-30T09:40:24Z",
  lastSuccessfulDatasetGenerationAt: "2026-09-30T09:40:24Z",
  lastSuccessfulDatasetPublicationAt: "2026-09-30T09:40:24Z",
  source: "Cloudflare Web Analytics",
  trafficViews: {
    raw: {
      status: "available",
      label: "Raw Traffic Map",
      countryData: "countries",
      classificationVersion: "raw-1.0",
      description: "All recorded aggregate visits in the governed observation window, including automated and unknown traffic."
    },
    qualityAdjusted: {
      status: "unavailable",
      label: "Quality-Adjusted Traffic Map",
      classificationVersion: "quality-adjusted-1.0",
      reason: "Unavailable pending sufficient documented evidence to identify automated traffic without country, browser, operating-system, referrer, or single-page assumptions."
    }
  },
  countries: [
    { iso: "SG", status: "very-high" },
    { iso: "SK", status: "high" },
    { iso: "US", status: "moderate" },
    { iso: "BR", status: "emerging" }
  ]
};

async function mockDataset(page, overrides = {}) {
  // Map smoke tests run on localhost, which must not send production analytics.
  await page.route("**/assets/data/oof-analytics-config.json", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ enabled: false })
  }));
  await page.route("**/_lara/status", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ model_availability: "unavailable" })
  }));
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
  const applicationErrors = [];
  const mapFailures = [];
  const analyticsRequests = [];
  page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", error => applicationErrors.push(error.message));
  page.on("response", response => {
    if (response.status() >= 400 && /(?:oof-global-interest-heat-map|ne_50m_admin_0_countries)/.test(response.url())) mapFailures.push(response.status());
  });
  page.on("request", request => { if (request.url().includes("/_oof/analytics/event")) analyticsRequests.push(request.url()); });
  await mockDataset(page);
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-globe.leaflet-container")).toBeVisible();
  await expect(page.getByText("High Interest", { exact: true })).toBeVisible();

  for (const [iso, status] of [["SG", "High Interest"], ["SK", "High Interest"], ["US", "Moderate Interest"], ["BR", "Emerging Interest"], ["CA", "Insufficient Signal"]]) {
    await page.locator("#global-interest-country-select").selectOption(iso);
    await expect(page.locator("#global-interest-country-status")).toContainText(status);
  }

  const zoomIn = page.getByRole("button", { name: "Zoom in" });
  await zoomIn.focus();
  await zoomIn.press("Enter");
  await page.getByRole("button", { name: "Reset map view" }).click();
  await expect(page.locator("#global-interest-country-name")).toHaveText("Select a country");
  expect(consoleErrors).toEqual([]);
  expect(applicationErrors).toEqual([]);
  expect(mapFailures).toEqual([]);
  expect(analyticsRequests).toEqual([]);
});

test("a genuine map script exception remains detectable", async ({ page }) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await mockDataset(page);
  await page.route("**/assets/js/oof-global-interest-heat-map.js?*", route => route.fulfill({
    status: 200, contentType: "application/javascript", body: 'throw new Error("simulated map failure");'
  }));
  await page.goto("/global-interest-heat-map.html");
  await expect.poll(() => errors).toContain("simulated map failure");
  await expect(page.locator("#global-interest-globe.leaflet-container")).toHaveCount(0);
});

test("a first-party map script failure remains detectable", async ({ page }) => {
  const failures = [];
  page.on("response", response => {
    if (response.url().includes("oof-global-interest-heat-map.js") && response.status() >= 400) failures.push(response.status());
  });
  await mockDataset(page);
  await page.route("**/assets/js/oof-global-interest-heat-map.js?*", route => route.fulfill({status: 503, body: "unavailable"}));
  await page.goto("/global-interest-heat-map.html");
  await expect.poll(() => failures).toContain(503);
  await expect(page.locator("#global-interest-globe.leaflet-container")).toHaveCount(0);
});

test("seven-day dataset presents four distinct categories", async ({ page }) => {
  await mockDataset(page, { algorithmVersion: "4.0", windowStart: "2026-09-23T00:00:00Z", windowEnd: "2026-09-30T00:00:00Z" });
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-very-high")).toBeVisible();
  await expect(page.locator("#global-interest-window")).toContainText("Rolling 7 days");
  for (const [iso, status] of [["SG", "Very High Interest"], ["SK", "High Interest"], ["US", "Moderate Interest"], ["BR", "Emerging Interest"]]) {
    await page.locator("#global-interest-country-select").selectOption(iso);
    await expect(page.locator("#global-interest-country-status")).toContainText(status);
  }
  const colors = await page.locator("#global-interest-country-list .oof-global-interest-country-swatch").evaluateAll(nodes => nodes.map(node => getComputedStyle(node).backgroundColor));
  expect(new Set(colors).size).toBe(4);
});

test("quality-adjusted view does not reuse raw country classifications without evidence", async ({ page }) => {
  await mockDataset(page);
  await page.goto("/global-interest-heat-map.html");
  await page.getByRole("button", { name: "Quality-Adjusted Traffic Map" }).click();
  await expect(page.locator("#global-interest-view-notice")).toContainText("Unavailable pending sufficient documented evidence");
  await expect(page.locator("#global-interest-country-list")).toContainText("Quality-Adjusted View Temporarily Unavailable");
  await expect(page.locator("#global-interest-country-list")).not.toContainText("No countries have a sufficient public signal");
  await page.locator("#global-interest-country-select").selectOption("SG");
  await expect(page.locator("#global-interest-country-status")).toContainText("unavailable pending sufficient documented evidence");
});

test("public country overview groups countries by interest classification and uses concise country names", async ({ page }) => {
  await mockDataset(page, {
    countries: [
      { iso: "CN", status: "emerging" },
      { iso: "SG", status: "very-high" },
      { iso: "SK", status: "high" },
      { iso: "US", status: "emerging" }
    ]
  });
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-country-list")).toHaveText(/Singapore[\s\S]*Slovakia[\s\S]*China[\s\S]*USA/);
  await expect(page.locator("#global-interest-country-list")).not.toContainText("People's Republic of China");
});

test("mobile map has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockDataset(page);
  await page.goto("/global-interest-heat-map.html");
  await expect(page.locator("#global-interest-globe.leaflet-container")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  await page.locator("#global-interest-country-select").selectOption("SG");
  await expect(page.locator("#global-interest-country-status")).toContainText("High Interest");
});

for (const width of [320, 375, 390, 430, 768, 1440]) {
  test(`world overview and assistant stay usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({width, height: 850});
    await mockDataset(page, {algorithmVersion: "4.0", windowStart: "2026-09-23T00:00:00Z", windowEnd: "2026-09-30T00:00:00Z"});
    await page.goto("/global-interest-heat-map.html");
    const map = page.locator("#global-interest-globe.leaflet-container");
    await expect(map).toBeVisible();
    await expect(page.locator(".oof-global-interest-assistant-dock #lara-root")).toBeAttached();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    const positions = await page.evaluate(() => {
      const bounds = document.querySelector("#global-interest-globe").getBoundingClientRect();
      return [...document.querySelectorAll(".oof-country-label-marker")].filter(node => ["USA", "Brazil"].includes(node.textContent.trim())).map(node => {
        const label = node.getBoundingClientRect();
        return {text: node.textContent.trim(), visible: label.right > bounds.left && label.left < bounds.right};
      });
    });
    expect(positions.find(item => item.text === "USA")?.visible).toBe(true);
    expect(positions.find(item => item.text === "Brazil")?.visible).toBe(true);
    const lara = page.locator(".oof-global-interest-assistant-dock #lara-root");
    await expect(lara).toHaveCSS("position", "static");
    await lara.locator(".lara-launch").click();
    await expect(lara.locator(".lara-panel.is-open")).toBeVisible();
    await lara.locator(".lara-close").click();
    await expect(lara.locator(".lara-panel.is-open")).toHaveCount(0);
  });
}

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
  await fallbackPage.locator("#global-interest-country-select").selectOption("SG");
  await expect(fallbackPage.locator("#global-interest-country-status")).toContainText("High Interest");
});
