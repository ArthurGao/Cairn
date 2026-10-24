import { describe, expect, it } from "vitest";

import { ApiError, errorMessage, unwrap } from "@/lib/api/fetch";
import { plural, timeLeft } from "@/lib/format";
import { highlight } from "@/lib/highlight";

const response = (status: number) => new Response(null, { status });

describe("highlight", () => {
  it("marks a quote across line breaks, like the backend's whitespace rule", () => {
    expect(highlight("employed as Warehouse Supervisor\nsince 1 June 2022.", "Supervisor since 1 June")).toEqual([
      { text: "employed as Warehouse ", mark: false },
      { text: "Supervisor\nsince 1 June", mark: true },
      { text: " 2022.", mark: false },
    ]);
  });

  it("is case-sensitive and escapes regex characters", () => {
    expect(highlight("Total (NZD) 1.00", "(NZD) 1.00")).toEqual([
      { text: "Total ", mark: false },
      { text: "(NZD) 1.00", mark: true },
    ]);
    expect(highlight("since 1 June", "SINCE 1 june")).toEqual([{ text: "since 1 June", mark: false }]);
  });

  it("leaves text unmarked for an empty quote", () => {
    expect(highlight("abc", "  ")).toEqual([{ text: "abc", mark: false }]);
  });
});

describe("unwrap", () => {
  it("returns data", () => {
    expect(unwrap({ data: [1], response: response(200) })).toEqual([1]);
  });

  it("throws the API's own message and code", () => {
    const error = { error: { code: "note_required", message: "dismissing a finding needs a note" } };
    expect(() => unwrap({ error, response: response(422) })).toThrowError(
      new ApiError(422, "note_required", "dismissing a finding needs a note"),
    );
  });

  it("says so when the error has no body", () => {
    expect(() => unwrap({ error: "Bad Gateway", response: response(502) })).toThrowError(
      "HTTP 502 with no error message",
    );
  });
});

describe("format", () => {
  it("pluralises", () => {
    expect([plural(1, "page"), plural(2, "page"), plural(0, "gap")]).toEqual(["1 page", "2 pages", "0 gaps"]);
  });

  it("explains network failures", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toBe("The API could not be reached (Failed to fetch)");
  });
});

describe("timeLeft", () => {
  const now = Date.parse("2026-10-24T03:00:00Z");
  it("counts down in days, hours and minutes", () => {
    expect(timeLeft("2026-10-30T02:59:00Z", now)).toBe("5 days 23 h left");
    expect(timeLeft("2026-10-25T03:30:00Z", now)).toBe("1 day 0 h left");
    expect(timeLeft("2026-10-24T05:12:00Z", now)).toBe("2 h 12 min left");
    expect(timeLeft("2026-10-24T03:45:30Z", now)).toBe("45 min left");
  });
  it("says expired at and after the deadline", () => {
    expect(timeLeft("2026-10-24T03:00:00Z", now)).toBe("expired");
    expect(timeLeft("2026-10-20T00:00:00Z", now)).toBe("expired");
  });
});
