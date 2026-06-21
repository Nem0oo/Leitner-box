"""Pure sync-resolution logic, kept free of DB/HTTP so it is cheaply testable.

Two independent mechanisms:
- last_modified comparison (last-write-wins) for Decks/Cards metadata.
- hash comparison for media blobs, so identical content never transfers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SyncAction(str, Enum):
    PUSH = "push"   # local is newer / only exists locally -> send to server
    PULL = "pull"   # remote is newer / only exists remotely -> fetch from server
    SKIP = "skip"   # identical, nothing to do


def resolve_record_sync(
    local_last_modified: float | None,
    remote_last_modified: float | None,
) -> SyncAction:
    """Last-write-wins resolution for a single record (Deck or Card) given
    its last_modified on each side. None means "does not exist on that side"."""
    if local_last_modified is None and remote_last_modified is None:
        return SyncAction.SKIP
    if local_last_modified is None:
        return SyncAction.PULL
    if remote_last_modified is None:
        return SyncAction.PUSH
    if local_last_modified > remote_last_modified:
        return SyncAction.PUSH
    if remote_last_modified > local_last_modified:
        return SyncAction.PULL
    return SyncAction.SKIP


def blob_needs_transfer(local_hash: str | None, remote_hash: str | None) -> bool:
    """A media blob only needs to move over the wire if the hashes differ.
    Identical hash -> zero bytes transferred, even if other card fields changed."""
    return local_hash != remote_hash


def diff_media_hashes(local_hashes: list[str], remote_hashes: list[str]) -> "MediaDiff":
    local_set = set(local_hashes)
    remote_set = set(remote_hashes)
    return MediaDiff(
        to_upload=sorted(local_set - remote_set),
        to_download=sorted(remote_set - local_set),
        shared=sorted(local_set & remote_set),
    )


@dataclass(frozen=True)
class MediaDiff:
    to_upload: list[str]
    to_download: list[str]
    shared: list[str]


@dataclass(frozen=True)
class RecordRef:
    id: int
    last_modified: float
    deleted: bool = False


def records_changed_since(records: list[RecordRef], since: float | None) -> list[RecordRef]:
    """Filter records modified after `since` (None means "everything"),
    used to build a pull manifest."""
    if since is None:
        return list(records)
    return [r for r in records if r.last_modified > since]
