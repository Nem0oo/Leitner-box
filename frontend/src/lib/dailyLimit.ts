/**
 * Daily limit on new cards, mirror of select_due / new_cards_introduced_on in
 * backend/app/srs.py: at most `newCardsPerDay` cards get their first rating
 * per review day and per direction, taken in creation order (card id).
 */
import { type DirectionState, isDue, reviewDay } from "./srs";

export const DEFAULT_NEW_CARDS_PER_DAY = 10;

/** How many of `states` had their first rating on the review day of `now`. */
export function newCardsIntroducedOn(states: Iterable<DirectionState>, now: number, timeZone?: string): number {
  const today = reviewDay(now, timeZone);
  let count = 0;
  for (const s of states) {
    if (s.first_review_at != null && reviewDay(s.first_review_at, timeZone) === today) count++;
  }
  return count;
}

/** Items to review now: every due card already introduced, then at most
 * `newSlots` new cards in creation order. */
export function selectDue<T extends { id: number; state: DirectionState }>(
  items: T[],
  now: number,
  newSlots: number,
  timeZone?: string,
): T[] {
  const sorted = [...items].sort((a, b) => a.id - b.id);
  const started = sorted.filter((i) => i.state.state !== "new" && isDue(i.state, now, timeZone));
  const fresh = sorted.filter((i) => i.state.state === "new");
  return [...started, ...fresh.slice(0, Math.max(newSlots, 0))];
}
