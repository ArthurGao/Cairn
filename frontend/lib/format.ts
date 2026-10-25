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

const KIND_LABEL = {
  consistency: "Consistency check",
  presubmission: "Pre-submission check",
  letter: "INZ letter reply",
} as const satisfies Record<CheckKind, string>;

export function checkKindLabel(kind: CheckKind): string {
  return KIND_LABEL[kind];
}

const DAY = new Intl.DateTimeFormat("en-NZ", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

/** A calendar date (`2026-11-07`) as people write it: 7 November 2026. */
export function formatDay(isoDate: string): string {
  return DAY.format(new Date(`${isoDate}T00:00:00Z`));
}

/** Working days to a deadline, as the API counts them (Monday to Friday, from tomorrow). */
export function workingDaysLabel(days: number): string {
  if (days < 0) return `${plural(-days, "working day")} overdue`;
  if (days === 0) return "no working days left";
  return `${plural(days, "working day")} left`;
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
