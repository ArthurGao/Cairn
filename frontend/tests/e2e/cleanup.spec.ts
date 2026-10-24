import { expect, test } from "@playwright/test";

import type { components } from "../../lib/api/schema";
import { apiError, base, json } from "./fixtures";

type S = components["schemas"];

const WF = "cleanup-2026-10-25T03:00:00Z";
const WF_API = `**/api/cleanup/${encodeURIComponent(WF)}`;
const WF_PAGE = `/manage/cleanup/${encodeURIComponent(WF)}`;
const STARTED = "2026-10-25T03:00:00Z";
const STALE_TEXT = "---\nname: intake-form-v1-dates\n---\n\nOld rule.\n";
const TARGET_BEFORE = "---\nname: conflicts-as-questions\n---\n\nAsk, never accuse.\n";
const TARGET_AFTER = "---\nname: conflicts-as-questions\n---\n\nAsk, never accuse.\nGive both sources.\n";
const MEMBER_TEXT = "---\nname: neutral-wording\n---\n\nNeutral questions.\n";

const changes: S["ProposedChange"][] = [
  {
    op_id: "archive:intake-form-v1-dates",
    kind: "archive",
    reason: "intake-form-v1-dates: last read 2026-04-02, 1 read(s)",
    changes: [{ slug: "intake-form-v1-dates", before: STALE_TEXT, after: null }],
    base_hashes: { "intake-form-v1-dates": "h1" },
  },
  {
    op_id: "merge:conflicts-as-questions",
    kind: "merge",
    reason: "merge of conflicts-as-questions, neutral-wording into conflicts-as-questions",
    changes: [
      { slug: "conflicts-as-questions", before: TARGET_BEFORE, after: TARGET_AFTER },
      { slug: "neutral-wording", before: MEMBER_TEXT, after: null },
    ],
    base_hashes: { "conflicts-as-questions": "h2", "neutral-wording": "h3" },
  },
];
const finding = (check: string, severity: S["Finding"]["severity"], message: string): S["Finding"] => ({
  check,
  severity,
  slugs: [],
  message,
  proposed: null,
  base_hashes: {},
});
const awaiting: S["CleanupState"] = {
  workflow_id: WF,
  status: "awaiting_review",
  started: STARTED,
  expires: new Date(Date.now() + (5 * 24 + 3) * 3_600_000 + 30_000).toISOString(),
  error: null,
  proposal: {
    findings: [finding("stale", "info", "intake-form-v1-dates: last read 2026-04-02"), finding("index_missing", "warn", "x.md is not in MEMORY.md")],
    changes,
    mechanical: ["chg_1"],
  },
  decision: null,
  outcome: null,
};

test.beforeEach(async ({ page }) => {
  await base(page);
});

test("cleanup list: rows with countdown, empty and error states", async ({ page }) => {
  await json(page, "**/api/cleanup", [
    { workflow_id: WF, status: "awaiting_review", started: STARTED, expires: awaiting.expires, changes: 2 },
    { workflow_id: "cleanup-2026-10-18T03:00:00Z", status: "expired", started: "2026-10-18T03:00:00Z", expires: null, changes: 1 },
  ]);
  await page.goto("/manage/cleanup");
  const rows = page.getByTestId("cleanup-row");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText("awaiting review");
  await expect(rows.nth(0)).toContainText("2 changes");
  await expect(rows.nth(0)).toContainText("5 days 3 h left");
  await expect(rows.nth(1)).toContainText("1 change");
  await expect(rows.nth(0).getByRole("link")).toHaveAttribute("href", WF_PAGE);

  await json(page, "**/api/cleanup", []);
  await page.reload();
  await expect(page.getByText("No cleanups yet.")).toBeVisible();

  await apiError(page, "**/api/cleanup", 503, "temporal_unavailable", "Temporal is unreachable");
  await page.reload();
  await expect(page.getByTestId("error")).toContainText("Temporal is unreachable");
});

