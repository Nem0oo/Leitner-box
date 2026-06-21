from app.storage import hash_bytes, source_unchanged, store_bytes, store_file_copy


def test_store_bytes_is_content_addressed(tmp_path):
    blob_dir = tmp_path / "blobs"
    h = store_bytes(blob_dir, b"hello world")
    assert h == hash_bytes(b"hello world")
    assert (blob_dir / h).read_bytes() == b"hello world"


def test_store_bytes_dedupes_identical_content(tmp_path):
    blob_dir = tmp_path / "blobs"
    h1 = store_bytes(blob_dir, b"same content")
    h2 = store_bytes(blob_dir, b"same content")
    assert h1 == h2
    assert len(list(blob_dir.iterdir())) == 1


def test_store_bytes_different_content_different_hash(tmp_path):
    blob_dir = tmp_path / "blobs"
    h1 = store_bytes(blob_dir, b"content A")
    h2 = store_bytes(blob_dir, b"content B")
    assert h1 != h2
    assert len(list(blob_dir.iterdir())) == 2


def test_store_file_copy_preserves_original(tmp_path):
    blob_dir = tmp_path / "blobs"
    source = tmp_path / "source.txt"
    source.write_text("preserved")
    h = store_file_copy(blob_dir, source)
    assert source.exists()
    assert (blob_dir / h).read_text() == "preserved"


def test_source_unchanged_true_when_mtime_and_size_match():
    assert source_unchanged(stat_mtime=100.0, stat_size=50, recorded_mtime=100.0, recorded_size=50) is True


def test_source_unchanged_false_when_mtime_differs():
    assert source_unchanged(stat_mtime=200.0, stat_size=50, recorded_mtime=100.0, recorded_size=50) is False


def test_source_unchanged_false_when_size_differs():
    assert source_unchanged(stat_mtime=100.0, stat_size=99, recorded_mtime=100.0, recorded_size=50) is False
