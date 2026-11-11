import asyncio

from yoink import db, jobs
from yoink.jobs import JobManager
from yoink.models import DownloadOptions
from yoink.vault import Vault
from yoink.ws import Broadcaster
from yoink.ydl.runner import JobResult


def test_shutdown_requeues_jobs_but_user_cancel_stays(tmp_path, monkeypatch):
    db.init(tmp_path / "test.db")

    def slow_download(job_id, url, opts, cancel_event, *rest):
        cancel_event.wait(10)
        return JobResult(status="cancelled")

    monkeypatch.setattr(jobs, "run_download_job", slow_download)
    options = DownloadOptions().model_dump_json()
    ids = [db.create_job(f"https://example.com/{n}", options) for n in range(4)]

    async def scenario():
        manager = JobManager(Broadcaster(), Vault(tmp_path / "vault.json"), max_concurrent=2)
        for job_id in ids:
            manager.enqueue(job_id)
        await asyncio.sleep(0.2)  # first two running, last two waiting
        manager.cancel(ids[0])
        manager.cancel(ids[3])
        await manager.shutdown()

    asyncio.run(scenario())
    statuses = [db.get_job(job_id)["status"] for job_id in ids]
    assert statuses == ["cancelled", "queued", "queued", "cancelled"]
