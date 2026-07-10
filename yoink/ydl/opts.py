"""The single mapping from DownloadOptions to a YoutubeDL opts dict.

Pure function — no I/O, no globals mutated — so it stays trivially unit-testable.
Hooks, archive, and logger are attached by the runner, not here."""

from .. import config
from ..models import DownloadOptions


def build_ydl_opts(options: DownloadOptions) -> dict:
    opts: dict = {
        "paths": {"home": options.output_dir or str(config.default_download_dir())},
        "quiet": True,
        "noprogress": True,
    }
    return opts
