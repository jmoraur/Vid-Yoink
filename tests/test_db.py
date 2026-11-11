import sqlite3

import pytest

from yoink import db
from yoink.models import DownloadOptions


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    db.init(tmp_path / "test.db")
    yield


def test_job_lifecycle():
    job_id = db.create_job("https://example.com/v", DownloadOptions().model_dump_json())
    row = db.get_job(job_id)
    assert row["status"] == "queued"
    db.mark_job_running(job_id)
    db.finish_job(job_id, "finished", files=["/tmp/a.mp4"], title="A")
    row = db.get_job(job_id)
    assert row["status"] == "finished"
    assert row["title"] == "A"
    assert "a.mp4" in row["files_json"]


def test_unfinished_jobs_are_queued_again_on_init(tmp_path):
    waiting = db.create_job("https://example.com/a", "{}")
    killed = db.create_job("https://example.com/b", "{}")
    db.mark_job_running(killed)
    done = db.create_job("https://example.com/c", "{}")
    db.finish_job(done, "cancelled")
    db.init(tmp_path / "test.db")  # simulate app restart on same file
    assert db.queued_job_ids() == [waiting, killed]
    assert db.get_job(done)["status"] == "cancelled"


def test_preset_crud():
    options = DownloadOptions(mode="audio", audio_format="mp3")
    preset_id = db.create_preset("music", options.model_dump_json())
    rows = db.list_presets()
    assert len(rows) == 1 and rows[0]["name"] == "music"
    assert db.update_preset(preset_id, "music-v2", options.model_dump_json())
    assert db.get_preset(preset_id)["name"] == "music-v2"
    assert db.delete_preset(preset_id)
    assert db.list_presets() == []


def test_archive_keys():
    with db.session() as conn:
        conn.execute(
            "INSERT INTO archive (extractor, video_id, created_at) VALUES (?, ?, ?)",
            ("youtube", "abc123", db.utcnow()),
        )
    assert db.archive_keys() == {"youtube abc123"}


def test_version_1_database_is_upgraded(tmp_path):
    """A database written by yoink 0.1.0 gains the job columns and keeps its rows."""
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(db.SCHEMA)
    old.execute("PRAGMA user_version = 1")
    old.execute(
        "INSERT INTO jobs (url, options_json, status, created_at)"
        " VALUES ('https://example.com/v', '{}', 'finished', '2026-07-10T10:00:00+00:00')"
    )
    old.commit()
    old.close()

    db.init(path)
    db.init(path)  # a second start must not try to add the columns again
    row = db.list_jobs()[0]
    assert (row["url"], row["status"]) == ("https://example.com/v", "finished")
    assert [row[c] for c in ("thumbnail", "filesize", "site", "skipped")] == [None] * 4
    db.finish_job(row["id"], "finished", thumbnail="https://x/t.jpg", site="Youtube",
                  filesize=1234, skipped=2)
    row = db.get_job(row["id"])
    assert (row["thumbnail"], row["site"], row["filesize"], row["skipped"]) == (
        "https://x/t.jpg", "Youtube", 1234, 2)
