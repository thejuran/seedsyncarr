---
status: partial
phase: 74-storage-capacity-tiles
source: [74-01-SUMMARY.md, 74-02-SUMMARY.md, 74-03-SUMMARY.md, 74-04-SUMMARY.md]
started: 2026-04-20T02:50:00Z
updated: 2026-04-19T23:50:00Z
resolution: structural-verification + 6 runtime items deferred
---

## Current Test

[testing paused — 6 runtime items deferred until after next dev release; 11 structural tests verified]

## Tests

### 1. Remote Storage tile — capacity mode
expected: Remote Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line when SSH df succeeds.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 2. Local Storage tile — capacity mode
expected: Local Storage tile shows integer % + "of X.XX TB" + progress bar + "X.XX GB used" sub-line, driven by local `shutil.disk_usage` on the watched path.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 3. Tile fallback to tracked-bytes when capacity unavailable
expected: If the remote SSH df call fails (or local disk read errors), the affected tile silently falls back to the pre-existing tracked-bytes layout — no error banner, no blank UI, the other tile is unaffected.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 4. Threshold color shifts
expected: Progress-bar color follows thresholds — default (amber on Remote, secondary on Local) below 80%; warning (amber, stronger) at ≥80% and <95%; danger (red) at ≥95%. Boundary values flip exactly at 80 and 95.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 5. Per-tile independence
expected: The two tiles evaluate capacity independently — Remote can render capacity mode while Local falls back (or vice versa). One tile's fallback does not pull the other into fallback.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 6. Download Speed and Active Tasks tiles unchanged
expected: The other two tiles in the stats strip render identically to before Phase 74 — no layout shift, no new icons, no regression.
result: blocked
blocked_by: release-build
reason: "defer until after next dev release"

### 7. Backend StorageStatus model + SSE serializer (structural)
expected: `Status.StorageStatus` inner class exists with 4 nullable byte-count properties (local_total, local_used, remote_total, remote_used); defaults to None; `SerializeStatusJson.status()` emits a top-level `storage` block with all four keys.
result: pass
evidence: "`python3 -m pytest tests/unittests/test_common/test_status.py tests/unittests/test_web/test_serialize/test_serialize_status.py -q` → 82 passed. test_status.py covers defaults, property round-trips, listener firing, reassign guard, copy preservation (5 storage tests); test_serialize_status.py covers null-default + int round-trip per field (4 storage tests)."

### 8. RemoteScanner df collection with shlex.quote + silent fallback (structural)
expected: `RemoteScanner.scan()` issues a second SSH call `df -B1 <shlex.quote(remote_path)>` after the main scan; on SshcpError or parse failure returns capacity as (None, None) with a WARN log; scan file list is preserved.
result: pass
evidence: "remote_scanner.py contains `_parse_df_output` static method and the df invocation uses `\"df -B1 {}\".format(shlex.quote(self.__remote_path_to_scan))` (T-74-05 injection mitigation). test_remote_scanner.py: TestParseDfOutput (7 cases: happy, trailing whitespace, missing data row, non-numeric, empty, unicode, truncated), TestRemoteScannerShleQuote (hostile path containing `; rm -rf /` round-trip), TestRemoteScannerDfSshFailure (SshcpError → (None, None) + scan files preserved). All green."

### 9. LocalScanner shutil.disk_usage + OSError/ValueError silent fallback (structural)
expected: `LocalScanner.scan()` calls `shutil.disk_usage(local_path)` after the filesystem scan; on OSError or ValueError returns (files, None, None) with WARN log; scan file list preserved.
result: pass
evidence: "local_scanner.py:24-41 catches `(OSError, ValueError)` and logs WARN; test_local_scanner.py (4 tests added retroactively on 2026-04-19): happy path real integers, OSError fallback preserving files, ValueError fallback preserving files, file-list identity preserved across fallback."

### 10. Controller >1% strict change gate + per-side independence (structural)
expected: `_should_update_capacity` returns True when new != old by strictly >1%; returns False at exact 1%; None→value always passes; per-side independence: remote None leaves local untouched and vice versa; paired total+used writes atomic.
result: pass
evidence: "controller.py:_should_update_capacity uses `abs(new - old) / abs(old) > 0.01` (strict). test_controller.py TestShouldUpdateCapacity (9 cases: None→value, value→None blocked, +1.1% passes, +0.5% blocked, exact 1% blocked, +0.0011% passes, 0→nonzero passes, 0→0 blocked, negative delta >1% passes). TestUpdateControllerStatusCapacity (8 cases: first-write, sub-1% skipped, >1% writes both atomically, None capacity preserves existing, per-side independence both directions, None scan noop, scan-time fields regression guard)."

### 11. ServerStatus DTO storage block with deploy-skew safety (structural)
expected: `IServerStatus.storage` has 4 number-or-null fields camelCase; `ServerStatusJson.storage?:` optional; `fromJson` uses `json.storage?.local_total ?? null` + 3 peer fields; missing-key JSON parses to all-null; `DefaultServerStatus.storage` all null for cold-load per D-14.
result: pass
evidence: "server-status.ts: IServerStatus, DefaultServerStatus, ServerStatus class, ServerStatusJson all carry storage block. fromJson uses optional chaining + ?? null for all 4 fields. server-status.spec.ts: 6 new tests (per-field init, null passthrough ×4, missing-key deploy-skew default, Default record cold-load)."

