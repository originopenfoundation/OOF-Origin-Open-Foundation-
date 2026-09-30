import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8770",
    headless: true
  },
  webServer: {
    command: "python -m http.server 8770 --bind 127.0.0.1",
    url: "http://127.0.0.1:8770/global-interest-heat-map.html",
    reuseExistingServer: true,
    timeout: 30000
  }
});
