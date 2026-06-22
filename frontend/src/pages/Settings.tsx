import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import { disableNotifications, enableNotifications, isStandalonePWA, pushSupported } from "../lib/push";
import { isMuted, setMuted } from "../lib/sound";

export default function Settings() {
  const [reminderTime, setReminderTime] = useState("");
  const [reminderEnabled, setReminderEnabled] = useState(false);
  const [muted, setMutedState] = useState(isMuted());
  const [notifStatus, setNotifStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [authEnabled, setAuthEnabled] = useState(false);

  useEffect(() => {
    api.getSettings().then((s) => {
      setReminderTime(s.reminder_time ?? "20:00");
      setReminderEnabled(s.reminder_enabled);
    });
    api.authStatus().then((s) => setAuthEnabled(s.auth_enabled));
  }, []);

  async function handleLogout() {
    await api.logout();
    window.location.reload();
  }

  async function save() {
    setSaving(true);
    try {
      await api.updateSettings({ reminder_time: reminderTime, reminder_enabled: reminderEnabled });
    } catch {
      alert("Enregistrement impossible (hors ligne ?)");
    } finally {
      setSaving(false);
    }
  }

  async function handleEnableNotifications() {
    if (!pushSupported()) {
      setNotifStatus("Les notifications ne sont pas supportées sur ce navigateur.");
      return;
    }
    if (!isStandalonePWA()) {
      setNotifStatus("Ajoutez d'abord l'application à l'écran d'accueil pour activer les notifications.");
      return;
    }
    const result = await enableNotifications();
    setNotifStatus(
      result === "granted"
        ? "Notifications activées."
        : result === "denied"
          ? "Permission refusée."
          : "Impossible d'activer les notifications.",
    );
  }

  async function handleDisableNotifications() {
    await disableNotifications();
    setNotifStatus("Notifications désactivées.");
  }

  function toggleMute() {
    const next = !muted;
    setMuted(next);
    setMutedState(next);
  }

  return (
    <Layout title="Réglages">
      <div className="card-panel">
        <div className="form-field">
          <label>Heure du rappel quotidien</label>
          <input type="time" value={reminderTime} onChange={(e) => setReminderTime(e.target.value)} />
        </div>
        <div className="row">
          <label className="muted">
            <input
              type="checkbox"
              checked={reminderEnabled}
              onChange={(e) => setReminderEnabled(e.target.checked)}
            />{" "}
            Rappel activé
          </label>
          <button className="btn secondary" onClick={save} disabled={saving}>
            {saving ? "…" : "Enregistrer"}
          </button>
        </div>
      </div>

      <div className="card-panel">
        <p className="muted">
          Sur iPhone/iPad : ajoutez d'abord cette application à l'écran d'accueil (Partager → Sur l'écran
          d'accueil), puis activez les notifications ci-dessous depuis l'app installée.
        </p>
        <div className="row">
          <button className="btn" onClick={handleEnableNotifications}>
            Activer les notifications
          </button>
          <button className="btn secondary" onClick={handleDisableNotifications}>
            Désactiver
          </button>
        </div>
        {notifStatus && <p className="muted">{notifStatus}</p>}
      </div>

      <div className="card-panel">
        <div className="row">
          <span className="muted">Son</span>
          <button className="btn secondary" onClick={toggleMute}>
            {muted ? "Réactiver le son" : "Couper le son"}
          </button>
        </div>
      </div>

      {authEnabled && (
        <div className="card-panel">
          <div className="row">
            <span className="muted">Session</span>
            <button className="btn secondary" onClick={handleLogout}>
              Se déconnecter
            </button>
          </div>
        </div>
      )}
    </Layout>
  );
}
