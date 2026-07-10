"""JobManager: concurrency gate, cancellation, and the worker-thread → event-loop
→ WebSocket progress plumbing. Must be constructed on a running event loop."""

import asyncio
import threading

from . import db
from .models import DownloadOptions
from .ws import Broadcaster
from .ydl.opts import build_ydl_opts
from .ydl.runner import JobResult, run_download_job

TERMINAL_STATUSES = {"finished", "error", "cancelled"}


class JobManager:
    def __init__(self, broadcaster: Broadcaster, max_concurrent: int = 2) -> None:
        self._loop = asyncio.get_running_loop()
        self._broadcaster = broadcaster
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cancel_events: dict[int, threading.Event] = {}
        self.live_progress: dict[int, dict] = {}

    def enqueue(self, job_id: int) -> None:
        self._cancel_events[job_id] = threading.Event()
        asyncio.create_task(self._run(job_id))

    def cancel(self, job_id: int) -> bool:
        """Request cancellation. Takes effect at the next progress hook (or when the
        job leaves the queue); the UI shows 'cancelling' until the job settles."""
        event = self._cancel_events.get(job_id)
        if event is None:
            return False
        event.set()
        self._publish_status(job_id, "cancelling")
        return True

    async def _run(self, job_id: int) -> None:
        async with self._semaphore:
            cancel_event = self._cancel_events[job_id]
            try:
                if cancel_event.is_set():  # cancelled while still queued
                    db.finish_job(job_id, "cancelled")
                    self._publish_status(job_id, "cancelled")
                    return
                row = db.get_job(job_id)
                if row is None:
                    return
                options = DownloadOptions.model_validate_json(row["options_json"])
                db.mark_job_running(job_id)
                self._publish_status(job_id, "running")
                try:
                    result = await asyncio.to_thread(
                        run_download_job,
                        job_id,
                        row["url"],
                        build_ydl_opts(options),
                        cancel_event,
                        self._emit_threadsafe,
                        row["subscription_id"],
                        options.force_download,
                    )
                except Exception as exc:  # runner handles expected errors; this is a backstop
                    result = JobResult(status="error", error=f"internal error: {exc!r}")
                db.finish_job(
                    job_id, result.status,
                    files=result.files, error=result.error, title=result.title,
                )
                self._publish_status(job_id, result.status)
            finally:
                self._cancel_events.pop(job_id, None)
                self.live_progress.pop(job_id, None)

    def _emit_threadsafe(self, event: dict) -> None:
        """Only entry point for worker threads."""
        self._loop.call_soon_threadsafe(self._handle_event, event)

    def _handle_event(self, event: dict) -> None:
        if event.get("type") == "job_progress":
            self.live_progress[event["job_id"]] = event
        self._broadcaster.publish(event)

    def _publish_status(self, job_id: int, status: str) -> None:
        self._broadcaster.publish({"type": "job_status", "job_id": job_id, "status": status})
