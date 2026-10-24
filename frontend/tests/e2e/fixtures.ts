import type { Page, Route } from "@playwright/test";

import type { components } from "../../lib/api/schema";

type S = components["schemas"];

export const CASE_ID = "01CASE";
export const CHECK_ID = "01CHECK";
const NOW = "2026-10-24T03:00:00Z";

export const health: S["HealthOk"] = {
  status: "ok",
  data_class: "synthetic",
  temporal: "ok",
  home: "../workspace",
  cases: "../.cases",
};

export const manifest: S["Manifest"] = {
  case_id: CASE_ID,
  label: "AEWV sample",
  created: NOW,
  data_class: "synthetic",
  documents: [
    {
      doc_id: "D1",
      filename: "questionnaire.pdf",
      stored_name: "D1.pdf",
      media_type: "application/pdf",
      bytes: 2100,
      sha256: "a",
      uploaded: NOW,
      status: "ingested",
      error: null,
      pages: [
        { n: 1, method: "text" },
        { n: 2, method: "text" },
      ],
    },
    {
      doc_id: "D2",
      filename: "employer-letter.pdf",
      stored_name: "D2.pdf",
      media_type: "application/pdf",
      bytes: 1600,
      sha256: "b",
      uploaded: NOW,
      status: "ingested",
      error: null,
      pages: [{ n: 1, method: "text" }],
    },
    {
      doc_id: "D3",
      filename: "unreadable-photo.jpg",
      stored_name: "D3.jpg",
      media_type: "image/jpeg",
      bytes: 30000,
      sha256: "c",
      uploaded: NOW,
      status: "ingested",
      error: null,
      pages: [{ n: 1, method: "unreadable" }],
    },
  ],
};

export const brief: S["CheckBrief"] = {
  check_id: CHECK_ID,
  kind: "consistency",
  checklist_skill: null,
  status: "completed",
  started: NOW,
  counts: { conflicts: 1, checked: 0, pending: 0, unable: 0, gaps: 1, clean: false },
  signed_off: null,
};

const fact = (fact_id: string, doc_id: string, page: number, value: string, quote: string): S["Fact"] => ({
  fact_id,
  doc_id,
  page,
  value,
  quote,
  category: "employment.period",
  subject: "applicant",
  qualifier: "Example Freight Ltd",
  normalised: value,
});

export const result: S["CheckResult"] = {
  check_id: CHECK_ID,
  case_id: CASE_ID,
  kind: "consistency",
  checklist: null,
  started: NOW,
  finished: NOW,
  status: "completed",
  error: null,
  coverage: {
    documents: 3,
    documents_failed: 0,
    pages: 4,
    pages_transcribed: 0,
    pages_unreadable: 1,
    facts_accepted: 2,
    facts_dropped: 0,
  },
  facts: [
    fact("f1", "D1", 2, "03/2022", "Start date: 03/2022"),
    fact("f2", "D2", 1, "since 1 June 2022", "since 1 June 2022"),
  ],
  conflicts: [
    {
      finding_id: "c1",
      fact_ids: ["f1", "f2"],
      origin: ["rule", "model"],
      summary: "Job start date differs",
      question: "The questionnaire gives March 2022 and the employer letter gives 1 June 2022. Which is correct?",
      drafted_by: "model",
    },
  ],
  items: [],
  gaps: [{ finding_id: "g1", doc_id: "D3", kind: "unreadable", pages: [1], reason: "unreadable-photo.jpg: 1 page(s) could not be read" }],
  dropped: [],
  wording_replacements: 0,
  calls: [],
};

export const view: S["CheckView"] = {
  check_id: CHECK_ID,
  case_id: CASE_ID,
  kind: "consistency",
  status: "completed",
  state: null,
  result,
  review: {},
  notes: {},
  blockers: ["c1", "g1"],
  signed_off: null,
  error: null,
};

export const checklists: S["ChecklistView"][] = [
  { skill: "presubmission-aewv", visa: "aewv", version: "0.1-sample", owner: "senior adviser", items: [], error: null },
];

export async function json(page: Page, pattern: string, body: unknown, status = 200): Promise<void> {
  await page.route(pattern, (route: Route) => route.fulfill({ status, json: body }));
}

export async function apiError(page: Page, pattern: string, status: number, code: string, message: string) {
  await json(page, pattern, { error: { code, message } }, status);
}

export async function base(page: Page): Promise<void> {
  await json(page, "**/api/health", health);
  await json(page, "**/api/checklists", checklists);
}
