import dataclasses
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from app.srs import (
    NEW_STATE,
    STATE_LEARNING,
    STATE_NEW,
    STATE_RELEARNING,
    STATE_REVIEW,
    RESET,
    compute_state,
    is_due,
    new_cards_introduced_on,
    normalize_rating,
    select_due,
)

T0 = dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc).timestamp()
MINUTE = 60
DAY = 86400
UTC = ZoneInfo("UTC")
PARIS = ZoneInfo("Europe/Paris")


def _ts(year, month, day, hour, minute=0, tz=UTC) -> float:
    return dt.datetime(year, month, day, hour, minute, tzinfo=tz).timestamp()


def _review_due_at(due_at: float):
    return dataclasses.replace(NEW_STATE, state=STATE_REVIEW, due_at=due_at, last_review_at=due_at - 5 * DAY,
                               stability=5.0, difficulty=5.0, review_count=3)


def _replay(ratings: list[str]):
    """Review each rating exactly when the previous one made the card due,
    returning the state after every step."""
    events: list[tuple[float, str]] = []
    states = []
    t = T0
    for rating in ratings:
        events.append((t, rating))
        state = compute_state(events)
        states.append(state)
        t = state.due_at
    return states


def test_normalize_rating_accepts_the_four_fsrs_grades():
    for rating in ("again", "hard", "good", "easy"):
        assert normalize_rating(rating) == rating


def test_normalize_rating_maps_legacy_binary_results():
    assert normalize_rating("success") == "good"
    assert normalize_rating("fail") == "again"


def test_normalize_rating_rejects_unknown_value():
    with pytest.raises(ValueError):
        normalize_rating("maybe")


def test_no_events_is_a_new_card_due_now():
    state = compute_state([])
    assert state.state == STATE_NEW
    assert state.review_count == 0
    assert state.last_review_at is None
    assert state.due_at is None
    assert state.stability is None
    assert is_due(state, now=0.0) is True


def test_first_good_enters_learning_steps_due_in_ten_minutes():
    state = compute_state([(T0, "good")])
    assert state.state == STATE_LEARNING
    assert state.step == 1
    assert state.due_at == pytest.approx(T0 + 10 * MINUTE)
    assert is_due(state, now=T0 + 10 * MINUTE - 1) is False
    assert is_due(state, now=T0 + 10 * MINUTE) is True


def test_reference_sequence_matches_fsrs6_default_parameters():
    # Same sequence as frontend/src/lib/srs.test.ts: both sides must agree.
    states = _replay(["good", "good", "good", "again", "good"])

    expected = [
        (STATE_LEARNING, 2.3065, 2.1181, T0 + 10 * MINUTE),
        (STATE_REVIEW, 2.3065, 2.1112, T0 + 10 * MINUTE + 2 * DAY),
        (STATE_REVIEW, 10.971, 2.1043, T0 + 10 * MINUTE + 13 * DAY),
        (STATE_RELEARNING, 1.539, 7.39, T0 + 20 * MINUTE + 13 * DAY),
        (STATE_REVIEW, 1.5718, 7.3778, T0 + 20 * MINUTE + 15 * DAY),
    ]
    for state, (name, stability, difficulty, due) in zip(states, expected):
        assert state.state == name
        assert state.stability == pytest.approx(stability, abs=1e-4)
        assert state.difficulty == pytest.approx(difficulty, abs=1e-4)
        assert state.due_at == pytest.approx(due)
    assert states[-1].review_count == 5


def test_legacy_results_replay_like_good_and_again():
    legacy = compute_state([(T0, "success"), (T0 + 600, "success"), (T0 + DAY * 3, "fail")])
    modern = compute_state([(T0, "good"), (T0 + 600, "good"), (T0 + DAY * 3, "again")])
    assert legacy == modern


def test_easy_on_new_card_skips_learning():
    state = compute_state([(T0, "easy")])
    assert state.state == STATE_REVIEW
    assert state.step is None
    assert state.due_at > T0 + DAY


def test_unordered_events_are_replayed_chronologically():
    ordered = compute_state([(T0, "good"), (T0 + 600, "good"), (T0 + 3 * DAY, "again")])
    shuffled = compute_state([(T0 + 3 * DAY, "again"), (T0, "good"), (T0 + 600, "good")])
    assert shuffled == ordered
    assert shuffled.last_review_at == T0 + 3 * DAY


def test_replay_is_deterministic():
    events = [(T0 + i * DAY, "good") for i in range(6)]
    assert compute_state(events) == compute_state(list(events))


# ---- Review days: a day starts at 04:00 local time ----

