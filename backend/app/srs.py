"""Spaced-repetition scheduling with FSRS-6 (py-fsrs, default parameters).

The scheduling state of a card (per direction) is never stored: it is
recomputed by replaying the ordered history of its ReviewEvents through the
FSRS scheduler. ReviewEvent stays append-only, so sync has no conflicts on
that table, and changing FSRS parameters later only means replaying again.

Fuzzing is disabled so a replay is deterministic and gives exactly the same
result as the frontend mirror (frontend/src/lib/srs.ts, ts-fsrs).

Ratings are the four FSRS grades. The two results recorded before FSRS was
adopted ("success" / "fail") are replayed as "good" / "again".
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from fsrs import Card, Rating, Scheduler, State

DIRECTIONS = ("recto_to_verso", "verso_to_recto")

RATING_AGAIN = "again"
RATING_HARD = "hard"
RATING_GOOD = "good"
RATING_EASY = "easy"
RATINGS = (RATING_AGAIN, RATING_HARD, RATING_GOOD, RATING_EASY)

LEGACY_RESULTS = {"success": RATING_GOOD, "fail": RATING_AGAIN}

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


NEW_STATE = CardDirectionState(
    state=STATE_NEW, step=None, stability=None, difficulty=None,
    last_review_at=None, due_at=None, review_count=0,
)


def _to_datetime(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)


def compute_state(timestamped_results: list[tuple[float, str]]) -> CardDirectionState:
    """Replay a (possibly unordered) list of (timestamp, result) for one
    card+direction and return the resulting scheduling state."""
    if not timestamped_results:
        return NEW_STATE

    ordered = sorted(timestamped_results, key=lambda item: item[0])
    card = Card(card_id=0, due=_to_datetime(ordered[0][0]))
    for ts, result in ordered:
        rating = _FSRS_RATING[normalize_rating(result)]
        card, _ = _scheduler.review_card(card, rating, review_datetime=_to_datetime(ts))

    return CardDirectionState(
        state=_STATE_NAME[card.state],
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        last_review_at=ordered[-1][0],
        due_at=card.due.timestamp(),
        review_count=len(ordered),
    )


def is_due(state: CardDirectionState, now: float) -> bool:
    if state.due_at is None:
        return True
    return now >= state.due_at
