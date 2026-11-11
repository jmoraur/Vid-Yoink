"""SQLite storage: schema, migrations (PRAGMA user_version), repository functions.

Connections are cheap; every operation opens its own via session(), so any thread
(event loop, request handlers, yt-dlp worker threads) can call these safely.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

_db_path: Path | None = None

SCHEMA = """
CREATE TABLE jobs (
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  options_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',  -- queued|running|finished|error|cancelled
  files_json TEXT,
  error TEXT,
  subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE archive (
  id INTEGER PRIMARY KEY,
  extractor TEXT NOT NULL,     -- lowercased extractor key (yt-dlp archive-id convention)
  video_id TEXT NOT NULL,
  title TEXT,
  subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
  job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL,
  UNIQUE (extractor, video_id)
);

CREATE TABLE presets (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  options_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE subscriptions (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  preset_id INTEGER REFERENCES presets(id),
  enabled INTEGER NOT NULL DEFAULT 1,
  check_interval_minutes INTEGER,  -- NULL = manual checks only
  last_check_at TEXT,
  next_check_at TEXT,
  last_check_result TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init(db_path: Path) -> None:
    global _db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _db_path = db_path
    with session() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            conn.executescript(SCHEMA)
            conn.execute("PRAGMA user_version = 1")
        # Jobs from a previous process can never resume; surface them as errors.
        conn.execute(
            "UPDATE jobs SET status = 'error', error = 'interrupted by app shutdown',"
            " finished_at = ? WHERE status IN ('queued', 'running')",
            (utcnow(),),
        )


def connect() -> sqlite3.Connection:
    assert _db_path is not None, "db.init() not called"
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        with conn:  # one transaction, committed on success
            yield conn
    finally:
        conn.close()


# --- jobs ---


def create_job(url: str, options_json: str, subscription_id: int | None = None) -> int:
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (url, options_json, subscription_id, created_at)"
            " VALUES (?, ?, ?, ?)",
            (url, options_json, subscription_id, utcnow()),
        )
        return cur.lastrowid


def get_job(job_id: int) -> sqlite3.Row | None:
    with session() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def list_jobs(status: str | None = None, limit: int = 100, offset: int = 0) -> list[sqlite3.Row]:
    query = "SELECT * FROM jobs"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with session() as conn:
        return conn.execute(query, params).fetchall()


def mark_job_running(job_id: int) -> None:
    with session() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?",
            (utcnow(), job_id),
        )


def finish_job(
    job_id: int,
    status: str,
    files: list[str] | None = None,
    error: str | None = None,
    title: str | None = None,
) -> None:
    with session() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, files_json = ?, error = ?,"
            " title = COALESCE(?, title), finished_at = ? WHERE id = ?",
            (status, json.dumps(files) if files else None, error, title, utcnow(), job_id),
        )


# --- archive ---


def archive_keys() -> set[str]:
    """All known '{extractor} {video_id}' keys, yt-dlp's archive-id format."""
    with session() as conn:
        rows = conn.execute("SELECT extractor, video_id FROM archive").fetchall()
    return {f"{r['extractor']} {r['video_id']}" for r in rows}


def add_archive_entry(
    extractor: str,
    video_id: str,
    title: str | None = None,
    job_id: int | None = None,
    subscription_id: int | None = None,
) -> None:
    with session() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO archive"
            " (extractor, video_id, title, job_id, subscription_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (extractor, video_id, title, job_id, subscription_id, utcnow()),
        )


def list_archive(
    subscription_id: int | None = None, q: str | None = None, limit: int = 500
) -> list[sqlite3.Row]:
    query = "SELECT * FROM archive"
    conditions, params = [], []
    if subscription_id is not None:
        conditions.append("subscription_id = ?")
        params.append(subscription_id)
    if q:
        conditions.append("(title LIKE ? OR video_id LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with session() as conn:
        return conn.execute(query, params).fetchall()


def delete_archive_entry(archive_id: int) -> bool:
    with session() as conn:
        return conn.execute("DELETE FROM archive WHERE id = ?", (archive_id,)).rowcount > 0


def delete_job(job_id: int) -> bool:
    with session() as conn:
        return conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,)).rowcount > 0


