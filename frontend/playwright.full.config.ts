import { defineConfig, devices } from "@playwright/test";

// Full e2e against the real stack (`make dev` with CAIRN_LLM_VENDOR=fake). Suite starts in M4.
export default defineConfig({
  testDir: "tests/e2e-full",
  reporter: "list",
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:4710" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
