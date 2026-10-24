import type { Schemas } from "@/lib/api/client";

/** What the check actually read, shown above the findings (design §12.1). */
export function CoverageBar({ coverage, kind }: { coverage: Schemas["Coverage"]; kind: string }) {
  const cells: { label: string; n: number; tone?: string }[] = [
    { label: "documents", n: coverage.documents },
    { label: "failed", n: coverage.documents_failed, tone: coverage.documents_failed ? "text-bad" : undefined },
    { label: "pages", n: coverage.pages },
    { label: "transcribed", n: coverage.pages_transcribed, tone: coverage.pages_transcribed ? "text-accent" : undefined },
    { label: "unreadable", n: coverage.pages_unreadable, tone: coverage.pages_unreadable ? "text-warn" : undefined },
  ];
  if (kind === "consistency") {
    cells.push(
      { label: "facts", n: coverage.facts_accepted ?? 0 },
      { label: "facts dropped", n: coverage.facts_dropped ?? 0, tone: coverage.facts_dropped ? "text-warn" : undefined },
    );
  }
  return (
    <dl data-testid="coverage" className="grid grid-cols-3 border-y border-ink sm:grid-cols-7">
      {cells.map((cell) => (
        <div key={cell.label} className="border-r border-rule px-3 py-2 last:border-r-0">
          <dt className="text-xs uppercase tracking-wide text-muted">{cell.label}</dt>
          <dd className={`num text-xl font-medium ${cell.tone ?? ""}`}>{cell.n}</dd>
        </div>
      ))}
    </dl>
  );
}
