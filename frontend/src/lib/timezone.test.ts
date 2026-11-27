import { describe, expect, it, vi } from "vitest";
import { syncDeviceTimezone } from "./timezone";

describe("syncDeviceTimezone", () => {
  it("sends the device timezone when the server has another one", async () => {
    const update = vi.fn().mockResolvedValue(undefined);
    const sent = await syncDeviceTimezone(async () => ({ reminder_timezone: "UTC" }), update, "Europe/Paris");
    expect(update).toHaveBeenCalledWith({ reminder_timezone: "Europe/Paris" });
    expect(sent).toBe(true);
  });

  it("does nothing when the server already has it", async () => {
    const update = vi.fn();
    const sent = await syncDeviceTimezone(async () => ({ reminder_timezone: "Europe/Paris" }), update, "Europe/Paris");
    expect(update).not.toHaveBeenCalled();
    expect(sent).toBe(false);
  });

  it("swallows network errors (offline)", async () => {
    const sent = await syncDeviceTimezone(() => Promise.reject(new Error("offline")), vi.fn(), "Europe/Paris");
    expect(sent).toBe(false);
  });
});
