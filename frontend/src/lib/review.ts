import { api } from "./api";
import { DEFAULT_NEW_CARDS_PER_DAY, newCardsIntroducedOn, selectDue } from "./dailyLimit";
import { FULL_PULL_KEY, db, getKV, setKV } from "./db";
import { DIRECTIONS, type Direction, type DirectionState, NEW_STATE, type ReviewRating, nextState } from "./srs";
import { pullChanges, pushPendingReviews } from "./sync";
import { syncDeviceTimezone } from "./timezone";

export interface DueCard {
  id: number;
  deck_id: number;
  deck_name: string;
  recto_text: string | null;
  recto_media: string[];
  verso_text: string | null;
  verso_media: string[];
  direction: Direction;
  state: DirectionState;
}

const NEW_CARDS_PER_DAY_KEY = "new_cards_per_day";

/** Daily new-card limit, cached locally so it applies offline. */
export async function getNewCardsPerDay(): Promise<number> {
  const raw = await getKV(NEW_CARDS_PER_DAY_KEY);
  const value = raw === undefined ? NaN : Number(raw);
  return Number.isFinite(value) ? value : DEFAULT_NEW_CARDS_PER_DAY;
}

export async function cacheNewCardsPerDay(value: number): Promise<void> {
  await setKV(NEW_CARDS_PER_DAY_KEY, String(value));
}

/** Best-effort refresh of the cached limit from the server (kept as is offline). */
export async function refreshNewCardsPerDay(): Promise<void> {
  try {
    await cacheNewCardsPerDay((await api.getSettings()).new_cards_per_day);
  } catch {
    // offline: keep the cached value
  }
}

/** Cards due now, read entirely from the local Dexie cache so review works
 * fully offline: every due card already introduced, plus the new cards still
 * allowed today (counted over all decks). Order is shuffled fresh on every
 * call, never persisted. */
export async function getDueCards(deckId: number | undefined, direction: Direction): Promise<DueCard[]> {
  const allCards = (await db.cards.toArray()).filter((c) => !c.deleted);
  const cards = deckId !== undefined ? allCards.filter((c) => c.deck_id === deckId) : allCards;
  const decks = await db.decks.toArray();
  const deckNames = new Map(decks.map((d) => [d.id, d.name]));

  const now = Date.now() / 1000;
  const introduced = newCardsIntroducedOn(
    allCards.map((c) => c[direction]),
    now,
  );
  const candidates: DueCard[] = cards.map((card) => ({
    id: card.id,
    deck_id: card.deck_id,
    deck_name: deckNames.get(card.deck_id) ?? "",
    recto_text: card.recto_text,
    recto_media: card.recto_media,
    verso_text: card.verso_text,
    verso_media: card.verso_media,
    direction,
    state: card[direction],
  }));
  const due = selectDue(candidates, now, (await getNewCardsPerDay()) - introduced);

  for (let i = due.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [due[i], due[j]] = [due[j], due[i]];
  }
  return due;
}

export async function dueCount(deckId: number | undefined, direction: Direction): Promise<number> {
  return (await getDueCards(deckId, direction)).length;
}

/** Apply a rating optimistically to the local cache, queue it for sync, and
 * opportunistically flush the queue if we're online. Returns the new state
 * (null if the card is no longer cached). */
export async function recordReview(
  cardId: number,
  direction: Direction,
  rating: ReviewRating,
): Promise<DirectionState | null> {
  const now = Date.now() / 1000;
  const card = await db.cards.get(cardId);
  if (!card) return null;

  const newState = nextState(card[direction], rating, now);
  await db.cards.put({ ...card, [direction]: newState });

  await db.reviewQueue.add({
    id: crypto.randomUUID(),
    card_id: cardId,
    direction,
    result: rating,
    timestamp: now,
  });

  if (navigator.onLine) {
    pushPendingReviews().catch(() => {});
  }
  return newState;
}

/** Start every card of a deck over as new (both directions) on the server,
 * then mirror it in the local cache. Needs to be online. */
export async function resetDeck(deckId: number): Promise<void> {
  await api.resetDeck(deckId);
  await db.cards
    .where("deck_id")
    .equals(deckId)
    .modify((card) => {
      for (const direction of DIRECTIONS) card[direction] = NEW_STATE;
    });
}

/** Fill the local cache from the server when it is empty, or refresh every
 * cached card once when a schema upgrade asked for it. The device timezone is
 * sent first so the server computes states with the same review days. */
export async function ensureSeeded(): Promise<void> {
  const empty = (await db.decks.count()) === 0;
  const needsFullPull = (await getKV(FULL_PULL_KEY)) === "1";
  if (!empty && !needsFullPull) return;
  try {
    await syncDeviceTimezone();
    if (empty) {
      const result = await api.syncPull();
      await db.transaction("rw", db.decks, db.cards, async () => {
        for (const deck of result.decks) {
          if (!deck.deleted) await db.decks.put({ ...deck, deleted: false, offline_enabled: false });
        }
        for (const card of result.cards) {
          if (!card.deleted) await db.cards.put(card);
        }
      });
    } else {
      await pushPendingReviews();
      await db.kv.delete("last_sync");
      await pullChanges();
    }
    await db.kv.delete(FULL_PULL_KEY);
  } catch {
    // offline: the cache stays as is and the next call retries
  }
}
