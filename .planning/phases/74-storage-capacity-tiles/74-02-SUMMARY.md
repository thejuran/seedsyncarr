---
phase: 74-storage-capacity-tiles
plan: 02
subsystem: backend
tags: [python, scanner, ssh, capacity, df, shutil, security]

requires:
  - phase: 74-01
    provides: Status.StorageStatus component with four nullable byte-count properties
provides:
  - LocalScanner inline shutil.disk_usage with OSError fallback
  - RemoteScanner second df -B1 SSH call with shlex.quote security wrap
  - _parse_df_output helper tolerating malformed/empty/binary output
  - Controller._should_update_capacity strict >1% gate
  - Per-side independent capacity assignment in _update_controller_status
affects: [74-04, future scanner refactors]

tech-stack:
  added: []
  patterns:
    - Ancillary SSH call with silent fallback (df after main scan)
    - Strict >1% delta gate for SSE-bound continuous metrics
    - Paired-measurement atomic writes (total+used updated together)

key-files:
  created:
    - src/python/tests/unittests/test_controller/test_controller.py
  modified:
    - src/python/controller/scan/scanner_process.py
    - src/python/controller/scan/local_scanner.py
    - src/python/controller/scan/remote_scanner.py
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py
    - src/python/tests/unittests/test_controller/test_controller_unit.py

key-decisions:
  - "Capacity collection is ancillary: failures NEVER fail the scan (silent fallback per D-16)"
  - "shlex.quote on every user-controlled remote path (T-74-05) — including the new df invocation"
  - "Paired total+used writes atomically when either exceeds the >1% gate (prevents bogus percentage display)"
  - "Strict > comparison (not >=) on the 1% gate per design spec"

patterns-established:
  - "df parser returns (None, None) on every failure mode — never raises"
  - "Capacity assignment block wrapped in try/except SshcpError + try/except parse to fully isolate ancillary failures from scan correctness"

requirements-completed: []

duration: ~30min
completed: 2026-04-20
---

# Phase 74-02: Scanner Disk-Usage Wiring Summary

**LocalScanner + RemoteScanner now collect disk capacity (`shutil.disk_usage` and `df -B1` over SSH) and the controller writes it to `Status.StorageStatus` per-side with a strict `>1%` change gate.**

## Performance

- **Duration:** ~30 min (orchestrator inline execution after gsd-executor agent dispatch failed)
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 6
- **Tests:** 18 new controller tests + 9 new remote_scanner tests; 777 total pass after regression sweep

## Accomplishments
- `ScannerResult` carries optional `total_bytes` / `used_bytes` (backward-compat default `None`)
- `IScanner.scan()` widened to return `Tuple[List[SystemFile], Optional[int], Optional[int]]`
- `ScanOutput` type alias added at module level
- `ScannerProcess.run_loop` destructures the 3-tuple and passes capacity into `ScannerResult`
- `LocalScanner` runs `shutil.disk_usage(self.__local_path)` after each scan with `OSError`/`ValueError` fallback to `(None, None)` + WARN log
- `RemoteScanner._parse_df_output` static method — never raises; returns `(None, None)` for empty / missing-data / non-numeric / unicode-decode failures
- `RemoteScanner.scan()` adds a second `self.__ssh.shell("df -B1 {}".format(shlex.quote(...)))` call after the main scan with try/except `SshcpError` + parse failure → silent fallback
- `Controller._should_update_capacity` static helper: `None → value` always passes; `> 1%` strict comparison; `0 → nonzero` passes; `0 → 0` blocks
- `Controller._update_controller_status` writes capacity per-side with the gate; total+used updated atomically as a paired measurement; per-side independence is structural

## Task Commits

1. **Task 1 RED: df parser + scan capacity tuple tests** — `d789d13` (test)
2. **Task 1 GREEN: scanner disk-usage wiring** — `35609c7` (feat) — also updated existing remote_scanner tests' counter-based ssh_shell mocks to account for the new df call slot
3. **Task 2 RED: >1% gate + per-side capacity tests** — `5a91c70` (test)
4. **Task 2 GREEN: controller capacity gate** — `c193ebb` (feat)

