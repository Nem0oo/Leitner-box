from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/push", tags=["push"])


@router.post("/subscribe", status_code=201)
def subscribe(payload: schemas.PushSubscriptionIn, db: Session = Depends(get_db)):
    existing = db.query(models.PushSubscription).filter_by(endpoint=payload.endpoint).first()
    if existing is None:
        db.add(models.PushSubscription(
            endpoint=payload.endpoint,
            p256dh=payload.keys["p256dh"],
            auth=payload.keys["auth"],
        ))
        db.commit()
    return {"status": "subscribed"}


@router.post("/unsubscribe", status_code=204)
def unsubscribe(payload: schemas.PushSubscriptionIn, db: Session = Depends(get_db)):
    db.query(models.PushSubscription).filter_by(endpoint=payload.endpoint).delete()
    db.commit()
