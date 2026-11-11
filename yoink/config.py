"""Paths and defaults. Data dir is overridable via YOINK_DATA_DIR (set by main.py --data-dir)."""

import os
from pathlib import Path


def data_dir() -> Path:
    env = os.environ.get("YOINK_DATA_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "yoink"


def exit_when_closed() -> bool:
    """Set by main.py --exit-when-closed: stop the server once its last window is gone."""
    return os.environ.get("YOINK_EXIT_WHEN_CLOSED") == "1"


def db_path() -> Path:
    return data_dir() / "app.db"


def vault_path() -> Path:
    return data_dir() / "vault.json"


def default_download_dir() -> Path:
    return Path.home() / "Downloads"
