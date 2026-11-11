"""Runs one download job inside a worker thread. Everything here executes off the
event loop: only communicate outward through the emit callback (thread-safe) and
per-thread DB connections."""

import os
import re
import time
from dataclasses import dataclass, field
from threading import Event
from typing import Callable

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from .. import db
from ..filters import item_key, reject_reason
from ..models import SubscriptionFilters

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
        self.hits: set[str] = set()  # ids yt-dlp looked up and found = items it skipped

    def __contains__(self, archive_id: object) -> bool:
        hit = super().__contains__(archive_id)
        if hit:
            self.hits.add(str(archive_id))
        return hit

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


class ErrorCollector:
    """yt-dlp's documented `logger` param. Our options come from yt-dlp's CLI
    parser, which sets ignoreerrors: a failed item is logged and skipped, never
    raised. This is the only place those failures can be seen."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def debug(self, msg: str) -> None:
        pass

    warning = debug

    def error(self, msg: str) -> None:
        # Drop terminal colour codes and yt-dlp's own "ERROR: " prefix, and keep each
        # failure on one line: the lines are joined later and counted in the interface.
        msg = re.sub(r"\x1b\[[0-9;]*m", "", msg).removeprefix("ERROR: ")
        self.errors.append(" ".join(msg.split()))


@dataclass
class JobResult:
    status: str  # finished | error | cancelled
    files: list[str] = field(default_factory=list)
    error: str | None = None  # also set on 'finished' when only some items failed
    title: str | None = None
    skipped: int = 0  # items not downloaded because they are in the archive
    thumbnail: str | None = None  # remote address of the (first) item's picture
    site: str | None = None  # "youtube.com"; yt-dlp's extractor name if it gives no domain
    filesize: int | None = None  # bytes on disk, all files together
    left_out: int = 0  # items the subscription's filters said no to


def run_download_job(
    job_id: int,
    url: str,
    ydl_opts: dict,
    cancel_event: Event,
    emit: Callable[[dict], None],
    subscription_id: int | None = None,
    force_download: bool = False,
    filters: SubscriptionFilters | None = None,
) -> JobResult:
    last_emit = 0.0
    left_out = 0
    files: list[str] = []  # final paths, one per video, via the MoveFiles hook
    title_map: dict[str, str | None] = {}  # archive_id -> title, filled by hooks
    first: dict = {}  # thumbnail and site of the first video seen (a playlist has neither)

    def remember_title(info: dict) -> None:
        if info.get("id") and info.get("extractor_key"):
            title_map[f"{info['extractor_key'].lower()} {info['id']}"] = info.get("title")
            first.setdefault("site", info.get("webpage_url_domain") or info["extractor_key"])
            if info.get("thumbnail"):
                first.setdefault("thumbnail", info["thumbnail"])

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
            "thumbnail": info.get("thumbnail"),
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
    opts["logger"] = log = ErrorCollector()
    opts["download_archive"] = archive = SqliteArchive(
        job_id,
        subscription_id,
        preload=set() if force_download else db.archive_keys(),
        title_map=title_map,
    )

    if filters and subscription_id is not None:
        # yt-dlp's documented `match_filter` param: asked for every item, a returned
        # text means "skip it". Called with full details, so this is where the upload
        # date is finally known. Every "no" is remembered with the subscription.
        remembered = db.filtered_keys(subscription_id)
        own_filter = opts.get("match_filter")  # the user's --match-filters, if any

        def match_filter(info: dict, *, incomplete: bool = False) -> str | None:
            nonlocal left_out
            key = item_key(info)
            if key in remembered:
                reason = "was left out by this subscription's filters before"
            else:
                reason = reject_reason(info, filters)
                if reason and key:
                    db.add_filtered(subscription_id, *key, info.get("title"), reason)
                    remembered.add(key)
            if reason:
                left_out += 1
                return reason
            return own_filter(info, incomplete=incomplete) if own_filter else None

        opts["match_filter"] = match_filter

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        info = info or {}
        files = _dedupe(files + _collect_files(info))
        errors = "\n".join(log.errors) or None
        return JobResult(
            # Nothing downloaded and something failed = failed. Some files plus
            # some failures (a playlist with one dead item) = finished, errors kept.
            status="error" if errors and not files else "finished",
            files=files,
            error=errors,
            title=info.get("title"),
            skipped=len(archive.hits),
            thumbnail=first.get("thumbnail") or info.get("thumbnail"),
            site=first.get("site") or info.get("extractor_key"),
            filesize=sum(os.path.getsize(f) for f in files if os.path.exists(f)) or None,
            left_out=left_out,
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