## Files Created/Modified
- `src/python/controller/scan/scanner_process.py` — `ScanOutput` alias, `IScanner.scan()` widening, `ScannerResult.total_bytes`/`.used_bytes`, `run_loop` destructure
- `src/python/controller/scan/local_scanner.py` — `import shutil`, `__local_path` storage, capacity collection in `scan()` with OSError fallback
- `src/python/controller/scan/remote_scanner.py` — `_parse_df_output` static method, capacity collection in `scan()` with SshcpError + parse fallback
- `src/python/controller/controller.py` — `_should_update_capacity` static helper, per-side capacity writes in `_update_controller_status`
- `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py` — 9 new tests (parser cases, shlex.quote regression, df SSH fallback) + 4 existing test counter updates
- `src/python/tests/unittests/test_controller/test_controller.py` — NEW file, 18 tests covering gate logic and capacity assignment matrix
- `src/python/tests/unittests/test_controller/test_controller_unit.py` — set MagicMock ScannerResult `total_bytes`/`used_bytes` to None to keep capacity-write block inert in scan-time-only tests

## Decisions Made
- Counter-based `ssh_shell` mocks in pre-existing remote_scanner tests had to be re-keyed (count 3 = df, count 4 = next main scan attempt). This is fragile but local — alternative would be to rewrite the harness, which is out of plan scope.
- Test infra: used `Controller.__new__(Controller)` to bypass the heavy `__init__` dependency graph, then injected `mock_context` with a real `Status()` instance. This keeps tests focused on the one method under test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test regression] Pre-existing `ssh_shell` mocks broke after adding df shell call**
- **Found during:** Task 1 verification
- **Issue:** Four existing tests use a counter-based `side_effect` that maps `count == 3` to "second scan attempt". After adding `df` (which executes between successful main scans), the third call became the df invocation rather than the second main scan.
- **Fix:** Bumped each affected mapping by one slot (count 3 → df returns `b""`; count 4 → original "second scan attempt" content). Also updated 3 `assertEqual(N, call_count)` assertions to reflect the new totals (2→3, 3→4, 4→6).
- **Files modified:** `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py`
- **Verification:** All 31 remote_scanner tests pass.
- **Committed in:** `35609c7` (Task 1 GREEN)

**2. [Rule 1 — Test regression] `MagicMock` ScannerResult tripped the new capacity-write block**
- **Found during:** Task 2 verification (broader regression sweep)
- **Issue:** `test_controller_unit.py::TestControllerUpdateStatus` constructs `MagicMock()` ScannerResults. After my change, `mock.total_bytes` returns a `MagicMock` (not `None`), which passes the `is not None` guard and then crashes the gate's arithmetic.
- **Fix:** Explicitly set `total_bytes = None` and `used_bytes = None` on those mocks, with a brief comment explaining the requirement.
- **Files modified:** `src/python/tests/unittests/test_controller/test_controller_unit.py`
- **Verification:** Both previously-failing tests now pass.
- **Committed in:** `c193ebb` (Task 2 GREEN)

---

**Total deviations:** 2 auto-fixed (both Rule 1 test regressions from interface widening)
**Impact on plan:** Necessary for correctness; no scope creep.

## Issues Encountered
- The originally-spawned `gsd-executor` subagents (both worktree-isolated and sequential) consistently failed with "I need Bash access" — a dispatch-layer issue with this session's agent registration. Falling back to inline orchestrator execution restored progress. This is environment-specific, not a plan defect.
- Pre-existing test collection errors (`timeout_decorator` missing, `test_scan_file_with_latin_chars` macOS encoding) are unrelated to this plan — verified by checking they fail on `main` before my changes too.

## User Setup Required
None.

## Next Phase Readiness
- `Status.StorageStatus.{local,remote}_total/used` are now populated on every scan cycle (subject to the >1% gate). The SSE stream wired in Plan 74-01 will emit real numbers as soon as the backend is restarted.
- Plan 74-04 can now drive its template assertions against real capacity data flowing through the existing SSE → `ServerStatus` → `DashboardStatsService` pipeline (Wave 1).

---
*Phase: 74-storage-capacity-tiles*
*Completed: 2026-04-20*
