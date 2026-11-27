import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ApiError, api } from "../lib/api";
import { db, type LocalCard, type LocalDeck } from "../lib/db";
import { useDirection } from "../lib/direction";
import { resetDeck } from "../lib/review";
import { type DirectionState, STATE_LABELS, type SrsState, formatInterval, isDue, reviewDay } from "../lib/srs";

const FILTERS: SrsState[] = ["new", "learning", "review", "relearning"];

function nextReviewLabel(state: DirectionState): string {
  const now = Date.now() / 1000;
  if (state.due_at === null) return "à apprendre";
  if (isDue(state, now)) return "à réviser";
  if (state.state !== "review") return `dans ${formatInterval(state.due_at - now)}`;
  const days = reviewDay(state.due_at) - reviewDay(now);
  return days === 1 ? "demain" : `dans ${formatInterval(days * 86400)}`;
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

  async function restartDeck() {
    if (
      !deck ||
      !confirm(
        `Remettre à zéro le deck "${deck.name}" ? Toutes ses cartes redeviennent nouvelles (dans les deux sens) ` +
          "et reviennent au rythme de la limite quotidienne. L'historique est conservé.",
      )
    )
      return;
    try {
      await resetDeck(id);
    } catch {
      alert("Remise à zéro impossible (hors ligne ?)");
      return;
    }
    await load();
  }

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
          <button className="btn secondary" onClick={restartDeck}>
            Remettre à zéro
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
              {STATE_LABELS[card[direction].state]} · {nextReviewLabel(card[direction])}
            </span>
          </div>
        </div>
      ))}
    </Layout>
  );
}
