"""Filesystem indexer for the manual-edit folder.

Layout expected on disk:

    <edit_dir>/<deck name>/carte_0001/recto.txt
                                       recto.mp3
                                       verso.txt
                                       verso.jpg

Files are grouped by prefix (everything before the first dot): all
`recto.*` files belong to the recto face, all `verso.*` to the verso face.
`recto.txt` / `verso.txt` are read as the card's text content; any other
extension is treated as a media attachment and content-addressed into the
blob store. Re-hashing is skipped when a file's mtime+size hasn't changed
since the last scan.

For text-only cards, building a `carte_XXXX/` folder by hand for every
card is slow. As a shortcut, a flat `<edit_dir>/<deck name>/cartes.txt`
file with one `recto;verso` pair per line is also supported: each scan
turns every line into its own `carte_XXXX/recto.txt` + `verso.txt` and
removes it from `cartes.txt`, so the file acts as an intake queue. The
separator is the first `;` on the line, so `verso` may itself contain
`;` but `recto` may not.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app import models, storage

FLAT_FILE_NAME = "cartes.txt"


@dataclass
class IndexResult:
    decks_created: int = 0
    cards_created: int = 0
    cards_updated: int = 0
    cards_unchanged: int = 0
    errors: list[str] = field(default_factory=list)


def get_or_create_deck(db: Session, name: str) -> models.Deck:
    deck = db.query(models.Deck).filter_by(name=name, deleted=False).first()
    if deck is not None:
        return deck
    deck = models.Deck(name=name, last_modified=time.time())
    db.add(deck)
    db.flush()
    return deck


def _hash_source_file(db: Session, blob_dir: Path, path: Path) -> str:
    rel_path = str(path)
    stat = path.stat()
    record = db.get(models.SourceFile, rel_path)
    if record is not None and storage.source_unchanged(stat.st_mtime, stat.st_size, record.mtime, record.size):
        return record.hash

    file_hash = storage.store_file_copy(blob_dir, path)
    if db.get(models.Blob, file_hash) is None:
        db.add(models.Blob(hash=file_hash, size=stat.st_size, mime=storage.guess_mime(path.name)))

    if record is not None:
        record.mtime = stat.st_mtime
        record.size = stat.st_size
        record.hash = file_hash
    else:
        db.add(models.SourceFile(path=rel_path, mtime=stat.st_mtime, size=stat.st_size, hash=file_hash))
    return file_hash


def _read_card_folder(db: Session, blob_dir: Path, card_folder: Path) -> dict:
    recto_text: str | None = None
    verso_text: str | None = None
    recto_media: list[str] = []
    verso_media: list[str] = []

    for f in sorted(card_folder.iterdir()):
        if not f.is_file():
            continue
        prefix = f.name.split(".", 1)[0]
        if prefix not in ("recto", "verso"):
            continue
        if f.name in ("recto.txt", "verso.txt"):
            text = f.read_text(encoding="utf-8").strip()
            if prefix == "recto":
                recto_text = text
            else:
                verso_text = text
        else:
            file_hash = _hash_source_file(db, blob_dir, f)
            (recto_media if prefix == "recto" else verso_media).append(file_hash)

    return {
        "recto_text": recto_text,
        "recto_media": recto_media,
        "verso_text": verso_text,
        "verso_media": verso_media,
    }


def _card_changed(card: models.Card, fields: dict) -> bool:
    return (
        card.recto_text != fields["recto_text"]
        or card.verso_text != fields["verso_text"]
        or list(card.recto_media or []) != fields["recto_media"]
        or list(card.verso_media or []) != fields["verso_media"]
    )


def _next_card_index(deck_folder: Path) -> int:
    max_index = 0
    for p in deck_folder.iterdir():
        if p.is_dir() and p.name.startswith("carte_"):
            suffix = p.name[len("carte_") :]
            if suffix.isdigit():
                max_index = max(max_index, int(suffix))
    return max_index + 1


def _materialize_flat_file(deck_folder: Path, result: IndexResult) -> None:
    flat_path = deck_folder / FLAT_FILE_NAME
    if not flat_path.exists():
        return

    lines = flat_path.read_text(encoding="utf-8").splitlines()
    remaining: list[str] = []
    next_index = _next_card_index(deck_folder)

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if ";" not in line:
            result.errors.append(f"{flat_path}: ligne ignorée (pas de ';'): {line!r}")
            remaining.append(raw_line)
            continue

        recto, _, verso = line.partition(";")
        recto, verso = recto.strip(), verso.strip()
        card_folder = deck_folder / f"carte_{next_index:04d}"
        card_folder.mkdir(parents=True)
        (card_folder / "recto.txt").write_text(recto, encoding="utf-8")
        (card_folder / "verso.txt").write_text(verso, encoding="utf-8")
        next_index += 1

    flat_path.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")


def scan_edit_dir(db: Session, edit_dir: Path, blob_dir: Path) -> IndexResult:
    result = IndexResult()
    if not edit_dir.exists():
        return result

    for deck_folder in sorted(p for p in edit_dir.iterdir() if p.is_dir()):
        existing_deck = db.query(models.Deck).filter_by(name=deck_folder.name, deleted=False).first()
        deck = get_or_create_deck(db, deck_folder.name)
        if existing_deck is None:
            result.decks_created += 1

        try:
            _materialize_flat_file(deck_folder, result)
        except Exception as exc:  # noqa: BLE001 - report and keep scanning
            result.errors.append(f"{deck_folder / FLAT_FILE_NAME}: {exc}")

        for card_folder in sorted(p for p in deck_folder.iterdir() if p.is_dir() and p.name.startswith("carte_")):
            try:
                fields = _read_card_folder(db, blob_dir, card_folder)
            except Exception as exc:  # noqa: BLE001 - report and keep scanning
                result.errors.append(f"{card_folder}: {exc}")
                continue

            source_folder = f"{deck_folder.name}/{card_folder.name}"
            card = db.query(models.Card).filter_by(source_folder=source_folder).first()
            if card is None:
                card = models.Card(deck_id=deck.id, source_folder=source_folder, last_modified=time.time(), **fields)
                db.add(card)
                result.cards_created += 1
            elif _card_changed(card, fields):
                for key, value in fields.items():
                    setattr(card, key, value)
                card.last_modified = time.time()
                card.deleted = False
                result.cards_updated += 1
            else:
                result.cards_unchanged += 1

    db.commit()
    return result
