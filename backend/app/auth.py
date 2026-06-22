"""Single shared-password auth: a signed session cookie, no user table.

The app has exactly one user, so there's no need for password hashing
or a sessions table -- a cookie signed with HMAC(sha256(password)) is
enough to prove the holder once supplied the correct password, and it
can't be forged without knowing it.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from app.config import settings

SESSION_COOKIE = "leitner_session"
SESSION_MAX_AGE_SECONDS = 90 * 24 * 60 * 60

PUBLIC_API_PATHS = {"/api/auth/login", "/api/auth/status", "/api/health", "/api/version"}


def _signing_key() -> bytes:
    return hashlib.sha256(settings.auth_password.encode()).digest()


def verify_password(password: str) -> bool:
    return bool(settings.auth_password) and hmac.compare_digest(password, settings.auth_password)


def create_session_token() -> str:
    issued_at = str(int(time.time()))
    sig = hmac.new(_signing_key(), issued_at.encode(), hashlib.sha256).hexdigest()
    return f"{issued_at}.{sig}"


def verify_session_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    issued_at, _, sig = token.partition(".")
    expected = hmac.new(_signing_key(), issued_at.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        age = time.time() - int(issued_at)
    except ValueError:
        return False
    return 0 <= age <= SESSION_MAX_AGE_SECONDS
