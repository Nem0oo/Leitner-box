"""Spaced-repetition scheduling with FSRS-6 (py-fsrs, default parameters).

The scheduling state of a card (per direction) is never stored: it is
recomputed by replaying the ordered history of its ReviewEvents through the
FSRS scheduler. ReviewEvent stays append-only, so sync has no conflicts on
that table, and changing FSRS parameters later only means replaying again.

Fuzzing is disabled so a replay is deterministic and gives exactly the same
result as the frontend mirror (frontend/src/lib/srs.ts, ts-fsrs).

Ratings are the four FSRS grades. The two results recorded before FSRS was
adopted ("success" / "fail") are replayed as "good" / "again".

Time is counted in review days of the user's timezone, each starting at
DAY_ROLLOVER_HOUR local time (as in Anki):
- a card in the review state is due from the start of the review day its
  due time falls on, not at the exact second;
- the elapsed time FSRS sees between two reviews is the difference of their
  review days. Both libraries are fed a "review clock" (local wall-clock time
  shifted back by the rollover, expressed as UTC) and the previous review is
  pinned to the start of its review day, so py-fsrs (whole 24 h periods) and
  ts-fsrs (UTC calendar days) count the same days.
Learning and relearning steps stay minute-based.

A RESET event (written for every card of a deck that is reset) starts the
card over: only the ratings after the last reset are replayed.

New cards are introduced at most `new_slots` per review day and per
direction, in creation order (card id). A card counts as introduced on the
review day of its first rating since the last reset.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from fsrs import Card, Rating, Scheduler, State

DIRECTIONS = ("recto_to_verso", "verso_to_recto")

RATING_AGAIN = "again"
RATING_HARD = "hard"
RATING_GOOD = "good"
RATING_EASY = "easy"
RATINGS = (RATING_AGAIN, RATING_HARD, RATING_GOOD, RATING_EASY)

LEGACY_RESULTS = {"success": RATING_GOOD, "fail": RATING_AGAIN}

RESET = "reset"

STATE_NEW = "new"
STATE_LEARNING = "learning"
STATE_REVIEW = "review"
STATE_RELEARNING = "relearning"
STATES = (STATE_NEW, STATE_LEARNING, STATE_REVIEW, STATE_RELEARNING)

_FSRS_RATING = {
    RATING_AGAIN: Rating.Again,
    RATING_HARD: Rating.Hard,
    RATING_GOOD: Rating.Good,
    RATING_EASY: Rating.Easy,
}

_STATE_NAME = {
    State.Learning: STATE_LEARNING,
    State.Review: STATE_REVIEW,
    State.Relearning: STATE_RELEARNING,
}

_scheduler = Scheduler(enable_fuzzing=False)

DAY_ROLLOVER_HOUR = 4
SECONDS_PER_DAY = 86400
UTC = ZoneInfo("UTC")


def normalize_rating(result: str) -> str:
    """Return the FSRS rating for a stored result, accepting legacy values."""
    if result in RATINGS:
        return result
    if result in LEGACY_RESULTS:
        return LEGACY_RESULTS[result]
    raise ValueError(f"Unknown review result: {result!r}")


@dataclass(frozen=True)
class CardDirectionState:
    state: str
    step: int | None
    stability: float | None
    difficulty: float | None
    last_review_at: float | None
    due_at: float | None
    review_count: int
    first_review_at: float | None


NEW_STATE = CardDirectionState(
    state=STATE_NEW, step=None, stability=None, difficulty=None,
    last_review_at=None, due_at=None, review_count=0, first_review_at=None,
)


def _to_datetime(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)


def review_clock(ts: float, tz: ZoneInfo) -> float:
    """Local wall-clock time minus the day rollover, as epoch seconds: its UTC
    calendar day is the review day of `ts`."""
    offset = dt.datetime.fromtimestamp(ts, tz).utcoffset() or dt.timedelta(0)
    return ts + offset.total_seconds() - DAY_ROLLOVER_HOUR * 3600


def review_day(ts: float, tz: ZoneInfo) -> int:
    """Index of the review day containing `ts` (days since the epoch)."""
    return math.floor(review_clock(ts, tz) / SECONDS_PER_DAY)


def compute_state(timestamped_results: list[tuple[float, str]], tz: ZoneInfo = UTC) -> CardDirectionState:
    """Replay a (possibly unordered) list of (timestamp, result) for one
    card+direction and return the resulting scheduling state."""
    ordered = sorted(timestamped_results, key=lambda item: item[0])
    resets = [i for i, (_, result) in enumerate(ordered) if result == RESET]
    if resets:
        ordered = ordered[resets[-1] + 1:]
    if not ordered:
        return NEW_STATE

    card = Card(card_id=0, due=_to_datetime(review_clock(ordered[0][0], tz)))
    previous_ts: float | None = None
    due_at = 0.0
    for ts, result in ordered:
        if previous_ts is not None:
            card.last_review = _to_datetime(review_day(previous_ts, tz) * SECONDS_PER_DAY)
        clock = review_clock(ts, tz)
        rating = _FSRS_RATING[normalize_rating(result)]
        card, _ = _scheduler.review_card(card, rating, review_datetime=_to_datetime(clock))
        due_at = ts + (card.due.timestamp() - clock)
        previous_ts = ts

    return CardDirectionState(
        state=_STATE_NAME[card.state],
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        last_review_at=ordered[-1][0],
        due_at=due_at,
        review_count=len(ordered),
        first_review_at=ordered[0][0],
    )


def is_due(state: CardDirectionState, now: float, tz: ZoneInfo = UTC) -> bool:
    if state.due_at is None:
        return True
    if state.state == STATE_REVIEW:
        return review_day(state.due_at, tz) <= review_day(now, tz)
    return now >= state.due_at


def new_cards_introduced_on(states: Iterable[CardDirectionState], now: float, tz: ZoneInfo = UTC) -> int:
    """How many cards had their first rating on the review day of `now`."""
    today = review_day(now, tz)
    return sum(
        1 for s in states
        if s.first_review_at is not None and review_day(s.first_review_at, tz) == today
    )


def select_due(
    states: Mapping[int, CardDirectionState], now: float, tz: ZoneInfo = UTC, *, new_slots: int,
) -> list[int]:
    """Ids of the cards to review now: every due card already introduced,
    then at most `new_slots` new cards in creation order."""
    ids = sorted(states)
    started = [cid for cid in ids if states[cid].state != STATE_NEW and is_due(states[cid], now, tz)]
    new = [cid for cid in ids if states[cid].state == STATE_NEW]
    return started + new[:max(new_slots, 0)]
