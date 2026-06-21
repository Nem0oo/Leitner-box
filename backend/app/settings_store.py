from sqlalchemy.orm import Session

from app import models
from app.leitner import DIRECTIONS

DEFAULTS = {
    "reminder_time": "",
    "reminder_enabled": "false",
    "direction": DIRECTIONS[0],
}


def get_setting(db: Session, key: str) -> str:
    row = db.get(models.Setting, key)
    if row is not None:
        return row.value
    return DEFAULTS.get(key, "")


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(models.Setting, key)
    if row is None:
        db.add(models.Setting(key=key, value=value))
    else:
        row.value = value


def get_bool(db: Session, key: str) -> bool:
    return get_setting(db, key).lower() == "true"
