import { defineConfig, devices } from "@playwright/test";

// Mocked e2e: every /api/** call is routed in the test, so no backend is needed.
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  reporter: "list",
  use: { baseURL: "http://localhost:4710", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:4710",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
