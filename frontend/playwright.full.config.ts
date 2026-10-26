import { defineConfig, devices } from "@playwright/test";

// Full e2e against the real stack: `make e2e-full` (dev servers, fake LLM vendor), or the demo
// stack behind Caddy (`make rehearse`), which sets the gate's credentials and serves
// https://localhost with Caddy's local CA.
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:4710";
const username = process.env.DEMO_USER;

export default defineConfig({
  testDir: "tests/e2e-full",
  reporter: "list",
  use: {
    baseURL,
    ...(username ? { httpCredentials: { username, password: process.env.DEMO_PASSWORD ?? "" } } : {}),
    ignoreHTTPSErrors: baseURL.startsWith("https://localhost"),
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
