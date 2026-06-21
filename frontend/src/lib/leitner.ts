/**
 * Client-side mirror of backend/app/leitner.py, used only to give immediate
 * optimistic UI feedback (box badge, due filtering) while offline review
 * events sit in the local queue waiting to be pushed. The server is always
 * the source of truth once synced.
 */

export const MIN_BOX = 1;
export const MAX_BOX = 5;

export const DIRECTIONS = ["recto_to_verso", "verso_to_recto"] as const;
export type Direction = (typeof DIRECTIONS)[number];

export const RESULT_SUCCESS = "success";
export const RESULT_FAIL = "fail";
export type ReviewResult = typeof RESULT_SUCCESS | typeof RESULT_FAIL;

export const BOX_INTERVAL_DAYS: Record<number, number> = {
  1: 1,
  2: 2,
  3: 4,
  4: 8,
  5: 16,
};

const SECONDS_PER_DAY = 86400;

export function nextBox(currentBox: number, result: ReviewResult): number {
  if (result === RESULT_SUCCESS) return Math.min(currentBox + 1, MAX_BOX);
  if (result === RESULT_FAIL) return MIN_BOX;
  throw new Error(`Unknown review result: ${result}`);
}

export function dueAt(box: number, lastReviewAt: number | null): number | null {
  if (lastReviewAt === null) return null;
  return lastReviewAt + BOX_INTERVAL_DAYS[box] * SECONDS_PER_DAY;
}

export function isDue(box: number, lastReviewAt: number | null, now: number): boolean {
  if (lastReviewAt === null) return true;
  const due = dueAt(box, lastReviewAt);
  return due !== null && now >= due;
}
