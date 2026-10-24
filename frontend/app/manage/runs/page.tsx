"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Loading } from "@/components/States";
import { api } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";
import { formatWhen } from "@/lib/format";

const TONE: Record<string, string> = { completed: "text-good", failed: "text-bad" };

export default function RunsPage() {
  const router = useRouter();
  const [task, setTask] = useState("");
  const runs = useQuery({ queryKey: keys.runs, queryFn: async () => unwrap(await api.GET("/api/runs")) });
  const start = useMutation({
    mutationFn: async (text: string) => unwrap(await api.POST("/api/runs", { body: { task: text } })),
    onSuccess: ({ run_id }) => router.push(`/manage/runs/${run_id}`),
  });
  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader crumbs={[{ label: "Manage" }]} title="Agent runs" />
      <section className="col-span-12 lg:col-span-5">
        <form
          className="grid gap-3 border-t border-ink pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (task.trim()) start.mutate(task.trim());
          }}
        >
          <label className="grid gap-1 text-sm">
            <span className="font-semibold uppercase tracking-wide">Task</span>
            <textarea
              value={task}
              onChange={(event) => setTask(event.target.value)}
              rows={5}
              placeholder="e.g. Draft a covering note listing the attachments for the sample AEWV case."
              className="border border-rule p-2"
            />
          </label>
          <button
            type="submit"
            disabled={!task.trim() || start.isPending}
            className="justify-self-start bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
          >
            {start.isPending ? "Starting…" : "Start run"}
          </button>
          {start.isError && (
            <p role="alert" className="text-sm text-bad">
              {errorMessage(start.error)}
            </p>
          )}
        </form>
      </section>
      <section className="col-span-12 lg:col-span-7">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Recent runs</h2>
        {runs.isPending ? (
          <Loading label="Loading runs…" />
        ) : runs.isError ? (
          <ErrorState error={runs.error} what="runs" />
        ) : runs.data.length === 0 ? (
          <Empty>No runs yet.</Empty>
        ) : (
          <ul className="border-t border-ink text-sm">
            {runs.data.map((run) => (
              <li key={run.run_id} data-testid="run-row" className="grid grid-cols-12 gap-3 border-b border-rule py-2">
                <Link href={`/manage/runs/${run.run_id}`} className="col-span-8 truncate hover:underline">
                  {run.task || <span className="font-mono">{run.run_id}</span>}
                </Link>
                <span className={`col-span-2 ${TONE[run.status] ?? "text-muted"}`}>{run.status}</span>
                <span className="col-span-2 text-right font-mono text-xs text-muted">
                  {run.started ? formatWhen(run.started) : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