### 12. DashboardStats + combineLatest merge with retention (structural)
expected: DashboardStats widened with 4 `*Capacity*` fields (`number | null`); ZERO_STATS capacity fields literal null (NOT 0); DashboardStatsService constructor uses `combineLatest([viewFileService.files, serverStatusService.status])` with `takeUntil(destroy$)`; retention semantics: file-list re-emit preserves capacity, status re-emit preserves file-derived counts.
result: pass
evidence: "dashboard-stats.service.ts: DashboardStats has 4 `*Capacity*: number | null` fields; ZERO_STATS uses `null` literals; constructor imports and calls `combineLatest([files, status]).pipe(takeUntil(destroy$))`. dashboard-stats.service.spec.ts: 4 new tests (capacity surfacing, per-tile independence remote-null local-populated, capacity retention on file-list re-emit, count retention on status re-emit)."

### 13. Template @if/@else capacity vs fallback + threshold class bindings (structural)
expected: stats-strip.component.html Remote tile `@if (stats.remoteCapacityTotal !== null && stats.remoteCapacityUsed !== null && stats.remoteCapacityTotal > 0)` capacity branch with integer % + "of {total}" + progress-fill class bindings for amber/warning/danger + "{used} used" sub-line; `@else` fallback = verbatim pre-phase-74 tracked-bytes layout. Same shape for Local tile with `--secondary` base.
result: pass
evidence: "stats-strip.component.html:10-41 Remote capacity @if with `@let remotePct = ...` and class bindings `[class.stat-progress-fill--amber]=\"remotePct < 80\"`, `[class.stat-progress-fill--warning]=\"remotePct >= 80 && remotePct < 95\"`, `[class.stat-progress-fill--danger]=\"remotePct >= 95\"`. Lines 51-82 Local capacity mirrors the shape with `--secondary` base. Both @else branches preserve the verbatim tracked-bytes markup. Percentage uses `| number:'1.0-0'` (integer rounding, D-05). Divide-by-zero guard via `remoteCapacityTotal > 0` three-part @if condition."

### 14. SCSS --warning / --danger modifiers using Bootstrap semantic tokens (structural)
expected: stats-strip.component.scss has `.stat-progress-fill--warning { background: var(--bs-warning, #ffc107); }` and `.stat-progress-fill--danger { background: var(--bs-danger, #dc3545); }`; no new SCSS variables introduced (D-11).
result: pass
evidence: "stats-strip.component.scss:143-149 — `&--warning { background: var(--bs-warning, #ffc107); }` and `&--danger { background: var(--bs-danger, #dc3545); }`. Existing `&--amber` and `&--secondary` rules preserved unchanged."

### 15. Frontend component threshold + rendering tests (structural)
expected: stats-strip.component.spec.ts has render tests for fallback both tiles, per-tile independence (both directions), integer % rounding, 79%/80%/94%/95% boundary class-binding tests, Local secondary base, progress-fill width binding.
result: pass
evidence: "stats-strip.component.spec.ts: 12 new tests per 74-04-SUMMARY — fallback both tiles, Remote/Local capacity mode, per-tile independence (both directions), integer % rounding (65.3% → 65%), amber at 79%, warning at 80% boundary, warning at 94%, danger at 95% boundary, Local secondary base < 80%, Local danger ≥95%, progress-fill width = used/total*100."

### 16. Download Speed + Active Tasks tiles preserved (structural)
expected: stats-strip.component.html Download Speed (lines 85-97) and Active Tasks (lines 99-114) render unchanged from pre-phase-74 markup — same class names, same pipes, same layout.
result: pass
evidence: "Template inspection: Download Speed card preserves `fa fa-arrow-down`, `fileSize:1:'value'` + `fileSize:1:'unit' + '/s'`, Peak sub-line. Active Tasks card preserves `fa fa-tasks`, `downloadingCount + queuedCount`, `.badge-dl` + `.badge-queued`. Neither card references any capacity field; both are outside the Phase 74 @if diffing scope."

### 17. Backend/frontend JSON contract match (structural, cross-subsystem)
expected: Backend emits `local_total`, `local_used`, `remote_total`, `remote_used` (snake_case); frontend parses the exact same four snake_case keys via `json.storage?.{key}`.
result: pass
evidence: "serialize_status.py emits constants `__KEY_STORAGE_LOCAL_TOTAL = \"local_total\"` etc.; server-status.ts fromJson reads `json.storage?.local_total`, `?.local_used`, `?.remote_total`, `?.remote_used`. Exact 4-for-4 snake_case match. Verified also by milestone-audit integration checker (report committed e96d765)."

## Summary

total: 17
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 6

## Gaps

[none — 11 structural tests pass via code inspection + unit-test runs; 6 runtime tests remain explicitly deferred per 74-CONTEXT.md §"Deferred Ideas" and design spec (SSH df unfakeable in E2E harness). All deferred items documented as manual-only in 74-VALIDATION.md.]
