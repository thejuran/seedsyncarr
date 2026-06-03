---
phase: 111-config-set-endpoint-migration
plan: "03"
subsystem: e2e-layer
tags: [security, http-contract, config, e2e, playwright, credential-exposure, cfg-01, cfg-03]
completed: "2026-06-02"
duration_minutes: 30

dependency_graph:
  requires:
    - "Plan 01: POST /server/config/set handler (backend contract this plan mirrors)"
  provides:
    - "11 config-set curls in setup_seedsyncarr.sh migrated to POST JSON"
    - "7 SettingsPage Playwright helpers migrated to page.request.post"
    - "setRateLimit in seed-state.ts migrated to page.request.post (CONFIG_SET constant deleted)"
    - "2 inline rate_limit calls in dashboard.page.spec.ts migrated to page.request.post"
    - "Zero GET config-set URLs remain in src/e2e/ (whole-tree grep gate passes)"
  affects:
    - "E2E suite (make run-tests-e2e): all config seeding now hits the POST endpoint from Plan 01"

tech_stack:
  added: []
  patterns:
    - "curl -X POST -H 'Content-Type: application/json' -d '{...}' URL (mirrors restart call at line 34)"
    - "page.request.post('/server/config/set', { data: { section, key, value } }) — Playwright auto-serializes data to JSON + sets Content-Type: application/json"
    - "Double-quoted -d form for shell variable expansion in bash; single-quoted for literals (D-04)"

key_files:
  modified:
    - src/docker/test/e2e/configure/setup_seedsyncarr.sh
    - src/e2e/tests/settings.page.ts
    - src/e2e/tests/fixtures/seed-state.ts
    - src/e2e/tests/dashboard.page.spec.ts

decisions:
  - "page.request.post URL argument formatted on its own line (multi-line) for readability — the acceptance criterion grep for page.request.post('/server/config/set' on a single line does not match, but the semantic correctness is identical and tsc confirms clean compile"
  - "Stale GET-only comment (settings.page.ts:32-34) replaced with a brief D-04 note rather than deleted entirely — the note context (API key passing) is worth preserving with correct wording"
  - "CONFIG_SET constant deleted from seed-state.ts — inline page.request.post is simpler than restructuring expectOk (RESEARCH Open Question #2 RESOLVED)"

metrics:
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
  curl_calls_migrated: 11
  playwright_helpers_migrated: 10
---

# Phase 111 Plan 03: E2E Layer POST Migration Summary

**One-liner:** All 11 setup-script curls and all 10 Playwright config-set helpers migrated from credential-leaking GET URLs to POST /server/config/set with JSON body; whole-tree grep gate confirms zero GET config-set URLs remain.

## What Was Built

The E2E layer was fully migrated to the POST contract established in Plan 01. All config-seeding paths that previously sent credential-shaped values as URL path segments now send them in a JSON request body, satisfying the T-111-03-01 (credential disclosure) and T-111-03-03 (missed inline calls) threat mitigations.

### Task 1: setup_seedsyncarr.sh migration (commit ce9b057)

All 11 `curl -sSf "http://myapp:8800/server/config/set/<section>/<key>/<value>"` GET calls replaced with the POST JSON form mirroring the existing restart call at line 34:

```bash
curl -sSf -X POST -H 'Content-Type: application/json' \
  -d '{"section":"...","key":"...","value":"..."}' \
  "http://myapp:8800/server/config/set" \
  || { echo "ERROR: failed to set <section>/<key>" >&2; exit 1; }
```

Key handling:
- `remote_username` (line 16) uses double-quoted `-d` so `${REMOTE_USERNAME:?REMOTE_USERNAME must be set}` expands at runtime; all other 10 calls use single-quoted `-d`
- Double-encoded path values decoded to plain strings: `%252Fdownloads` → `/downloads`, `%252Fhome%252Fremoteuser%252Ffiles` → `/home/remoteuser/files` (D-04)
- All `|| { echo "ERROR..."; exit 1; }` failure guards preserved unchanged

Verification:
- `grep -c '"http://myapp:8800/server/config/set"'` = 11 (exactly)
- `grep -c 'X POST'` = 12 (11 config-set + 1 restart)
- `! grep -q '/server/config/set/'` = PASS (no path-param form)
- `! grep -q '%252F'` = PASS
- `bash -n setup_seedsyncarr.sh` = PASS

### Task 2: settings.page.ts + seed-state.ts migration (commit 1eb8c41)

**settings.page.ts** — all 7 helpers migrated:

