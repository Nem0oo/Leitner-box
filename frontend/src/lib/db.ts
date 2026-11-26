import Dexie, { type Table } from "dexie";
import type { Direction, DirectionState, ReviewRating } from "./srs";

export type { DirectionState };

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
  // "success" / "fail" may still sit in a queue written before FSRS; the server maps them to good / again.
  result: ReviewRating | "success" | "fail";
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
    // v2: per-direction state moved from Leitner boxes to FSRS. Cached decks and
    // cards are dropped so ensureSeeded() pulls them again in the new shape;
    // the pending review queue is kept.
    this.version(2)
      .stores({})
      .upgrade(async (tx) => {
        await tx.table("decks").clear();
        await tx.table("cards").clear();
        await tx.table("kv").delete("last_sync");
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
