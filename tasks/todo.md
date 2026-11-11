# yoink — local yt-dlp web downloader

## Milestones

- [x] **M1 — End-to-end skeleton** *(done 2026-07-10: verified generic mp4 + real YouTube
      download, 2 concurrent jobs, WS progress events, cancel with 'cancelling' state,
      error surfacing, history persists across restart, 127.0.0.1-only binding)*
- [x] **M2 — Probe, options, presets** *(done 2026-07-10: video probe with real heights,
      flat playlist probe with already_downloaded flags, audio-only → .mp3 verified,
      playlist_items "1,3" downloaded exactly items 1+3, invalid extra_args → 422,
      presets CRUD + 409 on duplicate name, 20 unit tests green. Fixed: playlist entries
      drop requested_downloads → final paths now collected via MoveFiles pp-hook.)*
- [x] **M3 — Queue management + archive** *(done 2026-07-10: DB archive wired via
      SqliteArchive set-subclass; verified file moved to library → re-submit skipped with
      zero downloads; force_download bypasses check; delete archive row → re-downloads;
      retry/delete endpoints with 409 guard; archive browser page with search.)*
- [x] **M4 — Subscriptions + scheduler** *(done 2026-07-10: seeded 13 items without
      downloading; check-now after seed → 0 new; deleted 2 archive rows → check enqueued
      exactly 2 jobs with the sub's audio preset, tagged subscription_id; re-check → 0;
      1-min interval fired automatically and rescheduled.)*
- [x] **M5 — Vault** *(done 2026-07-10: scrypt+AES-GCM vault, 8 unit tests; live-verified
      init/lock/unlock, wrong password → 403, download using vault cookies via StringIO,
      restart → locked → job fails fast with clear message → unlock + retry finishes,
      grep of data dir shows no plaintext secrets, vault.json mode 600.)*
- [x] **M6 — Production polish** *(done 2026-07-10: SPA fallback serves client routes but
      404s unknown /api paths; settings API+page (default folder, parallel downloads,
      ffmpeg + yt-dlp status); default_output_dir setting consulted by opts builder;
      README; headless-Chromium screenshots of Download/Queue/Settings verified clean.)*

## Post-v1 additions

- [x] **Desktop launch like 001-Rsync-App** *(2026-07-10: scripts/yoink-app launcher +
      packaging/yoink.desktop + icon + install_desktop.sh, installed. Launcher owns the
      lifecycle: starts server if needed, opens Chromium app window, closing it TERMs the
      server. Backend: JobManager.shutdown() cancels all workers on lifespan teardown,
      uvicorn timeout_graceful_shutdown=5. Verified: window close → port free, no
      processes, DB writable; TERM mid-download → all stopped in 1s, job 'cancelled',
      .part kept; double-launch doesn't kill the first instance's server.)*

- [x] **Deep review pass** *(2026-07-19: full backend read. Fixed three latent
      issues: vault unlock now derives with the scrypt params stored in the file
      instead of module constants (tuning the KDF cost would have locked out every
      existing vault as "wrong password"; regression test added); scheduler holds
      strong refs to check tasks so pending subscription checks can't be
      garbage-collected mid-flight; vault writes fsync before the atomic rename.
      Wrote [vault-format.md](vault-format.md) so the file format is readable
      without the Python source. Accepted as-is, deliberately: change-password on
      a locked vault leaves it unlocked (password was just proven); two concurrent
      jobs for the same video can both download it (per-job archive snapshot; DB
      dedupes, only bandwidth wasted).)*

## M7 — Frontend redesign + publishing (2026-07-21)

- [x] Repo hygiene: remove private path references
- [x] Frontend redesign in place: design tokens + light/dark themes (`light-dark()`,
      persisted toggle), responsive to 360px, icon nav + queue badge, unified chip
      system, transfer-strip progress bar, skeleton/error/empty states on all list
      pages, accessibility pass (focus-visible, aria, reduced motion). No new deps.
- [x] Packaging code changes: frontend builds into `yoink/static/` (shipped in wheel),
      `uvicorn[standard]` → `uvicorn` + `websockets` (Fedora has no extras)
- [x] LICENSE: PolyForm Noncommercial 1.0.0
- [x] Launcher/desktop file: dual-mode launcher (dev checkout or system install),
      no hardcoded paths
- [x] RPM: source tarball script (pre-built frontend), `packaging/yoink.spec`
      (noarch, distro deps, Recommends ffmpeg/chromium), build + rpmlint +
      install/uninstall verification
- [x] README rewrite for the published repo (install via RPM as primary path)
- [x] Publish: GitHub repo Vid-Yoink, tag v0.1.0, release with RPM attached, CI
      workflow for future releases

## M8 — Fixes + interface rework (planned 2026-11-11, not started)

Fresh-eyes review found two confirmed problems (failed downloads saved as "finished";
any web page can reach the local server), a launcher that only finds Chromium, weak
spots in subscriptions, and an interface that needs a new layout more than new paint.
Full findings, steps and done-checks: [m8-plan.md](m8-plan.md).

- [ ] Phase 1 — correctness and safety (steps 1.1–1.8)
- [ ] Phase 2 — interface rework (steps 2.1–2.7)
- [ ] Phase 3 — new features (optional, pick per item)

## Deferred / future reference

- **Public cross-platform distribution** — analyzed 2026-07-10, initially deferred;
  M7 (2026-07-21) implements the Fedora/RPM + GitHub slice of it. The full analysis
  (downstream packaging fixes vs. upstream re-architecture, tool-vs-appliance decision,
  what survives a rewrite) is in [distribution-plan.md](distribution-plan.md).

## Notes

- yt-dlp warns about a missing JavaScript runtime for YouTube ("some formats may be
  missing") — installing deno fixes it; mention in README (M6).
- The interactive probe caps at the first 500 playlist entries; subscription checks and
  seeding read up to 5000 (M8 1.6).

## Review

All six milestones landed 2026-07-10, one commit each. Final state: 32 backend unit
tests green, ruff clean, tsc clean, production build served by `uv run yoink` on
127.0.0.1:8090 only.

**Verified end-to-end during the build (against real YouTube + direct URLs):**
video/audio/playlist downloads with live WS progress; two concurrent jobs; cancel with
"cancelling" intermediate state and resumable .part files; probe (video heights, flat
playlist entries with already-downloaded flags); playlist item selection; presets;
DB-backed archive proving moved files are never re-downloaded; force re-download;
subscriptions with seeding, check-now, and a live-fired 1-minute auto-check; encrypted
vault (wrong password 403, locked-job fail-fast + unlock-retry, no plaintext on disk,
0600 file); SPA deep links; settings persistence.

**Deviations from plan, all deliberate:** options map to yt-dlp via CLI argv +
parse_options (instead of a hand-built opts dict) — exact CLI semantics for free;
playlist file paths come from the MoveFiles pp-hook because playlist entries drop
requested_downloads; added force_download option (re-download without deleting archive
rows); advanced form sections consolidated into OptionsForm.tsx rather than one file per
section.

**Known gaps (documented in README):** cancellation can't interrupt ffmpeg/extraction;
probe/checks read first 500 playlist entries; cookie rotation discarded; max_concurrent
change needs restart; deno recommended for full YouTube format coverage.
