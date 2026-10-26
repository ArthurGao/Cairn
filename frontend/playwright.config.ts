import { defineConfig, devices } from "@playwright/test";

import { GATE, GATE_API } from "./tests/e2e-gate/gate";

// Mocked e2e: every /api/** call is routed in the test, so no backend is needed. Project "gate"
// runs the sign-in gate (design §16.1) on a dev server of its own with DEMO_* set (own build dir,
// so it can run next to the usual one on 4710).
export default defineConfig({
  fullyParallel: true,
  reporter: "list",
  use: { trace: "retain-on-failure", ...devices["Desktop Chrome"] },
  projects: [
    { name: "chromium", testDir: "tests/e2e", use: { baseURL: "http://localhost:4710" } },
    { name: "gate", testDir: "tests/e2e-gate", use: { baseURL: "http://localhost:4711" } },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:4710",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "next dev -p 4711",
      url: "http://localhost:4711/login",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_DIST_DIR: ".next-gate",
        NEXT_PUBLIC_API_URL: GATE_API,
        DEMO_USER: GATE.user,
        DEMO_PASSWORD: GATE.password,
        SESSION_SECRET: GATE.secret,
      },
    },
  ],
});
