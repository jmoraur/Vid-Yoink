# yoink — local yt-dlp web downloader

Plan reference: ~/.claude/plans/lazy-juggling-gadget.md (approved 2026-07-10)

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

## Notes

- yt-dlp warns about a missing JavaScript runtime for YouTube ("some formats may be
  missing") — installing deno fixes it; mention in README (M6).
- Probe/subscription checks cap at the first 500 playlist entries (documented limitation;
  fine for channels where new items appear first, can miss appends past 500 on huge
  regular playlists).

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
