import type { Direction } from "./leitner";

export const UNAUTHORIZED_EVENT = "leitner:unauthorized";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function notifyIfUnauthorized(status: number, path: string) {
  if (status === 401 && path !== "/api/auth/login") window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    notifyIfUnauthorized(res.status, path);
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, `${init?.method ?? "GET"} ${path} failed: ${res.status} ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface DeckDTO {
  id: number;
  name: string;
  description: string | null;
  last_modified: number;
  card_count: number;
  due_count: number;
  deleted: boolean;
}

export interface DirectionStateDTO {
  box: number;
  last_review_at: number | null;
  due_at: number | null;
  is_due: boolean;
}

export interface CardDTO {
  id: number;
  deck_id: number;
  recto_text: string | null;
  recto_media: string[];
  verso_text: string | null;
  verso_media: string[];
  last_modified: number;
  deleted: boolean;
  recto_to_verso: DirectionStateDTO;
  verso_to_recto: DirectionStateDTO;
}

export interface DueCardDTO {
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

export interface ReviewEventInput {
  id: string;
  card_id: number;
  direction: Direction;
  result: "success" | "fail";
  timestamp: number;
}

export interface SettingsDTO {
  reminder_time: string | null;
  reminder_enabled: boolean;
  direction: Direction;
  vapid_public_key: string;
}

export interface SyncPullResponse {
  server_time: number;
  decks: DeckDTO[];
  cards: CardDTO[];
}

export const api = {
  listDecks: (direction: Direction) => request<DeckDTO[]>(`/api/decks?direction=${direction}`),
  getDeck: (id: number, direction: Direction) => request<DeckDTO>(`/api/decks/${id}?direction=${direction}`),
  createDeck: (name: string, description?: string) =>
    request<DeckDTO>("/api/decks", { method: "POST", body: JSON.stringify({ name, description }) }),
  updateDeck: (id: number, payload: { name?: string; description?: string }) =>
    request<DeckDTO>(`/api/decks/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteDeck: (id: number) => request<void>(`/api/decks/${id}`, { method: "DELETE" }),

  listCards: (params: { deck_id?: number; direction: Direction; box?: number }) => {
    const qs = new URLSearchParams();
    if (params.deck_id !== undefined) qs.set("deck_id", String(params.deck_id));
    qs.set("direction", params.direction);
    if (params.box !== undefined) qs.set("box", String(params.box));
    return request<CardDTO[]>(`/api/cards?${qs.toString()}`);
  },
  getCard: (id: number) => request<CardDTO>(`/api/cards/${id}`),
  createCard: (payload: { deck_id: number; recto_text?: string; verso_text?: string }) =>
    request<CardDTO>("/api/cards", { method: "POST", body: JSON.stringify(payload) }),
  updateCard: (
    id: number,
    payload: Partial<{ recto_text: string; verso_text: string; recto_media: string[]; verso_media: string[]; deck_id: number }>,
  ) => request<CardDTO>(`/api/cards/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteCard: (id: number) => request<void>(`/api/cards/${id}`, { method: "DELETE" }),

  dueCards: (params: { deck_id?: number; direction: Direction }) => {
    const qs = new URLSearchParams();
    if (params.deck_id !== undefined) qs.set("deck_id", String(params.deck_id));
    qs.set("direction", params.direction);
    return request<DueCardDTO[]>(`/api/review/due?${qs.toString()}`);
  },
  dueCount: (params: { deck_id?: number; direction: Direction }) => {
    const qs = new URLSearchParams();
    if (params.deck_id !== undefined) qs.set("deck_id", String(params.deck_id));
    qs.set("direction", params.direction);
    return request<{ due_count: number }>(`/api/review/due-count?${qs.toString()}`);
  },
  pushReviewEvents: (events: ReviewEventInput[]) =>
    request<unknown[]>("/api/review/events/batch", { method: "POST", body: JSON.stringify({ events }) }),

  syncPull: (since?: number) =>
    request<SyncPullResponse>(`/api/sync/pull${since !== undefined ? `?since=${since}` : ""}`),
  checkBlobs: (hashes: string[]) =>
    request<{ missing: string[] }>("/api/sync/blobs/check", { method: "POST", body: JSON.stringify({ hashes }) }),

  uploadMedia: async (file: File | Blob, filename?: string): Promise<{ hash: string; size: number }> => {
    const form = new FormData();
    form.append("file", file, filename);
    const res = await fetch("/api/media/upload", { method: "POST", body: form });
    if (!res.ok) {
      notifyIfUnauthorized(res.status, "/api/media/upload");
      throw new Error(`upload failed: ${res.status}`);
    }
    return res.json();
  },
  mediaUrl: (hash: string) => `/api/media/${hash}`,

  getSettings: () => request<SettingsDTO>("/api/settings"),
  updateSettings: (payload: Partial<{ reminder_time: string; reminder_enabled: boolean; direction: Direction }>) =>
    request<SettingsDTO>("/api/settings", { method: "PUT", body: JSON.stringify(payload) }),

  pushSubscribe: (subscription: PushSubscriptionJSON) =>
    request<unknown>("/api/push/subscribe", {
      method: "POST",
      body: JSON.stringify({ endpoint: subscription.endpoint, keys: subscription.keys }),
    }),
  pushUnsubscribe: (subscription: PushSubscriptionJSON) =>
    request<unknown>("/api/push/unsubscribe", {
      method: "POST",
      body: JSON.stringify({ endpoint: subscription.endpoint, keys: subscription.keys }),
    }),

  rescan: () => request<Record<string, unknown>>("/api/indexer/rescan", { method: "POST" }),

  authStatus: () => request<{ auth_enabled: boolean; authenticated: boolean }>("/api/auth/status"),
  login: (password: string) =>
    request<{ ok: boolean }>("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
};
