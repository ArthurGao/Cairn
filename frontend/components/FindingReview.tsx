import type { ReviewAction } from "@/lib/api/queries";
import { ACTION_LABEL, ACTION_VERB } from "@/lib/format";

/** A finding's review state and the actions an adviser can take on it. */
export function FindingReview({
  findingId,
  state,
  note,
  locked,
  onAction,
}: {
  findingId: string;
  state: ReviewAction | undefined;
  note: string | undefined;
  locked: boolean;
  onAction: (action: ReviewAction) => void;
}) {
  const offered: ReviewAction[] =
    state && state !== "reopened" ? ["reopened"] : ["confirmed", "dismissed", "resolved"];
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span data-testid={`review-${findingId}`} className={state ? "font-medium" : "text-muted"}>
        {state ? ACTION_LABEL[state] : "Not reviewed"}
        {state && note ? <span className="font-normal text-muted"> — {note}</span> : null}
      </span>
      {!locked &&
        offered.map((action) => (
          <button
            key={action}
            type="button"
            aria-label={`${ACTION_VERB[action]} finding ${findingId}`}
            onClick={() => onAction(action)}
            className="border border-rule px-2 py-0.5 hover:border-ink"
          >
            {ACTION_VERB[action]}
          </button>
        ))}
    </div>
  );
}
