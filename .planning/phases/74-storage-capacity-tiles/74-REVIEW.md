---
phase: 74-storage-capacity-tiles
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - src/python/common/status.py
  - src/python/web/serialize/serialize_status.py
  - src/python/tests/unittests/test_common/test_status.py
  - src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py
  - src/python/controller/scan/scanner_process.py
  - src/python/controller/scan/local_scanner.py
  - src/python/controller/scan/remote_scanner.py
  - src/python/controller/controller.py
  - src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py
  - src/python/tests/unittests/test_controller/test_controller_unit.py
  - src/python/tests/unittests/test_controller/test_controller.py
  - src/angular/src/app/services/server/server-status.ts
  - src/angular/src/app/services/files/dashboard-stats.service.ts
  - src/angular/src/app/tests/unittests/services/server/server-status.spec.ts
  - src/angular/src/app/tests/unittests/services/files/dashboard-stats.service.spec.ts
  - src/angular/src/app/pages/files/stats-strip.component.html
  - src/angular/src/app/pages/files/stats-strip.component.scss
  - src/angular/src/app/pages/files/stats-strip.component.ts
  - src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: re_reviewed
re_reviewed: 2026-04-19T00:00:00Z
re_review_depth: deep
re_review_findings:
  critical: 1   # CR-01 (FIXED)
  warning: 2    # WR-04, WR-05 (FIXED)
  medium: 3     # MD-01, MD-03 (FIXED) + MD-04 (NOTED)
  total: 6
re_review_resolved:
  - CR-01  # ActiveScanner contract restored
  - WR-01  # per-field gate split
  - WR-04  # @let dedup in stats-strip template
  - WR-05  # MockServerStatusService preserves prior status
  - MD-01  # ScannerResult.error_message Optional[str]
  - MD-03  # _parse_df_output input typed
---

# Phase 74: Code Review Report

**Reviewed:** 2026-04-19
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 74 adds disk-capacity awareness end-to-end: a new `Status.StorageStatus` component, a `df -B1` SSH call in `RemoteScanner`, `shutil.disk_usage` in `LocalScanner`, a `>1%` change gate in the controller, JSON serialisation, and a four-tile Angular dashboard strip.

The five focal points from the review brief were examined in detail:

- **T-74-05 (shlex.quote on df path):** Correctly applied at `remote_scanner.py:130`. The regression test in `TestRemoteScannerShleQuote` verifies the shell string contains single-quoted path. No issue.
- **T-74-06 (malformed df parser):** `_parse_df_output` is fully defensive: UTF-8 decode error, empty output, header-only, too few columns, and non-numeric columns are all silently handled and return `(None, None)`. No issue.
- **T-74-08 (>1% change gate):** Implemented in `_should_update_capacity` and applied per-side in `_update_controller_status`. Corner-cases (`old=None`, `old=0`) are handled correctly. Tests in `TestShouldUpdateCapacity` cover boundary values. No issue.
- **T-74-14 (divide-by-zero in template):** The `@if` guard on line 10/50 of the template checks `> 0` before any division expression is evaluated. The fallback progress bar uses a ternary guard `stats.totalTrackedBytes > 0 ? ... : 0`. No divide-by-zero exposure.

Three warnings and three info items were found, none of which are security vulnerabilities or logic-level crashes. The most actionable is a silent capacity-write asymmetry in the controller gate (WR-01) that could cause a stale `remote_used` value to persist after the gate is crossed on `total` alone.

---

## Warnings

### WR-01: Capacity gate writes both fields atomically even when only one crossed the 1% threshold

**File:** `src/python/controller/controller.py:651-654`
**Issue:** The `_update_controller_status` method evaluates `_should_update_capacity` for `total` and `used` independently with an `or`, but then writes **both** fields together. If only `total` crossed 1% while `used` did not, the new `used` value (which may have changed slightly) is written anyway — and vice-versa. This is a semantic inconsistency: the gate was described as a per-field noise filter, but the `or` makes it an "either triggers both" gate. In most real-world cases `total` is static and only `used` changes, so the asymmetry is benign, but the behaviour differs from what the gate comment and per-side independence claim (D-12/D-13/D-15).

