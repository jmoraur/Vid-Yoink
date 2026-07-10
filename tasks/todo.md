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
- [ ] **M6 — Production polish**: static serving + SPA fallback, ffmpeg startup check,
      extra-args escape hatch, SponsorBlock section, settings page, README.
      Verify: npm run build && uv run yoink full workflow; port bound to 127.0.0.1 only.

## Notes

- yt-dlp warns about a missing JavaScript runtime for YouTube ("some formats may be
  missing") — installing deno fixes it; mention in README (M6).
- Probe/subscription checks cap at the first 500 playlist entries (documented limitation;
  fine for channels where new items appear first, can miss appends past 500 on huge
  regular playlists).

## Review

(filled in as milestones complete)
