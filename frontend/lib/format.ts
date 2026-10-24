import type { CheckKind } from "@/lib/api/queries";

const DATE = new Intl.DateTimeFormat("en-NZ", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Pacific/Auckland",
});

export function formatWhen(iso: string): string {
  return DATE.format(new Date(iso));
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

export function checkKindLabel(kind: CheckKind): string {
  return kind === "consistency" ? "Consistency check" : "Pre-submission check";
}

export const ACTION_LABEL = {
  confirmed: "Confirmed",
  dismissed: "Dismissed",
  resolved: "Resolved",
  reopened: "Reopened",
} as const;

export const ACTION_VERB = {
  confirmed: "Confirm",
  dismissed: "Dismiss",
  resolved: "Resolve",
  reopened: "Reopen",
} as const;

/** Time left before a review deadline, coarse enough to read at a glance. */
export function timeLeft(deadlineIso: string, nowMs: number): string {
  const minutes = Math.floor((new Date(deadlineIso).getTime() - nowMs) / 60_000);
  if (minutes <= 0) return "expired";
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  if (days > 0) return `${plural(days, "day")} ${hours} h left`;
  return hours > 0 ? `${hours} h ${minutes % 60} min left` : `${minutes} min left`;
}
