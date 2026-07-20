# Vid-Yoink

**yoink** is a local web UI for [yt-dlp](https://github.com/yt-dlp/yt-dlp): download
videos or audio from YouTube and ~1800 other sites, keep playlists in sync, and store
site credentials in an encrypted vault. Runs entirely on your machine, bound to
`127.0.0.1` only — there is no authentication, so never expose it to a network.

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
- Light and dark themes, responsive layout, keyboard-friendly.

## Install (Fedora)

Download the `.noarch.rpm` from the
[latest release](https://github.com/jmorarur/Vid-Yoink/releases) and:

```sh
sudo dnf install ./yoink-*.noarch.rpm
```

Built and tested on Fedora 44; needs Python ≥ 3.12.

**ffmpeg**: merging video+audio, audio extraction and embedding need the full ffmpeg.
Fedora's default `ffmpeg-free` lacks the required encoders — enable
[RPM Fusion](https://rpmfusion.org/Configuration) and `sudo dnf install ffmpeg`.

**Optional**: `deno` — yt-dlp uses it as a JavaScript runtime for YouTube; without one,
some YouTube formats may be missing (yt-dlp prints a warning).

## Usage

Launch **Yoink** from the application menu (or run `yoink-app`). This starts the server,
opens a dedicated app window, and when you close that window it shuts the server down
cleanly: running downloads are cancelled within seconds (partial files kept, resumable
via Retry), the port is released, and nothing keeps running in the background. Launching
a second time while a window is open just adds a window to the same instance.

Or run the bare server: `yoink` (serves http://127.0.0.1:8090, Ctrl+C to stop), with
optional `--port` and `--data-dir` flags.

Environment overrides for the launcher: `YOINK_PORT`, `YOINK_DATA_DIR`, `YOINK_BROWSER`
(e.g. `"firefox --new-window"` — but auto-shutdown-on-close only works with the default
Chromium app mode), `YOINK_BIN` (server binary override).

Data (database, vault) lives in `~/.local/share/yoink/`. Downloads default to
`~/Downloads` (change in Settings, per-preset, or per-download). Logs:
`~/.local/state/yoink/`.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Node.js.

```sh
uv sync                                              # backend venv
npm ci --prefix frontend                             # frontend deps
uv run uvicorn yoink.app:app --reload --port 8090    # terminal 1: backend
npm run dev --prefix frontend                        # terminal 2: frontend on :5173
uv run pytest                                        # backend tests
uv run ruff check yoink/ tests/                      # lint
npm run build --prefix frontend                      # production build -> yoink/static/
scripts/install_desktop.sh                           # per-user desktop entry for this checkout
```

## Building the RPM

```sh
sudo dnf builddep packaging/yoink.spec
bash packaging/make-source-tarball.sh    # builds frontend, writes ~/rpmbuild/SOURCES/
cp packaging/yoink.spec ~/rpmbuild/SPECS/
rpmbuild -ba ~/rpmbuild/SPECS/yoink.spec
```

Release checklist: bump `version` in `pyproject.toml` **and** `Version:` in
`packaging/yoink.spec` (the tarball script fails on mismatch), add a `%changelog` entry,
tag `v<version>` and push — CI builds the RPM and attaches it to the GitHub release.

## Notes & limitations

- Cancelling takes effect between download chunks; metadata extraction and an in-flight
  ffmpeg post-processing step can't be interrupted — the job shows "cancelling…" until it
  settles. Partial `.part` files are kept and resumed on retry.
- Playlist probing and subscription checks read the first 500 entries. For channels
  (newest first) this is fine; on huge regular playlists, items appended past 500 are
  missed.
- Changing "Parallel downloads" in Settings takes effect after a restart.
- If you forget the vault master password, the vault contents are unrecoverable (that's
  the point) — delete `~/.local/share/yoink/vault.json` and start over.
- yt-dlp may rotate cookies during a session; yoink deliberately discards those updates.
  Re-import cookies when they expire.
- Upgrading yt-dlp in a dev checkout: `uv lock --upgrade-package yt-dlp && uv sync`, then
  run one download and `uv run pytest` as a smoke test.

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free to use, modify, and share for any
noncommercial purpose; commercial use is not permitted.
