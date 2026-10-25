import { expect, test } from "@playwright/test";

import {
  CASE_ID,
  CHECK_ID,
  apiError,
  base,
  json,
  letterView,
  manifest,
  manifestWithLetter,
  result,
  view,
} from "./fixtures";

const CHECK_URL = `/cases/${CASE_ID}/checks/${CHECK_ID}`;
const CHECK_API = `**/api/cases/${CASE_ID}/checks/${CHECK_ID}`;

test.beforeEach(async ({ page }) => {
  await base(page);
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [] });
});

test("completed check: coverage, conflict with sources, gap, blockers", async ({ page }) => {
  await json(page, CHECK_API, view);
  await page.goto(CHECK_URL);
  const coverage = page.getByTestId("coverage");
  await expect(coverage.getByText("unreadable")).toBeVisible();
  await expect(coverage).toContainText("documents3");
  await expect(coverage).toContainText("facts2");
  const conflict = page.getByTestId("conflict");
  await expect(conflict).toHaveCount(1);
  await expect(conflict).toContainText("drafted by model");
  await expect(conflict).toContainText("found by rule + model");
  await expect(conflict.getByTestId("question")).toHaveText(result.conflicts[0].question);
  await expect(page.getByTestId("gap")).toContainText("unreadable-photo.jpg: 1 page(s) could not be read");
  await expect(page.getByTestId("blockers")).toHaveText("2 findings to settle: c1, g1");
  await page.getByLabel("Your name (recorded with every review)").fill("A. Adviser");
  await expect(page.getByRole("button", { name: "Sign off" })).toBeDisabled();  // blocked by c1, g1
});

test("citation opens the page with the quote highlighted", async ({ page }) => {
  await json(page, CHECK_API, view);
  await json(page, `**/api/cases/${CASE_ID}/documents/D2/pages/1`, {
    doc_id: "D2", page: 1, method: "text", source_sha256: "b", model: null, reason: null,
    text: "Alex Sample has been employed as Warehouse Supervisor\nsince 1 June 2022. Permanent.",
  });
  await page.goto(CHECK_URL);
  await page.getByRole("button", { name: "employer-letter.pdf · p1" }).click();
  const viewer = page.getByTestId("citation-viewer");
  await expect(viewer.getByRole("heading")).toHaveText("employer-letter.pdf · page 1");
  await expect(viewer.locator("mark")).toHaveText("since 1 June 2022");
});

