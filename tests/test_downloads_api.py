import json

import pytest

from yoink import db
from yoink.api import downloads


def make_job(status, files=None):
    job_id = db.create_job(f"https://example.com/{status}", "{}")
    if status != "queued":
        db.finish_job(job_id, status, files=files, error="boom" if status == "error" else None)
    return job_id


@pytest.fixture
def enqueued(client):
    """Stop the app from really running jobs; record what it would have started."""
    started = []
    client.app.state.jobs.enqueue = started.append
    return started


def test_new_job_fields_are_served(client):
    job_id = make_job("finished")
    db.finish_job(job_id, "finished", thumbnail="https://x/t.jpg", site="Youtube",
                  filesize=1234, skipped=2)
    job = client.get(f"/api/downloads/{job_id}").json()
    assert (job["thumbnail"], job["site"], job["filesize"], job["skipped"]) == (
        "https://x/t.jpg", "Youtube", 1234, 2)


def test_open_folder_uses_the_stored_path(client, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(downloads.subprocess, "Popen", lambda argv, **kw: opened.append(argv))
    with_file = make_job("finished", files=[str(tmp_path / "clip.mp4")])
    assert client.post(f"/api/downloads/{with_file}/open-folder").status_code == 200
    assert opened == [["xdg-open", str(tmp_path)]]

    # a request body cannot steer it, and jobs without a usable folder are refused
    gone = make_job("finished", files=["/no/such/folder/clip.mp4"])
    assert client.post(f"/api/downloads/{make_job('error')}/open-folder").status_code == 409
    assert client.post(f"/api/downloads/{gone}/open-folder", json={"path": "/etc"}).status_code == 409
    assert client.post("/api/downloads/9999/open-folder").status_code == 404
    assert len(opened) == 1


def test_retry_reuses_the_row(client, enqueued):
    job_id = make_job("error")
    job = client.post(f"/api/downloads/{job_id}/retry").json()
    assert (job["id"], job["status"], job["error"]) == (job_id, "queued", None)
    assert enqueued == [job_id]
    assert client.post(f"/api/downloads/{job_id}/retry").status_code == 409  # now waiting


def test_retry_failed_requeues_only_failed_jobs(client, enqueued):
    failed = [make_job("error"), make_job("error")]
    others = [make_job("finished"), make_job("cancelled")]
    assert client.post("/api/downloads/retry-failed").json() == {"retried": 2}
    assert sorted(enqueued) == failed
    assert [db.get_job(j)["status"] for j in failed + others] == [
        "queued", "queued", "finished", "cancelled"]
    assert client.post("/api/downloads/retry-failed").json() == {"retried": 0}


def test_clear_removes_done_jobs_only(client, enqueued):
    waiting = make_job("queued")
    finished, failed, cancelled = make_job("finished"), make_job("error"), make_job("cancelled")
    assert client.delete("/api/downloads", params={"status": "queued"}).status_code == 422
    assert client.delete("/api/downloads", params={"status": "finished"}).json() == {"deleted": 1}
    assert db.get_job(finished) is None and db.get_job(failed) is not None
    assert client.delete("/api/downloads").json() == {"deleted": 2}
    assert [j["id"] for j in client.get("/api/downloads").json()] == [waiting]
    assert json.loads(client.get("/api/downloads").text)[0]["status"] == "queued"
    assert db.get_job(cancelled) is None
