import { describe, expect, it } from "vitest";
import { newCardsIntroducedOn, selectDue } from "./dailyLimit";
import { NEW_STATE, nextState } from "./srs";

const at = (day: number, hour: number) => Date.UTC(2026, 0, day, hour) / 1000;
const NOW = at(10, 12);

describe("newCardsIntroducedOn", () => {
  it("counts the cards whose first rating falls on the review day of now", () => {
    const states = [
      nextState(NEW_STATE, "good", at(10, 9), "UTC"), // today
      nextState(NEW_STATE, "good", at(10, 3), "UTC"), // before 4am: previous review day
      nextState(nextState(NEW_STATE, "good", at(5, 9), "UTC"), "good", at(10, 9), "UTC"), // introduced earlier
      NEW_STATE,
    ];
    expect(newCardsIntroducedOn(states, NOW, "UTC")).toBe(1);
  });

  it("ignores cached states written without first_review_at", () => {
    const legacy = { ...nextState(NEW_STATE, "good", at(10, 9), "UTC"), first_review_at: undefined };
    expect(newCardsIntroducedOn([legacy as never], NOW, "UTC")).toBe(0);
  });
});

describe("selectDue", () => {
  it("keeps every due started card and the first new cards in creation order", () => {
    const learningDue = nextState(NEW_STATE, "good", at(9, 9), "UTC");
    const learningLater = nextState(NEW_STATE, "good", NOW - 60, "UTC");
    const items = [
      { id: 5, state: NEW_STATE },
      { id: 2, state: NEW_STATE },
      { id: 9, state: learningDue },
      { id: 3, state: NEW_STATE },
      { id: 4, state: learningLater },
    ];
    expect(selectDue(items, NOW, 2, "UTC").map((i) => i.id)).toEqual([9, 2, 3]);
    expect(selectDue(items, NOW, 0, "UTC").map((i) => i.id)).toEqual([9]);
    expect(selectDue(items, NOW, -3, "UTC").map((i) => i.id)).toEqual([9]);
  });
});
