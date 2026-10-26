"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { type ReactNode, useEffect, useMemo, useState } from "react";

import { type Citation, CitationViewer } from "@/components/CitationViewer";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CoverageBar } from "@/components/CoverageBar";
import { FindingReview } from "@/components/FindingReview";
import { Guide } from "@/components/Guide";
import { ModelBadge } from "@/components/ModelBadge";
import { PageHeader } from "@/components/PageHeader";
import { SignOffPanel } from "@/components/SignOffPanel";
import { ErrorState, Loading } from "@/components/States";
import { api, type Schemas } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { getCase, keys, type ReviewAction } from "@/lib/api/queries";
import { loadAdviser, saveAdviser } from "@/lib/adviser";
import { ACTION_LABEL, checkKindLabel, formatDay, formatWhen, plural, workingDaysLabel } from "@/lib/format";
import { useRouteParams } from "@/lib/params";

type Pending = { findingId: string; action: ReviewAction } | null;
type Source = (docId: string, page: number, quote: string, label?: string) => ReactNode;
type ReviewOf = (findingId: string) => ReactNode;

const STATUS_TONE = { checked: "text-good", pending: "text-bad", unable: "text-warn" } as const;
const DOWNGRADE = {
  missing: "not evaluated by the model",
  no_valid_citation: "marked checked without a source that could be verified",
  call_failed: "the model call failed",
} as const;
const EVIDENCE = {
  supported: { label: "supported by the case", tone: "text-good" },
  partial: { label: "partly supported", tone: "text-warn" },
  no_evidence: { label: "no evidence in the case", tone: "text-bad" },
  unable: { label: "could not be judged", tone: "text-warn" },
} as const;
const CONCERN_DOWNGRADE = {
  ...DOWNGRADE,
  no_valid_citation: "marked as supported without a source that could be verified",
} as const;
const DEADLINE_STATUS = {
  verified: "Read from the letter; the quoted words give this date.",
  unverified: "The quoted words do not give this date. Read the letter.",
  missing: "No reply deadline was found in the letter. Read the letter.",
} as const;

