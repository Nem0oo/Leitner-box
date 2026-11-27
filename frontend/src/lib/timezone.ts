import { api } from "./api";

export function deviceTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/** Make the server count review days (and fire the daily reminder) in this
 * device's timezone. Best-effort: returns whether an update was sent. */
export async function syncDeviceTimezone(
  getSettings: () => Promise<{ reminder_timezone: string }> = api.getSettings,
  updateSettings: (payload: { reminder_timezone: string }) => Promise<unknown> = api.updateSettings,
  timezone: string = deviceTimezone(),
): Promise<boolean> {
  try {
    const current = await getSettings();
    if (current.reminder_timezone === timezone) return false;
    await updateSettings({ reminder_timezone: timezone });
    return true;
  } catch {
    return false;
  }
}
