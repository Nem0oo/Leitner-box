import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app import models
from app.config import settings

logger = logging.getLogger(__name__)


def send_notification(subscription: models.PushSubscription, payload: dict) -> bool:
    if not settings.vapid_private_key:
        logger.warning("VAPID keys not configured, skipping push notification")
        return False
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return True
    except WebPushException as exc:
        logger.warning("Push failed for subscription %s: %s", subscription.id, exc)
        return False


def notify_all(db: Session, payload: dict) -> int:
    subs = db.query(models.PushSubscription).all()
    sent = 0
    expired_ids = []
    for sub in subs:
        if send_notification(sub, payload):
            sent += 1
        elif _is_gone(sub):
            expired_ids.append(sub.id)
    for sub_id in expired_ids:
        db.query(models.PushSubscription).filter_by(id=sub_id).delete()
    if expired_ids:
        db.commit()
    return sent


def _is_gone(subscription: models.PushSubscription) -> bool:
    # Best-effort cleanup; a failed send for a transient reason will simply
    # be retried on the next scheduled check, so we don't treat every
    # failure as "expired".
    return False
