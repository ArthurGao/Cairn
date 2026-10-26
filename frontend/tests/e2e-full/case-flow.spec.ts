import path from "node:path";

import { expect, test } from "@playwright/test";

import { API } from "./api";

const SAMPLE = process.env.E2E_SAMPLE_DIR ?? "";
const FILES = [
  "questionnaire.pdf",
  "employer-letter.pdf",
  "application-form.pdf",
  "tenancy.pdf",
  "cover-letter.pdf",
  "passport-scan.png",
  "unreadable-photo.jpg",
];

test("upload → consistency check → review → sign-off, with real file effects", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.goto("/cases");
  await expect(page.getByTestId("health-badge")).toHaveText("API healthy");
  await page.getByLabel("Label").fill("E2E sample");
  await page.getByRole("button", { name: "Create case" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("E2E sample");
  const caseId = page.url().split("/").pop() ?? "";

  await page.getByTestId("file-input").setInputFiles(FILES.map((f) => path.join(SAMPLE, f)));
  await expect(page.getByTestId("document-row")).toHaveCount(7);

  await page.getByRole("button", { name: "Run consistency check" }).click();
  await expect(page.getByTestId("conflict")).toHaveCount(2, { timeout: 60_000 });
  await expect(page.getByTestId("gap")).toHaveCount(1);
  await expect(page.getByTestId("coverage")).toContainText("documents7");
  await expect(page.getByTestId("conflict").nth(1)).toContainText("found by rule + model");

  await page.getByLabel("Your name (recorded with every review)").fill("E2E Adviser");
  await page.getByTestId("conflict").nth(0).getByRole("button", { name: "Dismiss" }).click();
  await page.getByRole("dialog").getByLabel("Note (required)").fill("Tenancy began after the move");
  await page.getByRole("dialog").getByRole("button", { name: "Dismissed" }).click();
  await expect(page.getByTestId("review-c1")).toHaveText("Dismissed — Tenancy began after the move");
  for (const finding of ["c2", "g1"]) {
    const card = page.getByTestId(`review-${finding}`).locator("xpath=../..");
    await card.getByRole("button", { name: "Confirm" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Confirmed" }).click();
    await expect(page.getByTestId(`review-${finding}`)).toHaveText("Confirmed");
  }
  await expect(page.getByTestId("blockers")).toHaveText("Every finding is settled.");
  await page.getByRole("button", { name: "Sign off" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Sign off" }).click();
  await expect(page.getByTestId("signoff")).toContainText("Signed off by E2E Adviser");

  const checkId = page.url().split("/").pop() ?? "";
  const view = await (await request.get(`${API}/api/cases/${caseId}/checks/${checkId}`)).json();
  expect(view.review).toEqual({ c1: "dismissed", c2: "confirmed", g1: "confirmed" });
  expect(view.blockers).toEqual([]);
  expect(view.signed_off.adviser).toBe("E2E Adviser");
  expect(view.result.conflicts.map((c: { fact_ids: string[] }) => c.fact_ids)).toEqual([
    ["f3", "f10", "f14"],
    ["f4", "f6", "f11"],
  ]);
});

test("pre-submission check: citations resolve against the uploaded documents", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("/cases");
  await page.getByLabel("Label").fill("E2E pre-submission");
  await page.getByRole("button", { name: "Create case" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("E2E pre-submission");
  await page.getByTestId("file-input").setInputFiles(FILES.map((f) => path.join(SAMPLE, f)));
  await expect(page.getByTestId("document-row")).toHaveCount(7);
  await page.getByRole("button", { name: "Run pre-submission check" }).click();
  await expect(page.getByRole("heading", { name: /^checked/ })).toHaveText("checked 3", { timeout: 60_000 });
  await expect(page.getByRole("heading", { name: /^pending/ })).toHaveText("pending 4");
  await expect(page.getByRole("heading", { name: /^unable/ })).toHaveText("unable 1");
  await page.getByRole("button", { name: /cover-letter\.pdf · p1/ }).click();
  await expect(page.getByTestId("citation-viewer").locator("mark")).toHaveText("Appendix 7 police certificate.");
});
