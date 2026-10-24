import { diffLines } from "@/lib/diff";

/** Line diff of a memory change; deletions red, additions green (design §12.3 semantics). */
export function OpDiff({ before, after }: { before: string | null; after: string | null }) {
  if (after === null && before !== null) {
    return <p className="text-xs text-muted">Moved to memory/_archive/ (restorable).</p>;
  }
  const rows = diffLines(before, after);
  return (
    <pre data-testid="op-diff" className="overflow-auto border border-rule font-mono text-xs leading-relaxed">
      {rows.map((row, n) => (
        <div
          key={n}
          className={row.kind === "add" ? "bg-good-wash" : row.kind === "del" ? "bg-bad-wash" : ""}
        >
          <span aria-hidden className="inline-block w-5 select-none pl-1 text-muted">
            {row.kind === "add" ? "+" : row.kind === "del" ? "−" : " "}
          </span>
          <span className="sr-only">{row.kind === "add" ? "added: " : row.kind === "del" ? "removed: " : ""}</span>
          {row.text}
        </div>
      ))}
    </pre>
  );
}
