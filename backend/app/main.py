import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import auth
from app.config import settings
from app.database import init_db
from app.indexer import scan_edit_dir
from app.routers import auth as auth_router
from app.routers import cards, decks, indexer, media, push, reviews, settings as settings_router, sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"
VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.resolved_blob_dir.mkdir(parents=True, exist_ok=True)
    settings.resolved_edit_dir.mkdir(parents=True, exist_ok=True)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        result = scan_edit_dir(db, settings.resolved_edit_dir, settings.resolved_blob_dir)
        logger.info("Startup indexer scan: %s", result)
    finally:
        db.close()

    scheduler = None
    try:
        from app.scheduler import start_scheduler

        scheduler = start_scheduler()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to start reminder scheduler")

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Leitner Box", lifespan=lifespan)


@app.middleware("http")
async def require_auth(request: Request, call_next):
    path = request.url.path
    if settings.auth_enabled and path.startswith("/api/") and path not in auth.PUBLIC_API_PATHS:
        token = request.cookies.get(auth.SESSION_COOKIE)
        if not auth.verify_session_token(token):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


app.include_router(auth_router.router)
app.include_router(decks.router)
app.include_router(cards.router)
app.include_router(reviews.router)
app.include_router(sync.router)
app.include_router(media.router)
app.include_router(settings_router.router)
app.include_router(push.router)
app.include_router(indexer.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/version")
def version():
    sha = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "unknown"
    return {"sha": sha}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
