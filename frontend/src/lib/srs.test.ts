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
      state = nextState(state, rating, t, "UTC");
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

// ---- Review days: a day starts at 04:00 local time (mirrors backend/tests/test_srs.py) ----

/** Epoch seconds for a wall-clock time in UTC, or in Paris (UTC+1 in winter). */
function ts(y: number, m: number, d: number, h: number, min = 0, tz: "UTC" | "Paris" = "UTC"): number {
  return Date.UTC(y, m - 1, d, h, min) / 1000 - (tz === "Paris" ? 3600 : 0);
}

function reviewDueAt(dueAt: number): DirectionState {
  return { ...NEW_STATE, state: "review", due_at: dueAt, last_review_at: dueAt - 5 * DAY, stability: 5, difficulty: 5, review_count: 3, is_due: false };
}

const PARIS = "Europe/Paris";

describe("review days", () => {
  it("makes a review card due from the start of its local review day", () => {
    const state = reviewDueAt(ts(2026, 1, 10, 21, 0, "Paris"));
    expect(isDue(state, ts(2026, 1, 10, 8, 0, "Paris"), PARIS)).toBe(true);
    expect(isDue(state, ts(2026, 1, 10, 4, 0, "Paris"), PARIS)).toBe(true);
    expect(isDue(state, ts(2026, 1, 10, 3, 59, "Paris"), PARIS)).toBe(false);
    expect(isDue(state, ts(2026, 1, 9, 23, 0, "Paris"), PARIS)).toBe(false);
  });

  it("puts a due time before 4am on the previous review day", () => {
    const state = reviewDueAt(ts(2026, 1, 11, 2, 0, "Paris"));
    expect(isDue(state, ts(2026, 1, 10, 8, 0, "Paris"), PARIS)).toBe(true);
  });

  it("depends on the timezone", () => {
    const state = reviewDueAt(ts(2026, 1, 4, 3, 30)); // 03:30 UTC = 04:30 Paris
    const now = ts(2026, 1, 3, 12);
    expect(isDue(state, now, "UTC")).toBe(true);
    expect(isDue(state, now, PARIS)).toBe(false);
  });

  it("keeps learning steps minute-based", () => {
    const state = nextState(NEW_STATE, "good", T0, PARIS);
    expect(isDue(state, T0 + 5 * MINUTE, PARIS)).toBe(false);
    expect(isDue(state, T0 + 10 * MINUTE, PARIS)).toBe(true);
  });

  it("counts elapsed review days, same vector as the backend", () => {
    const t1 = ts(2026, 1, 1, 20);
    const t2 = t1 + 4 * DAY - 12 * 3600;
    const t3 = t2 + 10 * DAY + 3 * 3600;
    const t4 = t3 + 20 * DAY - 30 * 3600;
    const steps: [number, "easy" | "good" | "hard", number, number, number][] = [
      [t1, "easy", 8.2956, 1.0, ts(2026, 1, 9, 20)],
      [t2, "good", 26.1948, 1.0, ts(2026, 1, 31, 8)],
      [t3, "good", 64.5675, 1.0, ts(2026, 3, 21, 11)],
      [t4, "hard", 103.6348, 4.0106, ts(2026, 5, 18, 5)],
    ];
    let state = NEW_STATE;
    for (const [t, rating, stability, difficulty, due] of steps) {
      state = nextState(state, rating, t, "UTC");
      expect(state.state).toBe("review");
      expect(state.stability).toBeCloseTo(stability, 4);
      expect(state.difficulty).toBeCloseTo(difficulty, 4);
      expect(state.due_at).toBeCloseTo(due, 3);
    }
  });

  it("counts elapsed review days in the given timezone", () => {
    const first = ts(2026, 1, 1, 10);
    const second = ts(2026, 1, 2, 3, 30); // Jan 1's review day in UTC, Jan 2's in Paris
    const utc = nextState(nextState(NEW_STATE, "easy", first, "UTC"), "good", second, "UTC");
    const paris = nextState(nextState(NEW_STATE, "easy", first, PARIS), "good", second, PARIS);
    expect(paris.stability!).toBeGreaterThan(utc.stability!);
  });
});

describe("first_review_at", () => {
  it("is set by the first rating and kept afterwards", () => {
    expect(NEW_STATE.first_review_at).toBeNull();
    const first = nextState(NEW_STATE, "good", T0, "UTC");
    expect(first.first_review_at).toBe(T0);
    expect(nextState(first, "good", T0 + DAY, "UTC").first_review_at).toBe(T0);
  });
});