**Current code:**
```python
if (Controller._should_update_capacity(old_total, remote_scan.total_bytes)
        or Controller._should_update_capacity(old_used, remote_scan.used_bytes)):
    self.__context.status.storage.remote_total = remote_scan.total_bytes
    self.__context.status.storage.remote_used = remote_scan.used_bytes
```

**Fix:** Write each field independently so the gate truly applies per-field:
```python
if Controller._should_update_capacity(old_total, remote_scan.total_bytes):
    self.__context.status.storage.remote_total = remote_scan.total_bytes
if Controller._should_update_capacity(old_used, remote_scan.used_bytes):
    self.__context.status.storage.remote_used = remote_scan.used_bytes
```
The same pattern applies to the local side at lines 659-663. If D-12/D-15 intend "pair writes" (total+used always together), the comment should say so and a paired-write test should be added.

---

### WR-02: `_parse_df_output` reads `lines[-1]` which may be the header row on some systems

**File:** `src/python/controller/scan/remote_scanner.py:43`
**Issue:** The parser takes the last non-empty line of `df` output, assuming it is the data row. On some remote filesystems (e.g. NFS mounts with long filesystem names that cause `df` to wrap), the last line may be a continuation of the header or a blank line from a different mount. The existing `len(lines) < 2` guard catches the zero/one-line case but not a multi-line header wrapping scenario. The current test suite only exercises a standard two-line output.

**Fix:** A more robust approach is to skip lines whose first field looks like a header (`Filesystem`) and take the first remaining data row rather than the last line. Alternatively, document the assumption explicitly and add a test for a wrapped header:
```python
# Skip header line by index rather than taking lines[-1]
data_line = next(
    (l for l in lines if not l.lower().startswith("filesystem")),
    None
)
if data_line is None:
    return (None, None)
parts = data_line.split()
```
The current code is silent-fallback anyway, so this is not catastrophic — it would just produce wrong capacity values for unusual `df` output shapes rather than `(None, None)`.

---

### WR-03: `StatusComponent.copy` bypasses Python's name-mangling for private attributes

**File:** `src/python/common/status.py:60`
**Issue:** The `copy` class method accesses private backing attributes using string concatenation:
```python
setattr(dst, "__" + prop, getattr(src, "__" + prop))
```
Python name-mangles double-underscore attributes relative to the class in which they are defined, so `__prop` on a `StatusComponent` subclass is actually stored as `_StatusComponent__prop` (or `_DummyStatusComponent__prop` depending on where the property was defined). The current implementation works because both `_create_property`'s `fget`/`fset` and `copy` use the same `"__" + name` string — they are all running outside the class body so mangling never applies. However, if a future subclass redefines `copy` inside the class body, or if a linter/refactoring tool changes the attribute storage convention, the string concatenation would silently break.

This is pre-existing, not new to Phase 74, but the `StorageStatus` class is the first new component that exercises the `copy` path in `test_storage_copy_preserves_values`. The test passes, confirming the current approach works, but the fragility is worth noting.

**Fix:** Add a comment documenting why `"__" + name` is correct here (name mangling only applies inside a class body) so future contributors do not "fix" it:
```python
# NOTE: Name mangling (__attr -> _ClassName__attr) only applies inside a class
# body. At module scope "__" + name is a literal string, which is what
# _create_property's fget/fset also use — so this intentional.
setattr(dst, "__" + prop, getattr(src, "__" + prop))
```

---

## Info

### IN-01: `TestUpdateControllerStatusCapacity.test_sub_one_percent_delta_is_skipped` does not distinguish total vs. used retention