export default function CheckPage() {
  const { id, checkId } = useRouteParams<"id" | "checkId">();
  const queryClient = useQueryClient();
  const [citation, setCitation] = useState<Citation | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [signing, setSigning] = useState(false);
  const [adviser, setAdviser] = useState("");
  useEffect(() => setAdviser(loadAdviser()), []);

  const check = useQuery({
    queryKey: keys.check(id, checkId),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/cases/{case_id}/checks/{check_id}", {
          params: { path: { case_id: id, check_id: checkId } },
        }),
      ),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 1000 : false),
  });
  const detail = useQuery({ queryKey: keys.case(id), queryFn: () => getCase(id) });
  const facts = useMemo(
    () => new Map((check.data?.result?.facts ?? []).map((f) => [f.fact_id, f])),
    [check.data?.result?.facts],
  );

  // A review or sign-off changes this check, its case page and the case list.
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: keys.check(id, checkId) }),
      queryClient.invalidateQueries({ queryKey: keys.case(id) }),
      queryClient.invalidateQueries({ queryKey: keys.cases }),
    ]);
  const review = useMutation({
    mutationFn: async ({ findingId, action, note }: { findingId: string; action: ReviewAction; note: string }) =>
      unwrap(
        await api.POST("/api/cases/{case_id}/checks/{check_id}/findings/{finding_id}/review", {
          params: { path: { case_id: id, check_id: checkId, finding_id: findingId } },
          body: { action, note: note || null, adviser },
        }),
      ),
    onSuccess: async () => {
      setPending(null);
      await refresh();
    },
  });
  const signOff = useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST("/api/cases/{case_id}/checks/{check_id}/signoff", {
          params: { path: { case_id: id, check_id: checkId } },
          body: { adviser },
        }),
      ),
    onSuccess: async () => {
      setSigning(false);
      await refresh();
    },
  });

  if (check.isPending) return <Loading label="Loading check…" />;
  if (check.isError) return <ErrorState error={check.error} what="the check" />;
  const view = check.data;
  const result = view.result;
  const names = new Map((detail.data?.manifest.documents ?? []).map((d) => [d.doc_id, d.filename]));
  const name = (docId: string) => names.get(docId) ?? docId;

  // Every source and open finding is a hint candidate; Guide shows it on the first one only.
  const reviewOf: ReviewOf = (findingId) => (
    <Guide
      id="check.review"
      hint="Confirm, dismiss or resolve"
      after="check.source"
      block
      enabled={!view.signed_off && !view.review[findingId]}
    >
      <FindingReview
        findingId={findingId}
        state={view.review[findingId]}
        note={view.notes[findingId]}
        locked={Boolean(view.signed_off)}
        onAction={(action) => setPending({ findingId, action })}
      />
    </Guide>
  );
  const source: Source = (docId, page, quote, label) => (
    <Guide id="check.source" hint="Click to see the page">
      <button
        type="button"
        onClick={() => setCitation({ docId, filename: name(docId), page, quote })}
        className="link text-left"
      >
        {label ?? `${name(docId)} · p${page}`}
      </button>
    </Guide>
  );

  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader
        crumbs={[
          { label: "Cases", href: "/cases" },
          { label: detail.data?.manifest.label ?? id, href: `/cases/${id}` },
          { label: <span className="font-mono">{checkId}</span> },
        ]}
        title={
          <>
            {checkKindLabel(view.kind)}
            {result?.checklist ? (
              <span className="ml-2 font-mono text-base font-normal text-muted">
                {result.checklist.skill} v{result.checklist.version}
              </span>
            ) : null}
            {result?.letter ? (
              <span className="ml-2 font-mono text-base font-normal text-muted">{name(result.letter.doc_id)}</span>
            ) : null}
          </>
        }
      >
        {result && (
          <p className="mt-1 font-mono text-xs text-muted">
            {formatWhen(result.started)} – {formatWhen(result.finished)} · {plural(result.calls.length, "model call")}
          </p>
        )}
      </PageHeader>

      {view.status === "running" && (
        <section className="col-span-12" data-testid="progress" role="status" aria-live="polite">
          <p className="text-sm">
            Running: <span className="font-medium">{view.state?.step ?? "starting"}</span>
          </p>
          {view.state && (
            <p className="num mt-1 font-mono text-xs text-muted">
              documents {view.state.documents_done}/{view.state.documents_total} · units {view.state.units_done}/
              {view.state.units_total}
            </p>
          )}
        </section>
      )}

      {view.status === "failed" && (
        <section className="col-span-12" role="alert" data-testid="check-failed">
          <div className="border-l-4 border-bad bg-bad-wash px-4 py-3 text-sm">
            <p className="font-medium">The check failed. No findings were written.</p>
            <p className="mt-1">{view.error}</p>
          </div>
        </section>
      )}

      {result && result.status === "completed" && (
        <>
          <section className="col-span-12 grid gap-3">
            <CoverageBar coverage={result.coverage} kind={result.kind} />
            {result.error && (
              <p role="alert" className="border-l-4 border-warn bg-warn-wash px-4 py-2 text-sm">
                {result.error}
              </p>
            )}
          </section>

          <section className="col-span-12 grid content-start gap-8 lg:col-span-7">
            {result.kind === "consistency" && (
              <Conflicts result={result} facts={facts} source={source} reviewOf={reviewOf} />
            )}
            {result.kind === "presubmission" && <Items result={result} source={source} reviewOf={reviewOf} />}
            {result.letter && (
              <Letter
                letter={result.letter}
                workingDays={view.deadline_working_days}
                relatedHref={(checkId) => `/cases/${id}/checks/${checkId}`}
                source={source}
                reviewOf={reviewOf}
              />
            )}
            <Gaps result={result} name={name} source={source} reviewOf={reviewOf} />
          </section>

          <aside className="col-span-12 grid content-start gap-8 lg:col-span-5">
            <div className="lg:sticky lg:top-6">
              <CitationViewer caseId={id} citation={citation} />
            </div>
            <SignOffPanel
              view={view}
              adviser={adviser}
              onAdviser={(value) => {
                setAdviser(value);
                saveAdviser(value);
              }}
              onSignOff={() => setSigning(true)}
            />
          </aside>
        </>
      )}

      <ConfirmDialog
        open={pending !== null}
        title={pending ? `${ACTION_LABEL[pending.action]}: ${pending.findingId}` : ""}
        confirmLabel={pending ? ACTION_LABEL[pending.action] : ""}
        noteLabel="Note"
        noteRequired={pending?.action === "dismissed"}
        busy={review.isPending}
        error={
          !adviser.trim()
            ? "Enter your name in the sign-off panel first."
            : review.isError
              ? errorMessage(review.error)
              : null
        }
        onCancel={() => {
          setPending(null);
          review.reset();
        }}
        onConfirm={(note) => pending && adviser.trim() && review.mutate({ ...pending, note })}
      >
        {pending?.action === "dismissed" ? "Say why this finding needs no follow-up." : null}
      </ConfirmDialog>
      <ConfirmDialog
        open={signing}
        title="Sign off this check"
        confirmLabel="Sign off"
        busy={signOff.isPending}
        error={signOff.isError ? errorMessage(signOff.error) : null}
        onCancel={() => {
          setSigning(false);
          signOff.reset();
        }}
        onConfirm={() => signOff.mutate()}
      >
        You confirm, as {adviser || "the adviser"}, that you have reviewed every finding. This is recorded and cannot be
        undone.
      </ConfirmDialog>
    </div>
  );
}

