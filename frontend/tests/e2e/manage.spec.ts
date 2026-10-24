import { expect, test } from "@playwright/test";

import type { components } from "../../lib/api/schema";
import { apiError, base, json } from "./fixtures";

type S = components["schemas"];

const NOW = "2026-10-24T03:00:00Z";
const RUN_ID = "01RUN";
const breakdown: S["ContextBreakdown"] = {
  agents_md: 386,
  skill_index: 165,
  memory_index: 240,
  l0_total: 791,
  baseline_all: 1374,
  omitted_index_lines: 0,
};
const BEFORE = "---\nname: covering-note\n---\nList attachments.\n";
const AFTER = "---\nname: covering-note\n---\nList attachments.\nNumber them as Appendix 1..n.\n";
const change: S["ChangeEntry"] = {
  id: "CH1",
  op_id: "op1",
  group_id: "G1",
  at: NOW,
  actor: `run:${RUN_ID}`,
  op: "update",
  slug: "covering-note",
  before: BEFORE,
  after: AFTER,
  base_hash: "h",
  reason: "adviser asked for numbered appendices",
  undo_of: null,
};
const run: S["RunState"] = {
  run_id: RUN_ID,
  task: "Draft a covering note",
  status: "completed",
  error: null,
  started: NOW,
  context: breakdown,
  steps: [
    { n: 1, kind: "llm", role: "agent.main", tool: null, arg: null, result_chars: null, truncated: null, tokens_in: 1200, tokens_out: 40, tokens: null, model: "anthropic/claude-sonnet-5.5", at: NOW },
    { n: 2, kind: "tool", role: null, tool: "read_memory", arg: "covering-note", result_chars: 700, truncated: false, tokens_in: null, tokens_out: null, tokens: 200, model: null, at: NOW },
    { n: 3, kind: "llm", role: "agent.main", tool: null, arg: null, result_chars: null, truncated: null, tokens_in: 1500, tokens_out: 300, tokens: null, model: "anthropic/claude-sonnet-5.5", at: NOW },
  ],
  loaded: ["memory:covering-note"],
  loaded_tokens: 200,
  answer: "Covering note: Appendix 1 passport, Appendix 2 employer letter.",
  writeback: {
    applied: [{ change_id: "CH1", op: "update", slug: "covering-note", before: BEFORE, after: AFTER, undone: false }],
    rejected: [{ index: 1, slug: "client-phone", code: "personal_data", reason: "body contains a phone number" }],
    error: null,
  },
};

test.beforeEach(async ({ page }) => {
  await base(page);
});

test("runs: empty list, then starting a run opens its page", async ({ page }) => {
  await json(page, "**/api/runs", []);
  await page.route("**/api/runs", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    expect(route.request().postDataJSON()).toEqual({ task: "Draft a covering note" });
    await route.fulfill({ status: 202, json: { run_id: RUN_ID } });
  });
  await json(page, `**/api/runs/${RUN_ID}`, run);
  await page.goto("/manage/runs");
  await expect(page.getByText("No runs yet.")).toBeVisible();
  await page.getByLabel("Task").fill("Draft a covering note");
  await page.getByRole("button", { name: "Start run" }).click();
  await expect(page).toHaveURL(`/manage/runs/${RUN_ID}`);
});

test("runs: list rows and API error", async ({ page }) => {
  await json(page, "**/api/runs", [
    { run_id: RUN_ID, task: "Draft a covering note", status: "completed", started: NOW },
    { run_id: "02RUN", task: "", status: "failed", started: null },
  ]);
  await page.goto("/manage/runs");
  const rows = page.getByTestId("run-row");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText("Draft a covering note");
  await expect(rows.nth(0)).toContainText("completed");
  await expect(rows.nth(1)).toContainText("02RUN");
  await expect(rows.nth(1)).toContainText("failed");

  await apiError(page, "**/api/runs", 503, "temporal_unavailable", "Temporal is not reachable");
  await page.reload();
  await expect(page.getByTestId("error")).toContainText("Temporal is not reachable");
});

test("run: steps, tokens, answer, applied diff and rejected codes", async ({ page }) => {
  await json(page, `**/api/runs/${RUN_ID}`, run);
  await page.goto(`/manage/runs/${RUN_ID}`);
  await expect(page.getByTestId("run-status")).toHaveText("completed");
  const steps = page.getByTestId("step");
  await expect(steps).toHaveCount(3);
  await expect(steps.nth(0)).toContainText("1200→40");
  await expect(steps.nth(0)).toContainText("tokens reported by vendor");
  await expect(steps.nth(1)).toContainText("read_memory covering-note 700 chars, ~200 tokens");
  await expect(page.getByTestId("token-bar")).toContainText("loaded on demand 200");
  await expect(page.getByTestId("token-bar")).toContainText("used 991 of 1374 if everything were loaded (estimated)");
  await expect(page.getByTestId("answer")).toHaveText(run.answer!);
  const applied = page.getByTestId("applied");
  await expect(applied).toHaveCount(1);
  await expect(applied.getByTestId("op-diff")).toContainText("added: Number them as Appendix 1..n.");
  await expect(page.getByTestId("rejected")).toHaveText("client-phone personal_data body contains a phone number");
});

