import io


def _create_deck(client, name="Espagnol"):
    return client.post("/api/decks", json={"name": name}).json()


def _create_card(client, deck_id, recto="hola", verso="hello"):
    return client.post("/api/cards", json={"deck_id": deck_id, "recto_text": recto, "verso_text": verso}).json()


def test_sync_pull_returns_everything_when_since_none(client):
    deck = _create_deck(client)
    _create_card(client, deck["id"])
    r = client.get("/api/sync/pull")
    body = r.json()
    assert len(body["decks"]) == 1
    assert len(body["cards"]) == 1
    assert "server_time" in body


def test_sync_pull_filters_by_since(client):
    deck = _create_deck(client)
    r1 = client.get("/api/sync/pull")
    checkpoint = r1.json()["server_time"]

    _create_card(client, deck["id"])
    r2 = client.get("/api/sync/pull", params={"since": checkpoint})
    body = r2.json()
    assert len(body["cards"]) == 1
    assert len(body["decks"]) == 0  # deck unchanged since checkpoint


def test_media_upload_then_download_roundtrip(client):
    content = b"fake media bytes"
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
    r = client.post("/api/media/upload", files=files)
    assert r.status_code == 200
    file_hash = r.json()["hash"]

    r2 = client.get(f"/api/media/{file_hash}")
    assert r2.status_code == 200
    assert r2.content == content


def test_media_upload_dedupes_by_hash(client):
    content = b"identical content"
    files = {"file": ("a.txt", io.BytesIO(content), "text/plain")}
    r1 = client.post("/api/media/upload", files=files)
    files = {"file": ("b.txt", io.BytesIO(content), "text/plain")}
    r2 = client.post("/api/media/upload", files=files)
    assert r1.json()["hash"] == r2.json()["hash"]


def test_sync_blob_check_reports_missing_hashes(client):
    content = b"some bytes"
    files = {"file": ("a.txt", io.BytesIO(content), "text/plain")}
    r = client.post("/api/media/upload", files=files)
    known_hash = r.json()["hash"]

    r2 = client.post("/api/sync/blobs/check", json={"hashes": [known_hash, "doesnotexist"]})
    assert r2.json()["missing"] == ["doesnotexist"]


def test_settings_defaults(client):
    r = client.get("/api/settings")
    body = r.json()
    assert body["reminder_enabled"] is False
    assert body["direction"] == "recto_to_verso"


def test_settings_update_persists(client):
    client.put("/api/settings", json={"reminder_time": "08:30", "reminder_enabled": True, "direction": "verso_to_recto"})
    r = client.get("/api/settings")
    body = r.json()
    assert body["reminder_time"] == "08:30"
    assert body["reminder_enabled"] is True
    assert body["direction"] == "verso_to_recto"


def test_push_subscribe_and_unsubscribe(client):
    payload = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "key1", "auth": "key2"}}
    r = client.post("/api/push/subscribe", json=payload)
    assert r.status_code == 201
    r2 = client.post("/api/push/unsubscribe", json=payload)
    assert r2.status_code == 204
