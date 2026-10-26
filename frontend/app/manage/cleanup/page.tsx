"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Guide } from "@/components/Guide";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Loading } from "@/components/States";
import { api } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";
import { formatWhen, plural, timeLeft } from "@/lib/format";
import { CLEANUP_ACTIVE, CleanupStatus } from "@/lib/cleanup";

export default function CleanupsPage() {
  const [waitingFor, setWaitingFor] = useState<number | null>(null); // rows listed at "Run now"
  const list = useQuery({
    queryKey: keys.cleanups,
    queryFn: async () => unwrap(await api.GET("/api/cleanup")),
    // Poll while a cleanup works, and after "Run now" until the schedule's new run is listed.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((c) => CLEANUP_ACTIVE.has(c.status)) || waitingFor !== null ? 1000 : false,
  });
  const trigger = useMutation({
    mutationFn: async () => unwrap(await api.POST("/api/cleanup/run")),
    onSuccess: () => setWaitingFor(list.data?.length ?? 0),
  });
  useEffect(() => {
    if (waitingFor !== null && (list.data?.length ?? 0) > waitingFor) setWaitingFor(null);
  }, [list.data, waitingFor]);
  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader crumbs={[{ label: "Manage" }]} title="Memory cleanup">
        <p className="mt-1 max-w-3xl text-sm text-muted">
          Every Sunday a cleanup lints the memory files and drafts merges of near-duplicates. Nothing but the index is
          changed until a person approves; an unanswered proposal expires.
        </p>
      </PageHeader>
      <section className="col-span-12 grid gap-2 lg:col-span-4">
        <Guide
          id="cleanup.run"
          hint="Try it now instead of waiting for Sunday"
          enabled={list.data?.length === 0}
          className="justify-self-start"
        >
          <button
            type="button"
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
            className="justify-self-start bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
          >
            {trigger.isPending ? "Starting…" : "Run cleanup now"}
          </button>
        </Guide>
        {trigger.isError && (
          <p role="alert" className="text-sm text-bad">
            {errorMessage(trigger.error)}
          </p>
        )}
        {trigger.isSuccess && (
          <p role="status" className="text-sm text-good">
            Cleanup started.
          </p>
        )}
      </section>
      <section className="col-span-12 lg:col-span-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Recent cleanups</h2>
        {list.isPending ? (
          <Loading label="Loading cleanups…" />
        ) : list.isError ? (
          <ErrorState error={list.error} what="cleanups" />
        ) : list.data.length === 0 ? (
          <Empty>No cleanups yet.</Empty>
        ) : (
          <ul className="border-t border-ink text-sm">
            {list.data.map((c) => (
              <li key={c.workflow_id} data-testid="cleanup-row" className="grid grid-cols-12 gap-3 border-b border-rule py-2">
                <Guide id="cleanup.open" hint="Open to review the proposal" block className="col-span-5 min-w-0">
                  <Link href={`/manage/cleanup/${encodeURIComponent(c.workflow_id)}`} className="link block truncate font-mono text-xs">
                    {c.workflow_id}
                  </Link>
                </Guide>
                <span className="col-span-3">
                  <CleanupStatus status={c.status} />
                </span>
                <span className="col-span-2">{plural(c.changes, "change")}</span>
                <span className="col-span-2 text-right font-mono text-xs text-muted">
                  {c.status === "awaiting_review" && c.expires
                    ? timeLeft(c.expires, Date.now())
                    : c.started
                      ? formatWhen(c.started)
                      : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
