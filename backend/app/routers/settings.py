from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas, settings_store
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return schemas.SettingsOut(
        reminder_time=settings_store.get_setting(db, "reminder_time") or None,
        reminder_enabled=settings_store.get_bool(db, "reminder_enabled"),
        direction=settings_store.get_setting(db, "direction"),
        vapid_public_key=settings.vapid_public_key,
    )


@router.put("", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    if payload.reminder_time is not None:
        settings_store.set_setting(db, "reminder_time", payload.reminder_time)
    if payload.reminder_enabled is not None:
        settings_store.set_setting(db, "reminder_enabled", "true" if payload.reminder_enabled else "false")
    if payload.direction is not None:
        settings_store.set_setting(db, "direction", payload.direction)
    db.commit()
    return get_settings(db)
