from app.sync import (
    RecordRef,
    SyncAction,
    blob_needs_transfer,
    diff_media_hashes,
    records_changed_since,
    resolve_record_sync,
)


def test_resolve_record_sync_local_newer_pushes():
    assert resolve_record_sync(local_last_modified=200.0, remote_last_modified=100.0) == SyncAction.PUSH


def test_resolve_record_sync_remote_newer_pulls():
    assert resolve_record_sync(local_last_modified=100.0, remote_last_modified=200.0) == SyncAction.PULL


def test_resolve_record_sync_identical_skips():
    assert resolve_record_sync(local_last_modified=100.0, remote_last_modified=100.0) == SyncAction.SKIP


def test_resolve_record_sync_missing_locally_pulls():
    assert resolve_record_sync(local_last_modified=None, remote_last_modified=100.0) == SyncAction.PULL


def test_resolve_record_sync_missing_remotely_pushes():
    assert resolve_record_sync(local_last_modified=100.0, remote_last_modified=None) == SyncAction.PUSH


def test_resolve_record_sync_missing_both_sides_skips():
    assert resolve_record_sync(local_last_modified=None, remote_last_modified=None) == SyncAction.SKIP


def test_blob_needs_transfer_identical_hash_no_transfer():
    assert blob_needs_transfer("abc123", "abc123") is False


def test_blob_needs_transfer_different_hash_transfers():
    assert blob_needs_transfer("abc123", "def456") is True


def test_blob_needs_transfer_text_only_change_does_not_force_media_transfer():
    # Card text changed but media hash identical -> zero bytes transferred.
    assert blob_needs_transfer("samehash", "samehash") is False


def test_blob_needs_transfer_missing_remote_transfers():
    assert blob_needs_transfer("abc123", None) is True


def test_diff_media_hashes_partitions_correctly():
    diff = diff_media_hashes(local_hashes=["a", "b", "c"], remote_hashes=["b", "c", "d"])
    assert diff.to_upload == ["a"]
    assert diff.to_download == ["d"]
    assert diff.shared == ["b", "c"]


def test_diff_media_hashes_identical_sets():
    diff = diff_media_hashes(["a", "b"], ["a", "b"])
    assert diff.to_upload == []
    assert diff.to_download == []
    assert diff.shared == ["a", "b"]


def test_records_changed_since_none_returns_all():
    records = [RecordRef(id=1, last_modified=10.0), RecordRef(id=2, last_modified=20.0)]
    assert records_changed_since(records, since=None) == records


def test_records_changed_since_filters_older_records():
    records = [RecordRef(id=1, last_modified=10.0), RecordRef(id=2, last_modified=20.0)]
    changed = records_changed_since(records, since=15.0)
    assert [r.id for r in changed] == [2]


def test_records_changed_since_strictly_greater_than():
    records = [RecordRef(id=1, last_modified=10.0)]
    assert records_changed_since(records, since=10.0) == []
