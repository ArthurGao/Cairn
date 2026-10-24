import { expect, test } from "@playwright/test";

const OK_BODY = {
  status: "ok",
  data_class: "synthetic",
  temporal: "ok",
  home: "../workspace",
  cases: "../.cases",
};

test("healthy API shows the badge and the synthetic-data banner", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({ json: OK_BODY }));
  await page.goto("/");
  await expect(page.getByTestId("health-badge")).toHaveText("API healthy");
  await expect(page.getByTestId("health-badge")).toHaveAttribute("data-state", "ok");
  await expect(page.getByTestId("data-class-banner")).toHaveText("Synthetic data only");
  await expect(page.getByTestId("health-detail")).toHaveCount(0);
});

test("client data class shows no synthetic banner", async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { ...OK_BODY, data_class: "client" } }),
  );
  await page.goto("/");
  await expect(page.getByTestId("health-badge")).toHaveText("API healthy");
  await expect(page.getByTestId("data-class-banner")).toHaveCount(0);
});

test("503 shows the API's message", async ({ page }) => {
  const message = "temporal: unreachable at localhost:7233 (connection refused)";
  await page.route("**/api/health", (route) =>
    route.fulfill({ status: 503, json: { error: { code: "unhealthy", message } } }),
  );
  await page.goto("/");
  await expect(page.getByTestId("health-badge")).toHaveText("API unhealthy");
  await expect(page.getByTestId("health-detail")).toHaveText(message);
  await expect(page.getByTestId("data-class-banner")).toHaveCount(0);
});

test("network failure shows API unreachable", async ({ page }) => {
  await page.route("**/api/health", (route) => route.abort("connectionrefused"));
  await page.goto("/");
  await expect(page.getByTestId("health-badge")).toHaveText("API unreachable");
  await expect(page.getByTestId("health-detail")).toHaveText("No response from http://localhost:4700");
});

test("shows a loading state until the first answer", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/health", async (route) => {
    await gate;
    await route.fulfill({ json: OK_BODY });
  });
  await page.goto("/");
  await expect(page.getByTestId("health-badge")).toHaveText("Checking API…");
  release();
  await expect(page.getByTestId("health-badge")).toHaveText("API healthy");
});
