import type { ReactNode } from "react";

import { errorMessage } from "@/lib/api/fetch";

/** Every data view renders loading, empty, error and success explicitly (frontend/AGENTS.md). */
export function Loading({ label }: { label: string }) {
  return (
    <p role="status" data-testid="loading" className="py-6 text-sm text-muted">
      {label}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div data-testid="empty" className="border-y border-rule py-6 text-sm text-muted">
      {children}
    </div>
  );
}

export function ErrorState({ error, what }: { error: unknown; what: string }) {
  return (
    <div role="alert" data-testid="error" className="border-l-4 border-bad bg-bad-wash px-4 py-3 text-sm">
      <p className="font-medium">Could not load {what}.</p>
      <p className="mt-1">{errorMessage(error)}</p>
    </div>
  );
}
