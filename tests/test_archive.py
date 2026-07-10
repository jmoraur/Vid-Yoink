import pytest

from yoink import db
from yoink.ydl.runner import SqliteArchive


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    db.init(tmp_path / "test.db")
    yield


def test_add_records_row_and_set_membership():
    with db.session() as conn:
        cur = conn.execute(
            "INSERT INTO subscriptions (name, url, created_at) VALUES (?, ?, ?)",
            ("sub", "https://example.com", db.utcnow()),
        )
        sub_id = cur.lastrowid
    titles = {"youtube abc": "A Title"}
    archive = SqliteArchive(job_id=None, subscription_id=sub_id, preload=set(), title_map=titles)
    archive.add("youtube abc")
    assert "youtube abc" in archive  # what yt-dlp checks to skip
    rows = db.list_archive()
    assert len(rows) == 1
    assert (rows[0]["extractor"], rows[0]["video_id"]) == ("youtube", "abc")
    assert rows[0]["title"] == "A Title"
    assert rows[0]["subscription_id"] == sub_id


def test_preload_makes_existing_ids_skippable():
    db.add_archive_entry("youtube", "known")
    archive = SqliteArchive(None, None, preload=db.archive_keys(), title_map={})
    assert "youtube known" in archive
    assert "youtube new" not in archive


def test_force_download_empty_preload_still_records():
    db.add_archive_entry("youtube", "known")
    archive = SqliteArchive(None, None, preload=set(), title_map={})
    assert "youtube known" not in archive  # nothing skipped
    archive.add("youtube known")  # duplicate insert absorbed
    assert len(db.list_archive()) == 1


def test_delete_entry_enables_redownload():
    db.add_archive_entry("youtube", "abc")
    entry_id = db.list_archive()[0]["id"]
    assert db.delete_archive_entry(entry_id)
    assert db.archive_keys() == set()