**File:** `src/python/tests/unittests/test_controller/test_controller.py:71-75`
**Issue:** This test verifies that a sub-1% delta on both fields is suppressed, but it uses the same assertion for `remote_total` and `remote_used`. Because of the `or`-based gate (WR-01), if only one field crosses 1%, the test would still pass (both get written anyway). Adding a test where `used` crosses 1% while `total` does not would lock down the intended behaviour and expose the WR-01 asymmetry:
```python
def test_only_used_crosses_threshold_still_writes_both_under_current_or_gate(self):
    c = self._make_controller_with_status()
    c._update_controller_status(self._result(2_000_000_000_000, 1_000_000_000_000), None)
    # total: +0.005% (below gate), used: +1.5% (above gate)
    c._update_controller_status(self._result(2_000_010_000_000, 1_015_000_000_000), None)
    # Under the current `or` implementation, both are written:
    self.assertEqual(2_000_010_000_000, c._Controller__context.status.storage.remote_total)
    self.assertEqual(1_015_000_000_000, c._Controller__context.status.storage.remote_used)
```

---

### IN-02: `ServerStatusJson.storage` is typed `optional` but downstream code does not guard against a missing `controller` key

**File:** `src/angular/src/app/services/server/server-status.ts:74`
**Issue:** `storage` is correctly typed as `storage?: { ... }` and `fromJson` uses optional chaining (`json.storage?.local_total ?? null`). However, the `controller` and `server` sub-objects are typed as required — if a legacy or malformed backend payload omits them, `json.controller.latest_local_scan_time` would throw a TypeError at runtime. This is not new to Phase 74, but the Phase 74 code introduced the `storage?` optional pattern and only applied it to the storage block. Making `controller` and `server` optional (or adding nullish guards) would make the parser consistently defensive.

---

### IN-03: Inline template duplication in `stats-strip.component.spec.ts`

**File:** `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts:8-112`
**Issue:** The spec file contains a verbatim copy of the production template (`STATS_STRIP_TEMPLATE`, 105 lines) used with `overrideTemplate`. A comment explains this avoids html/scss loader issues in Karma. While this is a pragmatic workaround, it means template changes must be mirrored in the spec manually — a common source of stale tests. Consider using `NO_ERRORS_SCHEMA` for simpler unit tests and reserving full template rendering for integration/e2e tests, or evaluating whether the Karma loader issue can be resolved so the real template is imported directly.

---

_Reviewed: 2026-04-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

# Phase 74: Re-Review (Deep, 2026-04-19)

**Re-reviewer:** Claude (deep-review skill)
**Scope:** 22 files (Phase 74 source + tests + downstream consumers)
**New findings:** 1 critical, 2 warning, 3 medium
**Status:** all blocking findings resolved

## CR-01: `ActiveScanner.scan()` violates new `IScanner` tuple contract — production crash on every active-scan cycle (FIXED)

**Files:** `src/python/controller/scan/active_scanner.py:34-52`, `src/python/controller/scan/scanner_process.py:90`

Phase 74-02 widened `IScanner.scan()` to return `Tuple[List[SystemFile], Optional[int], Optional[int]]` and updated `ScannerProcess.run_loop` to unpack three values. `RemoteScanner` and `LocalScanner` were updated, but `ActiveScanner` was missed. Since `ScanManager` wraps all three scanners in `ScannerProcess` instances, every active-scan tick would raise `ValueError: not enough values to unpack` (when the active-files list has 0/1/2/4+ entries) or — at exactly 3 active files — silently assign `SystemFile` instances to `total_bytes`/`used_bytes`, propagating into `Controller._should_update_capacity` as a `TypeError`.

Missed by the standard review because all five focal points were spec-internal; cross-implementation contract was not audited.

**Resolution:** `ActiveScanner.scan()` now returns `(result, None, None)`. `DummyScanner` test mock and the `_scan` lambda in `test_scanner_process.py` updated to match. New `TestIScannerContract::test_active_scanner_returns_three_tuple` regression test added.

## WR-01: Capacity gate writes both fields even when only one crossed 1% (RESOLVED — carried over from initial review)

**File:** `src/python/controller/controller.py:649-666`

The `or`-gate split into per-field `if`s (both remote and local sides). Two new locking tests added in `test_controller.py`:

- `test_used_crosses_threshold_total_does_not_writes_only_used`
- `test_total_crosses_threshold_used_does_not_writes_only_total`

Pre-existing `test_above_one_percent_delta_writes_both` repurposed to use deltas that cross 1% on both fields (matches new correct semantic).