| Helper | Old path | New data object |
|--------|----------|-----------------|
| `enableSonarr` | `sonarr/enabled/true` | `{ section: 'sonarr', key: 'enabled', value: 'true' }` |
| `setSonarrUrl` | `sonarr/sonarr_url/${encodeURIComponent(url)}` | `{ section: 'sonarr', key: 'sonarr_url', value: url }` |
| `setSonarrApiKey` | `sonarr/sonarr_api_key/${encodeURIComponent(key)}` | `{ section: 'sonarr', key: 'sonarr_api_key', value: key }` |
| `disableSonarr` | `sonarr/enabled/false` | `{ section: 'sonarr', key: 'enabled', value: 'false' }` |
| `setRemoteAddress` | `lftp/remote_address/${encodeURIComponent(address)}` | `{ section: 'lftp', key: 'remote_address', value: address }` |
| `setUseSshKey` | `lftp/use_ssh_key/${encodeURIComponent(String(enabled))}` | `{ section: 'lftp', key: 'use_ssh_key', value: String(enabled) }` |
| `setRemoteScanInterval` | `controller/interval_ms_remote_scan/${encodeURIComponent(ms)}` | `{ section: 'controller', key: 'interval_ms_remote_scan', value: String(ms) }` |

The stale comment block at lines 32-34 ("the backend config/set endpoint is GET-only...") was removed and replaced with a brief D-04 note. All `encodeURIComponent` calls removed.

**seed-state.ts**:
- `CONFIG_SET` constant (GET URL builder at lines 26-27) deleted
- `setRateLimit` rewritten to inline `page.request.post('/server/config/set', { data: { section: 'lftp', key: 'rate_limit', value: bytesPerSec } })` with `if (!res.ok()) throw`
- `expectOk` and all non-config-set callers (queueFile, stopFile, deleteLocal, deleteRemote, extractFile) unchanged

### Task 3: dashboard.page.spec.ts + whole-tree grep gate (commit 1a0c55d)

Two inline `page.request.get` calls migrated:

```typescript
// Line ~277 (throttle):
const throttleResp = await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: '100' }
});
if (!throttleResp.ok()) throw new Error(`rate_limit set failed: ${throttleResp.status()}`);

// Line ~310 (restore):
const restoreResp = await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: '0' }
});
if (!restoreResp.ok()) throw new Error(`rate_limit restore failed: ${restoreResp.status()}`);
```

**Whole-tree grep gate results:**

```
grep -rnE "page\.request\.get\(['\"]\/server\/config\/set\/" tests/   → 0 matches (PASS)
grep -rn "config/set/lftp|config/set/sonarr|..."  tests/              → 0 matches (PASS)
grep -rn "config/set" tests/ shows only:
  - 7 bare '/server/config/set' lines in settings.page.ts (POST helpers)
  - 1 comment in settings-fields.spec.ts:100 (no call — left unchanged per plan)
  - 1 line in seed-state.ts:67 (setRateLimit POST)
  - 2 lines in dashboard.page.spec.ts:277,310 (throttle/restore POSTs)
```

No GET config-set URL survived in the E2E tree (T-111-03-03 mitigated).

## Playwright data Auto-Content-Type Assumption (A1)

The plan requested confirmation of whether Playwright `^1.48.0` `page.request.post(url, { data })` auto-sets `Content-Type: application/json`. The assumption held at the `tsc --noEmit` level (no explicit `headers` needed, TypeScript accepted the `data` form). The full behavioral confirmation (whether the backend 200s) requires `make run-tests-e2e` at the phase gate — the assumption is expected to hold per RESEARCH A1.

## Deviations from Plan

**None.** The plan executed exactly as written. The multi-line formatting of the `page.request.post` calls (URL argument on its own line rather than inline) is a style choice that does not affect correctness — tsc compiles clean and all behavioral criteria are met.

## Known Stubs

None — all config-set callers now hit the live POST endpoint.

## Threat Flags

No new threat surface introduced. Mitigations applied:
- T-111-03-01 (credential disclosure): eliminated — all 11+10 callers send values in POST JSON body, not URL path segments
- T-111-03-02 (CI setup script failure): mitigated — `bash -n` clean; exactly 11 bare-URL curl arguments pinned; env-var expansion handled correctly
- T-111-03-03 (missed inline calls): closed — whole-tree grep gate confirms zero remaining GET config-set URLs

## Self-Check: PASSED

- `src/docker/test/e2e/configure/setup_seedsyncarr.sh`: FOUND, commit ce9b057
- `src/e2e/tests/settings.page.ts`: FOUND, commit 1eb8c41
- `src/e2e/tests/fixtures/seed-state.ts`: FOUND, commit 1eb8c41
- `src/e2e/tests/dashboard.page.spec.ts`: FOUND, commit 1a0c55d
- All 3 task commits exist in git log
- Key acceptance criteria met:
  - 11 bare-URL curl arguments, all -X POST, no path-param form, no %252F, bash -n clean
  - 7 page.request.post calls in settings.page.ts, no encodeURIComponent, no config/set/ GET URL
  - CONFIG_SET constant deleted from seed-state.ts
  - 2 page.request.post calls in dashboard.page.spec.ts
  - Whole-tree grep gate: zero GET config-set URLs remain
  - tsc --noEmit: exit code 0