# --- subscriptions ---


def list_subscriptions() -> list[sqlite3.Row]:
    with session() as conn:
        return conn.execute("SELECT * FROM subscriptions ORDER BY name").fetchall()


def get_subscription(sub_id: int) -> sqlite3.Row | None:
    with session() as conn:
        return conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()


def create_subscription(
    name: str,
    url: str,
    preset_id: int | None,
    enabled: bool,
    check_interval_minutes: int | None,
) -> int:
    next_check = _next_check(check_interval_minutes)
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO subscriptions"
            " (name, url, preset_id, enabled, check_interval_minutes, next_check_at, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, url, preset_id, int(enabled), check_interval_minutes, next_check, utcnow()),
        )
        return cur.lastrowid


def update_subscription(
    sub_id: int,
    name: str,
    url: str,
    preset_id: int | None,
    enabled: bool,
    check_interval_minutes: int | None,
) -> bool:
    with session() as conn:
        cur = conn.execute(
            "UPDATE subscriptions SET name = ?, url = ?, preset_id = ?, enabled = ?,"
            " check_interval_minutes = ?, next_check_at = ? WHERE id = ?",
            (
                name,
                url,
                preset_id,
                int(enabled),
                check_interval_minutes,
                _next_check(check_interval_minutes),
                sub_id,
            ),
        )
        return cur.rowcount > 0


def delete_subscription(sub_id: int) -> bool:
    with session() as conn:
        return conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,)).rowcount > 0


def due_subscriptions() -> list[sqlite3.Row]:
    with session() as conn:
        return conn.execute(
            "SELECT * FROM subscriptions WHERE enabled = 1"
            " AND check_interval_minutes IS NOT NULL AND next_check_at <= ?",
            (utcnow(),),
        ).fetchall()


def subscription_job_counts(sub_id: int) -> dict[str, tuple[int, int]]:
    """url -> (waiting or running jobs, failed jobs) for one subscription."""
    with session() as conn:
        rows = conn.execute(
            "SELECT url, SUM(status IN ('queued', 'running')), SUM(status = 'error')"
            " FROM jobs WHERE subscription_id = ? GROUP BY url",
            (sub_id,),
        ).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def record_subscription_check(sub_id: int, result: str) -> None:
    row = get_subscription(sub_id)
    interval = row["check_interval_minutes"] if row else None
    with session() as conn:
        conn.execute(
            "UPDATE subscriptions SET last_check_at = ?, next_check_at = ?,"
            " last_check_result = ? WHERE id = ?",
            (utcnow(), _next_check(interval), result, sub_id),
        )


def _next_check(interval_minutes: int | None) -> str | None:
    if interval_minutes is None:
        return None
    next_at = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
    return next_at.isoformat(timespec="seconds")


# --- settings ---


def get_setting(key: str) -> str | None:
    if _db_path is None:  # not initialized (unit tests building opts standalone)
        return None
    with session() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    with session() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


# --- presets ---


def list_presets() -> list[sqlite3.Row]:
    with session() as conn:
        return conn.execute("SELECT * FROM presets ORDER BY name").fetchall()


def get_preset(preset_id: int) -> sqlite3.Row | None:
    with session() as conn:
        return conn.execute("SELECT * FROM presets WHERE id = ?", (preset_id,)).fetchone()


def create_preset(name: str, options_json: str) -> int:
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO presets (name, options_json, updated_at) VALUES (?, ?, ?)",
            (name, options_json, utcnow()),
        )
        return cur.lastrowid


def update_preset(preset_id: int, name: str, options_json: str) -> bool:
    with session() as conn:
        cur = conn.execute(
            "UPDATE presets SET name = ?, options_json = ?, updated_at = ? WHERE id = ?",
            (name, options_json, utcnow(), preset_id),
        )
        return cur.rowcount > 0


def delete_preset(preset_id: int) -> bool:
    with session() as conn:
        return conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,)).rowcount > 0
