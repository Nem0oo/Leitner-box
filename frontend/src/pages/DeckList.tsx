import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import { db, type LocalDeck } from "../lib/db";
import { useDirection } from "../lib/direction";
import { dueCount, ensureSeeded } from "../lib/review";
import { downloadDeckMedia } from "../lib/sync";

interface DeckRow extends LocalDeck {
  card_count: number;
  due: number;
}

export default function DeckList() {
  const [direction] = useDirection();
  const [rows, setRows] = useState<DeckRow[] | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [rescanMessage, setRescanMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  async function load() {
    await ensureSeeded();
    const decks = await db.decks.filter((d) => !d.deleted).toArray();
    const out: DeckRow[] = [];
    for (const deck of decks) {
      const count = await db.cards.where("deck_id").equals(deck.id).filter((c) => !c.deleted).count();
      const due = await dueCount(deck.id, direction);
      out.push({ ...deck, card_count: count, due });
    }
    setRows(out.sort((a, b) => a.name.localeCompare(b.name)));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [direction]);

  async function createDeck() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const deck = await api.createDeck(newName.trim());
      await db.decks.put({
        id: deck.id,
        name: deck.name,
        description: deck.description,
        last_modified: deck.last_modified,
        deleted: false,
        offline_enabled: false,
      });
      setNewName("");
      await load();
    } catch {
      alert("Création impossible (hors ligne ?)");
    } finally {
      setCreating(false);
    }
  }

  async function toggleOffline(deck: DeckRow) {
    const offline_enabled = !deck.offline_enabled;
    await db.decks.update(deck.id, { offline_enabled });
    if (offline_enabled) await downloadDeckMedia(deck.id);
    await load();
  }

  async function rescan() {
    setRescanMessage("Scan en cours…");
    try {
      const result = await api.rescan();
      setRescanMessage(`Scan terminé: ${JSON.stringify(result)}`);
    } catch {
      setRescanMessage("Scan impossible (hors ligne ?)");
    }
  }

  return (
    <Layout title="Decks">
      <div className="card-panel">
        <div className="row">
          <input
            placeholder="Nom du nouveau deck"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <button className="btn" onClick={createDeck} disabled={creating}>
            Créer
          </button>
        </div>
      </div>

      {rows === null && <p className="muted">Chargement…</p>}
      {rows?.length === 0 && <p className="empty-state">Aucun deck pour le moment.</p>}

      {rows?.map((deck) => (
        <div className="card-panel" key={deck.id}>
          <div className="row">
            <strong>{deck.name}</strong>
            {deck.due > 0 && <span className="due-badge">{deck.due} dues</span>}
          </div>
          <p className="muted">{deck.card_count} carte(s)</p>
          <div className="row">
            <label className="muted">
              <input type="checkbox" checked={deck.offline_enabled} onChange={() => toggleOffline(deck)} /> Disponible
              hors ligne
            </label>
          </div>
          <div className="row" style={{ marginTop: "0.6rem" }}>
            <button className="btn secondary" onClick={() => navigate(`/decks/${deck.id}`)}>
              Détail
            </button>
            <button className="btn" disabled={deck.due === 0} onClick={() => navigate(`/review/${deck.id}`)}>
              Réviser
            </button>
          </div>
        </div>
      ))}

      <div className="card-panel">
        <p className="muted">
          Import en masse : déposez des dossiers <code>carte_XXXX/</code> dans le dossier d'édition du serveur, puis
          scannez. Pour des cartes texte uniquement, déposez plutôt un fichier{" "}
          <code>{"<nom_du_deck>/cartes.txt"}</code> avec une ligne <code>recto;verso</code> par carte : chaque ligne
          sera transformée en dossier <code>carte_XXXX/</code> puis retirée du fichier.
        </p>
        <button className="btn secondary block" onClick={rescan}>
          Scanner le dossier d'édition
        </button>
        {rescanMessage && <p className="muted">{rescanMessage}</p>}
      </div>
    </Layout>
  );
}
