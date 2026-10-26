import { type Page, type Request, expect, test } from "@playwright/test";

import { health } from "../e2e/fixtures";
import { GATE, GATE_API as API } from "./gate";

const BASIC = `Basic ${Buffer.from(`${GATE.user}:${GATE.password}`).toString("base64")}`;

/** Mocks the API; returns every request it saw so tests can check the credential sent. */
async function mockApi(page: Page, status = 200): Promise<Request[]> {
  const seen: Request[] = [];
  await page.route(`${API}/**`, (route) => {
    seen.push(route.request());
    if (status !== 200) return route.fulfill({ status, json: { error: { code: "unauthorized", message: "no" } } });
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({ json: path === "/api/health" ? health : [] });
  });
  return seen;
}

async function signIn(page: Page, user: string, password: string) {
  await page.getByLabel("Username").fill(user);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("a page without a session goes to /login, which calls no API", async ({ page }) => {
  const seen = await mockApi(page);
  await page.goto("/cases/01CASE");
  await expect(page).toHaveURL("/login?next=%2Fcases%2F01CASE");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);
  expect(seen.map((r) => r.url())).toEqual([]);
});

test("a wrong password is refused and sets no session", async ({ page, context }) => {
  await mockApi(page);
  await page.goto("/login");
  await signIn(page, GATE.user, "wrong");
  await expect(page.getByTestId("login-error")).toHaveText("Wrong username or password.");
  await expect(page).toHaveURL("/login");
  expect((await context.cookies()).map((c) => c.name)).not.toContain("cairn_session");
});

test("the right password opens the app, and every API call carries the credential", async ({ page, context }) => {
  const seen = await mockApi(page);
  await page.goto("/cases");
  await signIn(page, GATE.user, GATE.password);
  await expect(page).toHaveURL("/cases");
  await expect(page.getByTestId("health-badge")).toHaveText("API healthy");
  const session = (await context.cookies()).find((c) => c.name === "cairn_session");
  expect(session?.httpOnly).toBe(true);
  expect(seen.length).toBeGreaterThan(0);
  expect(new Set(seen.map((r) => r.headers()["authorization"]))).toEqual(new Set([BASIC]));
});

test("signing out ends the session", async ({ page }) => {
  await mockApi(page);
  await page.goto("/login");
  await signIn(page, GATE.user, GATE.password);
  await expect(page).toHaveURL("/cases");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/login");
  await page.goto("/manage/runs");
  await expect(page).toHaveURL("/login?next=%2Fmanage%2Fruns");
});

test("an API 401 (stale credential) sends the user back to /login", async ({ page }) => {
  await mockApi(page, 401);
  await page.goto("/login");
  await signIn(page, GATE.user, GATE.password);
  await expect(page).toHaveURL(/\/login\?next=%2Fcases/);
});
