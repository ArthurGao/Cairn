import type { Schemas } from "@/lib/api/client";
import { formatWhen, plural } from "@/lib/format";

/** Who signs off, what still blocks it, and the record once it is done (design §8.6). */
export function SignOffPanel({
  view,
  adviser,
  onAdviser,
  onSignOff,
}: {
  view: Schemas["CheckView"];
  adviser: string;
  onAdviser: (name: string) => void;
  onSignOff: () => void;
}) {
  return (
    <div className="grid gap-3 border-t border-ink pt-4" data-testid="signoff">
      <h2 className="text-sm font-semibold uppercase tracking-wide">Adviser sign-off</h2>
      {view.signed_off ? (
        <p className="text-sm text-good">
          Signed off by <span className="font-medium">{view.signed_off.adviser}</span> on{" "}
          {formatWhen(view.signed_off.at)}.
        </p>
      ) : (
        <>
          <label className="grid gap-1 text-sm">
            <span>Your name (recorded with every review)</span>
            <input
              value={adviser}
              onChange={(event) => onAdviser(event.target.value)}
              className="border border-rule px-2 py-1.5"
            />
          </label>
          <p className="text-sm" data-testid="blockers">
            {view.blockers.length === 0
              ? "Every finding is settled."
              : `${plural(view.blockers.length, "finding")} to settle: ${view.blockers.join(", ")}`}
          </p>
          <button
            type="button"
            disabled={view.blockers.length > 0 || !adviser.trim()}
            onClick={onSignOff}
            className="justify-self-start bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
          >
            Sign off
          </button>
        </>
      )}
    </div>
  );
}
