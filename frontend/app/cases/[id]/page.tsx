"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/PageHeader";
import { useState } from "react";

import { StatusCounts } from "@/components/StatusCounts";
import { Empty, ErrorState, Loading } from "@/components/States";
import { Upload } from "@/components/Upload";
import { api } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { type CheckKind, type DocSource, getCase, keys } from "@/lib/api/queries";
import { checkKindLabel, formatWhen, plural } from "@/lib/format";
import { useRouteParams } from "@/lib/params";

const METHOD_LABEL = { text: "text", transcribed: "transcribed by model", unreadable: "unreadable" } as const;
const METHOD_TONE = { text: "", transcribed: "text-accent", unreadable: "text-warn" } as const;

export default function CasePage() {
  const { id } = useRouteParams<"id">();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [checklist, setChecklist] = useState("");
  const [letter, setLetter] = useState("");

  const detail = useQuery({ queryKey: keys.case(id), queryFn: () => getCase(id) });
  const checklists = useQuery({
    queryKey: keys.checklists,
    queryFn: async () => unwrap(await api.GET("/api/checklists")),
  });
  const upload = useMutation({
    mutationFn: async ({ files, source }: { files: File[]; source: DocSource }) =>
      unwrap(
        await api.POST("/api/cases/{case_id}/documents", {
          params: { path: { case_id: id } },
          body: { files: files as unknown as string[], source },
          bodySerializer: () => {
            const form = new FormData();
            for (const file of files) form.append("files", file);
            form.append("source", source);
            return form;
          },
        }),
      ),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: keys.case(id) }),
        queryClient.invalidateQueries({ queryKey: keys.cases }),
      ]),
  });
  const start = useMutation({
    mutationFn: async (body: { kind: CheckKind; checklist_skill?: string; letter_doc_id?: string }) =>
      unwrap(await api.POST("/api/cases/{case_id}/checks", { params: { path: { case_id: id } }, body })),
    onSuccess: ({ check_id }) => router.push(`/cases/${id}/checks/${check_id}`),
  });

  if (detail.isPending) return <Loading label="Loading case…" />;
  if (detail.isError) return <ErrorState error={detail.error} what="the case" />;
  const { manifest, checks } = detail.data;
  const valid = (checklists.data ?? []).filter((c) => !c.error);
  const chosen = checklist || valid[0]?.skill || "";
  const letters = manifest.documents.filter((d) => d.source === "inz");
  const evidence = manifest.documents.filter((d) => d.source === "client");
  const chosenLetter = letter || letters[0]?.doc_id || "";

  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-10">
      <PageHeader
        crumbs={[{ label: "Cases", href: "/cases" }, { label: <span className="font-mono">{manifest.case_id}</span> }]}
        title={manifest.label}
      />

      <section className="col-span-12 lg:col-span-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Documents</h2>
        {manifest.documents.length === 0 ? (
          <Empty>No documents yet. Upload PDFs, images, text or Markdown files.</Empty>
        ) : (
          <table className="w-full border-t border-ink text-sm">
            <thead>
              <tr className="border-b border-rule text-left text-xs uppercase tracking-wide text-muted">
                <th className="py-2 font-medium">File</th>
                <th className="py-2 font-medium">Status</th>
                <th className="py-2 font-medium">Pages</th>
              </tr>
            </thead>
            <tbody>
              {manifest.documents.map((doc) => (
                <tr key={doc.doc_id} data-testid="document-row" className="border-b border-rule align-top">
                  <td className="py-2">
                    {doc.filename}
                    {doc.source === "inz" && (
                      <span className="ml-2 border border-ink px-1.5 py-0.5 text-[11px] uppercase tracking-wide">
                        INZ letter
                      </span>
                    )}
                    <div className="font-mono text-xs text-muted">{doc.media_type}</div>
                  </td>
                  <td className={`py-2 ${doc.status === "failed" ? "text-bad" : ""}`}>
                    {doc.status}
                    {doc.error ? <div className="text-xs">{doc.error}</div> : null}
                  </td>
                  <td className="py-2">
                    {doc.pages.length === 0 ? (
                      <span className="text-muted">—</span>
                    ) : (
                      <ul className="flex flex-wrap gap-x-3 text-xs">
                        {doc.pages.map((p) => (
                          <li key={p.n} className={METHOD_TONE[p.method]}>
                            <span className="num font-mono">p{p.n}</span> {METHOD_LABEL[p.method]}
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="mt-4 grid gap-3">
          <Upload busy={upload.isPending} onFiles={(files) => upload.mutate({ files, source: "client" })} />
          <Upload
            busy={upload.isPending}
            onFiles={(files) => upload.mutate({ files, source: "inz" })}
            what="An INZ letter (potentially prejudicial information or a request for information). It is read only when you prepare a reply, never as evidence."
            testId="letter-input"
          />
          {upload.isError && (
            <p role="alert" className="mt-2 text-sm text-bad">
              {errorMessage(upload.error)}
            </p>
          )}
          {upload.isSuccess && (
            <p role="status" className="mt-2 text-sm text-good">
              Uploaded {plural(upload.data.length, "file")}.
            </p>
          )}
        </div>
      </section>

      <aside className="col-span-12 grid content-start gap-6 lg:col-span-4">
        <div className="grid gap-3 border-t border-ink pt-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide">Run a check</h2>
          <button
            type="button"
            disabled={start.isPending || evidence.length === 0}
            onClick={() => start.mutate({ kind: "consistency" })}
            className="justify-self-start bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
          >
            Run consistency check
          </button>
          <label className="grid gap-1 text-sm">
            <span>Checklist</span>
            <select
              value={chosen}
              onChange={(event) => setChecklist(event.target.value)}
              className="border border-rule px-2 py-1.5"
            >
              {valid.map((c) => (
                <option key={c.skill} value={c.skill}>
                  {c.skill} (v{c.version})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={start.isPending || !chosen || evidence.length === 0}
            onClick={() => start.mutate({ kind: "presubmission", checklist_skill: chosen })}
            className="justify-self-start border border-accent px-3 py-1.5 text-sm text-accent disabled:opacity-40"
          >
            Run pre-submission check
          </button>
          {letters.length === 0 ? (
            <p className="text-sm text-muted">Upload an INZ letter to prepare a reply to it.</p>
          ) : (
            <>
              <label className="grid gap-1 text-sm">
                <span>Letter to reply to</span>
                <select
                  value={chosenLetter}
                  onChange={(event) => setLetter(event.target.value)}
                  className="border border-rule px-2 py-1.5"
                >
                  {letters.map((d) => (
                    <option key={d.doc_id} value={d.doc_id}>
                      {d.filename}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={start.isPending || !chosenLetter}
                onClick={() => start.mutate({ kind: "letter", letter_doc_id: chosenLetter })}
                className="justify-self-start border border-accent px-3 py-1.5 text-sm text-accent disabled:opacity-40"
              >
                Prepare reply
              </button>
            </>
          )}
          {checklists.isError && (
            <p role="alert" className="text-sm text-bad">
              Could not load checklists: {errorMessage(checklists.error)}
            </p>
          )}
          {start.isError && (
            <p role="alert" className="text-sm text-bad">
              {errorMessage(start.error)}
            </p>
          )}
        </div>

        <div className="grid gap-3 border-t border-ink pt-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide">Checks</h2>
          {checks.length === 0 ? (
            <Empty>No checks yet.</Empty>
          ) : (
            <ul className="grid gap-3 text-sm">
              {checks.map((check) => (
                <li key={check.check_id} data-testid="check-row" className="border-b border-rule pb-3">
                  <Link href={`/cases/${id}/checks/${check.check_id}`} className="font-medium hover:underline">
                    {checkKindLabel(check.kind)}
                  </Link>
                  <div className="font-mono text-xs text-muted">{formatWhen(check.started)}</div>
                  <div className="mt-1">
                    <StatusCounts check={check} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}
