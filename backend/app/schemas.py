from pydantic import BaseModel, ConfigDict

from app.leitner import DIRECTIONS, RESULT_FAIL, RESULT_SUCCESS


# ---- Decks ----

class DeckCreate(BaseModel):
    name: str
    description: str | None = None


class DeckUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DeckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    last_modified: float
    card_count: int = 0
    due_count: int = 0
    deleted: bool = False


# ---- Cards ----

class CardCreate(BaseModel):
    deck_id: int
    recto_text: str | None = None
    verso_text: str | None = None


class CardUpdate(BaseModel):
    recto_text: str | None = None
    verso_text: str | None = None
    recto_media: list[str] | None = None
    verso_media: list[str] | None = None
    deck_id: int | None = None


class CardDirectionStateOut(BaseModel):
    box: int
    last_review_at: float | None
    due_at: float | None
    is_due: bool


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    recto_text: str | None
    recto_media: list[str]
    verso_text: str | None
    verso_media: list[str]
    last_modified: float
    deleted: bool
    recto_to_verso: CardDirectionStateOut
    verso_to_recto: CardDirectionStateOut


# ---- Review events ----

class ReviewEventCreate(BaseModel):
    id: str | None = None
    card_id: int
    direction: str
    result: str
    timestamp: float | None = None


class ReviewEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    card_id: int
    timestamp: float
    direction: str
    result: str


class ReviewEventBatch(BaseModel):
    events: list[ReviewEventCreate]


# ---- Review session ----

class DueCardOut(BaseModel):
    id: int
    deck_id: int
    deck_name: str
    recto_text: str | None
    recto_media: list[str]
    verso_text: str | None
    verso_media: list[str]
    direction: str
    box: int


# ---- Sync ----

class SyncPullResponse(BaseModel):
    server_time: float
    decks: list[DeckOut]
    cards: list[CardOut]


# ---- Settings ----

class SettingsOut(BaseModel):
    reminder_time: str | None
    reminder_enabled: bool
    direction: str
    vapid_public_key: str


class SettingsUpdate(BaseModel):
    reminder_time: str | None = None
    reminder_enabled: bool | None = None
    direction: str | None = None


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: dict[str, str]


def validate_direction(direction: str) -> None:
    if direction not in DIRECTIONS:
        raise ValueError(f"Invalid direction: {direction}")


def validate_result(result: str) -> None:
    if result not in (RESULT_SUCCESS, RESULT_FAIL):
        raise ValueError(f"Invalid result: {result}")
