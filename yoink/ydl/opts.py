"""The single mapping from DownloadOptions to a YoutubeDL opts dict.

Strategy: assemble a CLI argv and run it through yt-dlp's own public
parse_options(). That keeps format selection, postprocessor ordering, and value
parsing identical to the real CLI — and makes the raw extra_args escape hatch
literally "appended last, overrides everything". Pure function, unit-tested.
Hooks, archive, and logger are attached by the runner, not here."""

import io
import optparse
import shlex

from yt_dlp import parse_options
from yt_dlp.utils import YoutubeDLError

from .. import config
from ..models import DownloadOptions
from ..vault import ResolvedSecrets


class OptionsError(ValueError):
    """A DownloadOptions value that yt-dlp's parser rejected."""


def build_argv(options: DownloadOptions) -> list[str]:
    argv: list[str] = []
    if options.mode == "audio":
        argv += ["--format", "bestaudio/best", "--extract-audio"]
        if options.audio_format != "best":
            argv += ["--audio-format", options.audio_format]
    else:
        if options.max_height:
            h = options.max_height
            argv += ["--format", f"bestvideo[height<=?{h}]+bestaudio/best[height<=?{h}]"]
        if options.container != "auto":
            argv += ["--merge-output-format", options.container]

    argv += ["--paths", f"home:{options.output_dir or config.default_download_dir()}"]
    if options.output_template:
        argv += ["--output", options.output_template]

    if options.no_playlist:
        argv += ["--no-playlist"]
    if options.playlist_items:
        argv += ["--playlist-items", options.playlist_items]

    if options.write_subtitles:
        argv += ["--write-subs"]
    if options.write_auto_subs:
        argv += ["--write-auto-subs"]
    if options.subtitle_langs:
        argv += ["--sub-langs", options.subtitle_langs]
    if options.embed_subtitles:
        argv += ["--embed-subs"]

    if options.embed_metadata:
        argv += ["--embed-metadata"]
    if options.embed_thumbnail:
        argv += ["--embed-thumbnail"]
    if options.write_thumbnail:
        argv += ["--write-thumbnail"]

    if options.sponsorblock_remove:
        argv += ["--sponsorblock-remove", ",".join(options.sponsorblock_remove)]
    if options.sponsorblock_mark:
        argv += ["--sponsorblock-mark", ",".join(options.sponsorblock_mark)]

    if options.proxy:
        argv += ["--proxy", options.proxy]
    if options.rate_limit:
        argv += ["--limit-rate", options.rate_limit]
    if options.retries is not None:
        argv += ["--retries", str(options.retries)]
    if options.concurrent_fragments:
        argv += ["--concurrent-fragments", str(options.concurrent_fragments)]

    if options.cookies_from_browser:
        argv += ["--cookies-from-browser", options.cookies_from_browser]

    if options.extra_args:
        argv += shlex.split(options.extra_args)
    return argv


def build_ydl_opts(options: DownloadOptions, secrets: ResolvedSecrets | None = None) -> dict:
    try:
        opts = dict(parse_options(build_argv(options)).ydl_opts)
    except (optparse.OptParseError, YoutubeDLError, ValueError) as exc:
        raise OptionsError(str(exc)) from exc
    opts["quiet"] = True
    opts["noprogress"] = True
    if secrets:
        # Applied directly (not via argv): cookies go in as an in-memory stream —
        # cookiefile accepts a text stream, so no secret ever touches disk.
        if secrets.username is not None:
            opts["username"] = secrets.username
            opts["password"] = secrets.password
        if secrets.cookies_content is not None:
            opts["cookiefile"] = io.StringIO(secrets.cookies_content)
    return opts
