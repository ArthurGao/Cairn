import type { Schemas } from "./api/client";

/** What one health request produced; never thrown, so the badge can render every case. */
export type HealthResult =
  | { kind: "ok"; body: Schemas["HealthOk"] }
  | { kind: "unhealthy"; message: string }
  | { kind: "unreachable"; baseUrl: string };

export type HealthView = {
  state: "loading" | "ok" | "unhealthy" | "unreachable";
  label: string;
  detail: string | null;
  synthetic: boolean;
};

/** Turn an openapi-fetch outcome (or a thrown fetch) into a HealthResult. */
export function toHealthResult(
  outcome:
    | { data?: Schemas["HealthOk"]; error?: Schemas["ErrorResponse"]; status: number }
    | { thrown: unknown },
  baseUrl: string,
): HealthResult {
  if ("thrown" in outcome) return { kind: "unreachable", baseUrl };
  if (outcome.data) return { kind: "ok", body: outcome.data };
  // Every API error has the ErrorResponse shape (design §11); a proxy in between may not.
  const message = outcome.error?.error?.message ?? `HTTP ${outcome.status} with no error message`;
  return { kind: "unhealthy", message };
}

export function healthView(result: HealthResult | undefined): HealthView {
  if (!result) return { state: "loading", label: "Checking API…", detail: null, synthetic: false };
  switch (result.kind) {
    case "ok":
      return {
        state: "ok",
        label: "API healthy",
        detail: null,
        synthetic: result.body.data_class === "synthetic",
      };
    case "unhealthy":
      return { state: "unhealthy", label: "API unhealthy", detail: result.message, synthetic: false };
    case "unreachable":
      return {
        state: "unreachable",
        label: "API unreachable",
        detail: `No response from ${result.baseUrl}`,
        synthetic: false,
      };
  }
}
