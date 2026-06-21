from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models, storage
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/media", tags=["media"])


@router.post("/upload")
async def upload_media(file: UploadFile, db: Session = Depends(get_db)):
    data = await file.read()
    file_hash = storage.store_bytes(settings.resolved_blob_dir, data)
    if db.get(models.Blob, file_hash) is None:
        db.add(models.Blob(
            hash=file_hash,
            size=len(data),
            mime=file.content_type or storage.guess_mime(file.filename or ""),
        ))
        db.commit()
    return {"hash": file_hash, "size": len(data)}


@router.get("/{file_hash}")
def get_media(file_hash: str, db: Session = Depends(get_db)):
    blob = db.get(models.Blob, file_hash)
    path = storage.blob_path(settings.resolved_blob_dir, file_hash)
    if blob is None or not path.exists():
        raise HTTPException(404, "blob not found")
    return FileResponse(path, media_type=blob.mime or "application/octet-stream")
