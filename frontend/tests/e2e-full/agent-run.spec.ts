import { expect, test } from "@playwright/test";

const API = "http://localhost:4700";

const slugs = async (request: import("@playwright/test").APIRequestContext) =>
  ((await (await request.get(`${API}/api/memory`)).json()).entries as { slug: string }[]).map((e) => e.slug);

test("run → validated write-back → undo, with real file effects", async ({ page, request }) => {
  test.setTimeout(120_000);
  expect(await slugs(request)).not.toContain("cover-note-dates");

  await page.goto("/manage/runs");
  await page
    .getByLabel("Task")
    .fill("Draft a short cover note for the AEWV synthetic case. Note: the adviser says always write dates as 24 October 2026 in cover notes.");
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(page.getByTestId("run-status")).toHaveText("completed", { timeout: 60_000 });
  await expect(page.getByTestId("step")).toHaveCount(3);
  await expect(page.getByTestId("step").nth(1)).toContainText("read_memory pilot-scope");
  await expect(page.getByTestId("answer")).toContainText("Draft cover note (AEWV, synthetic case)");
  const applied = page.getByTestId("applied");
  await expect(applied).toHaveCount(2);
  await expect(applied.getByRole("button")).toHaveText(["Undo", "Undo"]);
  await expect(applied.nth(0).getByRole("button")).toHaveAccessibleName("Undo create of cover-note-dates");
  await expect(applied.nth(1).getByRole("button")).toHaveAccessibleName("Undo update of pilot-scope");
  await expect(page.getByTestId("rejected")).toHaveText([
    /^questions-not-accusations duplicate/,
    /^client-contact personal_data/,
  ]);
  expect(await slugs(request)).toContain("cover-note-dates");

  await page.getByRole("button", { name: "Undo create of cover-note-dates" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Undo" }).click();
  await expect(applied.nth(0)).toContainText("undone");
  await expect(applied.nth(1).getByRole("button")).toHaveAccessibleName("Undo update of pilot-scope");
  // The created memory is archived, never deleted; the other op of the run stays applied.
  expect(await slugs(request)).not.toContain("cover-note-dates");
  expect(await slugs(request)).toContain("pilot-scope");
  const log = (await (await request.get(`${API}/api/memory/changelog?limit=500`)).json()) as {
    op: string;
    slug: string;
    undo_of: string | null;
  }[];
  expect(log.filter((e) => e.undo_of).map((e) => [e.op, e.slug])).toEqual([["archive", "cover-note-dates"]]);
});
