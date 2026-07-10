# yoink — local yt-dlp web downloader

Plan reference: ~/.claude/plans/lazy-juggling-gadget.md (approved 2026-07-10)

## Milestones

- [x] **M1 — End-to-end skeleton** *(done 2026-07-10: verified generic mp4 + real YouTube
      download, 2 concurrent jobs, WS progress events, cancel with 'cancelling' state,
      error surfacing, history persists across restart, 127.0.0.1-only binding)*: pyproject + uv, FastAPI app, jobs table, JobManager
      (semaphore=2, cancel events, WS broadcaster), runner with default opts, minimal React
      page (URL box + job list + live progress), dev proxy.
      Verify: paste URL → progress ticks over WS → file lands in ~/Downloads; 2 concurrent jobs.
- [x] **M2 — Probe, options, presets** *(done 2026-07-10: video probe with real heights,
      flat playlist probe with already_downloaded flags, audio-only → .mp3 verified,
      playlist_items "1,3" downloaded exactly items 1+3, invalid extra_args → 422,
      presets CRUD + 409 on duplicate name, 20 unit tests green. Fixed: playlist entries
      drop requested_downloads → final paths now collected via MoveFiles pp-hook.)*: /api/probe + ProbeCard/PlaylistEntryPicker, full
      DownloadOptions model, build_ydl_opts() + unit tests, basic + advanced form sections,
      presets CRUD.
      Verify: playlist probe shows entries; audio-only → .mp3; playlist_items works; pytest green.
- [x] **M3 — Queue management + archive** *(done 2026-07-10: DB archive wired via
      SqliteArchive set-subclass; verified file moved to library → re-submit skipped with
      zero downloads; force_download bypasses check; delete archive row → re-downloads;
      retry/delete endpoints with 409 guard; archive browser page with search.)*: cancel/retry/delete, SqliteArchive as
      download_archive, archive browser, history filters.
      Verify: cancel mid-download; re-submit same URL after moving file → skipped; delete
      archive row → re-downloads.
- [ ] **M4 — Subscriptions + scheduler**: CRUD, check-now, seed-existing, 60s asyncio
      scheduler loop, WS event + page.
      Verify: seed → check-now → 0 new; un-seeded playlist → N jobs; second check → 0 new;
      1-min interval fires automatically.
- [ ] **M5 — Vault**: scrypt+AES-GCM vault + tests, vault API, settings panel + unlock
      dialog, credentials/cookies wired into build_ydl_opts (StringIO), locked-vault error path.
      Verify: cookies for login-required video works; restart → locked → clear error →
      unlock + retry; no plaintext secrets on disk.
- [ ] **M6 — Production polish**: static serving + SPA fallback, ffmpeg startup check,
      extra-args escape hatch, SponsorBlock section, settings page, README.
      Verify: npm run build && uv run yoink full workflow; port bound to 127.0.0.1 only.

## Review

(filled in as milestones complete)
