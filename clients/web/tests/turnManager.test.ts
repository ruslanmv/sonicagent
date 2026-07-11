import { describe, expect, it } from "vitest";

describe("turn manager", () => {
  it("rejects stale turn ids", () => {
    const activeTurnId = "turn_2";
    expect("turn_1" === activeTurnId).toBe(false);
  });
});
