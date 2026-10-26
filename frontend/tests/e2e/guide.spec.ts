import { type Page, expect, test } from "@playwright/test";

import { CASE_ID, CHECK_ID, base, brief, json, manifest, view } from "./fixtures";

// First-use hints (components/Guide.tsx): the next thing to click pulses with a label until it
// has been clicked once in this browser.

const CHECK_URL = `/cases/${CASE_ID}/checks/${CHECK_ID}`;
const active = (page: Page) => page.locator(".guide-on");

test.beforeEach(async ({ page }) => base(page));

test("case list: the oldest case is hinted, and the hint stops once it was clicked", async ({ page }) => {
  const row = (case_id: string, label: string) => ({
    case_id, label, created: manifest.created, data_class: "synthetic", documents: 3, checks: [],
  });
  await json(page, "**/api/cases", [row("NEWEST", "4 · Newest case"), row(CASE_ID, "1 · Oldest case")]);
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [brief] });
  await page.goto("/cases");
  await expect(active(page)).toHaveCount(1);
  await expect(active(page)).toHaveAttribute("data-guide", "cases.open");
  await expect(active(page)).toContainText("1 · Oldest case");
  await expect(active(page).getByTestId("guide-hint")).toHaveText("Start with this case");

  await page.getByRole("link", { name: "1 · Oldest case" }).click();
  await expect(page).toHaveURL(`/cases/${CASE_ID}`);
  await page.goto("/cases");
  await expect(page.getByTestId("case-row")).toHaveCount(2);
  await expect(page.locator('[data-guide="cases.open"]')).toHaveCount(2);
  await expect(active(page)).toHaveCount(0);
  await expect(page.getByTestId("guide-hint")).toHaveCount(0);
});

test("case page: the whole check row opens the check, counts included", async ({ page }) => {
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [brief] });
  await json(page, `**/api/cases/${CASE_ID}/checks/${CHECK_ID}`, view);
  await page.goto(`/cases/${CASE_ID}`);
  const checkRow = page.getByTestId("check-row");
  await expect(checkRow.getByTestId("guide-hint")).toHaveText("Open to see the findings");
  await expect(checkRow).toContainText("Open →");
  await checkRow.getByText("1 conflicts").click();
  await expect(page).toHaveURL(CHECK_URL);
});

test("check page: source, then review, then sign-off, one hint at a time", async ({ page }) => {
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [] });
  await json(page, `**/api/cases/${CASE_ID}/checks/${CHECK_ID}`, view);
  await json(page, `**/api/cases/${CASE_ID}/documents/D1/pages/2`, {
    doc_id: "D1", page: 2, method: "text", source_sha256: "a", model: null, reason: null, text: "page text",
  });
  await page.goto(CHECK_URL);
  await expect(active(page)).toHaveCount(1);
  await expect(active(page)).toHaveAttribute("data-guide", "check.source");
  await expect(active(page).getByTestId("guide-hint")).toHaveText("Click to see the page");

  await active(page).getByRole("button").click();
  await expect(active(page)).toHaveCount(1);
  await expect(active(page)).toHaveAttribute("data-guide", "check.review");
  await expect(active(page).getByTestId("guide-hint")).toHaveText("Confirm, dismiss or resolve");

  // Opening the dialog counts as having found the review buttons; cancelling changes nothing.
  await active(page).getByRole("button", { name: /^Confirm finding/ }).click();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(active(page)).toHaveAttribute("data-guide", "check.signoff");
  await expect(active(page).getByTestId("guide-hint")).toHaveText("Sign off when every finding is settled");

  await page.reload();
  await expect(page.getByTestId("conflict")).toHaveCount(1);
  await expect(active(page)).toHaveAttribute("data-guide", "check.signoff");
});
