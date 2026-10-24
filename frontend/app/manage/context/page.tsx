"use client";

import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/PageHeader";
import { ErrorState, Loading } from "@/components/States";
import { TokenBar } from "@/components/TokenBar";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";

/** The progressive-disclosure explainer: exactly what the agent sees up front (design §5). */
export default function ContextPage() {
  const preview = useQuery({
    queryKey: keys.context,
    queryFn: async () => unwrap(await api.GET("/api/context/preview")),
  });
  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader crumbs={[{ label: "Manage" }]} title="Always-loaded context (L0)" />
      {preview.isPending ? (
        <div className="col-span-12">
          <Loading label="Building the context…" />
        </div>
      ) : preview.isError ? (
        <div className="col-span-12">
          <ErrorState error={preview.error} what="the context" />
        </div>
      ) : (
        <>
          <section className="col-span-12">
            <TokenBar breakdown={preview.data.breakdown} />
          </section>
          <section className="col-span-12">
            <p className="mb-3 max-w-3xl text-sm text-muted">
              This is every token the agent starts with. Memory bodies, skill bodies and reference files are not here:
              the agent loads them with tools when an index line says they are relevant.
            </p>
            <pre data-testid="prompt" className="overflow-auto border-t border-ink pt-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
              {preview.data.prompt}
            </pre>
          </section>
        </>
      )}
    </div>
  );
}
