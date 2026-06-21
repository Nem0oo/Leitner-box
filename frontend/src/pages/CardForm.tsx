import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { MediaRenderer } from "../components/MediaRenderer";
import { api } from "../lib/api";
import { db } from "../lib/db";

type Face = "recto" | "verso";

export default function CardForm() {
  const { cardId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const editing = Boolean(cardId);

  const [deckId, setDeckId] = useState<number | null>(
    searchParams.get("deck") ? Number(searchParams.get("deck")) : null,
  );
  const [decks, setDecks] = useState<{ id: number; name: string }[]>([]);
  const [rectoText, setRectoText] = useState("");
  const [versoText, setVersoText] = useState("");
  const [rectoMedia, setRectoMedia] = useState<string[]>([]);
  const [versoMedia, setVersoMedia] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [recording, setRecording] = useState<Face | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    db.decks
      .filter((d) => !d.deleted)
      .toArray()
      .then((list) => setDecks(list.map((d) => ({ id: d.id, name: d.name }))));
  }, []);

  useEffect(() => {
    if (!cardId) return;
    api.getCard(Number(cardId)).then((card) => {
      setDeckId(card.deck_id);
      setRectoText(card.recto_text ?? "");
      setVersoText(card.verso_text ?? "");
      setRectoMedia(card.recto_media);
      setVersoMedia(card.verso_media);
    });
  }, [cardId]);

  async function handleFileChosen(face: Face, files: FileList | null) {
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      const { hash } = await api.uploadMedia(file, file.name);
      if (face === "recto") setRectoMedia((m) => [...m, hash]);
      else setVersoMedia((m) => [...m, hash]);
    }
  }

  async function startRecording(face: Face) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      stream.getTracks().forEach((t) => t.stop());
      const { hash } = await api.uploadMedia(blob, "recording.webm");
      if (face === "recto") setRectoMedia((m) => [...m, hash]);
      else setVersoMedia((m) => [...m, hash]);
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(face);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(null);
  }

  async function save() {
    if (!deckId) {
      alert("Choisissez un deck");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        const card = await api.updateCard(Number(cardId), {
          recto_text: rectoText,
          verso_text: versoText,
          recto_media: rectoMedia,
          verso_media: versoMedia,
          deck_id: deckId,
        });
        await db.cards.put(card);
      } else {
        const card = await api.createCard({ deck_id: deckId, recto_text: rectoText, verso_text: versoText });
        const updated = await api.updateCard(card.id, { recto_media: rectoMedia, verso_media: versoMedia });
        await db.cards.put(updated);
      }
      navigate(`/decks/${deckId}`);
    } catch {
      alert("Enregistrement impossible (hors ligne ?)");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!editing || !confirm("Supprimer cette carte ?")) return;
    await api.deleteCard(Number(cardId));
    await db.cards.delete(Number(cardId));
    navigate(deckId ? `/decks/${deckId}` : "/decks");
  }

  function faceEditor(face: Face, text: string, setText: (v: string) => void, media: string[]) {
    return (
      <div className="card-panel">
        <div className="form-field">
          <label>{face === "recto" ? "Recto" : "Verso"}</label>
          <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        </div>
        <MediaRenderer hashes={media} />
        <div className="row" style={{ marginTop: "0.6rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <label className="btn secondary">
            Photo/Vidéo
            <input
              type="file"
              accept="image/*,video/*"
              capture="environment"
              style={{ display: "none" }}
              onChange={(e) => handleFileChosen(face, e.target.files)}
            />
          </label>
          <label className="btn secondary">
            Fichier
            <input
              type="file"
              multiple
              style={{ display: "none" }}
              onChange={(e) => handleFileChosen(face, e.target.files)}
            />
          </label>
          {recording === face ? (
            <button className="btn fail" onClick={stopRecording}>
              ⏹ Arrêter
            </button>
          ) : (
            <button className="btn secondary" onClick={() => startRecording(face)} disabled={recording !== null}>
              🎙 Enregistrer audio
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <Layout title={editing ? "Modifier la carte" : "Nouvelle carte"}>
      <div className="card-panel">
        <div className="form-field">
          <label>Deck</label>
          <select value={deckId ?? ""} onChange={(e) => setDeckId(Number(e.target.value))}>
            <option value="" disabled>
              Choisir un deck
            </option>
            {decks.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {faceEditor("recto", rectoText, setRectoText, rectoMedia)}
      {faceEditor("verso", versoText, setVersoText, versoMedia)}

      <button className="btn block" onClick={save} disabled={saving}>
        {saving ? "Enregistrement…" : "Enregistrer"}
      </button>
      {editing && (
        <button className="btn fail block" style={{ marginTop: "0.6rem" }} onClick={remove}>
          Supprimer
        </button>
      )}
    </Layout>
  );
}
