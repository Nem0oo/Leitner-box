import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card3D } from "../components/Card3D";
import { Layout } from "../components/Layout";
import { useDirection } from "../lib/direction";
import { type DueCard, getDueCards, recordReview } from "../lib/review";
import { type SessionQueue, afterAnswer, createQueue, currentCard, remainingCount } from "../lib/session";
import { playSound } from "../lib/sound";
import { RATINGS, RATING_LABELS, type ReviewRating, STATE_LABELS, formatInterval, previewIntervals } from "../lib/srs";

const nowSeconds = () => Date.now() / 1000;

export default function ReviewSession() {
  const { deckId } = useParams();
  const [direction] = useDirection();
  const [queue, setQueue] = useState<SessionQueue<DueCard> | null>(null);
  const [total, setTotal] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [counts, setCounts] = useState<Record<ReviewRating, number>>({ again: 0, hard: 0, good: 0, easy: 0 });
  const [, setTick] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    getDueCards(deckId ? Number(deckId) : undefined, direction).then((cards) => {
      setQueue(createQueue(cards));
      setTotal(cards.length);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const card = queue ? currentCard(queue, nowSeconds()) : null;

  // A re-injected card may only become due later: re-render until it does.
  useEffect(() => {
    if (!queue || card || remainingCount(queue) === 0) return;
    const timer = setInterval(() => setTick((t) => t + 1), 15_000);
    return () => clearInterval(timer);
  }, [queue, card]);

  function handleFlip() {
    setFlipped((f) => !f);
    playSound("flip");
  }

  async function answer(rating: ReviewRating) {
    if (!queue || !card) return;
    const newState = await recordReview(card.id, direction, rating);
    playSound(rating === "again" ? "fail" : "success");
    setCounts((c) => ({ ...c, [rating]: c[rating] + 1 }));
    setFlipped(false);
    const answered = newState ? { ...card, state: newState } : card;
    setQueue(afterAnswer(queue, answered, answered.state, nowSeconds()));
  }

  if (queue === null) {
    return (
      <Layout title="Révision">
        <p className="muted">Chargement…</p>
      </Layout>
    );
  }

  if (!card) {
    const waiting = remainingCount(queue) > 0;
    return (
      <Layout title="Révision">
        <div className="empty-state">
          <p>
            {total === 0
              ? "Aucune carte due pour le moment."
              : waiting
                ? "Pause : les cartes en apprentissage reviennent dans quelques minutes."
                : "Session terminée !"}
          </p>
          {total > 0 && (
            <p className="muted">
              {RATINGS.map((r) => `${RATING_LABELS[r]} : ${counts[r]}`).join(" · ")}
            </p>
          )}
          <button className="btn" onClick={() => navigate(deckId ? `/decks/${deckId}` : "/")}>
            Retour
          </button>
        </div>
      </Layout>
    );
  }

  const frontText = direction === "recto_to_verso" ? card.recto_text : card.verso_text;
  const frontMedia = direction === "recto_to_verso" ? card.recto_media : card.verso_media;
  const backText = direction === "recto_to_verso" ? card.verso_text : card.recto_text;
  const backMedia = direction === "recto_to_verso" ? card.verso_media : card.recto_media;
  const intervals = previewIntervals(card.state, nowSeconds());

  return (
    <Layout title={`Révision (${remainingCount(queue)} restante${remainingCount(queue) > 1 ? "s" : ""})`}>
      <p className="muted" style={{ textAlign: "center" }}>
        {card.deck_name} · {STATE_LABELS[card.state.state]}
      </p>
      <Card3D
        frontText={frontText}
        frontMedia={frontMedia}
        backText={backText}
        backMedia={backMedia}
        flipped={flipped}
        onFlip={handleFlip}
      />
      <div className="review-actions">
        {RATINGS.map((rating) => (
          <button key={rating} className={`btn rating-${rating}`} onClick={() => answer(rating)}>
            {RATING_LABELS[rating]}
            <small>{formatInterval(intervals[rating])}</small>
          </button>
        ))}
      </div>
    </Layout>
  );
}
