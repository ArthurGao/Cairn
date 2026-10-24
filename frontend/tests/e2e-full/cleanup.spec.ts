import { expect, test } from "@playwright/test";

const API = "http://localhost:4700";
const STALE = "intake-form-v1-dates";

test("trigger → approve → archived, with real file effects", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.goto("/manage/cleanup");
  // The worker creates the schedule at startup; retry until it exists.
  await expect(async () => {
    await page.getByRole("button", { name: "Run cleanup now" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Cleanup started." })).toBeVisible({ timeout: 1000 });
  }).toPass({ timeout: 30_000 });
  const row = page.getByTestId("cleanup-row").first();
  await expect(async () => {
    await page.reload();
    await expect(row).toContainText("awaiting review", { timeout: 1000 });
  }).toPass({ timeout: 60_000 });

  await row.getByRole("link").click();
  await expect(page.getByTestId("cleanup-status")).toContainText("awaiting review");
  await expect(page.getByTestId("change").filter({ hasText: "Merge conflicts-as-questions" })).toContainText(
    "drafted by model",
  );
  await page.getByLabel(`Archive ${STALE}`).check();
  await page.getByLabel("Your name (recorded with the decision)").fill("E2E Adviser");
  await page.getByRole("button", { name: "Approve selected (1)" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Approve" }).click();
  await expect(page.getByTestId("cleanup-status")).toHaveText("applied", { timeout: 30_000 });
  await expect(page.getByTestId("change").filter({ hasText: `Archive ${STALE}` })).toContainText("applied");

  const memory = (await (await request.get(`${API}/api/memory`)).json()) as { entries: { slug: string }[] };
  const slugs = memory.entries.map((e) => e.slug);
  expect(slugs).not.toContain(STALE);
  expect(slugs).toContain("neutral-wording-for-discrepancies"); // the merge was not approved
  const log = (await (await request.get(`${API}/api/memory/changelog?limit=500`)).json()) as {
    op: string;
    slug: string;
    actor: string;
  }[];
  expect(log.filter((e) => e.slug === STALE).map((e) => [e.op, e.actor.split(":")[0]])).toEqual([["archive", "cleanup"]]);
});
