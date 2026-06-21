import os
import time

from app import models
from app.indexer import scan_edit_dir


def _make_card_folder(base, deck_name, card_name, recto_text="Bonjour", verso_text="Hello", extra_media=False):
    folder = base / deck_name / card_name
    folder.mkdir(parents=True)
    (folder / "recto.txt").write_text(recto_text, encoding="utf-8")
    (folder / "verso.txt").write_text(verso_text, encoding="utf-8")
    if extra_media:
        (folder / "recto.mp3").write_bytes(b"fake audio bytes")
        (folder / "verso.jpg").write_bytes(b"fake image bytes")
    return folder


def test_scan_creates_deck_and_card(db, tmp_path):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    _make_card_folder(edit_dir, "Espagnol", "carte_0001")

    result = scan_edit_dir(db, edit_dir, blob_dir)

    assert result.decks_created == 1
    assert result.cards_created == 1
    deck = db.query(models.Deck).filter_by(name="Espagnol").one()
    card = db.query(models.Card).filter_by(deck_id=deck.id).one()
    assert card.recto_text == "Bonjour"
    assert card.verso_text == "Hello"
    assert card.source_folder == "Espagnol/carte_0001"


def test_scan_groups_multiple_media_files_under_same_prefix(db, tmp_path):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    _make_card_folder(edit_dir, "Espagnol", "carte_0001", extra_media=True)

    scan_edit_dir(db, edit_dir, blob_dir)

    card = db.query(models.Card).one()
    assert len(card.recto_media) == 1
    assert len(card.verso_media) == 1
    # media files actually copied into content-addressed blob store
    assert (blob_dir / card.recto_media[0]).exists()
    assert (blob_dir / card.verso_media[0]).exists()


def test_scan_is_idempotent_when_nothing_changed(db, tmp_path):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    _make_card_folder(edit_dir, "Espagnol", "carte_0001")

    scan_edit_dir(db, edit_dir, blob_dir)
    card_before = db.query(models.Card).one()
    last_modified_before = card_before.last_modified

    result2 = scan_edit_dir(db, edit_dir, blob_dir)

    assert result2.cards_created == 0
    assert result2.cards_unchanged == 1
    card_after = db.query(models.Card).one()
    assert card_after.last_modified == last_modified_before


def test_scan_updates_card_when_text_changes(db, tmp_path):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    folder = _make_card_folder(edit_dir, "Espagnol", "carte_0001")

    scan_edit_dir(db, edit_dir, blob_dir)
    card_before = db.query(models.Card).one()
    last_modified_before = card_before.last_modified

    time.sleep(0.01)
    (folder / "recto.txt").write_text("Bonjour modifié", encoding="utf-8")
    result2 = scan_edit_dir(db, edit_dir, blob_dir)

    assert result2.cards_updated == 1
    card_after = db.query(models.Card).one()
    assert card_after.recto_text == "Bonjour modifié"
    assert card_after.last_modified > last_modified_before


def test_scan_skips_rehash_when_mtime_and_size_unchanged(db, tmp_path, monkeypatch):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    _make_card_folder(edit_dir, "Espagnol", "carte_0001", extra_media=True)

    scan_edit_dir(db, edit_dir, blob_dir)

    calls = []
    from app import indexer as indexer_module
    original = indexer_module.storage.hash_file

    def spy_hash_file(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(indexer_module.storage, "hash_file", spy_hash_file)

    scan_edit_dir(db, edit_dir, blob_dir)

    assert calls == []  # mtime+size unchanged -> no re-hash performed


def test_scan_rehashes_when_media_file_modified(db, tmp_path, monkeypatch):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    folder = _make_card_folder(edit_dir, "Espagnol", "carte_0001", extra_media=True)

    scan_edit_dir(db, edit_dir, blob_dir)
    card_before = db.query(models.Card).one()
    old_hash = card_before.recto_media[0]

    time.sleep(0.01)
    (folder / "recto.mp3").write_bytes(b"different fake audio bytes, longer")
    os.utime(folder / "recto.mp3", None)
    scan_edit_dir(db, edit_dir, blob_dir)

    card_after = db.query(models.Card).one()
    new_hash = card_after.recto_media[0]
    assert new_hash != old_hash
    assert (blob_dir / new_hash).exists()


def test_scan_multiple_decks_and_cards(db, tmp_path):
    edit_dir = tmp_path / "edit"
    blob_dir = tmp_path / "blobs"
    _make_card_folder(edit_dir, "Espagnol", "carte_0001")
    _make_card_folder(edit_dir, "Espagnol", "carte_0002", recto_text="Adios", verso_text="Goodbye")
    _make_card_folder(edit_dir, "Allemand", "carte_0001", recto_text="Guten Tag", verso_text="Good day")

    result = scan_edit_dir(db, edit_dir, blob_dir)

    assert result.decks_created == 2
    assert result.cards_created == 3
    assert db.query(models.Deck).count() == 2
    assert db.query(models.Card).count() == 3


def test_scan_missing_edit_dir_is_noop(db, tmp_path):
    result = scan_edit_dir(db, tmp_path / "does-not-exist", tmp_path / "blobs")
    assert result.cards_created == 0
    assert result.errors == []
