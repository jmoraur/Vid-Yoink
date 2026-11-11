# Vid-Yoink

**yoink** is a local web UI for [yt-dlp](https://github.com/yt-dlp/yt-dlp): download
videos or audio from YouTube and ~1800 other sites, keep playlists in sync, and store
site credentials in an encrypted vault. Runs entirely on your machine, bound to
`127.0.0.1` only. There is no login, so never expose it to a network; requests that do
not come from its own pages on this machine (other websites open in your browser, for
example) are refused.

## Features

- **One Downloads screen**: paste a link, press Download, and watch it right there.
  Rows show a thumbnail, format, size, site and how long ago; one click opens the folder.
  Failed downloads say what went wrong in plain words and what to do next.
- **Several links at once**: paste a list, one link per line, and each becomes its own
  download.
- **Desktop notification** when a download finishes or fails (switch it off in Settings).
- **The queue survives closing the app**: unfinished downloads carry on from where they
  stopped the next time you open it.
- **Any yt-dlp site** works — the URL is probed and handed to yt-dlp's extractors.
- **Options UI**: the common cases (audio-only + format, max resolution, output folder,
  playlist item selection, subtitles, embed metadata/thumbnail) are one click; everything
  else lives in collapsible sections (network/proxy/rate limit, SponsorBlock, cookies &
  auth, output template) plus a raw yt-dlp arguments escape hatch that overrides
  everything. Save any configuration as a named **preset** (managed in Settings).
- **Subscriptions**: save a playlist/channel with a preset; "Check now" or an automatic
  interval downloads **only new items**. "Already downloaded" is tracked by video ID in
  yoink's own database (yt-dlp download-archive semantics) — **moving files into your
  media library never causes re-downloads**. "Downloaded items" (under Subscriptions)
  lists what is remembered; remove an entry to allow that video again. An item that
  keeps failing is given up on after three tries instead of being queued forever.
- **Subscription filters**: only items uploaded on or after a date, only titles that
  contain a word, skip Shorts, skip live streams. What a filter leaves out is remembered,
  so later checks do not look at it again; changing the filters starts that memory afresh.
- **Credential vault**: per-site logins and cookies.txt contents, encrypted with a master
  password (scrypt + AES-256-GCM). Secrets are held in memory only while unlocked and are
  passed to yt-dlp as in-memory streams — never written to disk in plaintext.
  `--cookies-from-browser` is also supported as a passthrough. If you want, the vault
  unlocks itself at launch using your desktop keyring (KWallet, GNOME Keyring); this is
  off unless you switch it on.
- Light and dark themes, responsive layout, keyboard-friendly.

## Install (Fedora)

Download the `.noarch.rpm` from the
[latest release](https://github.com/jmoraur/Vid-Yoink/releases) and:

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
cleanly: running downloads stop within seconds (partial files kept), the port is
released, and nothing keeps running in the background. Unfinished downloads stay in the
queue and carry on from where they stopped the next time you open the app. Launching
a second time while a window is open just adds a window to the same instance.

The dedicated window needs Chromium, Chrome or Brave. Without one of them, Yoink opens
as a normal tab in your default browser, and the server stops by itself about ten
seconds after you close the last Yoink tab.

Or run the bare server: `yoink` (serves http://127.0.0.1:8090, Ctrl+C to stop), with
optional `--port` and `--data-dir` flags. It keeps running without any window, so
subscriptions are checked in the background; add `--exit-when-closed` to make it stop
once the last browser tab showing it has closed.

Environment overrides for the launcher: `YOINK_PORT`, `YOINK_DATA_DIR`, `YOINK_BROWSER`
(e.g. `"firefox --new-window"`, opens a normal tab in that browser instead of the app
window), `YOINK_BIN` (server binary override).

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
  ffmpeg post-processing step can't be interrupted — the job shows "Stopping…" until it
  settles. Partial `.part` files are kept and resumed on retry.
- Thumbnails in the list are loaded from the video site each time; yoink stores no
  pictures. Offline, rows show an icon instead.
- Settings warns when yt-dlp is more than 90 days old (sites change, old versions break).
- The playlist preview on the download page shows the first 500 entries. Subscription
  checks read up to 5000, so only truly enormous playlists can have items missed.
- Changing "Parallel downloads" in Settings takes effect after a restart.
- Subscription filters: the playlist listing shows titles, Shorts and live state, so
  those are judged before anything is queued. The upload date is only known once the
  item is looked up, so with a date filter each new item appears briefly under "Now"
  and disappears again if it is too old. Shorts are recognised by their `/shorts/` link,
  which is how a channel lists them; a Short that sits in an ordinary playlist is not
  recognised.
- Vault unlock from the keyring needs the `secret-tool` command (package `libsecret`).
  The keyring holds the vault key, not your master password. Anyone who can use your
  logged-in desktop session can then use the stored logins, which is why it is opt-in.
- In a normal browser tab (no Chromium, Chrome or Brave), the server stops when the tab
  is gone. If the browser unloads the tab to save memory, that counts as closed; open
  Yoink again from the menu and unfinished downloads carry on.
- If you forget the vault master password, the vault contents are unrecoverable (that's
  the point) — delete `~/.local/share/yoink/vault.json` and start over.
- yt-dlp may rotate cookies during a session; yoink deliberately discards those updates.
  Re-import cookies when they expire.
- Upgrading yt-dlp in a dev checkout: `uv lock --upgrade-package yt-dlp && uv sync`, then
  run one download and `uv run pytest` as a smoke test.

## License

[PolyForm Noncommercial 1.0.0](LICENSE) — free to use, modify, and share for any
noncommercial purpose; commercial use is not permitted.
