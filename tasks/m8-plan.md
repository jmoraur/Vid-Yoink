# M8 — Fixes and interface rework

Written 2026-11-11 after a fresh-eyes review of the whole project (backend read in
full, app run with sample data, every page viewed in light, dark and phone width).
Nothing in this plan is built yet. Work top to bottom; one commit per numbered step.

**How to resume:** start at the first unchecked box. Each step lists where to change
the code and how to know it is done.

## What the review found

Confirmed by running it:

| # | Finding | Evidence |
|---|---------|----------|
| A | A failed download is saved as "finished" | `run_download_job` on a dead URL and on an unavailable YouTube video both returned `status='finished', files=[]`. Cause: the options come from yt-dlp's command-line parser, which sets `ignoreerrors='only_download'`, so errors are printed to the log and not raised (`yoink/ydl/runner.py:133`). |
| B | Any web page can talk to the server | With a foreign `Host`/`Origin`, the test client got: settings 200, new download with `--exec` 201, bodyless `POST /api/vault/lock` 200, `/ws` accepted. No check exists in `yoink/app.py` or `yoink/ws.py`. |
| C | The menu entry does not open on this machine | `~/.local/state/yoink/launcher.log`: "chromium not found" (2026-10-29). Only `google-chrome` and `firefox` are installed; `scripts/yoink-app:92` looks for `chromium-browser`/`chromium` only. |
| D | The dev checkout's yt-dlp is 4 months old | `uv.lock` pins 2026.7.4; yt-dlp prints its own "older than 90 days" warning. (The RPM uses Fedora's, 2026.10.21.) |

Found by reading the code (not yet reproduced):

- **E — Subscription checks ignore the queue.** `yoink/scheduler.py:52` queues every
  item that is not in the archive, even if a job for it is already waiting or running.
  A failed item is queued again on every check, forever.
- **F — Closing the window drops the queue.** `JobManager.shutdown` cancels every job,
  so they end as "cancelled"; anything left over is marked "interrupted" at next start
  (`yoink/db.py:83`). Each needs a manual retry.
- **G — Subscription checks read only the first 500 items** (`yoink/ydl/probe.py:8`).
- **H — No tests for the risky parts** (runner, job manager, scheduler, API), and CI
  runs only on release tags.

Interface (from screenshots):

- Looks like a generic admin panel; no thumbnails anywhere.
- Paste and progress are on two different pages.
- Six tabs for a small tool.
- Queue rows all look alike; live downloads and old history are mixed; no size, date,
  site or "open folder".
- Machine text shows through: ISO timestamps, raw yt-dlp errors, bare URLs as titles.
- Grey-filled inputs and the pale Download button look disabled.
- "Subtitles" appears twice on the Download page; deletes have no confirmation.

What is good and stays: the colour tokens, both themes, the component styles, the
argv-through-yt-dlp's-parser approach, the archive design, the vault.

---

## Phase 1 — Correctness and safety

Do this first. The new queue (Phase 2) is only useful if statuses are honest.

- [x] **1.1 Report failures as failures**
  - Where: `yoink/ydl/runner.py`.
  - How: give yt-dlp a `logger` object (documented option) whose `error()` collects
    messages. Count archive hits by overriding `__contains__` on `SqliteArchive`.
    After `extract_info`:
    - errors and no files → `error`, message = the collected errors
    - errors and some files → `finished`, with the errors kept in `error`
      (shown as "finished, N items failed")
    - no errors, no files, archive hits > 0 → `finished`, `skipped` count set
  - Also fix the docstring in `yoink/ydl/opts.py:7` (it says the runner attaches a
    logger; today it does not).
  - Done when: new `tests/test_runner.py` passes — `http://127.0.0.1:1/x.mp4` gives
    `error` with a non-empty message (works offline); a URL already in the archive
    gives `finished` with `skipped == 1`.

- [x] **1.2 Only accept requests from this machine's own pages**
  - Where: one small ASGI middleware in `yoink/app.py`, applied to HTTP and WebSocket.
  - Rule: the `Host` name must be `127.0.0.1` or `localhost`; if an `Origin` header is
    present, its host name must be too. Any port (keeps the Vite dev server on :5173
    working). Otherwise answer 403 / close the socket.
  - Done when: new `tests/test_security.py` passes — the four cases in finding B are
    now refused, and the same calls without foreign headers still work.

