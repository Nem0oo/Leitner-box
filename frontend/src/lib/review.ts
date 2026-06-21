import { api } from "./api";
import { db, type DirectionState } from "./db";
import { dueAt, isDue, nextBox, type Direction } from "./leitner";
import { pushPendingReviews } from "./sync";

export interface DueCard {
  id: number;
  deck_id: number;
  deck_name: string;
  recto_text: string | null;
  recto_media: string[];
  verso_text: string | null;
  verso_media: string[];
  direction: Direction;
  box: number;
}

/** Cards due now, read entirely from the local Dexie cache so review works
 * fully offline. Order is shuffled fresh on every call, never persisted. */
export async function getDueCards(deckId: number | undefined, direction: Direction): Promise<DueCard[]> {
  const cards = deckId !== undefined ? await db.cards.where("deck_id").equals(deckId).toArray() : await db.cards.toArray();
  const decks = await db.decks.toArray();
  const deckNames = new Map(decks.map((d) => [d.id, d.name]));

  const now = Date.now() / 1000;
  const due: DueCard[] = [];
  for (const card of cards) {
    if (card.deleted) continue;
    const state = card[direction];
    if (isDue(state.box, state.last_review_at, now)) {
      due.push({
        id: card.id,
        deck_id: card.deck_id,
        deck_name: deckNames.get(card.deck_id) ?? "",
        recto_text: card.recto_text,
        recto_media: card.recto_media,
        verso_text: card.verso_text,
        verso_media: card.verso_media,
        direction,
        box: state.box,
      });
    }
  }

  for (let i = due.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [due[i], due[j]] = [due[j], due[i]];
  }
  return due;
}

export async function dueCount(deckId: number | undefined, direction: Direction): Promise<number> {
  return (await getDueCards(deckId, direction)).length;
}

/** Apply a review result optimistically to the local cache, queue it for
 * sync, and opportunistically flush the queue if we're online. */
export async function recordReview(cardId: number, direction: Direction, result: "success" | "fail"): Promise<void> {
  const now = Date.now() / 1000;
  const card = await db.cards.get(cardId);
  if (!card) return;

  const newBox = nextBox(card[direction].box, result);
  const newState: DirectionState = { box: newBox, last_review_at: now, due_at: dueAt(newBox, now), is_due: false };
  await db.cards.put({ ...card, [direction]: newState });

  await db.reviewQueue.add({
    id: crypto.randomUUID(),
    card_id: cardId,
    direction,
    result,
    timestamp: now,
  });

  if (navigator.onLine) {
    pushPendingReviews().catch(() => {});
  }
}

export async function ensureSeeded(): Promise<void> {
  const count = await db.decks.count();
  if (count > 0) return;
  try {
    const result = await api.syncPull();
    await db.transaction("rw", db.decks, db.cards, async () => {
      for (const deck of result.decks) {
        await db.decks.put({ ...deck, deleted: false, offline_enabled: false });
      }
      for (const card of result.cards) {
        if (!card.deleted) await db.cards.put(card);
      }
    });
  } catch {
    // offline on first load with empty cache: nothing we can do yet
  }
}
