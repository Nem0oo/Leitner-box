"""Pure Leitner box logic.

The "current box" of a card (per direction) is never stored directly: it is
always recomputed from the ordered history of its ReviewEvents. This keeps
sync trivial for this table (append-only, no conflicts possible).

Box scheduling uses the classic doubling-interval Leitner schedule. This
interval table is not specified by the product spec, so a standard
1/2/4/8/16-day schedule is used; it is centralized here so it can be tuned
later without touching call sites.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_BOX = 1
MAX_BOX = 5

DIRECTIONS = ("recto_to_verso", "verso_to_recto")

RESULT_SUCCESS = "success"
RESULT_FAIL = "fail"

# Box -> number of days before a card reviewed into that box becomes due again.
BOX_INTERVAL_DAYS: dict[int, int] = {
    1: 1,
    2: 2,
    3: 4,
    4: 8,
    5: 16,
}

SECONDS_PER_DAY = 86400


def next_box(current_box: int, result: str) -> int:
    """Single Leitner transition: success climbs one box (capped at MAX_BOX),
    failure drops back to MIN_BOX."""
    if result == RESULT_SUCCESS:
        return min(current_box + 1, MAX_BOX)
    if result == RESULT_FAIL:
        return MIN_BOX
    raise ValueError(f"Unknown review result: {result!r}")


def compute_box(results: list[str]) -> int:
    """Fold a chronologically-ordered list of review results into the
    resulting box. An empty history means the card has never been reviewed
    in this direction and sits in box 1."""
    box = MIN_BOX
    for result in results:
        box = next_box(box, result)
    return box


@dataclass(frozen=True)
class CardDirectionState:
    box: int
    last_review_at: float | None
    review_count: int


def compute_state(timestamped_results: list[tuple[float, str]]) -> CardDirectionState:
    """Compute box + last review time from a (possibly unordered) list of
    (timestamp, result) tuples for one card+direction."""
    ordered = sorted(timestamped_results, key=lambda item: item[0])
    box = compute_box([result for _, result in ordered])
    last_review_at = ordered[-1][0] if ordered else None
    return CardDirectionState(box=box, last_review_at=last_review_at, review_count=len(ordered))


def due_at(box: int, last_review_at: float | None) -> float | None:
    """Timestamp (epoch seconds) at which a card+direction becomes due again.
    None means it has never been reviewed and is due immediately."""
    if last_review_at is None:
        return None
    interval_days = BOX_INTERVAL_DAYS[box]
    return last_review_at + interval_days * SECONDS_PER_DAY


def is_due(state: CardDirectionState, now: float) -> bool:
    if state.last_review_at is None:
        return True
    due = due_at(state.box, state.last_review_at)
    assert due is not None
    return now >= due
