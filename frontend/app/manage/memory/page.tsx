"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { OpDiff } from "@/components/OpDiff";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Loading } from "@/components/States";
import { UndoDialog } from "@/components/UndoDialog";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";
import { formatWhen } from "@/lib/format";

export default function MemoryPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [undoing, setUndoing] = useState<string | null>(null);
  const list = useQuery({ queryKey: keys.memory, queryFn: async () => unwrap(await api.GET("/api/memory")) });
  const detail = useQuery({
    queryKey: keys.memoryDetail(selected ?? ""),
    enabled: selected !== null,
    queryFn: async () => unwrap(await api.GET("/api/memory/{slug}", { params: { path: { slug: selected! } } })),
  });

  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader crumbs={[{ label: "Manage" }]} title="Memory" />
      <section className="col-span-12 lg:col-span-6">
        {list.isPending ? (
          <Loading label="Loading memory…" />
        ) : list.isError ? (
          <ErrorState error={list.error} what="memory" />
        ) : list.data.entries.length === 0 ? (
          <Empty>No memories yet. Runs write them back after validation.</Empty>
        ) : (
          <>
            <p data-testid="budget" className={`mb-4 text-sm ${list.data.budget.over ? "text-bad" : ""}`}>
              Index: <span className="num font-mono">{list.data.budget.tokens}</span> of{" "}
              <span className="num font-mono">{list.data.budget.budget}</span> tokens (estimated)
              {list.data.budget.over ? " — over budget" : ""}
            </p>
            {/* The API orders entries by type (user, feedback, project, reference, then invalid). */}
            {[...new Set(list.data.entries.map((e) => e.type))].map((type) => {
              const entries = list.data.entries.filter((e) => e.type === type);
              return (
                <div key={type} className="mb-6">
                  <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">{type || "no type"}</h2>
                  <ul className="border-t border-ink text-sm">
                    {entries.map((entry) => (
                      <li key={entry.slug} data-testid="memory-row" className="border-b border-rule">
                        <button
                          type="button"
                          onClick={() => setSelected(entry.slug)}
                          aria-pressed={selected === entry.slug}
                          className={`grid w-full grid-cols-12 gap-2 py-2 text-left ${selected === entry.slug ? "bg-accent-wash" : ""}`}
                        >
                          <span className="col-span-9">
                            <span className="font-medium">{entry.title}</span>
                            <span className="block text-xs text-muted">{entry.description}</span>
                          </span>
                          <span className="num col-span-3 text-right font-mono text-xs text-muted">
                            {entry.usage.reads} reads
                            <br />
                            {entry.usage.last_read ?? "never read"}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </>
        )}
      </section>
      <aside className="col-span-12 lg:col-span-6" aria-label="Memory detail">
        {selected === null ? (
          <p className="text-sm text-muted">Select a memory to see its file and history.</p>
        ) : detail.isPending ? (
          <Loading label="Loading memory…" />
        ) : detail.isError ? (
          <ErrorState error={detail.error} what="the memory" />
        ) : (
          <div className="grid gap-4" data-testid="memory-detail">
            <h2 className="border-b border-ink pb-2 font-mono text-sm">{detail.data.slug}.md</h2>
            <pre className="overflow-auto font-mono text-xs leading-relaxed whitespace-pre-wrap">{detail.data.text}</pre>
            <h3 className="text-xs font-semibold uppercase tracking-wide">History</h3>
            {detail.data.changelog.length === 0 ? (
              <p className="text-sm text-muted">Hand-written; no recorded changes.</p>
            ) : (
              <ol className="grid gap-4">
                {detail.data.changelog.map((entry) => (
                  <li key={entry.id} data-testid="history-entry" className="border-t border-rule pt-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-medium">{entry.op}</span>
                      <span className="font-mono text-muted">{entry.actor}</span>
                      <span className="font-mono text-muted">{formatWhen(entry.at)}</span>
                      {entry.op !== "index_sync" && (
                        <button
                          type="button"
                          onClick={() => setUndoing(entry.id)}
                          aria-label={`Undo ${entry.op} ${entry.id}`}
                          className="border border-rule px-2 py-0.5 hover:border-ink"
                        >
                          Undo
                        </button>
                      )}
                    </div>
                    <div className="mt-2">
                      <OpDiff before={entry.before} after={entry.after} />
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </aside>
      <UndoDialog changeId={undoing} onClose={() => setUndoing(null)}>
        Undoes the whole group this change belongs to. Nothing is deleted: archived memories can be restored.
      </UndoDialog>
    </div>
  );
}
