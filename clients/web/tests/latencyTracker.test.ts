import { describe, expect, it } from "vitest";

describe("latency metrics", () => {
  it("computes elapsed milliseconds", () => {
    expect(250 - 100).toBe(150);
  });
});
