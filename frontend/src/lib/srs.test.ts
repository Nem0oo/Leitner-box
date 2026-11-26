import { describe, expect, it } from "vitest";
import { type DirectionState, NEW_STATE, formatInterval, isDue, nextState, previewIntervals } from "./srs";

const T0 = Date.UTC(2026, 0, 1, 8, 0) / 1000;
const MINUTE = 60;
const DAY = 86400;

describe("nextState", () => {
  it("matches the FSRS-6 reference sequence shared with backend/tests/test_srs.py", () => {
    const expected: [DirectionState["state"], number, number, number][] = [
      ["learning", 2.3065, 2.1181, T0 + 10 * MINUTE],
      ["review", 2.3065, 2.1112, T0 + 10 * MINUTE + 2 * DAY],
      ["review", 10.971, 2.1043, T0 + 10 * MINUTE + 13 * DAY],
      ["relearning", 1.539, 7.39, T0 + 20 * MINUTE + 13 * DAY],
      ["review", 1.5718, 7.3778, T0 + 20 * MINUTE + 15 * DAY],
    ];
    let state = NEW_STATE;
    let t = T0;
    for (const [i, rating] of (["good", "good", "good", "again", "good"] as const).entries()) {
      state = nextState(state, rating, t);
      const [name, stability, difficulty, due] = expected[i];
      expect(state.state).toBe(name);
      expect(state.stability).toBeCloseTo(stability, 4);
      expect(state.difficulty).toBeCloseTo(difficulty, 4);
      expect(state.due_at).toBeCloseTo(due, 3);
      expect(state.last_review_at).toBe(t);
      t = state.due_at!;
    }
    expect(state.review_count).toBe(5);
  });

  it("puts a new card straight into review on easy", () => {
    const state = nextState(NEW_STATE, "easy", T0);
    expect(state.state).toBe("review");
    expect(state.step).toBeNull();
    expect(state.due_at!).toBeGreaterThan(T0 + DAY);
  });

  it("keeps is_due false right after a review", () => {
    expect(nextState(NEW_STATE, "again", T0).is_due).toBe(false);
  });
});

describe("isDue", () => {
  it("is always due for a new card", () => {
    expect(isDue(NEW_STATE, 0)).toBe(true);
  });

  it("follows due_at", () => {
    const state = nextState(NEW_STATE, "good", T0);
    expect(isDue(state, state.due_at! - 1)).toBe(false);
    expect(isDue(state, state.due_at!)).toBe(true);
  });
});

describe("previewIntervals", () => {
  it("gives the learning steps for a new card", () => {
    const preview = previewIntervals(NEW_STATE, T0);
    expect(preview.again).toBe(1 * MINUTE);
    expect(preview.good).toBe(10 * MINUTE);
    expect(preview.easy).toBeGreaterThan(DAY);
    expect(preview.hard).toBeGreaterThanOrEqual(preview.again);
    expect(preview.hard).toBeLessThanOrEqual(preview.good);
  });
});

describe("formatInterval", () => {
  it("formats minutes, hours, days, months and years in French", () => {
    expect(formatInterval(30)).toBe("< 1 min");
    expect(formatInterval(10 * MINUTE)).toBe("10 min");
    expect(formatInterval(3 * 3600)).toBe("3 h");
    expect(formatInterval(4 * DAY)).toBe("4 j");
    expect(formatInterval(65 * DAY)).toBe("2,1 mois");
    expect(formatInterval(500 * DAY)).toBe("1,4 an");
  });
});
