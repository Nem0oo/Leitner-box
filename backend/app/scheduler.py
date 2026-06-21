"""Daily reminder: send a single push notification at the configured time,
only if there is at least one due card (all decks, active direction)."""

from __future__ import annotations

import datetime as dt
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app import crud, models, push, settings_store
from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_last_sent_date: str | None = None


def check_and_notify() -> None:
    global _last_sent_date
    db = SessionLocal()
    try:
        if not settings_store.get_bool(db, "reminder_enabled"):
            return
        reminder_time = settings_store.get_setting(db, "reminder_time")
        if not reminder_time:
            return

        now = dt.datetime.now()
        today = now.date().isoformat()
        if _last_sent_date == today:
            return
        try:
            target_h, target_m = (int(x) for x in reminder_time.split(":"))
        except ValueError:
            logger.warning("Invalid reminder_time setting: %r", reminder_time)
            return
        if (now.hour, now.minute) < (target_h, target_m):
            return

        direction = settings_store.get_setting(db, "direction")
        card_ids = [cid for cid, in db.execute(
            select(models.Card.id).where(models.Card.deleted.is_(False))
        ).all()]
        if not card_ids:
            return
        due = crud.due_count_for_cards(db, card_ids, direction)
        if due <= 0:
            return

        sent = push.notify_all(db, {
            "title": "Cartes à réviser",
            "body": f"{due} carte(s) en attente de révision.",
        })
        if sent > 0:
            _last_sent_date = today
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_and_notify,
        "interval",
        minutes=settings.reminder_check_interval_minutes,
        id="daily_reminder_check",
        next_run_time=dt.datetime.now(),
    )
    scheduler.start()
    return scheduler
