import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app import models
from app.srs import DIRECTIONS

logger = logging.getLogger(__name__)

DEFAULTS = {
    "reminder_time": "",
    "reminder_enabled": "false",
    "direction": DIRECTIONS[0],
    "new_cards_per_day": "10",
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


def get_int(db: Session, key: str) -> int:
    try:
        return int(get_setting(db, key))
    except ValueError:
        return int(DEFAULTS[key])


def get_timezone(db: Session) -> ZoneInfo:
    """The user's timezone (sent by the client), used for review days and the
    daily reminder. Falls back to UTC when unset or unknown."""
    name = get_setting(db, "reminder_timezone") or "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("Unknown reminder_timezone %r, falling back to UTC", name)
        return ZoneInfo("UTC")
