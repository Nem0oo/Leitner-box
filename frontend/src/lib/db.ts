import Dexie, { type Table } from "dexie";
import type { Direction } from "./leitner";

export interface DirectionState {
  box: number;
  last_review_at: number | null;
  due_at: number | null;
  is_due: boolean;
}

export interface LocalDeck {
  id: number;
  name: string;
  description: string | null;
  last_modified: number;
  deleted: boolean;
  offline_enabled: boolean; // local-only preference, never synced to server
}

export interface LocalCard {
  id: number;
  deck_id: number;
  recto_text: string | null;
  recto_media: string[];
  verso_text: string | null;
  verso_media: string[];
  last_modified: number;
  deleted: boolean;
  recto_to_verso: DirectionState;
  verso_to_recto: DirectionState;
}

export interface PendingReviewEvent {
  id: string;
  card_id: number;
  direction: Direction;
  result: "success" | "fail";
  timestamp: number;
}

export interface CachedBlob {
  hash: string;
  blob: Blob;
}

export interface KeyValueEntry {
  key: string;
  value: string;
}

class LeitnerDB extends Dexie {
  decks!: Table<LocalDeck, number>;
  cards!: Table<LocalCard, number>;
  reviewQueue!: Table<PendingReviewEvent, string>;
  blobs!: Table<CachedBlob, string>;
  kv!: Table<KeyValueEntry, string>;

  constructor() {
    super("leitner-box");
    this.version(1).stores({
      decks: "id, last_modified, deleted",
      cards: "id, deck_id, last_modified, deleted",
      reviewQueue: "id, card_id",
      blobs: "hash",
      kv: "key",
    });
  }
}

export const db = new LeitnerDB();

export async function getKV(key: string): Promise<string | undefined> {
  const row = await db.kv.get(key);
  return row?.value;
}

export async function setKV(key: string, value: string): Promise<void> {
  await db.kv.put({ key, value });
}
