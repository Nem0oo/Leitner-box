import { describe, expect, it } from "vitest";
import { afterAnswer, createQueue, currentCard, remainingCount } from "./session";
import { NEW_STATE, nextState } from "./srs";

const NOW = Date.UTC(2026, 0, 1, 8, 0) / 1000;
const MINUTE = 60;

const a = { id: 1 };
const b = { id: 2 };
const c = { id: 3 };

describe("review session queue", () => {
  it("serves the initial cards in order", () => {
    let q = createQueue([a, b]);
    expect(currentCard(q, NOW)).toBe(a);
    q = afterAnswer(q, a, nextState(NEW_STATE, "easy", NOW), NOW);
    expect(currentCard(q, NOW)).toBe(b);
  });

  it("ends when every card graduated out of the session", () => {
    let q = createQueue([a]);
    q = afterAnswer(q, a, nextState(NEW_STATE, "easy", NOW), NOW);
    expect(currentCard(q, NOW)).toBeNull();
    expect(remainingCount(q)).toBe(0);
  });

  it("re-injects a card still in learning steps", () => {
    let q = createQueue([a, b]);
    q = afterAnswer(q, a, nextState(NEW_STATE, "again", NOW), NOW);
    expect(remainingCount(q)).toBe(2);
    expect(currentCard(q, NOW)).toBe(b);
  });

  it("serves a re-injected card once it is due, before the remaining cards", () => {
    let q = createQueue([a, b, c]);
    q = afterAnswer(q, a, nextState(NEW_STATE, "again", NOW), NOW); // due in 1 min
    const later = NOW + 2 * MINUTE;
    expect(currentCard(q, later)).toBe(a);
  });

  it("learns ahead a re-injected card not yet due when nothing else is left", () => {
    let q = createQueue([a]);
    q = afterAnswer(q, a, nextState(NEW_STATE, "good", NOW), NOW); // due in 10 min
    expect(currentCard(q, NOW)).toBe(a);
  });

  it("re-injects a relearning card after a lapse", () => {
    let state = nextState(NEW_STATE, "easy", NOW - 30 * 86400);
    state = nextState(state, "again", NOW);
    expect(state.state).toBe("relearning");
    let q = createQueue([a]);
    q = afterAnswer(q, a, state, NOW);
    expect(currentCard(q, NOW)).toBe(a);
  });
});
