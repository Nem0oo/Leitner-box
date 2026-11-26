import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { db } from "../lib/db";
import { useDirection } from "../lib/direction";
import { STATE_LABELS, type SrsState } from "../lib/srs";

const STATE_ORDER: SrsState[] = ["new", "learning", "review", "relearning"];

export default function Stats() {
  const [direction] = useDirection();
  const [stats, setStats] = useState<{ total: number; byState: Record<SrsState, number>; pending: number } | null>(null);

  useEffect(() => {
    (async () => {
      const pending = await db.reviewQueue.count();
      // Minimal stats from locally cached state; full history lives
      // server-side in ReviewEvents for future, richer reporting.
      const cards = (await db.cards.toArray()).filter((c) => !c.deleted);
      const byState: Record<SrsState, number> = { new: 0, learning: 0, review: 0, relearning: 0 };
      for (const card of cards) byState[card[direction].state]++;
      setStats({ total: cards.length, byState, pending });
    })();
  }, [direction]);

  return (
    <Layout title="Stats">
      <div className="card-panel">
        <p className="muted">Statistiques minimales (MVP). Les données complètes par révision sont conservées côté serveur pour une future vue détaillée.</p>
      </div>
      {stats && (
        <div className="card-panel">
          <div className="row">
            <span className="muted">Cartes au total</span>
            <strong>{stats.total}</strong>
          </div>
          {STATE_ORDER.map((s) => (
            <div className="row" key={s}>
              <span className="muted">{STATE_LABELS[s]}</span>
              <strong>{stats.byState[s]}</strong>
            </div>
          ))}
          <div className="row">
            <span className="muted">Révisions en attente de sync</span>
            <strong>{stats.pending}</strong>
          </div>
        </div>
      )}
    </Layout>
  );
}
