import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Direction } from "./leitner";

const STORAGE_KEY = "leitner.direction";
const CHANGE_EVENT = "leitner-direction-change";

export function getDirection(): Direction {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "verso_to_recto" ? "verso_to_recto" : "recto_to_verso";
}

export function setDirection(direction: Direction): void {
  localStorage.setItem(STORAGE_KEY, direction);
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: direction }));
  // Best-effort: keep the server's copy in sync so the daily reminder
  // scheduler (which has no client open) checks the right direction too.
  api.updateSettings({ direction }).catch(() => {});
}

export function useDirection(): [Direction, (d: Direction) => void] {
  const [direction, setDirectionState] = useState<Direction>(getDirection());

  useEffect(() => {
    const handler = (e: Event) => setDirectionState((e as CustomEvent<Direction>).detail);
    window.addEventListener(CHANGE_EVENT, handler);
    return () => window.removeEventListener(CHANGE_EVENT, handler);
  }, []);

  const update = useCallback((d: Direction) => setDirection(d), []);
  return [direction, update];
}

export function otherDirection(direction: Direction): Direction {
  return direction === "recto_to_verso" ? "verso_to_recto" : "recto_to_verso";
}
