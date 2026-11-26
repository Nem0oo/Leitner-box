import datetime as dt

import pytest

from app.srs import (
    STATE_LEARNING,
    STATE_NEW,
    STATE_RELEARNING,
    STATE_REVIEW,
    compute_state,
    is_due,
    normalize_rating,
)

T0 = dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc).timestamp()
MINUTE = 60
DAY = 86400


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