test("run: undo goes through the dialog and the change shows as undone", async ({ page }) => {
  let undone = false;
  await page.route(`**/api/runs/${RUN_ID}`, (route) =>
    route.fulfill({
      json: undone
        ? { ...run, writeback: { ...run.writeback!, applied: [{ ...run.writeback!.applied[0], undone: true }] } }
        : run,
    }),
  );
  await page.route("**/api/memory/changelog/CH1/undo", async (route) => {
    expect(route.request().method()).toBe("POST");
    undone = true;
    await route.fulfill({ json: [{ ...change, id: "CH2", undo_of: "CH1" }] });
  });
  await page.goto(`/manage/runs/${RUN_ID}`);
  await page.getByRole("button", { name: "Undo update of covering-note" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("The memory goes back to how it was before this run");
  await dialog.getByRole("button", { name: "Undo" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByTestId("applied")).toContainText("undone");
  expect(undone).toBe(true);
});

test("run: a failed run shows its error; a failed extraction is never 'nothing written'", async ({ page }) => {
  await json(page, `**/api/runs/${RUN_ID}`, {
    ...run,
    status: "completed",
    writeback: { applied: [], rejected: [], error: "memory extraction failed: schema" },
  });
  await page.goto(`/manage/runs/${RUN_ID}`);
  await expect(page.getByTestId("writeback").getByRole("alert")).toHaveText("memory extraction failed: schema");
  await expect(page.getByText("Nothing was written.")).toHaveCount(0);

  await json(page, `**/api/runs/${RUN_ID}`, { ...run, status: "failed", error: "max_steps reached", answer: null, writeback: null });
  await page.reload();
  await expect(page.getByTestId("run-status")).toHaveText("failed — max_steps reached");
  await expect(page.getByText("No answer.")).toBeVisible();
});

test("run: unknown run shows the API error", async ({ page }) => {
  await apiError(page, `**/api/runs/${RUN_ID}`, 404, "not_found", "no run 01RUN");
  await page.goto(`/manage/runs/${RUN_ID}`);
  await expect(page.getByTestId("error")).toContainText("no run 01RUN");
});

test("context: breakdown and the exact L0 prompt", async ({ page }) => {
  await json(page, "**/api/context/preview", { prompt: "# AGENTS.md\nBe precise.\n\n## Skills\n- presubmission-aewv", breakdown });
  await page.goto("/manage/context");
  await expect(page.getByTestId("token-bar")).toContainText("used 791 of 1374 if everything were loaded (estimated)");
  await expect(page.getByTestId("prompt")).toHaveText("# AGENTS.md\nBe precise.\n\n## Skills\n- presubmission-aewv");

  await apiError(page, "**/api/context/preview", 422, "context_budget", "L0 is 4100 tokens, over the 4000 budget");
  await page.reload();
  await expect(page.getByTestId("error")).toContainText("L0 is 4100 tokens, over the 4000 budget");
});

const memoryList: S["MemoryList"] = {
  entries: [
    { slug: "covering-note", title: "Covering note format", type: "feedback", description: "Number appendices", created: "2026-10-01", usage: { reads: 3, last_read: "2026-10-20", written_by_runs: 1 } },
    { slug: "aewv-threshold", title: "AEWV wage threshold", type: "reference", description: "Where to check the current rate", created: null, usage: { reads: 0, last_read: null, written_by_runs: 0 } },
    // Lint flags an invalid type; the list must still show the memory, not hide it.
    { slug: "loose-note", title: "Loose note", type: "notes", description: "Hand-written", created: null, usage: { reads: 0, last_read: null, written_by_runs: 0 } },
  ],
  budget: { tokens: 240, budget: 1500, over: false },
  broken: [],
};

test("memory: grouped by type with usage and budget; detail shows history and undo", async ({ page }) => {
  await json(page, "**/api/memory", memoryList);
  await json(page, "**/api/memory/covering-note", { slug: "covering-note", text: AFTER, body: "List attachments.\n", changelog: [change] });
  let undoCalls = 0;
  await page.route("**/api/memory/changelog/CH1/undo", async (route) => {
    undoCalls += 1;
    await route.fulfill({ json: [] });
  });
  await page.goto("/manage/memory");
  await expect(page.getByTestId("budget")).toHaveText("Index: 240 of 1500 tokens (estimated)");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(["feedback", "reference", "notes"]);
  const rows = page.getByTestId("memory-row");
  await expect(rows.nth(0)).toContainText("3 reads");
  await expect(rows.nth(1)).toContainText("never read");

  await rows.nth(0).getByRole("button").click();
  const detail = page.getByTestId("memory-detail");
  await expect(detail.getByRole("heading", { level: 2 })).toHaveText("covering-note.md");
  await expect(detail.getByTestId("history-entry")).toHaveCount(1);
  await detail.getByRole("button", { name: "Undo update CH1" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  expect(undoCalls).toBe(1);
});

test("memory: empty, over budget and error states", async ({ page }) => {
  await json(page, "**/api/memory", { entries: [], budget: { tokens: 0, budget: 1500, over: false }, broken: [] });
  await page.goto("/manage/memory");
  await expect(page.getByText("No memories yet. Runs write them back after validation.")).toBeVisible();

  await json(page, "**/api/memory", { ...memoryList, budget: { tokens: 1600, budget: 1500, over: true } });
  await page.reload();
  await expect(page.getByTestId("budget")).toHaveText("Index: 1600 of 1500 tokens (estimated) — over budget");

  await apiError(page, "**/api/memory", 500, "internal", "memory/MEMORY.md is unreadable");
  await page.reload();
  await expect(page.getByTestId("error")).toContainText("memory/MEMORY.md is unreadable");
});
