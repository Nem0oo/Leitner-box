import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, schemas, settings_store
from app.database import get_db
from app.srs import DIRECTIONS, STATES

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=list[schemas.CardOut])
def list_cards(
    deck_id: int | None = None,
    direction: str = "recto_to_verso",
    state: str | None = None,
    db: Session = Depends(get_db),
):
    if direction not in DIRECTIONS:
        raise HTTPException(400, "invalid direction")
    if state is not None and state not in STATES:
        raise HTTPException(400, "invalid state")

    query = select(models.Card).where(models.Card.deleted.is_(False))
    if deck_id is not None:
        query = query.where(models.Card.deck_id == deck_id)
    cards = db.execute(query).scalars().all()

    now = time.time()
    states = crud.get_card_states(db, [c.id for c in cards])
    tz = settings_store.get_timezone(db)
    out = [crud.serialize_card(c, states, tz, now) for c in cards]
    if state is not None:
        out = [c for c in out if c[direction]["state"] == state]
    return out


@router.post("", response_model=schemas.CardOut, status_code=201)
def create_card(payload: schemas.CardCreate, db: Session = Depends(get_db)):
    deck = db.get(models.Deck, payload.deck_id)
    if deck is None or deck.deleted:
        raise HTTPException(404, "deck not found")
    card = models.Card(
        deck_id=payload.deck_id,
        recto_text=payload.recto_text,
        verso_text=payload.verso_text,
        recto_media=[],
        verso_media=[],
        last_modified=time.time(),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    states = crud.get_card_states(db, [card.id])
    return crud.serialize_card(card, states, settings_store.get_timezone(db))


@router.get("/{card_id}", response_model=schemas.CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)):
    card = db.get(models.Card, card_id)
    if card is None or card.deleted:
        raise HTTPException(404, "card not found")
    states = crud.get_card_states(db, [card.id])
    return crud.serialize_card(card, states, settings_store.get_timezone(db))


@router.patch("/{card_id}", response_model=schemas.CardOut)
def update_card(card_id: int, payload: schemas.CardUpdate, db: Session = Depends(get_db)):
    card = db.get(models.Card, card_id)
    if card is None or card.deleted:
        raise HTTPException(404, "card not found")
    if payload.deck_id is not None:
        deck = db.get(models.Deck, payload.deck_id)
        if deck is None or deck.deleted:
            raise HTTPException(404, "deck not found")
        card.deck_id = payload.deck_id
    if payload.recto_text is not None:
        card.recto_text = payload.recto_text
    if payload.verso_text is not None:
        card.verso_text = payload.verso_text
    if payload.recto_media is not None:
        card.recto_media = payload.recto_media
    if payload.verso_media is not None:
        card.verso_media = payload.verso_media
    card.last_modified = time.time()
    db.commit()
    db.refresh(card)
    states = crud.get_card_states(db, [card.id])
    return crud.serialize_card(card, states, settings_store.get_timezone(db))


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.get(models.Card, card_id)
    if card is None or card.deleted:
        raise HTTPException(404, "card not found")
    card.deleted = True
    card.last_modified = time.time()
    db.commit()
