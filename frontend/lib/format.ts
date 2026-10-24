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
