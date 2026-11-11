import asyncio

import pytest

from yoink import db, scheduler
from yoink.models import ProbeEntry, ProbeResult
from yoink.ws import Broadcaster


class FakeManager:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, job_id):
        self.enqueued.append(job_id)


@pytest.fixture
def sub_id(tmp_path, monkeypatch):
    db.init(tmp_path / "test.db")
    entries = [ProbeEntry(id=i, ie_key="Youtube", url=f"https://x/{i}") for i in ("a", "b")]
    limits = []

    def fake_probe(url, keys, limit):
        limits.append(limit)
        return ProbeResult(kind="playlist", entries=entries)

    monkeypatch.setattr(scheduler, "probe_url", fake_probe)
    yield db.create_subscription("sub", "https://x/list", None, True, None)
    assert set(limits) == {scheduler.CHECK_LIMIT}  # checks read the whole list


def check(sub_id, manager):
    return asyncio.run(scheduler.check_subscription(sub_id, manager, Broadcaster()))


def test_second_check_does_not_queue_waiting_items_again(sub_id):
    manager = FakeManager()
    assert check(sub_id, manager)["new_jobs"] == 2
    assert check(sub_id, manager)["new_jobs"] == 0  # both still queued
    assert len(manager.enqueued) == 2


def test_item_that_keeps_failing_is_given_up(sub_id):
    manager = FakeManager()
    for attempt in range(scheduler.MAX_FAILURES):
        assert check(sub_id, manager)["new_jobs"] == 2, attempt
        for job_id in manager.enqueued:
            db.finish_job(job_id, "error", error="private video")
    result = check(sub_id, manager)
    assert (result["new_jobs"], result["failing"]) == (0, 2)
    assert len(manager.enqueued) == 2 * scheduler.MAX_FAILURES
    assert db.get_subscription(sub_id)["last_check_result"] == "0 new item(s), 2 failing"
