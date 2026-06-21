import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.leitner import DIRECTIONS

router = APIRouter(prefix="/api/decks", tags=["decks"])


def _deck_out(db: Session, deck: models.Deck, direction: str, now: float) -> schemas.DeckOut:
    card_ids = [cid for cid, in db.execute(
        select(models.Card.id).where(models.Card.deck_id == deck.id, models.Card.deleted.is_(False))
    ).all()]
    due = crud.due_count_for_cards(db, card_ids, direction, now) if card_ids else 0
    return schemas.DeckOut(
        id=deck.id,
        name=deck.name,
        description=deck.description,
        last_modified=deck.last_modified,
        card_count=len(card_ids),
        due_count=due,
    )


@router.get("", response_model=list[schemas.DeckOut])
def list_decks(direction: str = "recto_to_verso", db: Session = Depends(get_db)):
    if direction not in DIRECTIONS:
        raise HTTPException(400, "invalid direction")
    now = time.time()
    decks = db.execute(select(models.Deck).where(models.Deck.deleted.is_(False))).scalars().all()
    return [_deck_out(db, d, direction, now) for d in decks]


@router.post("", response_model=schemas.DeckOut, status_code=201)
def create_deck(payload: schemas.DeckCreate, db: Session = Depends(get_db)):
    deck = models.Deck(name=payload.name, description=payload.description, last_modified=time.time())
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return _deck_out(db, deck, "recto_to_verso", time.time())


@router.get("/{deck_id}", response_model=schemas.DeckOut)
def get_deck(deck_id: int, direction: str = "recto_to_verso", db: Session = Depends(get_db)):
    if direction not in DIRECTIONS:
        raise HTTPException(400, "invalid direction")
    deck = db.get(models.Deck, deck_id)
    if deck is None or deck.deleted:
        raise HTTPException(404, "deck not found")
    return _deck_out(db, deck, direction, time.time())


@router.patch("/{deck_id}", response_model=schemas.DeckOut)
def update_deck(deck_id: int, payload: schemas.DeckUpdate, db: Session = Depends(get_db)):
    deck = db.get(models.Deck, deck_id)
    if deck is None or deck.deleted:
        raise HTTPException(404, "deck not found")
    if payload.name is not None:
        deck.name = payload.name
    if payload.description is not None:
        deck.description = payload.description
    deck.last_modified = time.time()
    db.commit()
    db.refresh(deck)
    return _deck_out(db, deck, "recto_to_verso", time.time())


@router.delete("/{deck_id}", status_code=204)
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.get(models.Deck, deck_id)
    if deck is None or deck.deleted:
        raise HTTPException(404, "deck not found")
    deck.deleted = True
    deck.last_modified = time.time()
    db.commit()
