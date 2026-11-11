import asyncio
import threading
from datetime import date

from yoink import db, jobs
from yoink.filters import of, reject_reason
from yoink.jobs import JobManager
from yoink.models import DownloadOptions, SubscriptionFilters
from yoink.vault import Vault
from yoink.ws import Broadcaster
from yoink.ydl.opts import build_ydl_opts
from yoink.ydl.runner import JobResult, run_download_job


def reason(info, **filters):
    return reject_reason(info, SubscriptionFilters(**filters))


def test_rules():
    video = {"title": "Weekly News #12", "upload_date": "20261105",
             "webpage_url": "https://www.youtube.com/watch?v=abc", "live_status": "not_live"}
    assert reason(video, after=date(2026, 11, 5), title="news", skip_shorts=True, skip_live=True) is None
    assert reason(video, after=date(2026, 11, 6)) == "uploaded before 2026-11-06"
    assert reason(video, title="sports") == "title does not contain “sports”"
    assert reason({"url": "https://www.youtube.com/shorts/abc"}, skip_shorts=True) == "is a Short"
    assert reason({"original_url": "https://www.youtube.com/shorts/abc"}, skip_shorts=True)
    for state in ("is_live", "is_upcoming", "was_live", "post_live"):
        assert reason({"live_status": state}, skip_live=True) == "is a live stream"
    assert reason({"is_live": True}, skip_live=True)
    # what is not known is never held against an item (the listing has no dates)
    assert reason({"id": "abc"}, after=date(2026, 11, 6), title="x", skip_shorts=True, skip_live=True) is None
    assert reason({"url": "https://www.youtube.com/shorts/abc", "live_status": "was_live"}) is None


def test_subscription_without_filters_has_none(tmp_path):
    db.init(tmp_path / "test.db")
    plain = db.create_subscription("a", "https://x", None, True, None)
    unset = db.create_subscription("b", "https://x", None, True, None, SubscriptionFilters().model_dump_json())
    chosen = db.create_subscription(
        "c", "https://x", None, True, None, SubscriptionFilters(skip_shorts=True).model_dump_json())
    assert of(db.get_subscription(plain)) is None and of(db.get_subscription(unset)) is None
    assert of(db.get_subscription(chosen)).skip_shorts is True
    assert of(None) is None


def test_download_asks_the_filters_and_remembers(tmp_path, file_url):
    """Real yt-dlp against this machine: the item is judged with its full details."""
    db.init(tmp_path / "test.db")
    sub_id = db.create_subscription("sub", "https://x/list", None, True, None)
    opts = build_ydl_opts(DownloadOptions(output_dir=str(tmp_path / "out"), retries=0))

    def run(**filters):
        job_id = db.create_job(file_url, "{}", subscription_id=sub_id)
        return run_download_job(job_id, file_url, opts, threading.Event(), lambda event: None,
                                sub_id, False, SubscriptionFilters(**filters))

    left_out = run(title="something else")
    assert (left_out.status, left_out.files, left_out.error, left_out.left_out) == ("finished", [], None, 1)
    assert db.filtered_keys(sub_id) == {("generic", "clip")}
    assert db.archive_keys() == set()

    again = run(title="clip")  # would pass now, but it is remembered as left out
    assert (again.files, again.left_out) == ([], 1)

    with db.session() as conn:
        conn.execute("DELETE FROM filtered")
    passed = run(title="CLIP")
    assert (len(passed.files), passed.left_out) == (1, 0)


def test_job_with_everything_left_out_disappears(tmp_path, monkeypatch, notifications):
    db.init(tmp_path / "test.db")
    results = iter([JobResult(status="finished", left_out=1),
                    JobResult(status="finished", left_out=1, skipped=1)])
    monkeypatch.setattr(jobs, "run_download_job", lambda *args: next(results))
    options = DownloadOptions().model_dump_json()
    gone, kept = (db.create_job("https://example.com/v", options) for _ in range(2))

    async def scenario():
        manager = JobManager(Broadcaster(), Vault(tmp_path / "vault.json"), max_concurrent=1)
        manager.enqueue(gone)
        manager.enqueue(kept)
        await asyncio.wait(manager._tasks)

    asyncio.run(scenario())
    assert db.get_job(gone) is None
    assert db.get_job(kept)["status"] == "finished"
    assert [argv[-2] for argv in notifications] == ["Already downloaded"]  # none for the left-out one
