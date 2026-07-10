"""Paths and defaults. Data dir is overridable via YOINK_DATA_DIR (set by main.py --data-dir)."""

import os
from pathlib import Path


def data_dir() -> Path:
    env = os.environ.get("YOINK_DATA_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "yoink"


def db_path() -> Path:
    return data_dir() / "app.db"


def vault_path() -> Path:
    return data_dir() / "vault.json"


def default_download_dir() -> Path:
    return Path.home() / "Downloads"
