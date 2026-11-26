/**
 * Review session queue. Cards answered while still in FSRS learning or
 * relearning steps (due again within minutes) are re-injected into the
 * session: they come back as soon as they are due, ahead of the remaining
 * cards, and are served early when nothing else is left (learn-ahead), so a
 * session only ends once every card has left its short-term steps.
 */
import type { DirectionState } from "./srs";

/** How far ahead a not-yet-due re-injected card may be served when the queue is otherwise empty. */
export const LEARN_AHEAD_SECONDS = 20 * 60;

/** Only steps due within this window are re-injected into the current session. */
const REINJECT_WINDOW_SECONDS = 60 * 60;

interface Pending<T> {
  card: T;
  due: number;
}

export interface SessionQueue<T extends { id: number }> {
  main: T[];
  learning: Pending<T>[];
}

export function createQueue<T extends { id: number }>(cards: T[]): SessionQueue<T> {
  return { main: [...cards], learning: [] };
}

export function currentCard<T extends { id: number }>(q: SessionQueue<T>, now: number): T | null {
  const earliest = q.learning[0];
  if (earliest && earliest.due <= now) return earliest.card;
  if (q.main.length > 0) return q.main[0];
  if (earliest && earliest.due <= now + LEARN_AHEAD_SECONDS) return earliest.card;
  return null;
}

export function afterAnswer<T extends { id: number }>(
  q: SessionQueue<T>,
  card: T,
  newState: DirectionState,
  now: number,
): SessionQueue<T> {
  const main = q.main.filter((c) => c.id !== card.id);
  const learning = q.learning.filter((p) => p.card.id !== card.id);
  const inSteps = newState.state === "learning" || newState.state === "relearning";
  if (inSteps && newState.due_at !== null && newState.due_at - now <= REINJECT_WINDOW_SECONDS) {
    learning.push({ card, due: newState.due_at });
    learning.sort((x, y) => x.due - y.due);
  }
  return { main, learning };
}

export function remainingCount<T extends { id: number }>(q: SessionQueue<T>): number {
  return q.main.length + q.learning.length;
}