test("run now: the new cleanup appears without a reload", async ({ page }) => {
  let listCalls = 0;
  let triggered = false;
  await page.route("**/api/cleanup", (route) => {
    listCalls += 1;
    // The schedule's run shows up a couple of list calls after the trigger, as with visibility lag.
    const show = triggered && listCalls >= 4;
    return route.fulfill({
      json: show ? [{ workflow_id: WF, status: "linting", started: STARTED, expires: null, changes: 0 }] : [],
    });
  });
  await page.route("**/api/cleanup/run", (route) => {
    triggered = true;
    listCalls = 1;
    return route.fulfill({ status: 202, json: { status: "accepted" } });
  });
  await page.goto("/manage/cleanup");
  await expect(page.getByText("No cleanups yet.")).toBeVisible();
  await page.getByRole("button", { name: "Run cleanup now" }).click();
  await expect(page.getByTestId("cleanup-row")).toContainText("linting", { timeout: 8000 });
});

test("run now: a running cleanup is refused with the API's reason", async ({ page }) => {
  await json(page, "**/api/cleanup", []);
  await apiError(page, "**/api/cleanup/run", 409, "cleanup_in_progress", `a cleanup is still running: ${WF}`);
  await page.goto("/manage/cleanup");
  await page.getByRole("button", { name: "Run cleanup now" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "still running" })).toHaveText(
    `a cleanup is still running: ${WF}`,
  );
});

test("proposal: diffs, findings, and approving only the selected change", async ({ page }) => {
  let decided: unknown = null;
  await page.route(WF_API, (route) =>
    route.fulfill({
      json: decided
        ? {
            ...awaiting,
            status: "applied",
            decision: decided,
            outcome: { applied: ["archive:intake-form-v1-dates"], rejected: [] },
          }
        : awaiting,
    }),
  );
  await page.route(`${WF_API}/review`, async (route) => {
    decided = route.request().postDataJSON();
    await route.fulfill({ status: 202, json: { status: "accepted" } });
  });
  await page.goto(WF_PAGE);
  await expect(page.getByTestId("cleanup-status")).toHaveText("awaiting review — 5 days 3 h left to review");
  const items = page.getByTestId("change");
  await expect(items).toHaveCount(2);
  await expect(items.nth(0)).toContainText("Moved to memory/_archive/ (restorable).");
  await expect(items.nth(1)).toContainText("drafted by model");
  await expect(items.nth(1).getByTestId("op-diff")).toContainText("added: Give both sources.");
  await expect(page.getByTestId("finding")).toHaveText([
    "info stale intake-form-v1-dates: last read 2026-04-02",
    "warn index_missing x.md is not in MEMORY.md",
  ]);
  await expect(page.getByTestId("mechanical")).toContainText("MEMORY.md was re-derived");

  const approve = page.getByRole("button", { name: /Approve selected/ });
  await expect(approve).toBeDisabled();
  await page.getByLabel("Archive intake-form-v1-dates").check();
  await expect(approve).toHaveText("Approve selected (1)");
  await expect(approve).toBeDisabled(); // no reviewer name yet
  await page.getByLabel("Your name (recorded with the decision)").fill("A. Adviser");
  await approve.click();
  await expect(page.getByRole("dialog")).toContainText("1 change will be written.");
  await page.getByRole("dialog").getByRole("button", { name: "Approve" }).click();

  await expect(page.getByTestId("cleanup-status")).toHaveText("applied");
  expect(decided).toEqual({ approved_op_ids: ["archive:intake-form-v1-dates"], reviewer: "A. Adviser", reviewer_note: "" });
  await expect(items.nth(0)).toContainText("applied");
  await expect(items.nth(1)).not.toContainText("applied");
  await expect(page.getByTestId("decision")).toHaveText("DecisionApproved 1 change by A. Adviser");
  await expect(page.getByTestId("review-panel")).toHaveCount(0);
});

