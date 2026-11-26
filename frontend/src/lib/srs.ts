/**
 * Client-side mirror of backend/app/srs.py (FSRS-6, default parameters,
 * fuzz disabled), used for immediate optimistic updates while review events
 * wait in the offline queue. The server replays the full ReviewEvent history
 * and stays the source of truth once synced; both sides are checked against
 * the same reference sequence in their tests.
 */
import { type Card, type Grade, Rating, State, createEmptyCard, fsrs, generatorParameters } from "ts-fsrs";

export const DIRECTIONS = ["recto_to_verso", "verso_to_recto"] as const;
export type Direction = (typeof DIRECTIONS)[number];

export const RATINGS = ["again", "hard", "good", "easy"] as const;
export type ReviewRating = (typeof RATINGS)[number];

export type SrsState = "new" | "learning" | "review" | "relearning";

export interface DirectionState {
  state: SrsState;
  step: number | null;
  stability: number | null;
  difficulty: number | null;
  last_review_at: number | null;
  due_at: number | null;
  is_due: boolean;
  review_count: number;
}

export const NEW_STATE: DirectionState = {
  state: "new",
  step: null,
  stability: null,
  difficulty: null,
  last_review_at: null,
  due_at: null,
  is_due: true,
  review_count: 0,
};

export const RATING_LABELS: Record<ReviewRating, string> = {
  again: "À revoir",
  hard: "Difficile",
  good: "Bien",
  easy: "Facile",
};

export const STATE_LABELS: Record<SrsState, string> = {
  new: "Nouvelle",
  learning: "Apprentissage",
  review: "Révision",
  relearning: "Réapprentissage",
};

const scheduler = fsrs(generatorParameters({ enable_fuzz: false }));

const GRADE: Record<ReviewRating, Grade> = {
  again: Rating.Again,
  hard: Rating.Hard,
  good: Rating.Good,
  easy: Rating.Easy,
};

const TO_FSRS_STATE: Record<SrsState, State> = {
  new: State.New,
  learning: State.Learning,
  review: State.Review,
  relearning: State.Relearning,
};

const FROM_FSRS_STATE: Record<State, SrsState> = {
  [State.New]: "new",
  [State.Learning]: "learning",
  [State.Review]: "review",
  [State.Relearning]: "relearning",
};

function toDate(seconds: number): Date {
  return new Date(seconds * 1000);
}

function toFsrsCard(s: DirectionState, now: number): Card {
  if (s.state === "new" || s.last_review_at === null || s.due_at === null) return createEmptyCard(toDate(now));
  return {
    due: toDate(s.due_at),
    stability: s.stability ?? 0,
    difficulty: s.difficulty ?? 0,
    elapsed_days: 0,
    scheduled_days: 0,
    learning_steps: s.step ?? 0,
    reps: s.review_count,
    lapses: 0,
    state: TO_FSRS_STATE[s.state],
    last_review: toDate(s.last_review_at),
  };
}

function fromFsrsCard(card: Card, reviewedAt: number, reviewCount: number): DirectionState {
  const state = FROM_FSRS_STATE[card.state];
  const inSteps = state === "learning" || state === "relearning";
  return {
    state,
    step: inSteps ? card.learning_steps : null,
    stability: card.stability,
    difficulty: card.difficulty,
    last_review_at: reviewedAt,
    due_at: card.due.getTime() / 1000,
    is_due: false,
    review_count: reviewCount,
  };
}

/** State after reviewing `s` with `rating` at `now` (epoch seconds). */
export function nextState(s: DirectionState, rating: ReviewRating, now: number): DirectionState {
  const { card } = scheduler.next(toFsrsCard(s, now), toDate(now), GRADE[rating]);
  return fromFsrsCard(card, now, s.review_count + 1);
}

/** Seconds until the card would be due again, for each possible rating. */
export function previewIntervals(s: DirectionState, now: number): Record<ReviewRating, number> {
  const out = {} as Record<ReviewRating, number>;
  for (const rating of RATINGS) {
    out[rating] = Math.round((nextState(s, rating, now).due_at ?? now) - now);
  }
  return out;
}

export function isDue(s: DirectionState, now: number): boolean {
  return s.due_at === null || now >= s.due_at;
}

const HOUR = 3600;
const DAY = 86400;
const MONTH = 30.44 * DAY;
const YEAR = 365.25 * DAY;

function decimal(value: number): string {
  return value.toFixed(1).replace(".", ",").replace(/,0$/, "");
}

/** Short French label for a duration in seconds ("10 min", "4 j", "2,1 mois"). */
export function formatInterval(seconds: number): string {
  if (seconds < 60) return "< 1 min";
  if (seconds < HOUR) return `${Math.round(seconds / 60)} min`;
  if (seconds < DAY) return `${Math.round(seconds / HOUR)} h`;
  if (seconds < MONTH) return `${Math.round(seconds / DAY)} j`;
  if (seconds < YEAR) return `${decimal(seconds / MONTH)} mois`;
  return `${decimal(seconds / YEAR)} an${seconds >= 2 * YEAR ? "s" : ""}`;
}