def test_review_card_is_due_from_the_start_of_its_local_review_day():
    state = _review_due_at(_ts(2026, 1, 10, 21, tz=PARIS))
    assert is_due(state, _ts(2026, 1, 10, 8, tz=PARIS), PARIS) is True
    assert is_due(state, _ts(2026, 1, 10, 4, tz=PARIS), PARIS) is True
    assert is_due(state, _ts(2026, 1, 10, 3, 59, tz=PARIS), PARIS) is False  # still Jan 9's review day
    assert is_due(state, _ts(2026, 1, 9, 23, tz=PARIS), PARIS) is False


def test_due_time_before_4am_belongs_to_the_previous_review_day():
    state = _review_due_at(_ts(2026, 1, 11, 2, tz=PARIS))
    assert is_due(state, _ts(2026, 1, 10, 8, tz=PARIS), PARIS) is True


def test_review_day_depends_on_the_timezone():
    state = _review_due_at(_ts(2026, 1, 4, 3, 30))  # 03:30 UTC = 04:30 Paris
    now = _ts(2026, 1, 3, 12)
    assert is_due(state, now, UTC) is True
    assert is_due(state, now, PARIS) is False


def test_learning_steps_stay_minute_based():
    state = compute_state([(T0, "good")], PARIS)  # due in 10 minutes
    assert is_due(state, T0 + 5 * MINUTE, PARIS) is False
    assert is_due(state, T0 + 10 * MINUTE, PARIS) is True


def test_elapsed_time_counts_review_days_not_24h_periods():
    # Same vector as frontend/src/lib/srs.test.ts. Reviewing at 08:00 a card
    # last seen at 20:00 three and a half days earlier counts as 4 days.
    t1 = _ts(2026, 1, 1, 20)
    t2 = t1 + 4 * DAY - 12 * 3600
    t3 = t2 + 10 * DAY + 3 * 3600
    t4 = t3 + 20 * DAY - 30 * 3600
    expected = [
        ("easy", 8.2956, 1.0, _ts(2026, 1, 9, 20)),
        ("good", 26.1948, 1.0, _ts(2026, 1, 31, 8)),
        ("good", 64.5675, 1.0, _ts(2026, 3, 21, 11)),
        ("hard", 103.6348, 4.0106, _ts(2026, 5, 18, 5)),
    ]
    events = []
    for t, (rating, stability, difficulty, due) in zip([t1, t2, t3, t4], expected):
        events.append((t, rating))
        state = compute_state(events, UTC)
        assert state.state == STATE_REVIEW
        assert state.stability == pytest.approx(stability, abs=1e-4)
        assert state.difficulty == pytest.approx(difficulty, abs=1e-4)
        assert state.due_at == pytest.approx(due)


def test_elapsed_review_days_use_the_timezone():
    # 03:30 UTC on Jan 2 is still Jan 1's review day in UTC, but Jan 2's in Paris.
    events = [(_ts(2026, 1, 1, 10), "easy"), (_ts(2026, 1, 2, 3, 30), "good")]
    same_day = compute_state(events, UTC)
    next_day = compute_state(events, PARIS)
    assert next_day.stability > same_day.stability


def test_reset_event_starts_the_card_over_as_new():
    state = compute_state([(T0, "good"), (T0 + DAY, "good"), (T0 + 2 * DAY, RESET)])
    assert state == NEW_STATE


def test_reviews_after_a_reset_replay_from_a_new_card():
    after_reset = T0 + 30 * DAY
    state = compute_state([(T0, "again"), (T0 + DAY, "good"), (T0 + 2 * DAY, RESET), (after_reset, "good")])
    assert state == compute_state([(after_reset, "good")])
    assert state.review_count == 1
    assert state.first_review_at == after_reset


def test_first_review_at_is_the_first_rating():
    state = compute_state([(T0 + DAY, "good"), (T0, "good")])
    assert state.first_review_at == T0
    assert NEW_STATE.first_review_at is None


def test_new_cards_introduced_on_counts_first_reviews_of_the_review_day():
    now = _ts(2026, 1, 10, 12)
    states = [
        compute_state([(_ts(2026, 1, 10, 9), "good")]),  # today
        compute_state([(_ts(2026, 1, 10, 3), "good")]),  # before 4am: previous review day
        compute_state([(_ts(2026, 1, 5, 9), "good"), (_ts(2026, 1, 10, 9), "good")]),  # introduced earlier
        NEW_STATE,
    ]
    assert new_cards_introduced_on(states, now) == 1


def test_select_due_limits_new_cards_in_creation_order():
    now = _ts(2026, 1, 10, 12)
    learning_due = compute_state([(_ts(2026, 1, 9, 9), "good")])
    learning_later = compute_state([(now - 60, "good")])
    states = {5: NEW_STATE, 2: NEW_STATE, 9: learning_due, 3: NEW_STATE, 4: learning_later}
    assert select_due(states, now, new_slots=2) == [9, 2, 3]
    assert select_due(states, now, new_slots=0) == [9]
