import dataclasses

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.indexer import scan_edit_dir

router = APIRouter(prefix="/api/indexer", tags=["indexer"])


@router.post("/rescan")
def rescan(db: Session = Depends(get_db)) -> dict:
    result = scan_edit_dir(db, settings.resolved_edit_dir, settings.resolved_blob_dir)
    return dataclasses.asdict(result)
