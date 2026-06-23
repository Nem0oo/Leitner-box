import { api } from "./api";
import { db, getKV, setKV } from "./db";

const LAST_SYNC_KEY = "last_sync";

export async function pushPendingReviews(): Promise<number> {
  const pending = await db.reviewQueue.toArray();
  if (pending.length === 0) return 0;
  await api.pushReviewEvents(pending);
  await db.reviewQueue.bulkDelete(pending.map((p) => p.id));
  return pending.length;
}

export async function pullChanges(): Promise<{ decks: number; cards: number }> {
  const sinceRaw = await getKV(LAST_SYNC_KEY);
  const since = sinceRaw ? Number(sinceRaw) : undefined;
  const result = await api.syncPull(since);

  await db.transaction("rw", db.decks, db.cards, async () => {
    for (const deck of result.decks) {
      if (deck.deleted) {
        await db.decks.delete(deck.id);
      } else {
        await db.decks.put({
          id: deck.id,
          name: deck.name,
          description: deck.description,
          last_modified: deck.last_modified,
          deleted: false,
          offline_enabled: (await db.decks.get(deck.id))?.offline_enabled ?? false,
        });
      }
    }
    for (const card of result.cards) {
      if (card.deleted) {
        await db.cards.delete(card.id);
      } else {
        await db.cards.put(card);
      }
    }
  });

  await setKV(LAST_SYNC_KEY, String(result.server_time));
  return { decks: result.decks.length, cards: result.cards.length };
}

export async function downloadDeckMedia(deckId: number): Promise<void> {
  const cards = await db.cards.where("deck_id").equals(deckId).toArray();
  const hashes = new Set<string>();
  for (const card of cards) {
    card.recto_media.forEach((h) => hashes.add(h));
    card.verso_media.forEach((h) => hashes.add(h));
  }
  for (const hash of hashes) {
    if (await db.blobs.get(hash)) continue;
    const res = await fetch(api.mediaUrl(hash));
    if (!res.ok) continue;
    const blob = await res.blob();
    await db.blobs.put({ hash, blob });
  }
}

export async function fullSync(): Promise<{ decks: number; cards: number; reviewsPushed: number }> {
  const reviewsPushed = await pushPendingReviews();
  const { decks, cards } = await pullChanges();
  const offlineDecks = await db.decks.filter((d) => d.offline_enabled).toArray();
  for (const deck of offlineDecks) {
    await downloadDeckMedia(deck.id);
  }
  return { decks, cards, reviewsPushed };
}
