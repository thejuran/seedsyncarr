---
status: resolved
trigger: "e2e test failures — illusion.jpg downloads too fast between Docker containers for the stop command to catch it in QUEUED/DOWNLOADING state"
created: 2026-04-22
updated: 2026-04-22
---

# Debug Session: e2e-stopped-seed-too-fast

## Symptoms

- **Expected behavior:** The seed-state fixture should be able to queue a file, then stop it mid-download, producing a STOPPED state (localSize > 0, remoteSize > 0, state == DEFAULT).
- **Actual behavior:** The file downloads completely before the stop command takes effect, so the seed never reaches STOPPED state. The fixture fails, cascading to skip all UAT-02 tests in the serial block.
- **Error messages:** Fixture timeout — seed never transitions to STOPPED. All subsequent tests in test.describe.serial skipped.
- **Timeline:** Persists across multiple attempts: 2MB file, 10MB file, immediate API stop-after-queue. Both amd64 and arm64 runners fail identically.
- **Reproduction:** Run the e2e test suite — the seed-state fixture at src/e2e/tests/fixtures/seed-state.ts fails when trying to create a STOPPED seed.

## Key Files

- src/e2e/tests/fixtures/seed-state.ts (fixture)
- src/e2e/tests/dashboard.page.spec.ts (test)
- src/angular/src/app/services/files/view-file.service.ts:314-316 (STOPPED state logic)
- src/python/controller/controller.py:997 (stop accepts QUEUED or DOWNLOADING)
- src/python/lftp/lftp.py:233 (rate_limit property, not exposed via config API)

## Root Cause Analysis

- Backend queue API call blocks until lftp starts (callback.wait), and on fast Docker networks the download finishes during that blocking call.
- lftp uses 4 parallel connections per file (num_max_connections_per_root_file = 4).
- rate_limit property exists on Lftp class but is not exposed through the config API — only used in integration tests (rate_limit = 300).

## Resolution

- **root_cause:** No bandwidth throttling available to e2e tests; lftp rate_limit property existed but was not exposed through the config REST API, so the e2e fixture had no way to slow downloads enough for the stop command to win the race.
- **fix:** Exposed rate_limit through the full config chain (Config.Lftp property -> LftpManager runtime sync -> REST API) and updated the e2e seed-state fixture to throttle to 100 B/s before the STOPPED seed loop, restoring unlimited speed afterward.
- **files_changed:**
  - src/python/common/config.py — added rate_limit PROP to Config.Lftp with int_non_negative checker, backward-compat default 0
  - src/python/controller/lftp_manager.py — apply rate_limit at init, sync from config before each queue() call
  - src/e2e/tests/fixtures/seed-state.ts — set rate_limit=100 before STOPPED seed, reset to 0 in finally block
  - src/python/tests/unittests/test_common/test_config.py — updated test_lftp, test_to_file, test_from_file, _build_plaintext_config

## Evidence

- timestamp: 2026-04-22 — Integration tests already use rate_limit=100 on the lftp instance directly (test_controller.py lines 911,973,1075,1145,1203,1783,1839,1927)
- timestamp: 2026-04-22 — Config set REST API (/server/config/set/{section}/{key}/{value}) works generically via InnerConfig.set_property — adding rate_limit to Config.Lftp automatically exposes it
- timestamp: 2026-04-22 — LftpManager reads config once at init; runtime changes via REST API only update the Config object in memory. Added __sync_rate_limit() to propagate changes to the lftp process before each queue() call
- timestamp: 2026-04-22 — All 23 config unit tests pass, all 45 serialize+handler tests pass

## Eliminated

- tc network throttling in Docker — unnecessarily complex; rate_limit is already an lftp native feature
- Larger fixture files (50MB+) — would slow all tests, not just the STOPPED seed; does not address the fundamental race condition
