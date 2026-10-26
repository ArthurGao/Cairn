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
  build: "",
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
      source: "client",
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
      source: "client",
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
      source: "client",
      pages: [{ n: 1, method: "unreadable" }],
    },
  ],
};

/** The sample case with an INZ letter uploaded next to the evidence. */
export const manifestWithLetter: S["Manifest"] = {
  ...manifest,
  documents: [
    ...manifest.documents,
    {
      doc_id: "L1",
      filename: "ppi-aewv.pdf",
      stored_name: "L1.pdf",
      media_type: "application/pdf",
      bytes: 1900,
      sha256: "d",
      uploaded: NOW,
      status: "ingested",
      error: null,
      source: "inz",
      pages: [
        { n: 1, method: "text" },
        { n: 2, method: "text" },
      ],
    },
  ],
};

export const brief: S["CheckBrief"] = {
  check_id: CHECK_ID,
  kind: "consistency",
  checklist_skill: null,
  letter_doc_id: null,
  status: "completed",
  started: NOW,
  counts: { conflicts: 1, checked: 0, pending: 0, unable: 0, concerns: 0, not_supported: 0, gaps: 1, clean: false },
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
  letter: null,
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
  deadline_working_days: null,
};

export const letter: S["LetterResult"] = {
  doc_id: "L1",
  related_check_id: "01CONSISTENCY",
  deadline: { finding_id: "d1", status: "verified", due: "2026-11-07", quote: "If you do not respond by 7 November 2026", page: 2 },
  concerns: [
    {
      finding_id: "q1",
      summary: "Start date with Example Freight Ltd differs",
      passages: ["P8", "P9"],
      page: 1,
      quote: "start date with Example Freight Ltd as 03/2022",
      status: "partial",
      finding: "The questionnaire gives March 2022 and the employer letter gives 1 June 2022.",
      citations: [{ doc_id: "D2", page: 1, quote: "since 1 June 2022" }],
      client_request: "Payslips showing your first day",
      conflict_ids: ["c2"],
      downgraded: null,
    },
    {
      finding_id: "q2",
      summary: "Police certificate not received",
      passages: ["P10"],
      page: 1,
      quote: "none has been received",
      status: "no_evidence",
      finding: "No certificate is in the case.",
      citations: [],
      client_request: "Your police certificate",
      conflict_ids: [],
      downgraded: "no_valid_citation",
    },
  ],
  unaccounted: [{ finding_id: "u1", passage_id: "P15", page: 2, text: "A. Officer, Immigration Officer" }],
  client_email: "Hi,\n\n1. Payslips showing your first day\n2. Your police certificate\n",
  reply_outline: "Reply to INZ letter ppi-aewv.pdf\n\n1. Start date with Example Freight Ltd differs\n",
};

export const letterView: S["CheckView"] = {
  ...view,
  kind: "letter",
  result: { ...result, kind: "letter", conflicts: [], facts: [], letter },
  blockers: ["d1", "q1", "q2", "u1", "g1"],
  deadline_working_days: 9,
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
