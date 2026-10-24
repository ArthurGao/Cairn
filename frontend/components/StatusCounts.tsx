import type { Schemas } from "@/lib/api/client";

/** Counts, never a single pass/fail badge (design §12.2). */
export function StatusCounts({ check }: { check: Schemas["CheckBrief"] }) {
  if (check.status === "running") return <span className="text-muted">Running…</span>;
  if (check.status === "failed" || !check.counts) return <span className="text-bad">Failed</span>;
  const c = check.counts;
  const parts =
    check.kind === "consistency"
      ? [
          { n: c.conflicts, label: "conflicts", tone: c.conflicts ? "text-bad" : "" },
          { n: c.gaps, label: "gaps", tone: c.gaps ? "text-warn" : "" },
        ]
      : [
          { n: c.checked, label: "checked", tone: "text-good" },
          { n: c.pending, label: "pending", tone: c.pending ? "text-bad" : "" },
          { n: c.unable, label: "unable", tone: c.unable ? "text-warn" : "" },
          { n: c.gaps, label: "gaps", tone: c.gaps ? "text-warn" : "" },
        ];
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-0.5" data-testid="status-counts">
      {parts.map((p) => (
        <span key={p.label} className={p.tone}>
          <span className="num font-medium">{p.n}</span> {p.label}
        </span>
      ))}
      {check.signed_off ? <span className="text-good">signed off</span> : null}
    </span>
  );
}
