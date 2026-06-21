import time
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_ts() -> float:
    return time.time()


def new_uuid() -> str:
    return str(uuid.uuid4())


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_modified: Mapped[float] = mapped_column(Float, default=now_ts, onupdate=now_ts)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    cards: Mapped[list["Card"]] = relationship(back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id"), nullable=False, index=True)

    recto_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    recto_media: Mapped[list[str]] = mapped_column(JSON, default=list)
    verso_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    verso_media: Mapped[list[str]] = mapped_column(JSON, default=list)

    source_folder: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    last_modified: Mapped[float] = mapped_column(Float, default=now_ts, onupdate=now_ts)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    deck: Mapped["Deck"] = relationship(back_populates="cards")
    review_events: Mapped[list["ReviewEvent"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False, index=True)
    timestamp: Mapped[float] = mapped_column(Float, default=now_ts, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)

    card: Mapped["Card"] = relationship(back_populates="review_events")


class Blob(Base):
    __tablename__ = "blobs"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=now_ts)


class SourceFile(Base):
    """Tracks the on-disk edit folder so the indexer can skip re-hashing
    files whose mtime+size haven't changed."""

    __tablename__ = "source_files"

    path: Mapped[str] = mapped_column(String(1024), primary_key=True)
    mtime: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, default=now_ts)
