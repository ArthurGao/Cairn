import { describe, expect, it } from "vitest";

import {
  SESSION_TTL_SECONDS,
  credentialsMatch,
  gateFrom,
  safeNext,
  signSession,
  verifySession,
} from "@/lib/auth/session";

const CONFIG = { user: "demo", password: "correct horse", secret: "s".repeat(32) };
const NOW = Date.UTC(2026, 9, 26, 9, 0, 0);

describe("gateFrom", () => {
  it("is off locally when nothing is set", () => {
    expect(gateFrom({})).toEqual({ kind: "off" });
  });

  it("is on when all three are set", () => {
    const env = { DEMO_USER: "demo", DEMO_PASSWORD: "pw", SESSION_SECRET: "x" };
    expect(gateFrom(env)).toEqual({ kind: "on", config: { user: "demo", password: "pw", secret: "x" } });
  });

  it("fails closed on Vercel with nothing set, and anywhere with a partial set", () => {
    expect(gateFrom({ VERCEL: "1" })).toEqual({
      kind: "broken",
      missing: ["DEMO_USER", "DEMO_PASSWORD", "SESSION_SECRET"],
    });
    expect(gateFrom({ DEMO_USER: "demo", DEMO_PASSWORD: "pw" })).toEqual({
      kind: "broken",
      missing: ["SESSION_SECRET"],
    });
  });
});

describe("sessions", () => {
  it("verifies its own token until it expires", async () => {
    const token = await signSession("demo", CONFIG.secret, NOW);
    expect(await verifySession(token, CONFIG, NOW)).toBe(true);
    expect(await verifySession(token, CONFIG, NOW + (SESSION_TTL_SECONDS - 1) * 1000)).toBe(true);
    expect(await verifySession(token, CONFIG, NOW + SESSION_TTL_SECONDS * 1000)).toBe(false);
  });

  it("refuses a token signed with another secret, for another user, or edited", async () => {
    const token = await signSession("demo", CONFIG.secret, NOW);
    expect(await verifySession(token, { ...CONFIG, secret: "t".repeat(32) }, NOW)).toBe(false);
    expect(await verifySession(token, { ...CONFIG, user: "other" }, NOW)).toBe(false);
    const [expires, signature] = token.split(".");
    expect(await verifySession(`${Number(expires) + 3600}.${signature}`, CONFIG, NOW)).toBe(false);
    expect(await verifySession("not-a-token", CONFIG, NOW)).toBe(false);
    expect(await verifySession(`${expires}.${"0".repeat(64)}`, CONFIG, NOW)).toBe(false);
  });
});

describe("credentialsMatch", () => {
  it("accepts exactly the configured user and password", async () => {
    expect(await credentialsMatch("demo", "correct horse", CONFIG)).toBe(true);
    expect(await credentialsMatch("demo", "correct hors", CONFIG)).toBe(false);
    expect(await credentialsMatch("Demo", "correct horse", CONFIG)).toBe(false);
    // The separator keeps "de" + "mo\0correct horse"-style splits apart.
    expect(await credentialsMatch("demo\u0000correct", "horse", CONFIG)).toBe(false);
  });
});

describe("safeNext", () => {
  it("keeps local paths and drops anything that could leave the site", () => {
    expect(safeNext("/cases/01CASE")).toBe("/cases/01CASE");
    expect(safeNext(null)).toBe("/cases");
    expect(safeNext("https://evil.example")).toBe("/cases");
    expect(safeNext("//evil.example")).toBe("/cases");
    expect(safeNext("/\\evil.example")).toBe("/cases");
    // Browsers drop tabs and newlines in URLs, so these would become //evil.example.
    expect(safeNext("/\t/evil.example")).toBe("/cases");
    expect(safeNext("/\n/evil.example")).toBe("/cases");
    expect(safeNext("/cases?tab=checks#top")).toBe("/cases?tab=checks#top");
  });
});
