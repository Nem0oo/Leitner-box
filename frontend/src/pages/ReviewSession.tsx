import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card3D } from "../components/Card3D";
import { Layout } from "../components/Layout";
import { useDirection } from "../lib/direction";
import { type DueCard, getDueCards, recordReview } from "../lib/review";
import { playSound } from "../lib/sound";

export default function ReviewSession() {
  const { deckId } = useParams();
  const [direction] = useDirection();
  const [queue, setQueue] = useState<DueCard[] | null>(null);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [done, setDone] = useState({ success: 0, fail: 0 });
  const navigate = useNavigate();

  useEffect(() => {
    getDueCards(deckId ? Number(deckId) : undefined, direction).then(setQueue);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFlip() {
    setFlipped((f) => !f);
    playSound("flip");
  }

  async function answer(result: "success" | "fail") {
    if (!queue) return;
    const card = queue[index];
    await recordReview(card.id, direction, result);
    playSound(result);
    setDone((d) => ({ ...d, [result]: d[result] + 1 }));
    setFlipped(false);
    if (index + 1 < queue.length) {
      setIndex(index + 1);
    } else {
      setIndex(queue.length);
    }
  }

  if (queue === null) {
    return (
      <Layout title="Révision">
        <p className="muted">Chargement…</p>
      </Layout>
    );
  }

  if (queue.length === 0 || index >= queue.length) {
    return (
      <Layout title="Révision">
        <div className="empty-state">
          <p>{queue.length === 0 ? "Aucune carte due pour le moment." : "Session terminée !"}</p>
          {queue.length > 0 && (
            <p className="muted">
              {done.success} réussite(s), {done.fail} échec(s)
            </p>
          )}
          <button className="btn" onClick={() => navigate(deckId ? `/decks/${deckId}` : "/")}>
            Retour
          </button>
        </div>
      </Layout>
    );
  }

  const card = queue[index];
  const frontText = direction === "recto_to_verso" ? card.recto_text : card.verso_text;
  const frontMedia = direction === "recto_to_verso" ? card.recto_media : card.verso_media;
  const backText = direction === "recto_to_verso" ? card.verso_text : card.recto_text;
  const backMedia = direction === "recto_to_verso" ? card.verso_media : card.recto_media;

  return (
    <Layout title={`Révision (${index + 1}/${queue.length})`}>
      <p className="muted" style={{ textAlign: "center" }}>
        {card.deck_name} · Boîte {card.box}
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
        <button className="btn fail" onClick={() => answer("fail")}>
          Raté
        </button>
        <button className="btn success" onClick={() => answer("success")}>
          Réussi
        </button>
      </div>
    </Layout>
  );
}
