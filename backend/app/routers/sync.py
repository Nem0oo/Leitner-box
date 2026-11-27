import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, schemas, settings_store
from app.database import get_db

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/pull", response_model=schemas.SyncPullResponse)
def pull(since: float | None = None, db: Session = Depends(get_db)):
    """Everything (decks + cards, including tombstones) modified after
    `since`, plus the deck of every returned card so a device always has the
    deck its cards belong to. Devices cache the result in IndexedDB for
    offline use."""
    now = time.time()

    card_query = select(models.Card)
    if since is not None:
        card_query = card_query.where(models.Card.last_modified > since)
    cards = db.execute(card_query).scalars().all()

    deck_query = select(models.Deck)
    if since is not None:
        card_deck_ids = {c.deck_id for c in cards}
        deck_query = deck_query.where(
            (models.Deck.last_modified > since) | models.Deck.id.in_(card_deck_ids)
        )
    decks = db.execute(deck_query.order_by(models.Deck.id)).scalars().all()
    # tombstones (deleted=True) are intentionally included so clients can
    # remove decks they previously cached, rather than resurrecting them

    states = crud.get_card_states(db, [c.id for c in cards])
    tz = settings_store.get_timezone(db)
    deck_out = []
    for d in decks:
        card_ids = [cid for cid, in db.execute(
            select(models.Card.id).where(models.Card.deck_id == d.id, models.Card.deleted.is_(False))
        ).all()]
        deck_out.append(schemas.DeckOut(
            id=d.id, name=d.name, description=d.description, last_modified=d.last_modified,
            card_count=len(card_ids), due_count=0, deleted=d.deleted,
        ))

    return schemas.SyncPullResponse(
        server_time=now,
        decks=deck_out,
        cards=[crud.serialize_card(c, states, tz, now) for c in cards],
    )


class BlobCheckRequest(BaseModel):
    hashes: list[str]


class BlobCheckResponse(BaseModel):
    missing: list[str]  # hashes the server does NOT have -> client should upload these


@router.post("/blobs/check", response_model=BlobCheckResponse)
def check_blobs(payload: BlobCheckRequest, db: Session = Depends(get_db)):
    existing = {
        h for h, in db.execute(
            select(models.Blob.hash).where(models.Blob.hash.in_(payload.hashes))
        ).all()
    }
    missing = [h for h in payload.hashes if h not in existing]
    return BlobCheckResponse(missing=missing)
