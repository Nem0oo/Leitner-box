from fastapi import APIRouter, HTTPException, Request, Response

from app import auth
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _cookie_secure(request: Request) -> bool:
    return request.url.scheme == "https"


@router.get("/status")
def status(request: Request):
    if not settings.auth_enabled:
        return {"auth_enabled": False, "authenticated": True}
    token = request.cookies.get(auth.SESSION_COOKIE)
    return {"auth_enabled": True, "authenticated": auth.verify_session_token(token)}


@router.post("/login")
def login(payload: dict, request: Request, response: Response):
    if not settings.auth_enabled:
        return {"ok": True}
    password = payload.get("password", "")
    if not auth.verify_password(password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    response.set_cookie(
        auth.SESSION_COOKIE,
        auth.create_session_token(),
        max_age=auth.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(auth.SESSION_COOKIE)
    return {"ok": True}
