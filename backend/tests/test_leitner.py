import pytest

from app.leitner import (
    BOX_INTERVAL_DAYS,
    MAX_BOX,
    MIN_BOX,
    SECONDS_PER_DAY,
    compute_box,
    compute_state,
    due_at,
    is_due,
    next_box,
)


def test_next_box_success_climbs_one():
    assert next_box(1, "success") == 2
    assert next_box(3, "success") == 4


def test_next_box_success_caps_at_max():
    assert next_box(MAX_BOX, "success") == MAX_BOX


def test_next_box_fail_resets_to_min():
    assert next_box(5, "fail") == MIN_BOX
    assert next_box(1, "fail") == MIN_BOX


def test_next_box_invalid_result_raises():
    with pytest.raises(ValueError):
        next_box(1, "maybe")


def test_compute_box_empty_history_is_box_1():
    assert compute_box([]) == 1


def test_compute_box_consecutive_successes():
    assert compute_box(["success"] * 4) == 5  # 1 -> 2 -> 3 -> 4 -> 5


def test_compute_box_caps_even_with_more_successes_than_boxes():
    assert compute_box(["success"] * 10) == MAX_BOX


def test_compute_box_fail_resets_mid_streak():
    assert compute_box(["success", "success", "fail", "success"]) == 2


def test_compute_box_all_fail_stays_at_1():
    assert compute_box(["fail", "fail", "fail"]) == 1


def test_compute_state_orders_unsorted_input_by_timestamp():
    # Out-of-order input must still fold chronologically.
    results = [(30.0, "fail"), (10.0, "success"), (20.0, "success")]
    state = compute_state(results)
    # chronological: success, success, fail -> 1 -> 2 -> 3 -> 1
    assert state.box == 1
    assert state.last_review_at == 30.0
    assert state.review_count == 3


def test_compute_state_no_events():
    state = compute_state([])
    assert state.box == 1
    assert state.last_review_at is None
    assert state.review_count == 0


def test_due_at_none_when_never_reviewed():
    assert due_at(1, None) is None


def test_due_at_uses_box_interval():
    last = 1000.0
    assert due_at(3, last) == last + BOX_INTERVAL_DAYS[3] * SECONDS_PER_DAY


def test_is_due_never_reviewed_is_always_due():
    state = compute_state([])
    assert is_due(state, now=0.0) is True


def test_is_due_before_interval_elapsed_is_not_due():
    state = compute_state([(1000.0, "success")])  # box becomes 2, interval = 2 days
    almost_due = 1000.0 + BOX_INTERVAL_DAYS[2] * SECONDS_PER_DAY - 1
    assert is_due(state, now=almost_due) is False


def test_is_due_after_interval_elapsed_is_due():
    state = compute_state([(1000.0, "success")])
    exactly_due = 1000.0 + BOX_INTERVAL_DAYS[2] * SECONDS_PER_DAY
    assert is_due(state, now=exactly_due) is True


def test_two_directions_are_independent():
    # Same card, two directions tracked as separate histories entirely
    # outside this module's concern -- but verify nothing here assumes
    # a shared box between calls.
    recto_to_verso = compute_state([(10.0, "success"), (20.0, "success")])
    verso_to_recto = compute_state([(10.0, "fail")])
    assert recto_to_verso.box == 3
    assert verso_to_recto.box == 1
