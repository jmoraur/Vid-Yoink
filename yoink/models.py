"""Pydantic models shared across the API. DownloadOptions is the contract mirrored
by the frontend's TypeScript types and stored verbatim in presets and job snapshots."""

import json
import sqlite3

from pydantic import BaseModel


class DownloadOptions(BaseModel):
    output_dir: str | None = None  # None = app default download dir


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
            progress=progress,
        )
