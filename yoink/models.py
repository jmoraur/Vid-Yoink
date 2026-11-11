"""Pydantic models shared across the API. DownloadOptions is the contract mirrored
by the frontend's TypeScript types and stored verbatim in presets and job snapshots."""

import json
import sqlite3
from typing import Literal

from pydantic import BaseModel


class DownloadOptions(BaseModel):
    # basic
    mode: Literal["video", "audio"] = "video"
    audio_format: Literal["best", "mp3", "m4a", "opus", "flac", "wav"] = "best"
    max_height: int | None = None  # None = best available
    container: Literal["auto", "mp4", "mkv", "webm"] = "auto"
    output_dir: str | None = None  # None = app default download dir
    # playlist
    no_playlist: bool = False  # URL with list param: download just the one video
    playlist_items: str | None = None  # yt-dlp syntax, e.g. "1-5,8"
    # subtitles
    write_subtitles: bool = False
    write_auto_subs: bool = False
    subtitle_langs: str | None = None  # comma-separated
    embed_subtitles: bool = False
    # metadata / thumbnails
    embed_metadata: bool = False
    embed_thumbnail: bool = False
    write_thumbnail: bool = False
    # sponsorblock
    sponsorblock_remove: list[str] = []
    sponsorblock_mark: list[str] = []
    # network
    proxy: str | None = None
    rate_limit: str | None = None  # human form, e.g. "2M"
    retries: int | None = None
    concurrent_fragments: int | None = None
    # auth (vault labels resolved at run time; cookies_from_browser passed through)
    credential_label: str | None = None  # vault username/password entry
    cookies_label: str | None = None  # vault cookies.txt entry
    cookies_from_browser: str | None = None  # yt-dlp syntax: BROWSER[+KEYRING][:PROFILE]
    # output template (advanced)
    output_template: str | None = None
    # escape hatch: raw yt-dlp CLI arguments, parsed last so they override everything
    extra_args: str | None = None
    # skip the already-downloaded check (new downloads are still recorded)
    force_download: bool = False


class DownloadRequest(BaseModel):
    url: str
    options: DownloadOptions = DownloadOptions()


class JobOut(BaseModel):
    id: int
    url: str
    title: str | None = None
    status: str
    files: list[str] = []
    error: str | None = None
    subscription_id: int | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    thumbnail: str | None = None  # remote address; the app stores no pictures
    site: str | None = None
    filesize: int | None = None
    skipped: int = 0  # items left out because they were downloaded before
    progress: dict | None = None  # live snapshot, only for running jobs

    @classmethod
    def from_row(cls, row: sqlite3.Row, progress: dict | None = None) -> "JobOut":
        return cls(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            status=row["status"],
            files=json.loads(row["files_json"]) if row["files_json"] else [],
            error=row["error"],
            subscription_id=row["subscription_id"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            thumbnail=row["thumbnail"],
            site=row["site"],
            filesize=row["filesize"],
            skipped=row["skipped"] or 0,
            progress=progress,
        )


class ProbeRequest(BaseModel):
    url: str


class ProbeEntry(BaseModel):
    id: str | None = None
    ie_key: str | None = None  # extractor key, for computing archive ids
    title: str | None = None
    duration: float | None = None
    url: str | None = None
    already_downloaded: bool = False


class ProbeResult(BaseModel):
    kind: Literal["video", "playlist"]
    title: str | None = None
    webpage_url: str | None = None
    thumbnail: str | None = None
    duration: float | None = None
    uploader: str | None = None
    heights: list[int] = []  # video: available resolutions for the quality select
    count: int | None = None  # playlist: total entries (may exceed len(entries))
    entries: list[ProbeEntry] = []


class ArchiveEntryOut(BaseModel):
    id: int
    extractor: str
    video_id: str
    title: str | None = None
    subscription_id: int | None = None
    job_id: int | None = None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ArchiveEntryOut":
        return cls(**{k: row[k] for k in cls.model_fields})


class SubscriptionIn(BaseModel):
    name: str
    url: str
    preset_id: int | None = None
    enabled: bool = True
    check_interval_minutes: int | None = None  # None = manual checks only


class SubscriptionOut(SubscriptionIn):
    id: int
    last_check_at: str | None = None
    next_check_at: str | None = None
    last_check_result: str | None = None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SubscriptionOut":
        return cls(
            **{k: row[k] for k in cls.model_fields if k != "enabled"},
            enabled=bool(row["enabled"]),
        )


class PresetIn(BaseModel):
    name: str
    options: DownloadOptions


class PresetOut(BaseModel):
    id: int
    name: str
    options: DownloadOptions
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PresetOut":
        return cls(
            id=row["id"],
            name=row["name"],
            options=DownloadOptions.model_validate_json(row["options_json"]),
            updated_at=row["updated_at"],
        )
