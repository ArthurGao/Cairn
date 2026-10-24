"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ModelBadge } from "@/components/ModelBadge";
import { OpDiff } from "@/components/OpDiff";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, Loading } from "@/components/States";
import { loadAdviser, saveAdviser } from "@/lib/adviser";
import { api } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { keys, memoryKeys } from "@/lib/api/queries";
import { CLEANUP_ACTIVE, CleanupStatus } from "@/lib/cleanup";
import { formatWhen, plural, timeLeft } from "@/lib/format";
import { useRouteParams } from "@/lib/params";

const SEVERITY_TONE: Record<string, string> = { error: "text-bad", warn: "text-warn", info: "text-muted" };

export default function CleanupPage() {
  const { id } = useRouteParams<"id">();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirm, setConfirm] = useState<"approve" | "reject" | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  useEffect(() => setReviewer(loadAdviser()), []);

  const cleanup = useQuery({
    queryKey: keys.cleanup(id),
    queryFn: async () => unwrap(await api.GET("/api/cleanup/{workflow_id}", { params: { path: { workflow_id: id } } })),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return false;
      return CLEANUP_ACTIVE.has(status) || (submitted && status === "awaiting_review") ? 1000 : false;
    },
  });
  const review = useMutation({
    mutationFn: async (approved: string[]) =>
      unwrap(
        await api.POST("/api/cleanup/{workflow_id}/review", {
          params: { path: { workflow_id: id } },
          body: { approved_op_ids: approved, reviewer, reviewer_note: "" },
        }),
      ),
    onSuccess: async () => {
      setConfirm(null);
      setSubmitted(true);
      saveAdviser(reviewer);
      await Promise.all(
        [keys.cleanup(id), keys.cleanups, ...memoryKeys].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      );
    },
  });

  if (cleanup.isPending) return <Loading label="Loading cleanup…" />;
  if (cleanup.isError) return <ErrorState error={cleanup.error} what="the cleanup" />;
  const state = cleanup.data;
  const proposal = state.proposal;
  const awaiting = state.status === "awaiting_review";
  const applied = new Set(state.outcome?.applied ?? []);
  const rejected = new Map((state.outcome?.rejected ?? []).map((r) => [r.op_id, r]));
  const toggle = (opId: string) =>
    setSelected((now) => {
      const next = new Set(now);
      if (next.has(opId)) next.delete(opId);
      else next.add(opId);
      return next;
    });

  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader
        crumbs={[{ label: "Cleanup", href: "/manage/cleanup" }, { label: <span className="font-mono">{id}</span> }]}
        title="Cleanup proposal"
      >
        <p className="mt-1 text-sm" role="status" aria-live="polite" data-testid="cleanup-status">
          <CleanupStatus status={state.status} />
          {awaiting && state.expires ? (
            <span className="text-muted"> — {timeLeft(state.expires, Date.now())} to review</span>
          ) : null}
          {state.error ? <span className="text-bad"> — {state.error}</span> : null}
        </p>
      </PageHeader>

      <section className="col-span-12 lg:col-span-8" aria-label="Proposed changes">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Proposed changes</h2>
        {!proposal || proposal.changes.length === 0 ? (
          <p className="text-sm text-muted">
            {CLEANUP_ACTIVE.has(state.status) ? "Working…" : "Nothing to review: the memory files are healthy."}
          </p>
        ) : (
          <ol className="grid gap-6">
            {proposal.changes.map((change) => {
              const label = `${change.kind === "merge" ? "Merge" : "Archive"} ${change.changes.map((f) => f.slug).join(", ")}`;
              return (
              <li key={change.op_id} data-testid="change" className="border-t border-ink pt-3">
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  {awaiting && !submitted ? (
                    <label className="flex items-center gap-2 font-medium">
                      <input
                        type="checkbox"
                        checked={selected.has(change.op_id)}
                        onChange={() => toggle(change.op_id)}
                      />
                      {label}
                    </label>
                  ) : (
                    <span className="font-medium">{label}</span>
                  )}
                  {change.kind === "merge" && <ModelBadge />}
                  {applied.has(change.op_id) && <span className="text-good">applied</span>}
                  {rejected.has(change.op_id) && (
                    <span className="text-bad">rejected: {rejected.get(change.op_id)!.reason}</span>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted">{change.reason}</p>
                <div className="mt-3 grid gap-3">
                  {change.changes.map((file) => (
                    <div key={file.slug}>
                      <div className="mb-1 font-mono text-xs">{file.slug}.md</div>
                      <OpDiff before={file.before} after={file.after} />
                    </div>
                  ))}
                </div>
              </li>
              );
            })}
          </ol>
        )}
      </section>

      <aside className="col-span-12 grid content-start gap-8 lg:col-span-4">
        {awaiting && !submitted && proposal && proposal.changes.length > 0 && (
          <div className="grid gap-3 border-t border-ink pt-4" data-testid="review-panel">
            <h2 className="text-sm font-semibold uppercase tracking-wide">Review</h2>
            <label className="grid gap-1 text-sm">
              <span>Your name (recorded with the decision)</span>
              <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} className="border border-rule px-2 py-1.5" />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={selected.size === 0 || !reviewer.trim()}
                onClick={() => setConfirm("approve")}
                className="bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
              >
                Approve selected ({selected.size})
              </button>
              <button
                type="button"
                disabled={!reviewer.trim()}
                onClick={() => setConfirm("reject")}
                className="border border-rule px-3 py-1.5 text-sm hover:border-ink disabled:opacity-40"
              >
                Reject all
              </button>
            </div>
          </div>
        )}
        {state.decision && (
          <div className="border-t border-ink pt-4 text-sm" data-testid="decision">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Decision</h2>
            {state.decision.approved_op_ids.length === 0
              ? "All changes rejected"
              : `Approved ${plural(state.decision.approved_op_ids.length, "change")}`}
            {state.decision.reviewer ? ` by ${state.decision.reviewer}` : ""}
          </div>
        )}
        {proposal && proposal.mechanical.length > 0 && (
          <p className="border-t border-ink pt-4 text-sm" data-testid="mechanical">
            MEMORY.md was re-derived from the files (applied without review; undo is not needed).
          </p>
        )}
        {proposal && (
          <div className="border-t border-ink pt-4">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Findings</h2>
            {proposal.findings.length === 0 ? (
              <p className="text-sm text-muted">No findings.</p>
            ) : (
              <ul className="grid gap-2 text-sm">
                {proposal.findings.map((f, n) => (
                  <li key={n} data-testid="finding">
                    <span className={`font-mono text-xs ${SEVERITY_TONE[f.severity]}`}>{f.severity}</span>{" "}
                    <span className="font-mono text-xs">{f.check}</span> <span className="text-muted">{f.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {state.started && <p className="font-mono text-xs text-muted">started {formatWhen(state.started)}</p>}
      </aside>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm === "approve" ? "Apply the selected changes" : "Reject every change"}
        confirmLabel={confirm === "approve" ? "Approve" : "Reject all"}
        busy={review.isPending}
        error={review.isError ? errorMessage(review.error) : null}
        onCancel={() => {
          setConfirm(null);
          review.reset();
        }}
        onConfirm={() => review.mutate(confirm === "approve" ? [...selected] : [])}
      >
        {confirm === "approve"
          ? `${plural(selected.size, "change")} will be written. Archived memories move to memory/_archive/ and every change can be undone from the memory page.`
          : "Nothing will be written; the next weekly cleanup proposes again."}
      </ConfirmDialog>
    </div>
  );
}
