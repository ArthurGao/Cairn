import { expect, test } from "@playwright/test";

import { CASE_ID, apiError, base, brief, json, letterView, manifest, manifestWithLetter } from "./fixtures";

test.beforeEach(async ({ page }) => base(page));

test("case list: loading, then rows with counts", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/cases", async (route) => {
    await gate;
    await route.fulfill({
      json: [{ case_id: CASE_ID, label: "AEWV sample", created: manifest.created, data_class: "synthetic", documents: 3, checks: [brief] }],
    });
  });
  await page.goto("/cases");
  await expect(page.getByTestId("loading")).toHaveText("Loading cases…");
  release();
  await expect(page.getByTestId("case-row")).toHaveCount(1);
  const row = page.getByTestId("case-row");
  await expect(row.getByRole("link", { name: "AEWV sample" })).toBeVisible();
  await expect(row.getByLabel("Consistency check")).toHaveText("1 conflicts1 gaps");
  await expect(row.getByLabel("Pre-submission check")).toHaveText("Not run");
});

test("case list: empty and error are different things", async ({ page }) => {
  await json(page, "**/api/cases", []);
  await page.goto("/cases");
  await expect(page.getByTestId("empty")).toHaveText("No cases yet. Create one to upload documents and run a check.");
  await apiError(page, "**/api/cases", 503, "temporal_unavailable", "Temporal is unreachable at localhost:7233");
  await page.reload();
  await expect(page.getByTestId("error")).toHaveText("Could not load cases.Temporal is unreachable at localhost:7233");
});

