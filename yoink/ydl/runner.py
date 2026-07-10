"""Runs one download job inside a worker thread. Everything here executes off the
event loop: only communicate outward through the emit callback (thread-safe) and
per-thread DB connections."""

import os
import time
from dataclasses import dataclass, field
from threading import Event
from typing import Callable

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

PROGRESS_INTERVAL = 0.25  # seconds between job_progress events per job


@dataclass
class JobResult:
    status: str  # finished | error | cancelled
    files: list[str] = field(default_factory=list)
    error: str | None = None
    title: str | None = None


def run_download_job(
    job_id: int,
    url: str,
    ydl_opts: dict,
    cancel_event: Event,
    emit: Callable[[dict], None],
) -> JobResult:
    last_emit = 0.0

    def progress_hook(d: dict) -> None:
        nonlocal last_emit
        if cancel_event.is_set():
            raise DownloadCancelled("cancelled by user")
        now = time.monotonic()
        if d.get("status") == "downloading" and now - last_emit < PROGRESS_INTERVAL:
            return
        last_emit = now
        info = d.get("info_dict") or {}
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes")
        filename = d.get("filename")
        emit({
            "type": "job_progress",
            "job_id": job_id,
            "status": "downloading",
            "progress": downloaded / total if downloaded and total else None,
            "downloaded_bytes": downloaded,
            "total_bytes": total,
            "speed": d.get("speed"),
            "eta": d.get("eta"),
            "filename": os.path.basename(filename) if filename else None,
            "item_title": info.get("title"),
            "playlist_index": info.get("playlist_index"),
            "playlist_count": info.get("n_entries"),
        })

    def postprocessor_hook(d: dict) -> None:
        # No cancel check here: interrupting ffmpeg mid-run would leave broken files.
        if d.get("status") != "started":
            return
        info = d.get("info_dict") or {}
        emit({
            "type": "job_progress",
            "job_id": job_id,
            "status": "postprocessing",
            "progress": None,
            "postprocessor": d.get("postprocessor"),
            "item_title": info.get("title"),
        })

    opts = dict(ydl_opts)
    opts["progress_hooks"] = [progress_hook]
    opts["postprocessor_hooks"] = [postprocessor_hook]

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        return JobResult(
            status="finished",
            files=_collect_files(info),
            title=(info or {}).get("title"),
        )
    except DownloadCancelled:
        return JobResult(status="cancelled")
    except Exception as exc:  # extractor errors, network, ffmpeg...
        return JobResult(status="error", error=str(exc))


def _collect_files(info: dict | None) -> list[str]:
    if not info:
        return []
    entries = list(info.get("entries") or []) if info.get("_type") == "playlist" else [info]
    files = []
    for entry in entries:
        for dl in (entry or {}).get("requested_downloads") or []:
            if dl.get("filepath"):
                files.append(dl["filepath"])
    return files