- [x] **1.3 Subscription checks respect the queue**
  - Where: `yoink/scheduler.py:52`, one new query in `yoink/db.py`.
  - Rule: skip an item if this subscription already has a job for that URL that is
    queued or running, or that has failed 3 times. Show "N failing" in the check
    result so it is visible.
  - Done when: `tests/test_scheduler.py` — two checks in a row (probe faked) create
    jobs once; an item with 3 failed jobs is not queued a 4th time.

- [x] **1.4 The queue survives closing the app**
  - Where: `yoink/jobs.py` (`shutdown`, `_run`), `yoink/db.py:83`, `yoink/app.py`
    lifespan.
  - How: during shutdown, a job that stops because of the shutdown goes back to
    `queued` instead of `cancelled`. At start, queue every `queued`/`running` row
    again in id order instead of marking it as an error. Jobs the user cancelled stay
    cancelled.
  - Done when: start a slow download, close the app, start it again → the job runs
    again and continues from its `.part` file. Add a unit test for the start-up
    re-queue.

- [ ] **1.5 Launcher finds Chrome too**
  - Where: `scripts/yoink-app:92`.
  - How: try `chromium-browser`, `chromium`, `google-chrome`, `google-chrome-stable`,
    `brave-browser` in that order (all support `--app` and `--user-data-dir`). Update
    the error text, README and the `Recommends:` comment in `packaging/yoink.spec`.
  - Done when: launching from the app menu on this machine opens the window, and
    closing it stops the server (port 8090 free, no `yoink` process).

- [ ] **1.6 Subscription checks read the whole list**
  - Where: `yoink/ydl/probe.py` — let the caller pass the limit; keep 500 for the
    interactive preview, use 5000 for checks and seeding.
  - Done when: `tests/test_probe.py` covers the parameter; README limitation updated.

- [ ] **1.7 Fresh yt-dlp, and say when it is old**
  - `uv lock --upgrade-package yt-dlp && uv sync`, run tests and one real download.
  - Settings: yt-dlp's version is a date; show a warning when it is over 90 days old
    (`yoink/api/settings.py` adds `yt_dlp_outdated`).
  - Done when: the warning shows with a faked old version and not with the current one.

- [ ] **1.8 CI on every push**
  - New `.github/workflows/ci.yml`: `ruff check`, `pytest`, `npm ci && npm run build`
    (which runs `tsc`).
  - Done when: the workflow is green on the branch.

---

## Phase 2 — Interface rework

Keep `tokens.css`, the themes and the component look. Change the layout, the content
of the rows and the wording. No new dependencies.

Target main screen:

```
┌──────────────────────────────────────────────────────┐
│ yoink            Downloads · Subscriptions · Settings │
├──────────────────────────────────────────────────────┤
│ [ Paste a URL…                      ] [⚙] [Download] │
│  ▸ preview card: thumbnail, title, quality           │
│                                                      │
│ NOW                                                  │
│ [thumb] Title                 12% · 900 KiB/s · 1m   │
│ [thumb] Title                 queued                 │
│                                                      │
│ EARLIER                       Clear · Retry failed   │
│ [thumb] Title   mp3 · 142 MB · 2 h ago   [folder]    │
│ [thumb] Title   Private video — add a login  [retry] │
└──────────────────────────────────────────────────────┘
```

- [ ] **2.1 Backend support for richer rows**
  - Database migration to version 2 (`yoink/db.py`): add to `jobs` the columns
    `thumbnail TEXT`, `filesize INTEGER`, `site TEXT`, `skipped INTEGER`.
  - `yoink/ydl/runner.py` fills them from yt-dlp's info (`thumbnail`,
    `extractor_key`, size of the final files on disk); `JobOut` and
    `frontend/src/api/types.ts` gain the fields.
  - New endpoints in `yoink/api/downloads.py`:
    - `POST /api/downloads/{id}/open-folder` — runs `xdg-open` on the folder of the
      job's first file. The path comes from the database, never from the request.
    - `POST /api/downloads/retry-failed` and `DELETE /api/downloads?status=…` for the
      "Retry failed" and "Clear" buttons.
  - Done when: a migration test opens a version-1 database and reads the new columns;
    endpoint tests pass; an old database from `~/.local/share/yoink` still loads.

- [ ] **2.2 Three sections instead of six**
  - `frontend/src/App.tsx`: Downloads (`/`), Subscriptions, Settings.
  - Presets: managed inside Settings; picked and saved from the options panel (as now).
  - Archive: a second view inside Subscriptions ("Downloaded items").
  - Old addresses (`/queue`, `/presets`, `/archive`) redirect.
  - Done when: every old feature is still reachable in at most two clicks.

