---
phase: 74
slug: storage-capacity-tiles
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-19
---

# Phase 74 — Validation Strategy

> Retroactive Nyquist validation of storage-capacity-tiles phase. Generated after all four plans executed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 7.x + unittest.TestCase (Python 3.9) |
| **Backend config** | `src/python/pyproject.toml` |
| **Frontend framework** | Karma + Jasmine via Angular CLI |
| **Frontend config** | `src/angular/angular.json`, `karma.conf.js` |
| **Backend quick run** | `cd src/python && python -m pytest tests/unittests/test_common/test_status.py tests/unittests/test_web/test_serialize/test_serialize_status.py tests/unittests/test_controller/test_scan/test_remote_scanner.py tests/unittests/test_controller/test_scan/test_local_scanner.py tests/unittests/test_controller/test_controller.py -x` |
| **Frontend quick run** | `cd src/angular && npx ng test --include='**/services/server/server-status.spec.ts' --include='**/services/files/dashboard-stats.service.spec.ts' --include='**/stats-strip.component.spec.ts' --watch=false --browsers=ChromeHeadless` |
| **Full suite (backend)** | `cd src/python && python -m pytest -x` |
| **Full suite (frontend)** | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless` |
| **Type check** | `cd src/angular && npx tsc --noEmit -p tsconfig.json` |
| **Estimated runtime** | backend ~5s, frontend ~30s |

---

## Sampling Rate

- **After every task commit:** Run the plan-scoped quick command (backend or frontend per plan tags)
- **After every plan wave:** Run the full backend + frontend suites for that subsystem
- **Before `/gsd-verify-work`:** Full backend + frontend suites must be green
- **Max feedback latency:** ~35 seconds for full backend + frontend subset

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 74-01-T1 | 01 | 1 | StorageStatus component + 4 nullable byte-count fields + listener chain + copy preservation | T-74-02, T-74-03 | Status model guards against component reassignment; defaults None for cold-load | unit | `cd src/python && python -m pytest tests/unittests/test_common/test_status.py -k storage -x` | ✅ | ✅ green |
| 74-01-T2 | 01 | 1 | SerializeStatusJson emits `storage` block with 4 number-or-null fields | T-74-01, T-74-04 | Fixed string keys, numeric passthrough, no user input interpolation | unit | `cd src/python && python -m pytest tests/unittests/test_web/test_serialize/test_serialize_status.py -k storage -x` | ✅ | ✅ green |
| 74-02-T1a | 02 | 2 | `_parse_df_output` tolerates malformed/empty/unicode/non-numeric output → returns (None, None) | T-74-06 | Parser never raises; silent fallback per D-16 | unit | `cd src/python && python -m pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py::TestParseDfOutput -x` | ✅ | ✅ green |
| 74-02-T1b | 02 | 2 | `df -B1` SSH call uses `shlex.quote` on user-controlled remote_path | T-74-05 | Command injection mitigation on authenticated SSH boundary | unit | `cd src/python && python -m pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py::TestRemoteScannerShleQuote -x` | ✅ | ✅ green |
| 74-02-T1c | 02 | 2 | RemoteScanner SshcpError on df → (None, None) + WARN; scan file list preserved | T-74-06 | Ancillary data failure never fails scan | unit | `cd src/python && python -m pytest tests/unittests/test_controller/test_scan/test_remote_scanner.py::TestRemoteScannerDfSshFailure -x` | ✅ | ✅ green |
| 74-02-T1d | 02 | 2 | LocalScanner `shutil.disk_usage` happy path + OSError/ValueError silent fallback | T-74-09 | Unmounted path doesn't crash scanner process | unit | `cd src/python && python -m pytest tests/unittests/test_controller/test_scan/test_local_scanner.py -x` | ✅ | ✅ green (filled 2026-04-19) |
| 74-02-T2a | 02 | 2 | `_should_update_capacity` strict `>1%` gate (79/80/94/95 + None-to-value + 0-boundary) | T-74-08 | SSE flood prevention on continuous metrics | unit | `cd src/python && python -m pytest tests/unittests/test_controller/test_controller.py::TestShouldUpdateCapacity -x` | ✅ | ✅ green |
| 74-02-T2b | 02 | 2 | `_update_controller_status` writes capacity per-side with gate; paired total+used atomic; per-side independence | T-74-08 | Scan-time field regressions guarded | unit | `cd src/python && python -m pytest tests/unittests/test_controller/test_controller.py::TestUpdateControllerStatusCapacity -x` | ✅ | ✅ green |
| 74-03-T1 | 03 | 1 | IServerStatus.storage DTO snake→camel mapping + deploy-skew default + cold-load default | T-74-10 | Missing-key JSON doesn't throw; null passthrough | unit | `cd src/angular && npx ng test --include='**/services/server/server-status.spec.ts' --watch=false --browsers=ChromeHeadless` | ✅ | ✅ green |
| 74-03-T2 | 03 | 1 | DashboardStats 4 capacity fields (null defaults) + `combineLatest` merge retention + per-tile independence | T-74-13 | Teardown preserved via `takeUntil`; cold-load null per D-14 | unit | `cd src/angular && npx ng test --include='**/services/files/dashboard-stats.service.spec.ts' --watch=false --browsers=ChromeHeadless` | ✅ | ✅ green |
| 74-04-T1 | 04 | 2 | SCSS `--warning` / `--danger` modifiers + DecimalPipe import; TS compile clean | T-74-17 | Bootstrap token fallback hex guards missing CSS var | build | `cd src/angular && npx tsc --noEmit -p tsconfig.json` | ✅ | ✅ green |
| 74-04-T2 | 04 | 2 | Capacity/fallback `@if`/`@else` branches; divide-by-zero guard (`total > 0`); integer % rounding (D-05); threshold class bindings at 80/95 | T-74-14, T-74-15 | Three-part guard prevents NaN render; Angular default escaping | build+unit | `cd src/angular && npx ng build --configuration=development` | ✅ | ✅ green |
| 74-04-T3 | 04 | 2 | 12 render tests: fallback both tiles, capacity both tiles, per-tile independence (both directions), 79/80/94/95 boundaries, integer %, Local secondary base, progress-fill width binding | — | Tests assert class names and rendered text fragments | unit | `cd src/angular && npx ng test --include='**/stats-strip.component.spec.ts' --watch=false --browsers=ChromeHeadless` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The single gap (`test_local_scanner.py`) was filled retroactively by `/gsd-validate-phase` on 2026-04-19.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Remote Storage tile capacity mode on live seedbox | UAT Test 1 | SSH `df` cannot be faked in E2E harness (per locked design spec §"Tests"); requires real seedbox | Start seedsyncarr with valid SSH config; load dashboard; confirm tile shows `XX%` + `of X.XX TB` + progress bar + `X.XX GB used` when SSE delivers non-null remote storage |
| Local Storage tile capacity mode on live install | UAT Test 2 | Requires real mounted local path; verification that `shutil.disk_usage` returns real values on deployed machine | Start on real host; load dashboard; confirm Local tile shows integer % + total + progress bar + used sub-line driven by `shutil.disk_usage(local_path)` |
| Tile fallback to tracked-bytes on capacity failure | UAT Test 3 | Requires induced failure (disconnect SSH, bad path) — timing-dependent | Run with invalid SSH creds → Remote tile stays in fallback; run with unmounted local path → Local tile stays in fallback; other tile unaffected |
| Threshold color shifts at 80%/95% on real disk usage | UAT Test 4 | Requires real disk at boundary usage levels; unit tests cover the class-binding logic at 79/80/94/95 | Observe tile colors when disk crosses 80% (warning yellow) and 95% (danger red); boundary flip is deterministic per class-binding tests |
| Per-tile independence on live asymmetric state | UAT Test 5 | Requires asymmetric failure mode (remote SSH down, local mount up); unit tests cover the logic structurally | Disable SSH → Remote falls back, Local stays capacity; vice versa for unmounted local |
| Download Speed / Active Tasks tiles regression check | UAT Test 6 | Visual regression — existing tiles render identically | Before/after screenshot comparison of the two unchanged tiles |

These 6 UAT items are paused per `74-UAT.md` until after the next dev release. The locked design spec explicitly defers E2E coverage for this phase (SSH `df` unfakeable in harness).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (gap filled retroactively on 2026-04-19)
- [x] No watch-mode flags (all `--watch=false` in frontend commands)
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-19

---

## Validation Audit 2026-04-19

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

### Gap resolved

- **REQ-02.2 (Plan 74-02 Task 1)** — LocalScanner.scan() capacity collection + OSError/ValueError silent fallback — filled by `test_local_scanner.py` with 4 passing unit tests (happy path, OSError fallback, ValueError fallback, file-list identity preservation across fallback).
