import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ApiError, api } from "../lib/api";
import { db, type LocalCard, type LocalDeck } from "../lib/db";
import { useDirection } from "../lib/direction";
import { STATE_LABELS, type SrsState, formatInterval } from "../lib/srs";

const FILTERS: SrsState[] = ["new", "learning", "review", "relearning"];

function nextReviewLabel(dueAt: number | null): string {
  if (dueAt === null) return "à apprendre";
  const delta = dueAt - Date.now() / 1000;
  return delta <= 0 ? "à réviser" : `dans ${formatInterval(delta)}`;
}

export default function DeckDetail() {
  const { deckId } = useParams();
  const id = Number(deckId);
  const [direction] = useDirection();
  const [deck, setDeck] = useState<LocalDeck | null>(null);
  const [cards, setCards] = useState<LocalCard[]>([]);
  const [stateFilter, setStateFilter] = useState<SrsState | null>(null);
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

  const filtered = stateFilter === null ? cards : cards.filter((c) => c[direction].state === stateFilter);

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
        <button className={stateFilter === null ? "active" : ""} onClick={() => setStateFilter(null)}>
          Toutes
        </button>
        {FILTERS.map((s) => (
          <button key={s} className={stateFilter === s ? "active" : ""} onClick={() => setStateFilter(s)}>
            {STATE_LABELS[s]}
          </button>
        ))}
      </div>

      {filtered.length === 0 && <p className="empty-state">Aucune carte dans ce filtre.</p>}

      {filtered.map((card) => (
        <div className="card-panel" key={card.id} onClick={() => navigate(`/cards/${card.id}/edit`)}>
          <div className="row">
            <span>{card.recto_text || "(sans texte)"}</span>
            <span className="muted">
              {STATE_LABELS[card[direction].state]} · {nextReviewLabel(card[direction].due_at)}
            </span>
          </div>
        </div>
      ))}
    </Layout>
  );
}
