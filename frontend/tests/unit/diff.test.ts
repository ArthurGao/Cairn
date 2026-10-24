import { describe, expect, it } from "vitest";

import { diffLines } from "@/lib/diff";

describe("diffLines", () => {
  it("marks changed lines and keeps the common ones in order", () => {
    expect(diffLines("a\nb\nc\n", "a\nB\nc\nd\n")).toEqual([
      { kind: "same", text: "a" },
      { kind: "del", text: "b" },
      { kind: "add", text: "B" },
      { kind: "same", text: "c" },
      { kind: "add", text: "d" },
    ]);
  });

  it("treats a missing side as empty (create, archive)", () => {
    expect(diffLines(null, "x\ny")).toEqual([
      { kind: "add", text: "x" },
      { kind: "add", text: "y" },
    ]);
    expect(diffLines("x", null)).toEqual([{ kind: "del", text: "x" }]);
  });

  it("returns nothing for two empty texts", () => {
    expect(diffLines("", "")).toEqual([]);
  });
});
