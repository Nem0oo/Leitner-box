import { describe, expect, it } from "vitest";
import { MAX_BOX, MIN_BOX, dueAt, isDue, nextBox } from "./leitner";

describe("nextBox", () => {
  it("climbs one box on success", () => {
    expect(nextBox(1, "success")).toBe(2);
    expect(nextBox(3, "success")).toBe(4);
  });

  it("caps at MAX_BOX on success", () => {
    expect(nextBox(MAX_BOX, "success")).toBe(MAX_BOX);
  });

  it("resets to MIN_BOX on fail", () => {
    expect(nextBox(5, "fail")).toBe(MIN_BOX);
    expect(nextBox(1, "fail")).toBe(MIN_BOX);
  });
});

describe("dueAt / isDue", () => {
  it("is always due when never reviewed", () => {
    expect(isDue(1, null, 0)).toBe(true);
    expect(dueAt(1, null)).toBeNull();
  });

  it("is not due before the box interval elapses", () => {
    const last = 1000;
    const almostDue = dueAt(2, last)! - 1;
    expect(isDue(2, last, almostDue)).toBe(false);
  });

  it("is due once the box interval elapses", () => {
    const last = 1000;
    const due = dueAt(2, last)!;
    expect(isDue(2, last, due)).toBe(true);
  });
});
