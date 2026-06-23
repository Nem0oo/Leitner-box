import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ApiError, api } from "../lib/api";
import { db, type LocalCard, type LocalDeck } from "../lib/db";
import { useDirection } from "../lib/direction";
import { MAX_BOX, MIN_BOX } from "../lib/leitner";

export default function DeckDetail() {
  const { deckId } = useParams();
  const id = Number(deckId);
  const [direction] = useDirection();
  const [deck, setDeck] = useState<LocalDeck | null>(null);
  const [cards, setCards] = useState<LocalCard[]>([]);
  const [box, setBox] = useState<number | null>(null);
  const navigate = useNavigate();

  async function load() {
    setDeck((await db.decks.get(id)) ?? null);
    const all = await db.cards.where("deck_id").equals(id).filter((c) => !c.deleted).toArray();
    setCards(all);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const filtered = box === null ? cards : cards.filter((c) => c[direction].box === box);

  async function removeDeck() {
    if (!deck || !confirm(`Supprimer le deck "${deck.name}" et toutes ses cartes ?`)) return;
    try {
      await api.deleteDeck(id);
    } catch (err) {
      // 404 means the server already considers it deleted (stale local cache) - clean up anyway.
      if (!(err instanceof ApiError && err.status === 404)) {
        alert("Suppression impossible (hors ligne ?)");
        return;
      }
    }
    await db.transaction("rw", db.decks, db.cards, async () => {
      await db.decks.delete(id);
      await db.cards.where("deck_id").equals(id).delete();
    });
    navigate("/decks");
  }

  return (
    <Layout title={deck?.name ?? "Deck"}>
      <div className="card-panel">
        <div className="row">
          <button className="btn secondary" onClick={() => navigate(`/cards/new?deck=${id}`)}>
            + Ajouter une carte
          </button>
          <button className="btn" onClick={() => navigate(`/review/${id}`)}>
            Réviser ce deck
          </button>
          <button className="btn fail" onClick={removeDeck}>
            Supprimer le deck
          </button>
        </div>
      </div>

      <div className="box-filter">
        <button className={box === null ? "active" : ""} onClick={() => setBox(null)}>
          Toutes
        </button>
        {Array.from({ length: MAX_BOX - MIN_BOX + 1 }, (_, i) => i + MIN_BOX).map((b) => (
          <button key={b} className={box === b ? "active" : ""} onClick={() => setBox(b)}>
            Boîte {b}
          </button>
        ))}
      </div>

      {filtered.length === 0 && <p className="empty-state">Aucune carte dans ce filtre.</p>}

      {filtered.map((card) => (
        <div className="card-panel" key={card.id} onClick={() => navigate(`/cards/${card.id}/edit`)}>
          <div className="row">
            <span>{card.recto_text || "(sans texte)"}</span>
            <span className="muted">Boîte {card[direction].box}</span>
          </div>
        </div>
      ))}
    </Layout>
  );
}
