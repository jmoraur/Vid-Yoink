"""URL probing: fetch metadata without downloading, using flat playlist extraction
so large playlists stay fast. Runs in a worker thread (blocking)."""

from yt_dlp import YoutubeDL

from ..models import ProbeEntry, ProbeResult

# How many playlist entries to read. The preview in the UI stays small and fast;
# subscription checks and seeding read (nearly) everything so nothing is missed.
PREVIEW_LIMIT = 500
CHECK_LIMIT = 5000

PROBE_OPTS = {
    "extract_flat": "in_playlist",
    "skip_download": True,
    "quiet": True,
    "noprogress": True,
    "socket_timeout": 20,
}


def probe_url(url: str, archive_keys: set[str], limit: int = PREVIEW_LIMIT) -> ProbeResult:
    with YoutubeDL({**PROBE_OPTS, "playlistend": limit}) as ydl:
        info = ydl.extract_info(url, download=False)
    return _to_result(info or {}, archive_keys)


def _to_result(info: dict, archive_keys: set[str]) -> ProbeResult:
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
        return ProbeResult(
            kind="playlist",
            title=info.get("title"),
            webpage_url=info.get("webpage_url"),
            uploader=info.get("uploader") or info.get("channel"),
            count=info.get("playlist_count") or len(entries),
            entries=[
                ProbeEntry(
                    id=e.get("id"),
                    ie_key=e.get("ie_key"),
                    title=e.get("title"),
                    duration=e.get("duration"),
                    url=e.get("url") or e.get("webpage_url"),
                    already_downloaded=_archive_key(e) in archive_keys,
                )
                for e in entries
            ],
        )
    heights = sorted(
        {
            f["height"]
            for f in info.get("formats") or []
            if f.get("height") and f.get("vcodec") != "none"
        },
        reverse=True,
    )
    return ProbeResult(
        kind="video",
        title=info.get("title"),
        webpage_url=info.get("webpage_url"),
        thumbnail=info.get("thumbnail"),
        duration=info.get("duration"),
        uploader=info.get("uploader") or info.get("channel"),
        heights=heights,
    )


def _archive_key(entry: dict) -> str:
    # Matches yt-dlp's archive-id convention: lowercased extractor key + video id.
    return f"{(entry.get('ie_key') or '').lower()} {entry.get('id')}"
