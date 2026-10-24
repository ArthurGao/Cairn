"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorState, Loading } from "@/components/States";
import { API_URL, api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";
import { highlight } from "@/lib/highlight";

export type Citation = { docId: string; filename: string; page: number; quote: string };

/** The cited page beside the finding, quote highlighted; renders come from the server (§13). */
export function CitationViewer({ caseId, citation }: { caseId: string; citation: Citation | null }) {
  const page = useQuery({
    queryKey: keys.page(caseId, citation?.docId ?? "", citation?.page ?? 0),
    enabled: citation !== null,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/cases/{case_id}/documents/{doc_id}/pages/{n}", {
          params: { path: { case_id: caseId, doc_id: citation!.docId, n: citation!.page } },
        }),
      ),
  });

  if (!citation) {
    return <p className="text-sm text-muted">Select a source to read the page it comes from.</p>;
  }
  return (
    <div className="grid gap-3" data-testid="citation-viewer">
      <div className="flex items-baseline justify-between gap-3 border-b border-ink pb-2">
        <h3 className="text-sm font-semibold">
          {citation.filename} <span className="num font-mono font-normal">· page {citation.page}</span>
        </h3>
        <a
          href={`${API_URL}/api/cases/${caseId}/documents/${citation.docId}/pages/${citation.page}/render`}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-accent underline"
        >
          Page image <span className="sr-only">(opens in a new tab)</span>↗
        </a>
      </div>
      {page.isPending ? (
        <Loading label="Loading page…" />
      ) : page.isError ? (
        <ErrorState error={page.error} what="the page" />
      ) : (
        <>
          {page.data.method === "transcribed" && (
            <p className="text-xs text-accent">Transcribed by model ({page.data.model}): check the page image.</p>
          )}
          {page.data.method === "unreadable" ? (
            <p className="text-sm text-warn">Unreadable: {page.data.reason}</p>
          ) : (
            <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed">
              {highlight(page.data.text, citation.quote).map((segment, n) =>
                segment.mark ? <mark key={n}>{segment.text}</mark> : <span key={n}>{segment.text}</span>,
              )}
            </pre>
          )}
        </>
      )}
    </div>
  );
}
