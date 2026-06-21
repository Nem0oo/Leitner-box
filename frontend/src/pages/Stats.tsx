import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { db } from "../lib/db";

export default function Stats() {
  const [stats, setStats] = useState<{ total: number; success: number; fail: number; pending: number } | null>(null);

  useEffect(() => {
    (async () => {
      const pending = await db.reviewQueue.count();
      // Minimal MVP stats from locally cached state; full history lives
      // server-side in ReviewEvents for future, richer reporting.
      const cards = await db.cards.toArray();
      let success = 0;
      let fail = 0;
      for (const card of cards) {
        if (card.recto_to_verso.box > 1) success++;
        if (card.recto_to_verso.box === 1 && card.recto_to_verso.last_review_at) fail++;
      }
      setStats({ total: cards.length, success, fail, pending });
    })();
  }, []);

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
          <div className="row">
            <span className="muted">En progression (boîte &gt; 1)</span>
            <strong>{stats.success}</strong>
          </div>
          <div className="row">
            <span className="muted">Révisions en attente de sync</span>
            <strong>{stats.pending}</strong>
          </div>
        </div>
      )}
    </Layout>
  );
}
