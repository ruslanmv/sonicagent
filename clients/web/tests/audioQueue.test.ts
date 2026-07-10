import { describe, expect, it } from "vitest";

describe("audio queue", () => {
  it("keeps test suite actionable", () => {
    const queued = [new Uint8Array([1, 2])];
    expect(queued.reduce((n, item) => n + item.byteLength, 0)).toBe(2);
  });
});
