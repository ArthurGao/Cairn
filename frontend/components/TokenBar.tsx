import type { Schemas } from "@/lib/api/client";

/** L0 parts and what the run loaded, against loading everything eagerly (design §5). */
export function TokenBar({ breakdown, loaded = 0 }: { breakdown: Schemas["ContextBreakdown"]; loaded?: number }) {
  const total = Math.max(breakdown.baseline_all, breakdown.l0_total + loaded, 1);
  const parts = [
    { label: "AGENTS.md", n: breakdown.agents_md, tone: "bg-ink" },
    { label: "skill index", n: breakdown.skill_index, tone: "bg-accent" },
    { label: "memory index", n: breakdown.memory_index, tone: "bg-muted" },
    { label: "loaded on demand", n: loaded, tone: "bg-warn" },
  ];
  const used = breakdown.l0_total + loaded;
  return (
    <figure data-testid="token-bar" className="grid gap-2">
      <div className="flex h-3 w-full border border-ink" aria-hidden>
        {parts.map((p) => (
          <div key={p.label} className={p.tone} style={{ width: `${(100 * p.n) / total}%` }} />
        ))}
      </div>
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-xs">
        {parts.map((p) => (
          <span key={p.label}>
            <span className={`mr-1 inline-block h-2 w-2 ${p.tone}`} aria-hidden />
            {p.label} <span className="num font-mono">{p.n}</span>
          </span>
        ))}
        <span className="font-medium">
          used <span className="num font-mono">{used}</span> of{" "}
          <span className="num font-mono">{breakdown.baseline_all}</span> if everything were loaded (estimated)
        </span>
        {breakdown.omitted_index_lines > 0 && (
          <span className="text-warn">{breakdown.omitted_index_lines} memory index lines omitted (over budget)</span>
        )}
      </figcaption>
    </figure>
  );
}
