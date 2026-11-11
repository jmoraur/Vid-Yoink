import asyncio

import pytest

from yoink import db, scheduler
from yoink.models import ProbeEntry, ProbeResult, SubscriptionFilters
from yoink.ws import Broadcaster


class FakeManager:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, job_id):
        self.enqueued.append(job_id)


@pytest.fixture
def sub_id(tmp_path, monkeypatch):
    db.init(tmp_path / "test.db")
    entries = [
        ProbeEntry(id=i, ie_key="Youtube", url=f"https://x/{i}", title=f"Episode {i}")
        for i in ("a", "b")
    ]
    limits = []

    def fake_probe(url, keys, limit, flatten):
        assert flatten  # checks want the videos inside a channel's tabs
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
    assert db.get_subscription(sub_id)["last_check_result"] == "nothing new, 2 failing"


def set_filters(sub_id, **filters):
    db.update_subscription(
        sub_id, "sub", "https://x/list", None, True, None,
        SubscriptionFilters(**filters).model_dump_json(),
    )


def test_filtered_items_are_left_out_and_remembered(sub_id):
    manager = FakeManager()
    set_filters(sub_id, title="episode A")
    assert check(sub_id, manager)["new_jobs"] == 1  # "Episode a" passes, any case
    assert db.get_job(manager.enqueued[0])["url"] == "https://x/a"
    assert db.filtered_keys(sub_id) == {("youtube", "b")}
    assert db.get_subscription(sub_id)["filtered_count"] == 1

    # a remembered item stays out even though nothing is waiting or failing for it
    db.finish_job(manager.enqueued[0], "cancelled")
    db.add_filtered(sub_id, "youtube", "a", "Episode a", "uploaded before 2026-11-01")
    assert check(sub_id, manager)["new_jobs"] == 0

    # saving the same filters keeps the memory; new filters start it afresh
    set_filters(sub_id, title="episode A")
    assert len(db.filtered_keys(sub_id)) == 2
    set_filters(sub_id, title="episode")
    assert db.filtered_keys(sub_id) == set()
    assert check(sub_id, manager)["new_jobs"] == 2
