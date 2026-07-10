# Distribution plan — publishing yoink for general, cross-platform use

**Status (2026-07-10): deferred.** The app stays local (Linux, run from this checkout,
desktop launcher). This document preserves the analysis and options for the day we
revisit. Nothing here is scheduled work.

---

## 1. Current state and what ties it to this machine

The stack itself (FastAPI, yt-dlp, SQLite, `cryptography`, Vite/React frontend) is
cross-platform. What is Linux- and checkout-specific is everything around it:

| What | Where | Assumption baked in |
|---|---|---|
| Data paths | `yoink/config.py:11`, `yoink/main.py` | XDG layout (`~/.local/share`, `~/.local/state`) |
| Frontend serving | `yoink/app.py:15` | `frontend/dist/` sits next to the package in the repo; `dist/` is gitignored, so a fresh clone needs Node |
| Desktop launcher | `scripts/yoink-app`, `packaging/yoink.desktop` | bash, SIGTERM lifecycle, `notify-send`/`kdialog`, Chromium app mode, `.desktop` install |
| Tool dependencies | README prerequisites | ffmpeg (full build) and optionally deno are installed by the user, per OS |
| Runtime | `uv.lock`, `.venv` | app runs from a git checkout with a venv beside it |

Each of these is a *symptom* of an upstream design decision that was right for
"app on my machine" and wrong for "anyone, any OS":

| Downstream symptom | Upstream cause |
|---|---|
| Need to bundle frontend, add platformdirs, fight PyInstaller | The app is a **repo + environment**, not an **artifact** |
| Per-OS ffmpeg/deno install instructions | Dependencies are a **prerequisite of the environment**, not managed by the app |
| The bash launcher (PID watching, SIGTERM, browser detection) | UI and server are **separate processes glued together from outside** |
| Release needed every time yt-dlp breaks | yt-dlp is a **pinned in-process library**, so upstream fixes require our releases |

Two paths follow: fix the symptoms (Path A) or re-make the decisions (Path B).

---

## 2. Path A — keep the architecture, fix distribution downstream

### 2.1 Code changes required regardless of channel

1. **Paths** — replace hardcoded XDG paths with `platformdirs` (macOS:
   `~/Library/Application Support`, Windows: `%APPDATA%`). ~5-line change.
2. **Frontend as package data** — build `dist/` in CI, ship it *inside* the wheel,
   resolve via `importlib.resources` instead of the repo-relative path in
   `app.py:15`. End users then never need Node; it becomes contributor-only.
3. **ffmpeg discovery** — detect at startup, show per-OS install hints in the UI.
   Alternative: depend on `static-ffmpeg`-style packages that ship binaries via
   PyPI (zero friction, but heavier and another supply chain to trust). yt-dlp's
   audience is used to installing ffmpeg, so hints are defensible.
4. **Launcher** — either fold it into Python (`yoink --app` spawns the browser
   window and exits when it closes; Chromium's `--app=URL` works on Chrome and
   Edge on all three OSes, and Edge ships with Windows), or accept "opens a tab in
   the default browser" as the portable baseline (what most yt-dlp web UIs do).
   Note: Windows has no SIGTERM semantics — the current kill-based lifecycle does
   not port as-is.
5. **Repo hygiene** — LICENSE file (nothing is legally usable without one), CI
   (pytest, ruff, frontend build), release workflow, versioning.
6. **Network security** — the app binds 127.0.0.1 with **no authentication**.
   Self-hosters will immediately try `--host 0.0.0.0` on a NAS, exposing the vault
   unlock endpoint to the LAN. Either refuse non-localhost binds or require a
   token for them.
7. **Name check** — verify "yoink" is free on PyPI before anything else; it
   dictates the install command people type.

### 2.2 Distribution channels, in increasing effort

| Channel | Effort | Reach | Notes |
|---|---|---|---|
| **Source install** (clone + uv + npm) | near-free | developers only | Works today modulo §2.1; prerequisites filter out most people |
| **PyPI → `uvx yoink` / `pipx install yoink`** | low | anyone with one command | **Best effort-to-reach ratio.** Needs §2.1 items 1–2; uv itself is a one-line install everywhere |
| **Docker image** (ghcr.io + compose file) | low-medium | self-hosters, NAS | Bake ffmpeg + deno into the image; volume-mount downloads and data. How MeTube-class apps are consumed. Caveats: `--cookies-from-browser` can't reach the host browser from a container; no desktop feel |
| **Native installers** (.dmg/.msi/AppImage via PyInstaller) | high, ongoing | non-technical users | Code signing + notarization on macOS, SmartScreen on Windows, CI release matrix. Skip unless the project finds a non-technical audience |

**Path A recommendation:** PyPI as primary channel, Docker as secondary, keep the
Linux desktop launcher as a documented optional extra. Modest code changes.

### 2.3 What Path A does not fix

- **Release treadmill**: yt-dlp stays a pinned library; every upstream breakage
  (frequent — YouTube changes constantly) requires us to cut a release.
- **Launcher fragility is ported, not solved**: the browser/server split still
  needs external glue on every OS.
- **The tool/appliance tension** (§3.1) remains unresolved.

---

## 3. Path B — upstream re-architecture (design for distribution)

Four decisions to re-make, in dependency order.

### 3.1 Decision 1 — product model: tool or appliance

The app currently straddles two models:

- **Tool**: open it, download things, close it. The desktop launcher embodies this.
- **Appliance**: runs continuously; subscriptions check playlists at 3am. The
  scheduler embodies this — and close-on-window-exit *defeats* it.

