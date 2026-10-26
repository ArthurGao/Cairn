import { describe, expect, it } from "vitest";

import type { Schemas } from "@/lib/api/client";
import { healthView, toHealthResult } from "@/lib/health";

const BASE = "http://localhost:4700";
const OK_BODY = {
  status: "ok",
  data_class: "synthetic",
  temporal: "ok",
  home: "../workspace",
  cases: "../.cases",
  build: "",
} as const;

describe("toHealthResult", () => {
  it("maps a 200 body to ok", () => {
    expect(toHealthResult({ data: OK_BODY, status: 200 }, BASE)).toEqual({ kind: "ok", body: OK_BODY });
  });

  it("maps a 503 error body to unhealthy with the API's message", () => {
    const error = { error: { code: "unhealthy", message: "temporal: unreachable at localhost:7233 (x)" } };
    expect(toHealthResult({ error, status: 503 }, BASE)).toEqual({
      kind: "unhealthy",
      message: "temporal: unreachable at localhost:7233 (x)",
    });
  });

  it("says so when an error response has no message", () => {
    const proxyBody = "Bad Gateway" as unknown as Schemas["ErrorResponse"];
    expect(toHealthResult({ error: proxyBody, status: 502 }, BASE)).toEqual({
      kind: "unhealthy",
      message: "HTTP 502 with no error message",
    });
  });

  it("maps a thrown fetch to unreachable", () => {
    expect(toHealthResult({ thrown: new TypeError("Failed to fetch") }, BASE)).toEqual({
      kind: "unreachable",
      baseUrl: BASE,
    });
  });
});

describe("healthView", () => {
  it("renders loading before the first result", () => {
    expect(healthView(undefined)).toEqual({
      state: "loading",
      label: "Checking API…",
      detail: null,
      synthetic: false,
    });
  });

  it("flags synthetic data on a healthy API", () => {
    expect(healthView({ kind: "ok", body: OK_BODY })).toEqual({
      state: "ok",
      label: "API healthy",
      detail: null,
      synthetic: true,
    });
  });

  it("does not flag synthetic for client data", () => {
    expect(healthView({ kind: "ok", body: { ...OK_BODY, data_class: "client" } }).synthetic).toBe(false);
  });

  it("shows the unhealthy message as detail", () => {
    expect(healthView({ kind: "unhealthy", message: "home: /x has no AGENTS.md" })).toEqual({
      state: "unhealthy",
      label: "API unhealthy",
      detail: "home: /x has no AGENTS.md",
      synthetic: false,
    });
  });

  it("names the URL it could not reach", () => {
    expect(healthView({ kind: "unreachable", baseUrl: BASE })).toEqual({
      state: "unreachable",
      label: "API unreachable",
      detail: "No response from http://localhost:4700",
      synthetic: false,
    });
  });
});
