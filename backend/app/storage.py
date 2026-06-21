"""Content-addressed blob storage on the local filesystem.

Files are stored at blobs/<sha256 hash>, deduplicated automatically. The
indexer avoids re-hashing unchanged source files by comparing mtime+size
before falling back to a full hash.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
from pathlib import Path


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def blob_path(blob_dir: Path, file_hash: str) -> Path:
    return blob_dir / file_hash


def blob_exists(blob_dir: Path, file_hash: str) -> bool:
    return blob_path(blob_dir, file_hash).exists()


def store_bytes(blob_dir: Path, data: bytes) -> str:
    file_hash = hash_bytes(data)
    blob_dir.mkdir(parents=True, exist_ok=True)
    dest = blob_path(blob_dir, file_hash)
    if not dest.exists():
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
    return file_hash


def store_file_copy(blob_dir: Path, source: Path) -> str:
    """Hash a source file and copy it into the blob store under its hash,
    without deleting the original (used by the indexer for edit-folder files)."""
    file_hash = hash_file(source)
    blob_dir.mkdir(parents=True, exist_ok=True)
    dest = blob_path(blob_dir, file_hash)
    if not dest.exists():
        tmp = dest.with_suffix(".tmp")
        shutil.copyfile(source, tmp)
        os.replace(tmp, dest)
    return file_hash


def guess_mime(filename: str) -> str | None:
    mime, _ = mimetypes.guess_type(filename)
    return mime


def source_unchanged(stat_mtime: float, stat_size: int, recorded_mtime: float, recorded_size: int) -> bool:
    """Cheap change-detection used by the indexer: only re-hash a file when
    its mtime or size differs from what was last recorded."""
    return stat_mtime == recorded_mtime and stat_size == recorded_size
