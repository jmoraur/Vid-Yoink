# yoink

A local web UI for [yt-dlp](https://github.com/yt-dlp/yt-dlp): download videos or audio
from YouTube and ~1800 other sites, keep playlists in sync, and store site credentials in
an encrypted vault. Runs entirely on your machine, bound to `127.0.0.1`.

## Features

- **Downloads** with live progress, cancel/retry, concurrent queue, history.
- **Any yt-dlp site** works — the URL is probed and handed to yt-dlp's extractors.
- **Options UI**: the common cases (audio-only + format, max resolution, output folder,
  playlist item selection, subtitles, embed metadata/thumbnail) are one click; everything
  else lives in collapsible sections (network/proxy/rate limit, SponsorBlock, cookies &
  auth, output template) plus a raw yt-dlp arguments escape hatch that overrides
  everything. Save any configuration as a named **preset**.
- **Subscriptions**: save a playlist/channel with a preset; "Check now" or an automatic
  interval downloads **only new items**. "Already downloaded" is tracked by video ID in
  yoink's own database (yt-dlp download-archive semantics) — **moving files into your
  media library never causes re-downloads**. The Archive page lets you inspect entries or
  delete one to force a re-download.
- **Credential vault**: per-site logins and cookies.txt contents, encrypted with a master
  password (scrypt + AES-256-GCM). Secrets are held in memory only while unlocked and are
  passed to yt-dlp as in-memory streams — never written to disk in plaintext.
  `--cookies-from-browser` is also supported as a passthrough.

## Requirements

- Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js (only to build the frontend)
- **ffmpeg** — required for merging video+audio, audio extraction, and embedding.
  On Fedora you need RPM Fusion's full ffmpeg; the `ffmpeg-free` package lacks encoders.
- Optional: **deno** — yt-dlp uses it as a JavaScript runtime for YouTube; without one,
  some YouTube formats may be missing (yt-dlp prints a warning).

## Run

```sh
npm install --prefix frontend && npm run build --prefix frontend  # once, and after UI changes
uv run yoink                          # serves http://127.0.0.1:8090
uv run yoink --port 9000 --data-dir ~/somewhere  # optional flags
```

Data (database, vault) lives in `~/.local/share/yoink/`. Downloads default to
`~/Downloads` (change in Settings, per-preset, or per-download).

## Development

```sh
uv run uvicorn yoink.app:app --reload --port 8090   # terminal 1: backend
npm run dev --prefix frontend                        # terminal 2: frontend on :5173
uv run pytest                                        # backend tests
uv run ruff check yoink/ tests/                      # lint
```

## Notes & limitations

- Cancelling takes effect between download chunks; metadata extraction and an in-flight
  ffmpeg post-processing step can't be interrupted — the job shows "cancelling…" until it
  settles. Partial `.part` files are kept and resumed on retry.
- Playlist probing and subscription checks read the first 500 entries. For channels
  (newest first) this is fine; on huge regular playlists, items appended past 500 are
  missed.
- If you forget the vault master password, the vault contents are unrecoverable (that's
  the point) — delete `~/.local/share/yoink/vault.json` and start over.
- yt-dlp may rotate cookies during a session; yoink deliberately discards those updates.
  Re-import cookies when they expire.
- Upgrading yt-dlp: `uv lock --upgrade-package yt-dlp && uv sync`, then run one download
  and `uv run pytest` as a smoke test.
