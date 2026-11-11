import asyncio

from yoink import db, jobs, notify
from yoink.jobs import JobManager
from yoink.models import DownloadOptions
from yoink.vault import Vault
from yoink.ws import Broadcaster
from yoink.ydl.runner import JobResult


def done(status, **fields):
    job_id = db.create_job("https://example.com/v", "{}")
    db.finish_job(job_id, status, **fields)
    notify.job_done(job_id)


def test_what_is_said(tmp_path, notifications):
    db.init(tmp_path / "test.db")
    done("finished", files=["/tmp/a.mp4"], title="-Tom <b>& Jerry")
    done("finished", files=["/tmp/a.mp4"], error="one item failed")
    done("finished", skipped=1)
    done("error", error="private video")
    done("cancelled")
    assert [argv[-2:] for argv in notifications] == [
        ["Download finished", "-Tom &lt;b&gt;&amp; Jerry"],
        ["Download finished, some items failed", "https://example.com/v"],
        ["Already downloaded", "https://example.com/v"],
        ["Download failed", "https://example.com/v"],
    ]
    assert notifications[0][-3] == "--"  # a title is never read as an option

    db.set_setting("notifications", "0")
    done("error", error="private video")
    assert len(notifications) == 4


def test_a_finished_job_notifies_once(tmp_path, monkeypatch, notifications):
    db.init(tmp_path / "test.db")
    monkeypatch.setattr(
        jobs, "run_download_job",
        lambda *args: JobResult(status="finished", files=["/tmp/a.mp4"], title="A"),
    )
    job_id = db.create_job("https://example.com/v", DownloadOptions().model_dump_json())

    async def scenario():
        manager = JobManager(Broadcaster(), Vault(tmp_path / "vault.json"))
        manager.enqueue(job_id)
        await asyncio.wait(manager._tasks)  # let it run to the end

    asyncio.run(scenario())
    assert [argv[-2:] for argv in notifications] == [["Download finished", "A"]]


def test_setting_round_trip(client):
    assert client.get("/api/settings").json()["notifications"] is True
    assert client.put("/api/settings", json={"notifications": False}).json()["notifications"] is False
