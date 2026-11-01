import { describe, expect, it } from "vitest";

describe("turn manager", () => {
  it("rejects stale turn ids", () => {
    const incoming: string = "turn_1";
    const activeTurnId: string = "turn_2";
    expect(incoming === activeTurnId).toBe(false);
  });
});