test("creating a case opens it", async ({ page }) => {
  await json(page, "**/api/cases", []);
  await page.route("**/api/cases", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    expect(route.request().postDataJSON()).toEqual({ label: "New AEWV" });
    await route.fulfill({ status: 201, json: { case_id: CASE_ID } });
  });
  await json(page, `**/api/cases/${CASE_ID}`, { manifest: { ...manifest, label: "New AEWV", documents: [] }, checks: [] });
  await page.goto("/cases");
  await page.getByLabel("Label").fill("New AEWV");
  await page.getByRole("button", { name: "Create case" }).click();
  await expect(page).toHaveURL(`/cases/${CASE_ID}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("New AEWV");
  await expect(page.getByTestId("empty").first()).toHaveText("No documents yet. Upload PDFs, images, text or Markdown files.");
});

test("case page: documents with page methods and checks", async ({ page }) => {
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [brief] });
  await page.goto(`/cases/${CASE_ID}`);
  const rows = page.getByTestId("document-row");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText("p1 text");
  await expect(rows.nth(2)).toContainText("p1 unreadable");
  await expect(page.getByTestId("check-row")).toHaveCount(1);
  await expect(page.getByTestId("check-row")).toContainText("1 conflicts");
});

test("case page: upload sends multipart files and refreshes", async ({ page }) => {
  let uploaded = false;
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({ json: { manifest: uploaded ? manifest : { ...manifest, documents: [] }, checks: [] } }),
  );
  await page.route(`**/api/cases/${CASE_ID}/documents`, async (route) => {
    const body = route.request().postDataBuffer()?.toString() ?? "";
    expect(body).toContain('name="files"; filename="notes.md"');
    uploaded = true;
    await route.fulfill({ status: 201, json: [manifest.documents[0]] });
  });
  await page.goto(`/cases/${CASE_ID}`);
  await page.getByTestId("file-input").setInputFiles({ name: "notes.md", mimeType: "text/markdown", buffer: Buffer.from("# Notes") });
  await expect(page.getByRole("status").filter({ hasText: "Uploaded" })).toHaveText("Uploaded 1 file.");
  await expect(page.getByTestId("document-row")).toHaveCount(3);
});

test("case page: upload errors show the API message", async ({ page }) => {
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [] });
  await apiError(page, `**/api/cases/${CASE_ID}/documents`, 415, "unsupported_type", "x.exe: only PDF, PNG, JPEG, plain text and Markdown files are accepted");
  await page.goto(`/cases/${CASE_ID}`);
  await page.getByTestId("file-input").setInputFiles({ name: "x.exe", mimeType: "application/octet-stream", buffer: Buffer.from("MZ") });
  await expect(page.locator("main").getByRole("alert")).toHaveText("x.exe: only PDF, PNG, JPEG, plain text and Markdown files are accepted");
});

test("case page: starting a pre-submission check sends the chosen checklist", async ({ page }) => {
  await json(page, `**/api/cases/${CASE_ID}`, { manifest, checks: [] });
  await page.route(`**/api/cases/${CASE_ID}/checks`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({ kind: "presubmission", checklist_skill: "presubmission-aewv" });
    await route.fulfill({ status: 202, json: { check_id: "01NEW" } });
  });
  await json(page, `**/api/cases/${CASE_ID}/checks/01NEW`, {
    check_id: "01NEW",
    case_id: CASE_ID,
    kind: "presubmission",
    status: "running",
    state: { check_id: "01NEW", case_id: CASE_ID, kind: "presubmission", step: "checking", documents_total: 3, documents_done: 3, units_total: 2, units_done: 1, error: null },
    result: null,
    review: {},
    notes: {},
    blockers: [],
    signed_off: null,
    error: null,
  });
  await page.goto(`/cases/${CASE_ID}`);
  await page.getByRole("button", { name: "Run pre-submission check" }).click();
  await expect(page).toHaveURL(`/cases/${CASE_ID}/checks/01NEW`);
  await expect(page.getByTestId("progress")).toContainText("Running: checking");
  await expect(page.getByTestId("progress")).toContainText("documents 3/3 · units 1/2");
});

test("case page: missing case shows the API error", async ({ page }) => {
  await apiError(page, `**/api/cases/${CASE_ID}`, 404, "case_not_found", `case ${CASE_ID} does not exist`);
  await page.goto(`/cases/${CASE_ID}`);
  await expect(page.getByTestId("error")).toHaveText(`Could not load the case.case ${CASE_ID} does not exist`);
});

test("case page: an INZ letter is uploaded as such and a reply is prepared for it", async ({ page }) => {
  let uploaded = false;
  await page.route(`**/api/cases/${CASE_ID}`, (route) =>
    route.fulfill({ json: { manifest: uploaded ? manifestWithLetter : manifest, checks: [] } }),
  );
  await page.route(`**/api/cases/${CASE_ID}/documents`, async (route) => {
    const body = route.request().postDataBuffer()?.toString() ?? "";
    expect(body).toContain('name="files"; filename="ppi-aewv.pdf"');
    expect(body).toMatch(/name="source"\r\n\r\ninz\r\n/);
    uploaded = true;
    await route.fulfill({ status: 201, json: [manifestWithLetter.documents[3]] });
  });
  await page.route(`**/api/cases/${CASE_ID}/checks`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({ kind: "letter", letter_doc_id: "L1" });
    await route.fulfill({ status: 202, json: { check_id: "01NEW" } });
  });
  await json(page, `**/api/cases/${CASE_ID}/checks/01NEW`, { ...letterView, check_id: "01NEW", status: "running", result: null });
  await page.goto(`/cases/${CASE_ID}`);
  await expect(page.getByText("Upload an INZ letter to prepare a reply to it.")).toBeVisible();
  await page.getByTestId("letter-input").setInputFiles({ name: "ppi-aewv.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });
  await expect(page.getByTestId("document-row").nth(3)).toContainText("ppi-aewv.pdfINZ letter");
  await expect(page.getByLabel("Letter to reply to")).toHaveValue("L1");
  await page.getByRole("button", { name: "Prepare reply" }).click();
  await expect(page).toHaveURL(`/cases/${CASE_ID}/checks/01NEW`);
});

test("case page: a letter reply is listed with its concern counts", async ({ page }) => {
  const reply = {
    ...brief,
    kind: "letter" as const,
    letter_doc_id: "L1",
    counts: { ...brief.counts!, conflicts: 0, concerns: 3, not_supported: 2, gaps: 0 },
  };
  await json(page, `**/api/cases/${CASE_ID}`, { manifest: manifestWithLetter, checks: [reply] });
  await page.goto(`/cases/${CASE_ID}`);
  await expect(page.getByTestId("check-row")).toContainText("INZ letter reply");
  await expect(page.getByTestId("status-counts")).toHaveText("3 concerns2 not fully supported0 gaps");
});
