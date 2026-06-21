import random
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.leitner import DIRECTIONS, RESULT_FAIL, RESULT_SUCCESS, is_due

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/due", response_model=list[schemas.DueCardOut])
def due_cards(deck_id: int | None = None, direction: str = "recto_to_verso", db: Session = Depends(get_db)):
    """Cards due now, in random order. Order is generated fresh on every
    call and never persisted, per spec (no fixed seed, never repeats)."""
    if direction not in DIRECTIONS:
        raise HTTPException(400, "invalid direction")

    query = (
        select(models.Card, models.Deck.name)
        .join(models.Deck, models.Deck.id == models.Card.deck_id)
        .where(models.Card.deleted.is_(False), models.Deck.deleted.is_(False))
    )
    if deck_id is not None:
        query = query.where(models.Card.deck_id == deck_id)
    rows = db.execute(query).all()

    now = time.time()
    states = crud.get_card_states(db, [c.id for c, _ in rows])
    due = [
        schemas.DueCardOut(
            id=card.id,
            deck_id=card.deck_id,
            deck_name=deck_name,
            recto_text=card.recto_text,
            recto_media=card.recto_media or [],
            verso_text=card.verso_text,
            verso_media=card.verso_media or [],
            direction=direction,
            box=states[(card.id, direction)].box,
        )
        for card, deck_name in rows
        if is_due(states[(card.id, direction)], now)
    ]
    random.shuffle(due)
    return due


@router.get("/due-count")
def due_count(deck_id: int | None = None, direction: str = "recto_to_verso", db: Session = Depends(get_db)):
    if direction not in DIRECTIONS:
        raise HTTPException(400, "invalid direction")
    query = select(models.Card.id).where(models.Card.deleted.is_(False))
    if deck_id is not None:
        query = query.where(models.Card.deck_id == deck_id)
    card_ids = [cid for cid, in db.execute(query).all()]
    if not card_ids:
        return {"due_count": 0}
    return {"due_count": crud.due_count_for_cards(db, card_ids, direction)}


def _insert_event(db: Session, payload: schemas.ReviewEventCreate) -> models.ReviewEvent | None:
    if payload.direction not in DIRECTIONS:
        raise HTTPException(400, f"invalid direction: {payload.direction}")
    if payload.result not in (RESULT_SUCCESS, RESULT_FAIL):
        raise HTTPException(400, f"invalid result: {payload.result}")
    card = db.get(models.Card, payload.card_id)
    if card is None:
        raise HTTPException(404, f"card not found: {payload.card_id}")

    if payload.id is not None and db.get(models.ReviewEvent, payload.id) is not None:
        return None  # already recorded (idempotent offline-queue push)

    event = models.ReviewEvent(
        id=payload.id or models.new_uuid(),
        card_id=payload.card_id,
        direction=payload.direction,
        result=payload.result,
        timestamp=payload.timestamp or time.time(),
    )
    db.add(event)
    return event


@router.post("/events", response_model=schemas.ReviewEventOut, status_code=201)
def create_review_event(payload: schemas.ReviewEventCreate, db: Session = Depends(get_db)):
    event = _insert_event(db, payload)
    db.commit()
    if event is None:
        event = db.get(models.ReviewEvent, payload.id)
    db.refresh(event)
    return event


@router.post("/events/batch", response_model=list[schemas.ReviewEventOut])
def create_review_events_batch(payload: schemas.ReviewEventBatch, db: Session = Depends(get_db)):
    """Idempotent bulk push for the offline review-event queue."""
    inserted_ids = []
    for item in payload.events:
        event = _insert_event(db, item)
        if event is not None:
            inserted_ids.append(event.id)
        elif item.id is not None:
            inserted_ids.append(item.id)
    db.commit()
    return db.execute(
        select(models.ReviewEvent).where(models.ReviewEvent.id.in_(inserted_ids))
    ).scalars().all()
