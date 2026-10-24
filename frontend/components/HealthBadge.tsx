"use client";

import { useQuery } from "@tanstack/react-query";

import { API_URL, api } from "@/lib/api/client";
import { type HealthResult, type HealthView, healthView, toHealthResult } from "@/lib/health";

const TONE: Record<HealthView["state"], string> = {
  loading: "border-rule text-muted",
  ok: "border-good text-good",
  unhealthy: "border-bad text-bad",
  unreachable: "border-bad text-bad",
};

async function fetchHealth(): Promise<HealthResult> {
  try {
    const { data, error, response } = await api.GET("/api/health");
    return toHealthResult({ data, error, status: response.status }, API_URL);
  } catch (thrown) {
    return toHealthResult({ thrown }, API_URL);
  }
}

export function HealthBadge() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: fetchHealth, refetchInterval: 10_000 });
  const view = healthView(data);

  return (
    <div className="flex flex-col items-end gap-1">
      <p
        role="status"
        data-testid="health-badge"
        data-state={view.state}
        className={`rounded border px-2 py-0.5 text-sm ${TONE[view.state]}`}
      >
        {view.label}
      </p>
      {view.detail && (
        <p data-testid="health-detail" className="max-w-md text-right text-xs text-muted">
          {view.detail}
        </p>
      )}
      {view.synthetic && (
        <p data-testid="data-class-banner" className="text-xs font-semibold uppercase tracking-wide">
          Synthetic data only
        </p>
      )}
    </div>
  );
}
