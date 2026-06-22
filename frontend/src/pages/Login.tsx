import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../lib/api";

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login(password);
      onSuccess();
    } catch {
      setError("Mot de passe incorrect.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <main className="app-content">
        <form className="card-panel" onSubmit={handleSubmit}>
          <h1>Leitner Box</h1>
          <div className="form-field">
            <label>Mot de passe</label>
            <input
              type="password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={loading || !password}>
            {loading ? "…" : "Se connecter"}
          </button>
        </form>
      </main>
    </div>
  );
}
