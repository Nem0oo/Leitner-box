def _create_deck(client, name="Espagnol"):
    return client.post("/api/decks", json={"name": name}).json()


def _create_card(client, deck_id, recto="hola", verso="hello"):
    return client.post("/api/cards", json={"deck_id": deck_id, "recto_text": recto, "verso_text": verso}).json()


def test_due_cards_includes_never_reviewed_card(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    r = client.get("/api/review/due", params={"direction": "recto_to_verso"})
    assert [c["id"] for c in r.json()] == [card["id"]]


def test_due_cards_excludes_recently_reviewed_card(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "success",
    })
    r = client.get("/api/review/due", params={"direction": "recto_to_verso"})
    assert r.json() == []


def test_due_cards_grouped_mode_spans_all_decks(client):
    deck1 = _create_deck(client, "Espagnol")
    deck2 = _create_deck(client, "Allemand")
    card1 = _create_card(client, deck1["id"])
    card2 = _create_card(client, deck2["id"])
    r = client.get("/api/review/due")
    ids = {c["id"] for c in r.json()}
    assert ids == {card1["id"], card2["id"]}


def test_due_cards_filtered_by_deck(client):
    deck1 = _create_deck(client, "Espagnol")
    deck2 = _create_deck(client, "Allemand")
    card1 = _create_card(client, deck1["id"])
    _create_card(client, deck2["id"])
    r = client.get("/api/review/due", params={"deck_id": deck1["id"]})
    assert [c["id"] for c in r.json()] == [card1["id"]]


def test_review_event_good_moves_new_card_into_learning(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    r = client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "good",
    })
    assert r.status_code == 201
    state = client.get(f"/api/cards/{card['id']}").json()
    assert state["recto_to_verso"]["state"] == "learning"
    assert state["recto_to_verso"]["review_count"] == 1
    assert state["recto_to_verso"]["is_due"] is False
    assert state["verso_to_recto"]["state"] == "new"  # other direction untouched


def test_review_event_again_on_review_card_enters_relearning(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    t0 = 1_767_254_400.0  # 2026-01-01 08:00 UTC
    for ts, rating in [(t0, "good"), (t0 + 600, "good"), (t0 + 3 * 86400, "again")]:
        client.post("/api/review/events", json={
            "card_id": card["id"], "direction": "recto_to_verso", "result": rating, "timestamp": ts,
        })
    state = client.get(f"/api/cards/{card['id']}").json()["recto_to_verso"]
    assert state["state"] == "relearning"
    assert state["stability"] is not None
    assert state["difficulty"] is not None


def test_review_event_legacy_success_still_accepted(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    r = client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "success",
    })
    assert r.status_code == 201
    state = client.get(f"/api/cards/{card['id']}").json()["recto_to_verso"]
    assert state["state"] == "learning"


def test_review_event_invalid_result_rejected(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    r = client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "maybe",
    })
    assert r.status_code == 400


def test_batch_review_events_idempotent_on_repeated_id(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    event = {
        "id": "11111111-1111-1111-1111-111111111111",
        "card_id": card["id"], "direction": "recto_to_verso", "result": "success",
    }
    r1 = client.post("/api/review/events/batch", json={"events": [event]})
    assert len(r1.json()) == 1
    # simulate offline queue retry pushing the same event id again
    r2 = client.post("/api/review/events/batch", json={"events": [event]})
    assert len(r2.json()) == 1

    card_state = client.get(f"/api/cards/{card['id']}").json()
    assert card_state["recto_to_verso"]["review_count"] == 1  # only applied once, not twice


def test_due_count_follows_the_configured_timezone(client, db):
    from app import crud

    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    # easy on a new card -> review state due 8 days later, at 03:30 UTC (04:30 Paris)
    reviewed_at = 1_767_324_600.0  # 2026-01-02 03:30 UTC
    client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "easy", "timestamp": reviewed_at,
    })
    now = 1_767_960_000.0  # 2026-01-09 12:00 UTC: same review day as the due time in UTC, the day before in Paris

    assert crud.due_count_for_cards(db, [card["id"]], "recto_to_verso", now) == 1
    client.put("/api/settings", json={"reminder_timezone": "Europe/Paris"})
    db.expire_all()
    assert crud.due_count_for_cards(db, [card["id"]], "recto_to_verso", now) == 0


def test_due_count_endpoint(client):
    deck = _create_deck(client)
    _create_card(client, deck["id"])
    _create_card(client, deck["id"])
    r = client.get("/api/review/due-count", params={"deck_id": deck["id"]})
    assert r.json()["due_count"] == 2


def test_new_cards_per_day_limits_due_new_cards(client):
    client.put("/api/settings", json={"new_cards_per_day": 2})
    deck = _create_deck(client)
    cards = [_create_card(client, deck["id"], recto=str(i)) for i in range(3)]
    due = client.get("/api/review/due").json()
    assert sorted(c["id"] for c in due) == [cards[0]["id"], cards[1]["id"]]
    assert client.get("/api/review/due-count").json()["due_count"] == 2
    assert client.get("/api/decks").json()[0]["due_count"] == 2


def test_new_cards_reviewed_today_use_up_the_daily_limit(client):
    client.put("/api/settings", json={"new_cards_per_day": 2})
    deck = _create_deck(client)
    other = _create_deck(client, "Allemand")
    first = _create_card(client, other["id"])
    cards = [_create_card(client, deck["id"], recto=str(i)) for i in range(3)]
    client.post("/api/review/events", json={"card_id": first["id"], "direction": "recto_to_verso", "result": "good"})
    due = client.get("/api/review/due", params={"deck_id": deck["id"]}).json()
    assert [c["id"] for c in due] == [cards[0]["id"]]
    # the limit is per direction
    other_direction = client.get("/api/review/due", params={"direction": "verso_to_recto"}).json()
    assert len(other_direction) == 2


def test_reset_deck_makes_its_cards_new_again(client):
    deck = _create_deck(client)
    other = _create_deck(client, "Allemand")
    card = _create_card(client, deck["id"])
    kept = _create_card(client, other["id"])
    for cid in (card["id"], kept["id"]):
        for direction in ("recto_to_verso", "verso_to_recto"):
            client.post("/api/review/events", json={"card_id": cid, "direction": direction, "result": "easy"})
    before = client.get(f"/api/cards/{card['id']}").json()

    r = client.post(f"/api/decks/{deck['id']}/reset")
    assert r.status_code == 204

    after = client.get(f"/api/cards/{card['id']}").json()
    assert after["recto_to_verso"]["state"] == "new"
    assert after["verso_to_recto"]["state"] == "new"
    assert after["recto_to_verso"]["review_count"] == 0
    assert after["last_modified"] > before["last_modified"]
    assert client.get(f"/api/cards/{kept['id']}").json()["recto_to_verso"]["state"] == "review"


def test_reset_unknown_deck_is_404(client):
    assert client.post("/api/decks/999/reset").status_code == 404


def test_reset_is_not_accepted_as_a_review_result(client):
    deck = _create_deck(client)
    card = _create_card(client, deck["id"])
    r = client.post("/api/review/events", json={
        "card_id": card["id"], "direction": "recto_to_verso", "result": "reset",
    })
    assert r.status_code == 400
