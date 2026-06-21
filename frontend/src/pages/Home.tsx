import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DirectionToggle } from "../components/DirectionToggle";
import { Layout } from "../components/Layout";
import { useDirection } from "../lib/direction";
import { dueCount, ensureSeeded } from "../lib/review";
import { fullSync } from "../lib/sync";

export default function Home() {
  const [direction] = useDirection();
  const [due, setDue] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  async function refresh() {
    await ensureSeeded();
    setDue(await dueCount(undefined, direction));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [direction]);

  async function handleSync() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await fullSync();
      setSyncMessage(`Sync OK — ${result.decks} deck(s), ${result.cards} carte(s), ${result.reviewsPushed} révision(s) envoyée(s).`);
      await refresh();
    } catch {
      setSyncMessage("Sync impossible (hors ligne ?)");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <Layout title="Leitner Box">
      <div className="card-panel" style={{ textAlign: "center" }}>
        <p className="muted">Direction de révision</p>
        <DirectionToggle />
      </div>

      <div className="card-panel" style={{ textAlign: "center" }}>
        <p className="muted">Cartes dues maintenant</p>
        <p style={{ fontSize: "2.6rem", fontWeight: 700, margin: "0.2rem 0" }}>{due ?? "…"}</p>
        <button className="btn block" disabled={!due} onClick={() => navigate("/review")}>
          Réviser
        </button>
      </div>

      <div className="card-panel">
        <div className="row">
          <span className="muted">Synchronisation</span>
          <button className="btn secondary" onClick={handleSync} disabled={syncing}>
            {syncing ? "Sync…" : "Synchroniser"}
          </button>
        </div>
        {syncMessage && <p className="muted">{syncMessage}</p>}
      </div>
    </Layout>
  );
}