This is a product call, not a technical one, and it gates everything below. One
model must drive the architecture; the other can survive as a mode.
Observation: **subscriptions are yoink's most differentiated feature** versus
other yt-dlp UIs, and they only fully work in the appliance model.

### 3.2 Decision 2 — invert the dependency relationship: the app manages its tools

Instead of "Requirements: Python ≥3.12, uv, Node, ffmpeg, deno", the app on first
run downloads the official **yt-dlp single-file binary** and a **static ffmpeg
build** for the current OS into its data directory, verifies them, and updates
them at runtime — independently of app releases. (This is how Stacher-class
cross-platform yt-dlp GUIs work.)

Wins:
- Install prerequisites drop to zero.
- **Off the release treadmill**: when yt-dlp breaks, users click "update yt-dlp"
  in Settings instead of waiting for our version bump.

Honest costs — yt-dlp becomes a subprocess, and we lose the tight in-process
integrations we currently rely on:

| Current (library, in-process) | After (binary, subprocess) |
|---|---|
| Vault passes cookies as **in-memory streams** — never on disk in plaintext (M5 guarantee) | Cookies must reach the subprocess via a temp file or stdin — a real **security-design change** that weakens or complicates the current vault guarantee |
| Python **progress hooks** drive live WS updates | Parse `--progress` JSON from stdout |
| Cancellation between chunks; ffmpeg post-processing uninterruptible ("cancelling…" limbo) | Kill the subprocess — actually **cleaner** than today |
| Full access to extractor internals (probe, archive set-subclass in M3) | Limited to CLI surface: `--flat-playlist -J` for probing, `--download-archive` file semantics or pre-filtering by ID ourselves |

This table is the central tradeoff of the whole plan.

### 3.3 Decision 3 — unify the process model

The launcher exists because no process owns the browser/server pairing. Fixes:

- **Tool model**: the app owns its window — a webview (Tauri; or pywebview if
  staying Python) where closing the window *is* ending the process. The entire
  launcher problem category disappears rather than getting ported per-OS.
- **Appliance model**: no window at all; the browser is just a client. Also
  simpler than today.

### 3.4 Decision 4 — the app is an artifact, not a checkout

Frontend embedded in the binary as an asset; config injected, not assumed; one
file per OS built by CI. This is where the language question lives:

- **Python fights this model** — bundling an interpreter (PyInstaller/PyOxidizer)
  is always somewhat fragile.
- Once yt-dlp is a subprocess (§3.2), **Python loses its main reason for being
  the backend language**. What remains is queue management, SQLite, a scheduler,
  and a vault — any language does that fine.
- **Go** and **Tauri/Rust** are built for single-artifact distribution.

### 3.5 Coherent end-states

**B-1 — Tool: Tauri desktop app**
- Existing frontend runs inside the Tauri webview (talks HTTP or Tauri IPC via a
  thin adapter); small Rust core; yt-dlp + ffmpeg as managed sidecar binaries.
- Produces a signable ~10 MB installer per OS.
- Subscriptions degrade to "check while the app is open" (or need a separate
  headless mode — re-introducing the two-process problem).

**B-2 — Appliance: single Go binary**
- Frontend embedded (`go:embed`); same managed-binaries approach; runs equally
  well double-clicked on a laptop ("opens a browser window on launch" as the
  desktop concession) or as a Docker container on a NAS.
- Subscriptions work as designed, 24/7.
- Requires real authentication — it *will* get exposed to LANs.

### 3.6 What survives a rewrite, what does not

Transfers almost untouched:
- **Frontend** (~1,900 lines TypeScript) — talks HTTP/JSON, doesn't care what
  serves it.
- **Domain design** (thinking, not code): archive-by-video-ID semantics so moving
  files never re-downloads; vault crypto format (scrypt + AES-256-GCM);
  preset/subscription modeling; queue terminal-state guarantees; the
  close-cleanly lifecycle contract.

Gets rewritten:
- **Backend** (~1,800 lines Python): FastAPI routes, job manager, scheduler,
  vault I/O, yt-dlp integration. Real but bounded; the least differentiated part
  of the app.

---

## 4. Costs of going public that no architecture fixes

- **yt-dlp churn**: even with runtime tool updates (§3.2), extractor behavior
  changes can break our probe/options assumptions. A public app implicitly
  promises upkeep.
- **Issue triage** from users on platforms we don't run.
- **Signing/notarization fees and process** if we ever ship native installers.
- **Support surface of the vault**: "I forgot my master password" is by design
  unrecoverable; expect the issue reports anyway.

---

## 5. Recommendation snapshot (as of 2026-07-10)

1. **Stay local for now** — decided.
2. If we want public reach cheaply later: **Path A, PyPI (`uvx yoink`) +
   Docker**. Modest changes (§2.1), keeps the Python codebase, accepts the
   release treadmill.
3. If we commit to a real cross-platform product: **Path B**, and the gating
   question is §3.1 (tool vs appliance). Lean **B-2 (Go appliance)** because
   subscriptions are the differentiator and only fully work there; frontend and
   domain design carry over.
4. First concrete action on any path: **check the PyPI name**, add a LICENSE.

## 6. Revisit triggers

Re-open this document when any of these happens:
- We actually want someone else to run yoink (friend, other machine, NAS).
- yt-dlp version bumps become a recurring maintenance annoyance (strengthens the
  §3.2 managed-binary argument).
- The desktop launcher needs porting anyway (e.g. new machine/OS) — at that point
  compare the porting cost against §3.3 directly.
