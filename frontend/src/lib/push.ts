import { api } from "./api";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

export function isStandalonePWA(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

export function pushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window;
}

/** Must be called from inside a user-gesture event handler (iOS Safari requirement). */
export async function enableNotifications(): Promise<"granted" | "denied" | "unsupported" | "not-installed"> {
  if (!pushSupported()) return "unsupported";
  if (!isStandalonePWA()) return "not-installed";

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";

  const registration = await navigator.serviceWorker.ready;
  const settings = await api.getSettings();
  if (!settings.vapid_public_key) return "denied";

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(settings.vapid_public_key) as BufferSource,
  });
  await api.pushSubscribe(subscription.toJSON() as PushSubscriptionJSON);
  return "granted";
}

export async function disableNotifications(): Promise<void> {
  if (!pushSupported()) return;
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (subscription) {
    await api.pushUnsubscribe(subscription.toJSON() as PushSubscriptionJSON);
    await subscription.unsubscribe();
  }
}
