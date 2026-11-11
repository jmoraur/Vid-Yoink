"""Subscription checking: a plain 60-second asyncio loop plus the check/seed
functions shared by the scheduler and the manual API endpoints."""

import asyncio
import logging

from . import db
from .jobs import JobManager
from .models import DownloadOptions
from .ws import Broadcaster
from .ydl.probe import probe_url

log = logging.getLogger(__name__)

# A subscription item whose download failed this often is left alone, so a dead or
# members-only video is not queued again on every check. Retrying it by hand, or
# removing its failed jobs from the list, gives it another go.
MAX_FAILURES = 3

_in_flight: set[int] = set()
# Strong refs so pending checks can't be garbage-collected mid-flight (the event
# loop only holds weak refs to tasks); same pattern as JobManager._tasks.
_check_tasks: set[asyncio.Task] = set()


async def scheduler_loop(manager: JobManager, broadcaster: Broadcaster) -> None:
    while True:
        try:
            for row in db.due_subscriptions():
                task = asyncio.create_task(
                    check_subscription(row["id"], manager, broadcaster)
                )
                _check_tasks.add(task)
                task.add_done_callback(_check_tasks.discard)
        except Exception:
            log.exception("scheduler tick failed")
        await asyncio.sleep(60)


async def check_subscription(
    sub_id: int, manager: JobManager, broadcaster: Broadcaster
) -> dict:
    """Probe the subscription URL and enqueue a job for every entry that is not in
    the archive, not already waiting or running, and has not failed MAX_FAILURES
    times. Used by both the scheduler and the 'Check now' endpoint."""
    if sub_id in _in_flight:
        return {"subscription_id": sub_id, "new_jobs": 0, "error": "check already running"}
    _in_flight.add(sub_id)
    try:
        row = db.get_subscription(sub_id)
        if row is None:
            return {"subscription_id": sub_id, "new_jobs": 0, "error": "no such subscription"}
        new_jobs: list[int] = []
        failing = 0
        error: str | None = None
        try:
            probe = await asyncio.to_thread(probe_url, row["url"], db.archive_keys())
            options_json = _subscription_options_json(row)
            counts = db.subscription_job_counts(sub_id)
            for entry in probe.entries:
                if entry.already_downloaded or not entry.url:
                    continue
                active, failed = counts.get(entry.url, (0, 0))
                if failed >= MAX_FAILURES:
                    failing += 1
                if active or failed >= MAX_FAILURES:
                    continue
                job_id = db.create_job(entry.url, options_json, subscription_id=sub_id)
                manager.enqueue(job_id)
                new_jobs.append(job_id)
            result = f"{len(new_jobs)} new item(s)" + (f", {failing} failing" if failing else "")
        except Exception as exc:
            error = str(exc)
            result = f"error: {error}"
        db.record_subscription_check(sub_id, result)
        broadcaster.publish({
            "type": "subscription_checked",
            "subscription_id": sub_id,
            "new_jobs": len(new_jobs),
            "failing": failing,
            "error": error,
        })
        return {
            "subscription_id": sub_id,
            "new_jobs": len(new_jobs),
            "failing": failing,
            "error": error,
        }
    finally:
        _in_flight.discard(sub_id)


async def seed_subscription(sub_id: int) -> int:
    """Mark everything currently in the subscription as already downloaded (archive
    rows only, no downloads). For adding a channel you already have locally."""
    row = db.get_subscription(sub_id)
    if row is None:
        raise ValueError("no such subscription")
    probe = await asyncio.to_thread(probe_url, row["url"], set())
    count = 0
    for entry in probe.entries:
        if entry.id and entry.ie_key:
            db.add_archive_entry(
                entry.ie_key.lower(), entry.id, title=entry.title, subscription_id=sub_id
            )
            count += 1
    return count


def _subscription_options_json(row) -> str:
    if row["preset_id"] is not None:
        preset = db.get_preset(row["preset_id"])
        if preset is not None:
            return preset["options_json"]
    return DownloadOptions().model_dump_json()
