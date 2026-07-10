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

from .. import db

PROGRESS_INTERVAL = 0.25  # seconds between job_progress events per job


class SqliteArchive(set):
    """Accepted by YoutubeDL's documented `download_archive` param (a set, or a
    filename). yt-dlp checks membership to skip already-downloaded videos and calls
    add() to record new ones — which we mirror into the archive table, so the
    'already downloaded' state lives in the DB and survives files being moved away.

    With force_download the preload is empty: nothing gets skipped, but new
    downloads are still recorded (INSERT OR IGNORE absorbs duplicates)."""

    def __init__(
        self,
        job_id: int,
        subscription_id: int | None,
        preload: set[str],
        title_map: dict[str, str | None],
    ) -> None:
        super().__init__(preload)
        self._job_id = job_id
        self._subscription_id = subscription_id
        self._title_map = title_map

    def add(self, archive_id: str) -> None:
        extractor, _, video_id = str(archive_id).partition(" ")
        db.add_archive_entry(
            extractor,
            video_id,
            title=self._title_map.get(archive_id),
            job_id=self._job_id,
            subscription_id=self._subscription_id,
        )
        super().add(archive_id)


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
    subscription_id: int | None = None,
    force_download: bool = False,
) -> JobResult:
    last_emit = 0.0
    files: list[str] = []  # final paths, one per video, via the MoveFiles hook
    title_map: dict[str, str | None] = {}  # archive_id -> title, filled by hooks

    def remember_title(info: dict) -> None:
        if info.get("id") and info.get("extractor_key"):
            title_map[f"{info['extractor_key'].lower()} {info['id']}"] = info.get("title")

    def progress_hook(d: dict) -> None:
        nonlocal last_emit
        if cancel_event.is_set():
            raise DownloadCancelled("cancelled by user")
        info = d.get("info_dict") or {}
        remember_title(info)
        now = time.monotonic()
        if d.get("status") == "downloading" and now - last_emit < PROGRESS_INTERVAL:
            return
        last_emit = now
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
        info = d.get("info_dict") or {}
        if d.get("status") == "finished" and d.get("postprocessor") == "MoveFiles":
            # MoveFiles runs last for every video (also inside playlists, whose
            # entries do NOT retain requested_downloads) with the final filepath.
            if info.get("filepath"):
                files.append(info["filepath"])
        if d.get("status") == "started":
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
    opts["download_archive"] = SqliteArchive(
        job_id,
        subscription_id,
        preload=set() if force_download else db.archive_keys(),
        title_map=title_map,
    )

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        return JobResult(
            status="finished",
            files=_dedupe(files + _collect_files(info)),
            title=(info or {}).get("title"),
        )
    except DownloadCancelled:
        return JobResult(status="cancelled")
    except Exception as exc:  # extractor errors, network, ffmpeg...
        return JobResult(status="error", error=str(exc))


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


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