- [ ] **2.3 One Downloads screen**
  - Merge `pages/NewDownload.tsx` and `pages/Queue.tsx`.
  - Paste bar always on top; options (`OptionsForm`, `PresetBar`) in a panel that
    opens from the ⚙ button and shows a one-line summary when closed
    (reuse `summarize()` from `pages/Presets.tsx`).
  - After pressing Download: stay on the page, clear the field, the job appears
    under NOW.
  - Two lists: NOW (queued, running) and EARLIER (everything else) with the existing
    filter chips plus "Clear finished" and "Retry failed".
  - Done when: paste → download → watch → open folder works without leaving the page.

- [ ] **2.4 New row**
  - `components/JobRow.tsx`: small 16:9 thumbnail (icon fallback when missing or it
    fails to load), title, one quiet line of facts (format · size · site · "2 h ago"),
    a small coloured dot plus word instead of the capital-letter badge, actions on the
    right (cancel / retry / open folder / remove).
  - Thumbnails are loaded from the remote address stored with the job; nothing is
    saved to disk.
  - Done when: screenshots of a running, queued, finished, skipped, failed and
    cancelled row all read clearly at 1100 px and 390 px, in both themes.

- [ ] **2.5 Human wording**
  - One helper for relative times (`Intl.RelativeTimeFormat`); use it in jobs,
    subscriptions and the archive. Full date in the tooltip.
  - Subscriptions: "Checks every 2 hours · last checked 10 min ago · 2 new".
  - Errors: a short table of known yt-dlp messages → plain sentence with a next step
    ("This video is private. Add a login under Settings → Vault."). Raw text stays
    available behind "Details".
  - Jobs without a title show the site and the last part of the address, not the full
    URL.

- [ ] **2.6 Form polish**
  - Inputs: white surface with a border (grey fill only when really disabled).
  - Primary button: full colour when usable, clearly greyed only when not.
  - Remove the duplicate "Subtitles" control in `OptionsForm.tsx`.
  - Confirm before deleting a subscription, preset or vault entry (inline
    "Delete? Yes / No", no dialog library).
  - Settings: split the status line into separate rows (yt-dlp version, ffmpeg).

- [ ] **2.7 Check the result**
  - `npm run build` clean, `uv run pytest` green, `uv run ruff check yoink/ tests/`.
  - Screenshots of every screen: 1100×900 and 390×800, light and dark (recipe below).
  - Keyboard only: paste, download, cancel, open options, switch section.
  - Update README screenshots/feature list, bump version, changelog entry in the spec.

---

## Phase 3 — New features (after Phase 2, each optional)

- [ ] **Desktop notification** when a download finishes or fails (`notify-send` from
      the server; `libnotify` is already a recommended package).
- [ ] **Paste several URLs at once** (one per line → one job each).
- [ ] **Subscription filters**: only newer than a date, title contains, skip shorts and
      live streams. Filtered items must be remembered so they are not re-checked every
      time.
- [ ] **Unlock the vault from the desktop keyring** (opt-in), so the password is not
      asked on every launch.
- [ ] **Stop the server when the last window closes**, from inside the server (it
      already knows its connected windows). Makes Firefox and others work like Chromium.

Left out on purpose: cross-platform packaging, user accounts, anything multi-user.

---

## Decisions to confirm (defaults are used unless changed)

1. **Resume on launch (1.4):** default yes, unfinished jobs restart automatically.
2. **Partly failed playlists (1.1):** default "finished" with a warning line, not "error".
3. **Failed subscription items (1.3):** default stop after 3 failures.
4. **Thumbnails (2.4):** default load from the remote address, nothing stored locally.
5. **Three sections (2.2):** default as drawn above.

---

## Screenshot recipe

Runs a throwaway copy on a spare port with its own data folder; the real data in
`~/.local/share/yoink` is not touched.

```sh
D=$(mktemp -d)
# optional: fill "$D/app.db" with sample rows using yoink.db functions
YOINK_DATA_DIR="$D" .venv/bin/yoink --port 8792 &
google-chrome --headless=new --hide-scrollbars --user-data-dir="$D/prof" \
  --window-size=1100,900 --virtual-time-budget=4000 \
  --screenshot="$D/queue.png" http://127.0.0.1:8792/queue
# dark: add --force-dark-mode     phone: --window-size=390,800
kill %1
```

For a row with a live progress bar and no internet: serve a large file with
`python3 -m http.server` and download it with a rate limit (`"rate_limit": "900K"`).
