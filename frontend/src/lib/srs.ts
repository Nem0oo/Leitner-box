/**
 * Client-side mirror of backend/app/srs.py (FSRS-6, default parameters,
 * fuzz disabled), used for immediate optimistic updates while review events
 * wait in the offline queue. The server replays the full ReviewEvent history
 * and stays the source of truth once synced; both sides are checked against
 * the same reference sequences in their tests.
 *
 * Time is counted in review days starting at DAY_ROLLOVER_HOUR local time
 * (timezone argument, the device's when omitted): a review card is due from
 * the start of its due day, and FSRS sees the elapsed time as a difference of
 * review days. See backend/app/srs.py for the "review clock" both sides feed
 * to their FSRS library.
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
  /** First rating since the last deck reset; may be missing from states cached before it existed. */
  first_review_at: number | null;
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
  first_review_at: null,
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

export const DAY_ROLLOVER_HOUR = 4;
const SECONDS_PER_DAY = 86400;

function toDate(seconds: number): Date {
  return new Date(seconds * 1000);
}

/** Offset of `timeZone` (device timezone when undefined) from UTC at `ts`, in seconds. */
export function utcOffsetSeconds(ts: number, timeZone?: string): number {
  const date = toDate(Math.floor(ts));
  if (timeZone === undefined) return -date.getTimezoneOffset() * 60;
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone,
      hourCycle: "h23",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
    })
      .formatToParts(date)
      .map((p) => [p.type, Number(p.value)]),
  );
  const wallClock = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second);
  return Math.round((wallClock - date.getTime()) / 1000);
}

/** Local wall-clock time minus the day rollover, as epoch seconds: its UTC calendar day is the review day of `ts`. */
function reviewClock(ts: number, timeZone?: string): number {
  return ts + utcOffsetSeconds(ts, timeZone) - DAY_ROLLOVER_HOUR * 3600;
}

/** Index of the review day containing `ts` (days since the epoch). */
export function reviewDay(ts: number, timeZone?: string): number {
  return Math.floor(reviewClock(ts, timeZone) / SECONDS_PER_DAY);
}

function toFsrsCard(s: DirectionState, clock: number, timeZone?: string): Card {
  if (s.state === "new" || s.last_review_at === null || s.due_at === null) return createEmptyCard(toDate(clock));
  return {
    due: toDate(reviewClock(s.due_at, timeZone)),
    stability: s.stability ?? 0,
    difficulty: s.difficulty ?? 0,
    elapsed_days: 0,
    scheduled_days: 0,
    learning_steps: s.step ?? 0,
    reps: s.review_count,
    lapses: 0,
    state: TO_FSRS_STATE[s.state],
    // Pinned to the start of its review day so the elapsed time is a whole number of review days.
    last_review: toDate(reviewDay(s.last_review_at, timeZone) * SECONDS_PER_DAY),
  };
}

/** State after reviewing `s` with `rating` at `now` (epoch seconds). */
export function nextState(s: DirectionState, rating: ReviewRating, now: number, timeZone?: string): DirectionState {
  const clock = reviewClock(now, timeZone);
  const { card } = scheduler.next(toFsrsCard(s, clock, timeZone), toDate(clock), GRADE[rating]);
  const state = FROM_FSRS_STATE[card.state];
  const inSteps = state === "learning" || state === "relearning";
  return {
    state,
    step: inSteps ? card.learning_steps : null,
    stability: card.stability,
    difficulty: card.difficulty,
    last_review_at: now,
    due_at: now + (card.due.getTime() / 1000 - clock),
    is_due: false,
    review_count: s.review_count + 1,
    first_review_at: s.state === "new" ? now : (s.first_review_at ?? null),
  };
}

/** Seconds until the card would be due again, for each possible rating. */
export function previewIntervals(s: DirectionState, now: number, timeZone?: string): Record<ReviewRating, number> {
  const out = {} as Record<ReviewRating, number>;
  for (const rating of RATINGS) {
    out[rating] = Math.round((nextState(s, rating, now, timeZone).due_at ?? now) - now);
  }
  return out;
}

export function isDue(s: DirectionState, now: number, timeZone?: string): boolean {
  if (s.due_at === null) return true;
  if (s.state === "review") return reviewDay(s.due_at, timeZone) <= reviewDay(now, timeZone);
  return now >= s.due_at;
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