## WR-04: Stats-strip template repeats `used / total * 100` four times per tile (FIXED)

**File:** `src/angular/src/app/pages/files/stats-strip.component.html:11-26, 51-66`

Each capacity-mode tile evaluated the percentage expression four times across class bindings, width binding, and display. Risk: a future refactor narrowing one expression but not the others (e.g., changing `< 80` to `<= 80` in only one binding) would silently desync threshold colors from width.

**Resolution:** Used Angular `@let remotePct = ...` / `@let localPct = ...` declarations at the top of each capacity-mode block; all bindings now reference the single computed value. Inlined test template in `stats-strip.component.spec.ts` updated to match.

## WR-05: `MockServerStatusService.pushStatus` silently resets `server` and `controller` blocks to defaults (FIXED)

**File:** `src/angular/src/app/tests/unittests/services/files/dashboard-stats.service.spec.ts:18-30`

The helper called `new ServerStatus({storage})` which reset all other fields to defaults. If a future change makes `DashboardStatsService` derive any signal from `status.server.up` or `status.controller.latestRemoteScanFailed`, the tests would silently render against `up: false` rather than the values the test author intended.

**Resolution:** `pushStatus` now reads the current `BehaviorSubject` value and carries `server`/`controller` forward. Class also adds `implements Pick<ServerStatusService, "status">` to constrain the structural contract.

## MD-01: `ScannerResult.error_message` typed `str = None` rather than `Optional[str] = None` (FIXED)

**File:** `src/python/controller/scan/scanner_process.py:46`

Pre-existing inconsistency that Phase 74's new `Optional[int]` annotations highlighted. Tightened to `Optional[str] = None` while in the area.

## MD-03: `_parse_df_output(out)` accepted any input type (FIXED)

**File:** `src/python/controller/scan/remote_scanner.py:31`

Annotated as `out: Union[bytes, str]` (kept `Union` form for consistency with the rest of the file's `typing`-style annotations).

## MD-04: Per-field gate split may emit up to 2 SSE notifications per scan with one transient mixed frame (NOTED, no action)

**File:** `src/python/controller/controller.py:649-666`

Each `StatusComponent._set_property` call fires the listener chain synchronously. After WR-01's split, when both fields cross the gate the controller still fires twice in succession (no regression vs. the old paired write), but an attentive SSE client may briefly see `Status` with the new `remote_total` and the old `remote_used` (between the two `if`s). Sub-millisecond, harmless given the ≥1% gate's coarse precision.

**Recommendation:** leave as-is. Per-field correctness wins. If SSE volume becomes observable, batch both writes via a `StorageStatus.update_pair()` method that suspends notifications until both fields are set.

## Carry-over status from initial standard review

| Finding | Status |
|---------|--------|
| WR-01 (atomic-pair gate) | RESOLVED |
| WR-02 (`df` last-line robustness) | UNCHANGED — silent-fallback-safe per D-16 |
| WR-03 (`StatusComponent.copy` name-mangling comment) | UNCHANGED — pre-existing, non-blocking |
| IN-01 (test for asymmetric gate) | SUPERSEDED — two locking tests added in `test_controller.py` |
| IN-02 (controller/server optional typing in DTO) | UNCHANGED — pre-existing API |
| IN-03 (template inline duplication in spec) | UNCHANGED — pragmatic Karma workaround |

## Verification

- 188 Python tests pass: `test_controller`, `test_remote_scanner`, `test_status`, `test_serialize_status`, `test_controller_unit`, `TestIScannerContract`.
- 47 Angular tests pass: `dashboard-stats.service.spec`, `server-status.spec`, `stats-strip.component.spec`.
- `ng build` (development) succeeds with only pre-existing Sass deprecation warnings.
- 3 macOS-only `MagicMock` pickling failures in `test_scanner_process.py` are pre-existing platform issues (Python 3.9 `spawn` start method) and would pass in CI's Linux env.

_Re-reviewed: 2026-04-19_
_Reviewer: Claude (deep-review skill)_
_Depth: deep_
