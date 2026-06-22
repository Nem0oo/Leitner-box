import pytest
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.main import app


@pytest.fixture
def auth_client():
    settings.auth_password = "s3cret"
    try:
        with TestClient(app) as c:
            yield c
    finally:
        settings.auth_password = ""


def test_auth_disabled_by_default_allows_requests(client):
    r = client.get("/api/decks")
    assert r.status_code == 200


def test_status_reports_disabled_when_no_password(client):
    r = client.get("/api/auth/status")
    assert r.json() == {"auth_enabled": False, "authenticated": True}


def test_protected_route_requires_session_when_enabled(auth_client):
    r = auth_client.get("/api/decks")
    assert r.status_code == 401


def test_public_routes_bypass_auth(auth_client):
    assert auth_client.get("/api/health").status_code == 200
    assert auth_client.get("/api/version").status_code == 200
    assert auth_client.get("/api/auth/status").status_code == 200


def test_login_wrong_password_rejected(auth_client):
    r = auth_client.post("/api/auth/login", json={"password": "nope"})
    assert r.status_code == 401
    assert auth_client.get("/api/decks").status_code == 401


def test_login_then_access_protected_route(auth_client):
    r = auth_client.post("/api/auth/login", json={"password": "s3cret"})
    assert r.status_code == 200
    assert auth_client.get("/api/decks").status_code == 200
    assert auth_client.get("/api/auth/status").json() == {"auth_enabled": True, "authenticated": True}


def test_logout_clears_session(auth_client):
    auth_client.post("/api/auth/login", json={"password": "s3cret"})
    assert auth_client.get("/api/decks").status_code == 200
    auth_client.post("/api/auth/logout")
    assert auth_client.get("/api/decks").status_code == 401


def test_verify_session_token_rejects_tampered_signature():
    settings.auth_password = "s3cret"
    try:
        token = auth.create_session_token()
        issued_at, _, _sig = token.partition(".")
        tampered = f"{issued_at}.deadbeef"
        assert auth.verify_session_token(tampered) is False
        assert auth.verify_session_token(token) is True
    finally:
        settings.auth_password = ""


def test_verify_session_token_rejects_expired():
    settings.auth_password = "s3cret"
    try:
        old_token = f"1.{'0' * 64}"
        assert auth.verify_session_token(old_token) is False
    finally:
        settings.auth_password = ""
