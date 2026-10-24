import type { Schemas } from "@/lib/api/client";

type Status = Schemas["CleanupState"]["status"];

/** Cleanup statuses (design §7.4) the UI polls through, and how each reads. */
export const CLEANUP_ACTIVE: ReadonlySet<Status> = new Set<Status>(["linting", "drafting", "applying"]);

const TONE: Partial<Record<Status, string>> = {
  awaiting_review: "text-warn",
  applied: "text-good",
  failed: "text-bad",
  expired: "text-muted",
  rejected: "text-muted",
};

export function CleanupStatus({ status }: { status: Status }) {
  return <span className={TONE[status] ?? ""}>{status.replaceAll("_", " ")}</span>;
}