test("reject all sends an empty decision", async ({ page }) => {
  let decided: unknown = null;
  await json(page, WF_API, awaiting);
  await page.route(`${WF_API}/review`, async (route) => {
    decided = route.request().postDataJSON();
    await route.fulfill({ status: 202, json: { status: "accepted" } });
  });
  await page.goto(WF_PAGE);
  await page.getByLabel("Your name (recorded with the decision)").fill("A. Adviser");
  await page.getByRole("button", { name: "Reject all" }).click();
  await expect(page.getByRole("dialog")).toContainText("Nothing will be written");
  await page.getByRole("dialog").getByRole("button", { name: "Reject all" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  expect(decided).toEqual({ approved_op_ids: [], reviewer: "A. Adviser", reviewer_note: "" });
});

test("a review the API refuses keeps the dialog open with its reason", async ({ page }) => {
  await json(page, WF_API, awaiting);
  await apiError(page, `${WF_API}/review`, 409, "not_awaiting_review", `cleanup ${WF} is expired, not awaiting review`);
  await page.goto(WF_PAGE);
  await page.getByLabel("Your name (recorded with the decision)").fill("A. Adviser");
  await page.getByRole("button", { name: "Reject all" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Reject all" }).click();
  await expect(page.getByRole("dialog")).toContainText("is expired, not awaiting review");
});

test("expired, rejected-on-apply and missing cleanups", async ({ page }) => {
  await json(page, WF_API, {
    ...awaiting,
    status: "applied",
    decision: { approved_op_ids: ["merge:conflicts-as-questions"], reviewer: "", reviewer_note: "" },
    outcome: { applied: [], rejected: [{ op_id: "merge:conflicts-as-questions", reason: "neutral-wording: the file changed" }] },
  });
  await page.goto(WF_PAGE);
  await expect(page.getByTestId("change").nth(1)).toContainText("rejected: neutral-wording: the file changed");
  await expect(page.getByTestId("review-panel")).toHaveCount(0);

  await json(page, WF_API, { ...awaiting, status: "expired" });
  await page.reload();
  await expect(page.getByTestId("cleanup-status")).toHaveText("expired");
  await expect(page.getByRole("checkbox")).toHaveCount(0);

  await apiError(page, WF_API, 404, "cleanup_not_found", `no cleanup ${WF}`);
  await page.reload();
  await expect(page.getByTestId("error")).toContainText(`no cleanup ${WF}`);
});

test("skills: by source with L1/L2 sizes and checklist items", async ({ page }) => {
  await json(page, "**/api/skills", [
    { name: "case-consistency-check", description: "Cross-check facts", source: "local", read_only: false, body_chars: 1200, references: [{ path: "references/fact-categories.md", chars: 900 }] },
    { name: "presubmission-aewv", description: "AEWV checklist", source: "local", read_only: false, body_chars: 800, references: [{ path: "references/checklist.yaml", chars: 2400 }] },
    { name: "team-style", description: "House style", source: "/mnt/shared-skills", read_only: true, body_chars: 300, references: [] },
  ]);
  await json(page, "**/api/checklists", [
    { skill: "presubmission-aewv", visa: "aewv", version: "0.1", owner: "senior adviser", error: null, items: [
      { id: "passport-valid", requirement: "Passport valid for the whole stay", verify: "dates" },
      { id: "job-offer", requirement: "Job offer from an accredited employer", verify: "letter" },
    ] },
  ]);
  await page.goto("/manage/skills");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(["Local", "/mnt/shared-skillsread-only mount"]);
  const skills = page.getByTestId("skill");
  await expect(skills).toHaveCount(3);
  await expect(skills.nth(0)).toContainText("L1 SKILL.md body 1200 chars");
  await expect(skills.nth(0)).toContainText("L2 references/fact-categories.md 900 chars");
  await expect(page.getByRole("list", { name: "presubmission-aewv checklist" }).getByRole("listitem")).toHaveText([
    "passport-valid Passport valid for the whole stay",
    "job-offer Job offer from an accredited employer",
  ]);

  await apiError(page, "**/api/skills", 500, "internal", "skills/ is unreadable");
  await page.reload();
  await expect(page.getByTestId("error")).toContainText("skills/ is unreadable");
});
