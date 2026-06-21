def _create_deck(client, name="Espagnol"):
    r = client.post("/api/decks", json={"name": name, "description": "desc"})
    assert r.status_code == 201
    return r.json()


def _create_card(client, deck_id, recto="hola", verso="hello"):
    r = client.post("/api/cards", json={"deck_id": deck_id, "recto_text": recto, "verso_text": verso})
    assert r.status_code == 201
    return r.json()


def test_create_and_list_decks(client):
    _create_deck(client, "Espagnol")
    r = client.get("/api/decks")
    assert r.status_code == 200
    decks = r.json()
    assert len(decks) == 1
    assert decks[0]["name"] == "Espagnol"
    assert decks[0]["card_count"] == 0


def test_create_card_starts_in_box_1_both_directions(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    assert card["recto_to_verso"]["box"] == 1
    assert card["verso_to_recto"]["box"] == 1
    assert card["recto_to_verso"]["is_due"] is True


def test_card_in_nonexistent_deck_404(client):
    r = client.post("/api/cards", json={"deck_id": 999, "recto_text": "a", "verso_text": "b"})
    assert r.status_code == 404


def test_delete_card_is_tombstoned_not_listed(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    r = client.delete(f"/api/cards/{card['id']}")
    assert r.status_code == 204
    r = client.get("/api/cards", params={"deck_id": deck["id"]})
    assert r.json() == []


def test_filter_cards_by_box(client):
    deck = _create_deck(client)
    card1 = _create_card(client, deck["id"])
    card2 = _create_card(client, deck["id"])

    client.post("/api/review/events", json={
        "card_id": card1["id"], "direction": "recto_to_verso", "result": "success",
    })

    r = client.get("/api/cards", params={"deck_id": deck["id"], "direction": "recto_to_verso", "box": 2})
    boxed = r.json()
    assert [c["id"] for c in boxed] == [card1["id"]]

    r = client.get("/api/cards", params={"deck_id": deck["id"], "direction": "recto_to_verso", "box": 1})
    boxed = r.json()
    assert [c["id"] for c in boxed] == [card2["id"]]


def test_deck_due_count_reflects_active_direction(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "success",
    })
    # recto_to_verso just reviewed -> box 2, interval 2 days -> not due now
    r = client.get(f"/api/decks/{deck['id']}", params={"direction": "recto_to_verso"})
    assert r.json()["due_count"] == 0
    # verso_to_recto never reviewed -> still due
    r = client.get(f"/api/decks/{deck['id']}", params={"direction": "verso_to_recto"})
    assert r.json()["due_count"] == 1
