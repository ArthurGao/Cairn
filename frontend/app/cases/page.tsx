"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Guide } from "@/components/Guide";
import { StatusCounts } from "@/components/StatusCounts";
import { Empty, ErrorState, Loading } from "@/components/States";
import { api, type Schemas } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { type CheckKind, keys } from "@/lib/api/queries";
import { checkKindLabel, formatWhen } from "@/lib/format";

function latest(checks: Schemas["CheckBrief"][], kind: CheckKind) {
  return checks.find((c) => c.kind === kind);
}

export default function CasesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const cases = useQuery({
    queryKey: keys.cases,
    queryFn: async () => unwrap(await api.GET("/api/cases")),
  });
  const create = useMutation({
    mutationFn: async (name: string) => unwrap(await api.POST("/api/cases", { body: { label: name } })),
    onSuccess: async ({ case_id }) => {
      await queryClient.invalidateQueries({ queryKey: keys.cases });
      router.push(`/cases/${case_id}`);
    },
  });

  return (
    <div className="grid grid-cols-12 gap-6">
      <section className="col-span-12 md:col-span-8">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Cases</h1>
        {cases.isPending ? (
          <Loading label="Loading cases…" />
        ) : cases.isError ? (
          <ErrorState error={cases.error} what="cases" />
        ) : cases.data.length === 0 ? (
          <Empty>No cases yet. Create one to upload documents and run a check.</Empty>
        ) : (
          <table className="w-full border-t border-ink text-sm">
            <thead>
              <tr className="border-b border-rule text-left text-xs uppercase tracking-wide text-muted">
                <th className="py-2 font-medium">Case</th>
                <th className="py-2 text-right font-medium">Docs</th>
                <th className="py-2 pl-6 font-medium">Consistency</th>
                <th className="py-2 pl-6 font-medium">Pre-submission</th>
              </tr>
            </thead>
            <tbody>
              {cases.data.map((c, n) => (
                <tr key={c.case_id} data-testid="case-row" className="border-b border-rule align-top">
                  <td className="py-3">
                    {/* The list is newest first; the walkthrough starts with the oldest case. */}
                    <Guide id="cases.open" hint="Start with this case" enabled={n === cases.data.length - 1}>
                      <Link href={`/cases/${c.case_id}`} className="link font-medium">
                        {c.label}
                      </Link>
                    </Guide>
                    <div className="font-mono text-xs text-muted">{formatWhen(c.created)}</div>
                  </td>
                  <td className="num py-3 text-right">{c.documents}</td>
                  {(["consistency", "presubmission"] as const).map((kind) => {
                    const check = latest(c.checks, kind);
                    return (
                      <td key={kind} className="py-3 pl-6" aria-label={checkKindLabel(kind)}>
                        {check ? <StatusCounts check={check} /> : <span className="text-muted">Not run</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <aside className="col-span-12 md:col-span-4">
        <form
          className="grid gap-3 border-t border-ink pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (label.trim()) create.mutate(label.trim());
          }}
        >
          <h2 className="text-sm font-semibold uppercase tracking-wide">New case</h2>
          <label className="grid gap-1 text-sm">
            <span>Label</span>
            <input
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="e.g. AEWV — sample applicant"
              className="border border-rule px-2 py-1.5"
            />
          </label>
          <button
            type="submit"
            disabled={!label.trim() || create.isPending}
            className="justify-self-start bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
          >
            {create.isPending ? "Creating…" : "Create case"}
          </button>
          {create.isError && (
            <p role="alert" className="text-sm text-bad">
              {errorMessage(create.error)}
            </p>
          )}
        </form>
      </aside>
    </div>
  );
}