function SectionTitle({ label, count, tone = "" }: { label: string; count: number; tone?: string }) {
  return (
    <h2 className={`mb-3 text-sm font-semibold uppercase tracking-wide ${tone}`}>
      {label} <span className="num font-normal text-muted">{count}</span>
    </h2>
  );
}

function Citations({ citations, source }: { citations: Schemas["Citation"][]; source: Source }) {
  if (citations.length === 0) return null;
  return (
    <ul className="mt-1 grid gap-0.5 text-xs">
      {citations.map((c, n) => (
        <li key={n}>
          {source(c.doc_id, c.page, c.quote)} <span className="text-muted">“{c.quote}”</span>
        </li>
      ))}
    </ul>
  );
}

function Conflicts({
  result,
  facts,
  source,
  reviewOf,
}: {
  result: Schemas["CheckResult"];
  facts: Map<string, Schemas["Fact"]>;
  source: Source;
  reviewOf: ReviewOf;
}) {
  return (
    <div>
      <SectionTitle label="Conflicts" count={result.conflicts.length} />
      {result.conflicts.length === 0 ? (
        <p className="border-y border-rule py-4 text-sm text-muted">No conflicts between the documents that were read.</p>
      ) : (
        <ol className="grid gap-5">
          {result.conflicts.map((conflict) => (
            <li key={conflict.finding_id} data-testid="conflict" className="border-t border-ink pt-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-muted">{conflict.finding_id}</span>
                <span className="text-sm font-medium">{conflict.summary}</span>
                {conflict.drafted_by === "model" && <ModelBadge />}
                <span className="text-xs text-muted">found by {conflict.origin.join(" + ")}</span>
              </div>
              <table className="mt-2 w-full text-sm">
                <tbody>
                  {conflict.fact_ids.map((factId) => {
                    const fact = facts.get(factId);
                    if (!fact) return null;
                    return (
                      <tr key={factId} className="border-b border-rule">
                        <td className="py-1.5 pr-3 font-medium text-bad">{fact.value}</td>
                        <td className="py-1.5 text-xs">
                          {source(fact.doc_id, fact.page, fact.quote)}
                          <div className="text-muted">“{fact.quote}”</div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="mt-2 text-sm" data-testid="question">
                {conflict.question}
              </p>
              <div className="mt-2">{reviewOf(conflict.finding_id)}</div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Items({ result, source, reviewOf }: { result: Schemas["CheckResult"]; source: Source; reviewOf: ReviewOf }) {
  return (
    <>
      {(["pending", "unable", "checked"] as const).map((status) => {
        const items = result.items.filter((i) => i.status === status);
        return (
          <div key={status}>
            <SectionTitle label={status} count={items.length} tone={STATUS_TONE[status]} />
            {items.length === 0 ? (
              <p className="border-y border-rule py-3 text-sm text-muted">None.</p>
            ) : (
              <ol className="grid gap-4">
                {items.map((item) => (
                  <li key={item.finding_id} data-testid="item" className="border-t border-ink pt-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-muted">{item.finding_id}</span>
                      <span className="font-mono text-sm font-medium">{item.item_id}</span>
                      <ModelBadge />
                    </div>
                    <p className="mt-1 text-sm">{item.finding}</p>
                    {item.downgraded && (
                      <p className="mt-1 text-xs text-warn">
                        Set to {item.status} by code: {DOWNGRADE[item.downgraded]}.
                      </p>
                    )}
                    <Citations citations={item.citations} source={source} />
                    {item.status !== "checked" && <div className="mt-2">{reviewOf(item.finding_id)}</div>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        );
      })}
    </>
  );
}

function Gaps({
  result,
  name,
  source,
  reviewOf,
}: {
  result: Schemas["CheckResult"];
  name: (docId: string) => string;
  source: Source;
  reviewOf: ReviewOf;
}) {
  return (
    <div>
      <SectionTitle label="Not checked" count={result.gaps.length} tone="text-warn" />
      {result.gaps.length === 0 ? (
        <p className="border-y border-rule py-3 text-sm text-muted">Every document and page was read.</p>
      ) : (
        <ol className="grid gap-4">
          {result.gaps.map((gap) => (
            <li key={gap.finding_id} data-testid="gap" className="border-t border-ink pt-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-mono text-xs text-muted">{gap.finding_id}</span>
                <span className="font-medium">{name(gap.doc_id)}</span>
                <span className="text-warn">{gap.kind}</span>
              </div>
              <p className="mt-1 text-sm">{gap.reason}</p>
              {gap.pages.map((n) => (
                <span key={n} className="mr-3 text-xs">
                  {source(gap.doc_id, n, "", `page ${n}`)}
                </span>
              ))}
              <div className="mt-2">{reviewOf(gap.finding_id)}</div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Letter({
  letter,
  workingDays,
  relatedHref,
  source,
  reviewOf,
}: {
  letter: Schemas["LetterResult"];
  workingDays: number | null;
  relatedHref: (checkId: string) => string;
  source: Source;
  reviewOf: ReviewOf;
}) {
  const { deadline } = letter;
  return (
    <>
      <div data-testid="deadline" className="border-t border-ink pt-3">
        <SectionTitle label="Reply deadline" count={1} />
        <p className="num text-2xl font-medium" data-testid="deadline-date">
          {deadline.due ? formatDay(deadline.due) : "Not found"}
        </p>
        {workingDays !== null && (
          <p className={`text-sm ${workingDays <= 3 ? "text-bad" : ""}`} data-testid="working-days">
            {workingDaysLabel(workingDays)}{" "}
            <span className="text-xs text-muted">(Monday to Friday; public holidays not counted)</span>
          </p>
        )}
        <p className={`mt-1 text-sm ${deadline.status === "verified" ? "" : "text-warn"}`}>
          {DEADLINE_STATUS[deadline.status]}
        </p>
        {deadline.quote && deadline.page !== null && (
          <p className="mt-1 text-xs">
            {source(letter.doc_id, deadline.page, deadline.quote)}{" "}
            <span className="text-muted">“{deadline.quote}”</span>
          </p>
        )}
        <p className="mt-2 text-xs text-muted">Confirm the date against the letter before you rely on it.</p>
        <div className="mt-2">{reviewOf(deadline.finding_id)}</div>
      </div>

      <div>
        <SectionTitle label="INZ concerns" count={letter.concerns.length} />
        {letter.concerns.length === 0 ? (
          <p className="border-y border-rule py-3 text-sm text-muted">No concerns were read from the letter.</p>
        ) : (
          <ol className="grid gap-5">
            {letter.concerns.map((concern) => (
              <li key={concern.finding_id} data-testid="concern" className="border-t border-ink pt-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-muted">{concern.finding_id}</span>
                  <span className="text-sm font-medium">{concern.summary}</span>
                  <ModelBadge />
                </div>
                <p className="mt-1 text-xs">
                  INZ: {source(letter.doc_id, concern.page, concern.quote)}{" "}
                  <span className="text-muted">“{concern.quote}”</span>
                </p>
                <p className="mt-2 text-sm">
                  <span className={`font-medium ${EVIDENCE[concern.status].tone}`} data-testid="evidence-status">
                    {EVIDENCE[concern.status].label}
                  </span>
                  {" — "}
                  {concern.finding}
                </p>
                {concern.downgraded && (
                  <p className="mt-1 text-xs text-warn">
                    Set by code: {CONCERN_DOWNGRADE[concern.downgraded]}.
                  </p>
                )}
                <Citations citations={concern.citations} source={source} />
                {concern.conflict_ids.length > 0 && letter.related_check_id && (
                  <p className="mt-1 text-xs">
                    Related conflicts:{" "}
                    {concern.conflict_ids.map((cid) => (
                      <Link key={cid} href={relatedHref(letter.related_check_id ?? "")} className="link mr-2 font-mono">
                        {cid}
                      </Link>
                    ))}
                  </p>
                )}
                {concern.client_request && (
                  <p className="mt-1 text-xs">
                    Ask the client for: <span data-testid="client-request">{concern.client_request}</span>
                  </p>
                )}
                <div className="mt-2">{reviewOf(concern.finding_id)}</div>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div>
        <SectionTitle label="Passages in no concern" count={letter.unaccounted.length} tone="text-warn" />
        {letter.unaccounted.length === 0 ? (
          <p className="border-y border-rule py-3 text-sm text-muted">
            Every passage of the letter is in a concern or was read as context.
          </p>
        ) : (
          <ol className="grid gap-4">
            {letter.unaccounted.map((u) => (
              <li key={u.finding_id} data-testid="unaccounted" className="border-t border-ink pt-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-mono text-xs text-muted">{u.finding_id}</span>
                  {source(letter.doc_id, u.page, u.text, `${u.passage_id} · p${u.page}`)}
                </div>
                <p className="mt-1 text-sm">“{u.text}”</p>
                <p className="mt-1 text-xs text-muted">Check whether this raises a point the reply must answer.</p>
                <div className="mt-2">{reviewOf(u.finding_id)}</div>
              </li>
            ))}
          </ol>
        )}
      </div>

      <Draft title="Email to the client" text={letter.client_email} empty="Nothing to ask the client for." testId="client-email" />
      <Draft title="Reply outline" text={letter.reply_outline} empty="No concerns to outline." testId="reply-outline" />
    </>
  );
}

/** Assembled by code from the results above; copied by the adviser, never sent from here. */
function Draft({ title, text, empty, testId }: { title: string; text: string; empty: string; testId: string }) {
  const [copied, setCopied] = useState<"" | "copied" | "failed">("");
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide">{title}</h2>
        {text && (
          <button
            type="button"
            onClick={() =>
              navigator.clipboard.writeText(text).then(
                () => setCopied("copied"),
                () => setCopied("failed"),
              )
            }
            className="border border-rule px-2 py-0.5 text-xs hover:border-ink"
          >
            {copied === "copied" ? "Copied" : "Copy"}
          </button>
        )}
      </div>
      {copied === "failed" && <p className="mb-2 text-xs text-warn">Could not copy; select the text instead.</p>}
      {text ? (
        <pre data-testid={testId} className="overflow-x-auto whitespace-pre-wrap border border-rule px-3 py-2 font-mono text-xs">
          {text}
        </pre>
      ) : (
        <p className="border-y border-rule py-3 text-sm text-muted">{empty}</p>
      )}
      <p className="mt-1 text-xs text-muted">Built from the findings above. Edit it before you use it; nothing is sent from here.</p>
    </div>
  );
}
