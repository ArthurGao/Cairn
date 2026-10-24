"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";

import { ModelBadge } from "@/components/ModelBadge";
import { OpDiff } from "@/components/OpDiff";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, Loading } from "@/components/States";
import { TokenBar } from "@/components/TokenBar";
import { UndoDialog } from "@/components/UndoDialog";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";

const ACTIVE = new Set(["running", "extracting", "writing"]);

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const [undoing, setUndoing] = useState<string | null>(null);
  const run = useQuery({
    queryKey: keys.run(id),
    queryFn: async () => unwrap(await api.GET("/api/runs/{run_id}", { params: { path: { run_id: id } } })),
    refetchInterval: (query) => (ACTIVE.has(query.state.data?.status ?? "") ? 1000 : false),
  });

  if (run.isPending) return <Loading label="Loading run…" />;
  if (run.isError) return <ErrorState error={run.error} what="the run" />;
  const state = run.data;

  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader
        crumbs={[{ label: "Runs", href: "/manage/runs" }, { label: <span className="font-mono">{id}</span> }]}
        title={state.task || "Agent run"}
      >
        <p className="mt-1 text-sm" role="status" aria-live="polite" data-testid="run-status">
          {state.status}
          {state.error ? <span className="text-bad"> — {state.error}</span> : null}
        </p>
      </PageHeader>

      {state.context && (
        <section className="col-span-12">
          <TokenBar breakdown={state.context} loaded={state.loaded_tokens} />
        </section>
      )}

      <section className="col-span-12 lg:col-span-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Steps</h2>
        <ol className="border-t border-ink text-sm">
          {state.steps.map((step) => (
            <li key={step.n} data-testid="step" className="grid grid-cols-12 gap-2 border-b border-rule py-1.5">
              <span className="num col-span-1 font-mono text-xs text-muted">{step.n}</span>
              {step.kind === "llm" ? (
                <span className="col-span-11">
                  model call <span className="font-mono text-xs text-muted">{step.model}</span>{" "}
                  <span className="num font-mono text-xs">
                    {step.tokens_in}→{step.tokens_out}
                  </span>{" "}
                  <span className="text-xs text-muted">tokens reported by vendor</span>
                </span>
              ) : (
                <span className="col-span-11">
                  <span className="font-mono">{step.tool}</span> <span className="font-mono text-accent">{step.arg}</span>{" "}
                  <span className="num font-mono text-xs text-muted">
                    {step.result_chars} chars, ~{step.tokens} tokens
                  </span>
                  {step.truncated ? <span className="text-xs text-warn"> (cut)</span> : null}
                </span>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="col-span-12 grid content-start gap-8 lg:col-span-7">
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide">
            Answer {state.answer ? <ModelBadge /> : null}
          </h2>
          {state.answer ? (
            <p data-testid="answer" className="whitespace-pre-wrap border-t border-ink pt-3 text-sm">
              {state.answer}
            </p>
          ) : (
            <p className="text-sm text-muted">{ACTIVE.has(state.status) ? "Working…" : "No answer."}</p>
          )}
        </div>

        {state.writeback && (
          <div data-testid="writeback">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Memory write-back</h2>
            {state.writeback.error && (
              <p role="alert" className="mb-3 border-l-4 border-bad bg-bad-wash px-3 py-2 text-sm">
                {state.writeback.error}
              </p>
            )}
            {state.writeback.applied.length === 0 && !state.writeback.error && (
              <p className="text-sm text-muted">Nothing was written.</p>
            )}
            <ol className="grid gap-4">
              {state.writeback.applied.map((op) => {
                return (
                  <li key={op.change_id} data-testid="applied" className="border-t border-ink pt-2">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="text-good">{op.op}</span>
                      <span className="font-mono">{op.slug}</span>
                      <ModelBadge />
                      {op.undone ? (
                        <span className="text-xs text-muted">undone</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setUndoing(op.change_id)}
                          aria-label={`Undo ${op.op} of ${op.slug}`}
                          className="border border-rule px-2 py-0.5 text-xs hover:border-ink"
                        >
                          Undo
                        </button>
                      )}
                    </div>
                    <div className="mt-2">
                      <OpDiff before={op.before} after={op.after} />
                    </div>
                  </li>
                );
              })}
            </ol>
            {state.writeback.rejected.length > 0 && (
              <>
                <h3 className="mt-6 mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Rejected by code</h3>
                <ul className="grid gap-1 text-sm">
                  {state.writeback.rejected.map((r) => (
                    <li key={r.index} data-testid="rejected">
                      <span className="font-mono">{r.slug}</span> <span className="font-mono text-bad">{r.code}</span>{" "}
                      <span className="text-muted">{r.reason}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </section>

      <UndoDialog changeId={undoing} onClose={() => setUndoing(null)} refresh={[keys.run(id)]}>
        The memory goes back to how it was before this run; the change log keeps both versions.
      </UndoDialog>
    </div>
  );
}