test("dismissing needs a note; the review is sent with the adviser's name", async ({ page }) => {
  let reviewed = false;
  await page.route(CHECK_API, (route) =>
    route.fulfill({ json: reviewed ? { ...view, review: { c1: "dismissed" }, notes: { c1: "Date format only" }, blockers: ["g1"] } : view }),
  );
  await page.route(`${CHECK_API}/findings/c1/review`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({ action: "dismissed", note: "Date format only", adviser: "A. Adviser" });
    reviewed = true;
    await route.fulfill({ json: { at: "2026-10-24T04:00:00Z", check_id: CHECK_ID, finding_id: "c1", action: "dismissed", note: "Date format only", adviser: "A. Adviser" } });
  });
  await page.goto(CHECK_URL);
  await page.getByLabel("Your name (recorded with every review)").fill("A. Adviser");
  await page.getByTestId("conflict").getByRole("button", { name: "Dismiss" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Dismissed" })).toBeDisabled();
  await dialog.getByLabel("Note (required)").fill("Date format only");
  await dialog.getByRole("button", { name: "Dismissed" }).click();
  await expect(page.getByTestId("review-c1")).toHaveText("Dismissed — Date format only");
  await expect(page.getByTestId("blockers")).toHaveText("1 finding to settle: g1");
});

test("sign-off is allowed once everything is settled and is shown after", async ({ page }) => {
  let signed = false;
  await page.route(CHECK_API, (route) =>
    route.fulfill({
      json: { ...view, review: { c1: "confirmed", g1: "confirmed" }, blockers: [], signed_off: signed ? { adviser: "A. Adviser", at: "2026-10-24T04:30:00Z" } : null },
    }),
  );
  await page.route(`${CHECK_API}/signoff`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({ adviser: "A. Adviser" });
    signed = true;
    await route.fulfill({ json: { at: "2026-10-24T04:30:00Z", check_id: CHECK_ID, finding_id: null, action: "signed_off", note: null, adviser: "A. Adviser" } });
  });
  await page.goto(CHECK_URL);
  await page.getByLabel("Your name (recorded with every review)").fill("A. Adviser");
  await page.getByRole("button", { name: "Sign off" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Sign off" }).click();
  await expect(page.getByTestId("signoff")).toContainText("Signed off by A. Adviser on");
});

test("sign-off conflict from the API is shown in the dialog", async ({ page }) => {
  await json(page, CHECK_API, { ...view, review: { c1: "confirmed", g1: "confirmed" }, blockers: [] });
  await apiError(page, `${CHECK_API}/signoff`, 409, "signoff_blocked", "settle these findings first: g1");
  await page.goto(CHECK_URL);
  await page.getByLabel("Your name (recorded with every review)").fill("A. Adviser");
  await page.getByRole("button", { name: "Sign off" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Sign off" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveText("settle these findings first: g1");
});

test("a failed check says no findings were written", async ({ page }) => {
  await json(page, CHECK_API, { ...view, status: "failed", result: { ...result, status: "failed", conflicts: [], gaps: [], facts: [] }, error: "client data may only go to allow-listed vendors" });
  await page.goto(CHECK_URL);
  await expect(page.getByTestId("check-failed")).toHaveText("The check failed. No findings were written.client data may only go to allow-listed vendors");
  await expect(page.getByTestId("conflict")).toHaveCount(0);
});

test("pre-submission items grouped by status with downgrades explained", async ({ page }) => {
  const items = [
    { finding_id: "i1", item_id: "passport-present", status: "checked", finding: "Present", citations: [{ doc_id: "D1", page: 1, quote: "Full name" }], downgraded: null },
    { finding_id: "i2", item_id: "translations-present", status: "pending", finding: "All in English", citations: [], downgraded: "no_valid_citation" },
    { finding_id: "i3", item_id: "police-certificates", status: "unable", finding: "Not in the case", citations: [], downgraded: null },
  ] as const;
  await json(page, CHECK_API, {
    ...view,
    kind: "presubmission",
    blockers: ["i2", "i3", "g1"],
    result: { ...result, kind: "presubmission", checklist: { skill: "presubmission-aewv", version: "0.1-sample" }, conflicts: [], facts: [], items },
  });
  await page.goto(CHECK_URL);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Pre-submission checkpresubmission-aewv v0.1-sample");
  await expect(page.getByRole("heading", { name: /^pending/ })).toHaveText("pending 1");
  await expect(page.getByRole("heading", { name: /^unable/ })).toHaveText("unable 1");
  await expect(page.getByRole("heading", { name: /^checked/ })).toHaveText("checked 1");
  await expect(page.getByTestId("item").nth(0)).toContainText("Set to pending by code: marked checked without a source that could be verified.");
});

test("check load error shows the API message", async ({ page }) => {
  await apiError(page, CHECK_API, 503, "temporal_unavailable", "Temporal is unreachable at localhost:7233");
  await page.goto(CHECK_URL);
  await expect(page.getByTestId("error")).toHaveText("Could not load the check.Temporal is unreachable at localhost:7233");
});

test("INZ letter reply: deadline, concerns with evidence, unplaced passage, drafts", async ({ page }) => {
  await json(page, `**/api/cases/${CASE_ID}`, { manifest: manifestWithLetter, checks: [] });
  await json(page, CHECK_API, letterView);
  await page.goto(CHECK_URL);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("INZ letter replyppi-aewv.pdf");
  const deadline = page.getByTestId("deadline");
  await expect(deadline.getByTestId("deadline-date")).toHaveText("7 November 2026");
  await expect(deadline.getByTestId("working-days")).toHaveText(
    "9 working days left (Monday to Friday; public holidays not counted)",
  );
  await expect(deadline).toContainText("Read from the letter; the quoted words give this date.");
  await expect(deadline.getByRole("button", { name: "ppi-aewv.pdf · p2" })).toBeVisible();
  await expect(deadline.getByTestId("review-d1")).toHaveText("Not reviewed");
  const concerns = page.getByTestId("concern");
  await expect(concerns).toHaveCount(2);
  await expect(concerns.nth(0).getByTestId("evidence-status")).toHaveText("partly supported");
  await expect(concerns.nth(0)).toContainText("drafted by model");
  await expect(concerns.nth(0).getByRole("link", { name: "c2" })).toHaveAttribute("href", `/cases/${CASE_ID}/checks/01CONSISTENCY`);
  await expect(concerns.nth(0).getByTestId("client-request")).toHaveText("Payslips showing your first day");
  await expect(concerns.nth(1).getByTestId("evidence-status")).toHaveText("no evidence in the case");
  await expect(concerns.nth(1)).toContainText("Set by code: marked as supported without a source that could be verified.");
  await expect(page.getByTestId("unaccounted")).toContainText("“A. Officer, Immigration Officer”");
  await expect(page.getByTestId("client-email")).toHaveText("Hi,\n\n1. Payslips showing your first day\n2. Your police certificate\n");
  await expect(page.getByTestId("reply-outline")).toContainText("1. Start date with Example Freight Ltd differs");
  await expect(page.getByTestId("blockers")).toHaveText("5 findings to settle: d1, q1, q2, u1, g1");
});

test("INZ letter reply: an overdue or unverified deadline is flagged", async ({ page }) => {
  const letter = letterView.result!.letter!;
  await json(page, `**/api/cases/${CASE_ID}`, { manifest: manifestWithLetter, checks: [] });
  await json(page, CHECK_API, {
    ...letterView,
    deadline_working_days: -2,
    result: { ...letterView.result, letter: { ...letter, deadline: { ...letter.deadline, status: "unverified" } } },
  });
  await page.goto(CHECK_URL);
  await expect(page.getByTestId("working-days")).toContainText("2 working days overdue");
  await expect(page.getByTestId("deadline")).toContainText("The quoted words do not give this date. Read the letter.");
});
