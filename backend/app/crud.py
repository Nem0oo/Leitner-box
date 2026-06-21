from __future__ import annotations

import time
from itertools import groupby

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.leitner import DIRECTIONS, CardDirectionState, compute_state, due_at, is_due


def get_card_states(db: Session, card_ids: list[int] | None = None) -> dict[tuple[int, str], CardDirectionState]:
    """Compute {(card_id, direction): CardDirectionState} for the given cards
    (or all cards if None) from the full ReviewEvent history."""
    query = select(models.ReviewEvent.card_id, models.ReviewEvent.direction,
                    models.ReviewEvent.timestamp, models.ReviewEvent.result)
    if card_ids is not None:
        query = query.where(models.ReviewEvent.card_id.in_(card_ids))
    query = query.order_by(models.ReviewEvent.card_id, models.ReviewEvent.direction, models.ReviewEvent.timestamp)

    rows = db.execute(query).all()
    states: dict[tuple[int, str], CardDirectionState] = {}
    for (card_id, direction), group in groupby(rows, key=lambda r: (r[0], r[1])):
        timestamped = [(ts, result) for _, _, ts, result in group]
        states[(card_id, direction)] = compute_state(timestamped)

    target_ids = card_ids if card_ids is not None else [
        cid for cid, in db.execute(select(models.Card.id)).all()
    ]
    for cid in target_ids:
        for direction in DIRECTIONS:
            states.setdefault((cid, direction), compute_state([]))
    return states


def card_direction_state_out(state: CardDirectionState, now: float | None = None) -> dict:
    now = now if now is not None else time.time()
    return {
        "box": state.box,
        "last_review_at": state.last_review_at,
        "due_at": due_at(state.box, state.last_review_at),
        "is_due": is_due(state, now),
    }


def serialize_card(card: models.Card, states: dict[tuple[int, str], CardDirectionState], now: float | None = None) -> dict:
    now = now if now is not None else time.time()
    return {
        "id": card.id,
        "deck_id": card.deck_id,
        "recto_text": card.recto_text,
        "recto_media": card.recto_media or [],
        "verso_text": card.verso_text,
        "verso_media": card.verso_media or [],
        "last_modified": card.last_modified,
        "deleted": card.deleted,
        "recto_to_verso": card_direction_state_out(states[(card.id, "recto_to_verso")], now),
        "verso_to_recto": card_direction_state_out(states[(card.id, "verso_to_recto")], now),
    }


def due_count_for_cards(db: Session, card_ids: list[int], direction: str, now: float | None = None) -> int:
    now = now if now is not None else time.time()
    states = get_card_states(db, card_ids)
    return sum(1 for cid in card_ids if is_due(states[(cid, direction)], now))
