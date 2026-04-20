# Phase 74: Storage Capacity Tiles - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 9 (4 backend, 5 frontend, plus tests)
**Analogs found:** 9 / 9 (all exact or role-match in-repo)

All targets have strong, in-repo analogs. No "no-analog" cases — this phase is a pure composition over existing patterns (`StatusComponent`, `Sshcp.shell`, `combineLatest`, `FileSizePipe`, `stat-progress-fill`).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/common/status.py` (extend `Status`) | model | event-driven (property notify) | `Status.ServerStatus` / `Status.ControllerStatus` in same file | exact |
| `src/python/web/serialize/serialize_status.py` (extend `status()`) | serializer | transform | existing `SerializeStatusJson.status()` in same file | exact |
| `src/python/controller/scan/local_scanner.py` (capacity hook) | scanner / service | file-I/O | existing `LocalScanner.scan()` in same file | exact-role |
| `src/python/controller/scan/remote_scanner.py` (capacity hook) | scanner / service | SSH request-response | `DeleteRemoteProcess.run_once()` (SSH call shape) + `RemoteScanner.scan()` (same file SSH idiom) | exact |
| `src/python/controller/controller.py` (`_update_controller_status`) | orchestrator | event-driven | `_update_controller_status()` at line 620-635 in same file | exact |
| `src/angular/src/app/services/server/server-status.ts` | model / DTO | transform (snake→camel) | existing `controller` block `fromJson` in same file | exact |
| `src/angular/src/app/services/files/dashboard-stats.service.ts` | service (rxjs) | combineLatest merge | `transfer-table.component.ts:98-116` (`combineLatest` of two streams) | exact |
| `src/angular/src/app/pages/files/stats-strip.component.html` | component template | request-response (async pipe) | existing Remote/Local card blocks in same file, lines 14-20 (progress) | exact |
| `src/angular/src/app/pages/files/stats-strip.component.scss` | styles | — | existing `.stat-progress-fill--amber` / `.stat-progress-fill--secondary` modifiers in same file, lines 130-142 | exact |
| `src/python/tests/unittests/test_common/test_status.py` (add `StorageStatus` tests) | test | — | existing `TestStatusComponent` in same file | exact |
| `src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py` (extend) | test | — | existing `test_controller_status_*` in same file | exact |
| `src/angular/src/app/tests/unittests/services/server/server-status.spec.ts` (extend) | test | — | existing `controller` block assertions in same file | exact |
| `src/angular/src/app/tests/unittests/services/files/dashboard-stats.service.spec.ts` (extend) | test | — | existing `should compute remote and local tracked bytes` in same file | exact |
| `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts` (extend) | test | — | existing MockDashboardStatsService in same file | exact |

---

## Pattern Assignments

### `src/python/common/status.py` — add `StorageStatus` component (model, event-driven)

**Analog:** Same file, lines 105-140 (`ServerStatus`, `ControllerStatus`, and their registration in `Status.__init__`).

**Component-class pattern to copy** (lines 105-125):
```python
class ServerStatus(StatusComponent):
    up = StatusComponent._create_property("up")
    error_msg = StatusComponent._create_property("error_msg")

    def __init__(self):
        super().__init__()
        self.up = True
        self.error_msg = None

class ControllerStatus(StatusComponent):
    latest_local_scan_time = StatusComponent._create_property("latest_local_scan_time")
    latest_remote_scan_time = StatusComponent._create_property("latest_remote_scan_time")
    latest_remote_scan_failed = StatusComponent._create_property("latest_remote_scan_failed")
    latest_remote_scan_error = StatusComponent._create_property("latest_remote_scan_error")

    def __init__(self):
        super().__init__()
        self.latest_local_scan_time = None
        self.latest_remote_scan_time = None
        self.latest_remote_scan_failed = None
        self.latest_remote_scan_error = None
```

**Registration pattern to copy** (lines 129-140):
```python
# Component registration
server = BaseStatus._create_property("server")
controller = BaseStatus._create_property("controller")

def __init__(self):
    self._listeners = []
    self._listeners_lock = Lock()
    self.__comp_listener = Status.CompListener(self)

    # Component initialization
    self.server = self.__create_component(Status.ServerStatus)
    self.controller = self.__create_component(Status.ControllerStatus)
```

**Apply to `StorageStatus`:**
- Inner-class name: `StorageStatus` (between `ControllerStatus` and the `# ----- End of component definition -----` marker).
- Four properties via `StatusComponent._create_property(…)`: `local_total`, `local_used`, `remote_total`, `remote_used`.
- `__init__` assigns each to `None` (spec `(total, used)` is nullable by design).
- Register as `storage = BaseStatus._create_property("storage")` next to `controller` (line 131).
- Initialize in `Status.__init__` via `self.storage = self.__create_component(Status.StorageStatus)` next to the `self.controller = …` line (line 140).

**No changes to `CompListener`, `copy()`, or listener locking** — all inherited automatically.

---

### `src/python/web/serialize/serialize_status.py` — extend `SerializeStatusJson.status()`

**Analog:** Same file, lines 17-40 (current `status()` method emitting `server` + `controller` blocks).

**Pattern to copy** (lines 27-37):
```python
json_dict[SerializeStatusJson.__KEY_CONTROLLER] = dict()
json_dict[SerializeStatusJson.__KEY_CONTROLLER][SerializeStatusJson.__KEY_CONTROLLER_LATEST_LOCAL_SCAN_TIME] = \
    str(status.controller.latest_local_scan_time.timestamp()) \
        if status.controller.latest_local_scan_time else None
…
json_dict[SerializeStatusJson.__KEY_CONTROLLER][SerializeStatusJson.__KEY_CONTROLLER_LATEST_REMOTE_SCAN_FAILED] = \
    status.controller.latest_remote_scan_failed
```

**Apply to `storage` block:**
- Add private key constants at the top of the class next to the existing `__KEY_*` constants:
  - `__KEY_STORAGE = "storage"`
  - `__KEY_STORAGE_LOCAL_TOTAL = "local_total"`
  - `__KEY_STORAGE_LOCAL_USED = "local_used"`
  - `__KEY_STORAGE_REMOTE_TOTAL = "remote_total"`
  - `__KEY_STORAGE_REMOTE_USED = "remote_used"`
- Under `status()`, after the controller block, create `json_dict[__KEY_STORAGE] = dict()` and populate four entries straight from `status.storage.*` (plain int-or-None passthrough — no `str(…)` wrap, unlike timestamps; byte counts are numeric).
- Backward-compat note: existing tests construct `Status()` and expect no breakage; all four storage fields default to `None`, so new keys serialize as `null` — the existing `test_event_names` and `test_server_status_*` tests keep passing.

---

### `src/python/controller/scan/local_scanner.py` and `remote_scanner.py` — wire capacity collection

**Analog (SSH call shape):** `src/python/controller/delete/delete_process.py:37-48` — canonical `Sshcp` + `shlex.quote` + try/except-`SshcpError` pattern:
```python
self.__ssh = Sshcp(host=remote_address,
                   port=remote_port,
                   user=remote_username,
                   password=remote_password)
…
try:
    out = self.__ssh.shell("rm -rf {}".format(shlex.quote(file_path)))
    self.logger.debug("Remote delete output: {}".format(out.decode()))
except SshcpError:
    self.logger.exception("Exception while deleting remote file")
```

**Analog (same-file SSH call with output parsing):** `remote_scanner.py:60-102` — already uses `self.__ssh.shell(…)` + `shlex.quote(...)` + catches `SshcpError` + parses bytes output with a `try/except` guard:
```python
try:
    out = self.__ssh.shell("{} {}".format(
        shlex.quote(self.__remote_path_to_scan_script),
        shlex.quote(self.__remote_path_to_scan))
    )
except SshcpError as e:
    …
try:
    out_str = out.decode('utf-8') if isinstance(out, bytes) else out
    file_dicts = json.loads(out_str)
    …
except (json.JSONDecodeError, KeyError, TypeError, ValueError) as err:
    self.logger.error("JSON decode error: {}\n{}".format(str(err), out))
    raise ScannerError(…)
```

**Apply to Phase 74 (local):** In `LocalScanner.scan()` (lines 22-29), after `self.__scanner.scan()` succeeds, call `shutil.disk_usage(self.__local_path)` where `self.__local_path` is plumbed in through `__init__` (currently the scanner only receives it via `SystemScanner(local_path)` — expose it as `self.__local_path = local_path` so `scan()` can reuse it for `disk_usage`). Return the `(total, used)` alongside the file list — see "Plumbing decision" below.

**Apply to Phase 74 (remote):** In `RemoteScanner.scan()`, after the main `scan` shell call succeeds, issue a second `self.__ssh.shell("df -B1 {}".format(shlex.quote(self.__remote_path_to_scan)))`. Wrap in its own `try/except SshcpError` + parse-error `try/except`. On *any* failure (SSH or parse), **log at WARN and return `(None, None)`** for capacity — per D-16 silent-fallback rule. Do not raise; the scan result itself is still good.

**`df -B1` parse pattern** (Claude's discretion per CONTEXT.md):
- Output shape: `Filesystem 1B-blocks Used Available Use% Mounted on\n/dev/sda1 1999999488 123456789 …`
- Strategy: split on newlines, take last non-empty line, `split()`, index 1 = total, index 2 = used. Wrap in `try/except (IndexError, ValueError)` → log WARN + return `(None, None)`.
- Do NOT raise `ScannerError` for `df` failures — it's non-critical ancillary data.

**Plumbing decision (Claude's discretion per CONTEXT.md D-14/D-15):** Extend `ScannerResult` (or add a parallel result type) with nullable `total_bytes` / `used_bytes`, populate in `ScannerProcess.run_loop()` (lines 83-94 of `scanner_process.py`), then surface into `Status.StorageStatus` in `controller.py:_update_controller_status()` alongside the existing `latest_*` writes. **The planner should pick between (a) widening `ScannerResult` vs (b) adding a separate capacity field on `ScannerResult` — both are spec-compliant.** The >1% gate lives in `_update_controller_status` before assigning to `self.__context.status.storage.*`.

---

### `src/python/controller/controller.py` — extend `_update_controller_status`

**Analog:** Same file, lines 620-635:
```python
def _update_controller_status(self,
                              remote_scan: Optional[ScannerResult],
                              local_scan: Optional[ScannerResult]) -> None:
    if remote_scan is not None:
        self.__context.status.controller.latest_remote_scan_time = remote_scan.timestamp
        self.__context.status.controller.latest_remote_scan_failed = remote_scan.failed
        self.__context.status.controller.latest_remote_scan_error = remote_scan.error_message
    if local_scan is not None:
        self.__context.status.controller.latest_local_scan_time = local_scan.timestamp
```

**Apply to Phase 74:** After each existing block, add capacity assignment guarded by the >1% change gate:
```python
if remote_scan is not None and remote_scan.total_bytes is not None:
    if self.__should_update_capacity(self.__context.status.storage.remote_total, remote_scan.total_bytes) \
       or self.__should_update_capacity(self.__context.status.storage.remote_used, remote_scan.used_bytes):
        self.__context.status.storage.remote_total = remote_scan.total_bytes
        self.__context.status.storage.remote_used = remote_scan.used_bytes
```

Where `__should_update_capacity(old, new)` returns `True` if `old is None` or the ratio delta exceeds 1% (spec-mandated gate, per D-12/D-13). Same pattern mirrored for local. Per-side independence (D-15) — `remote_*` failure does not touch `local_*` assignments and vice versa.

**No error_msg plumbing** per D-16 — silent fallback only logs at WARN inside the scanner.

---

### `src/angular/src/app/services/server/server-status.ts` — extend `IServerStatus` + `ServerStatusJson`

**Analog:** Same file, lines 6-77 — mirror the `controller` block's structure verbatim for the `storage` block.

**Interface extension pattern** (lines 6-30):
```typescript
interface IServerStatus {
    server: { up: boolean; errorMessage: string; };
    controller: {
        latestLocalScanTime: Date | null;
        latestRemoteScanTime: Date | null;
        latestRemoteScanFailed: boolean;
        latestRemoteScanError: string;
    };
}
const DefaultServerStatus: IServerStatus = {
    server: { up: false, errorMessage: "" },
    controller: {
        latestLocalScanTime: null,
        latestRemoteScanTime: null,
        latestRemoteScanFailed: false,
        latestRemoteScanError: ""
    }
};
```

**`fromJson` snake→camel pattern** (lines 52-77):
```typescript
return new ServerStatus({
    server: {
        up: json.server.up,
        errorMessage: json.server.error_msg
    },
    controller: {
        latestLocalScanTime: latestLocalScanTime,
        …
        latestRemoteScanError: json.controller.latest_remote_scan_error
    }
});
```

**JSON DTO pattern** (lines 84-96):
```typescript
export interface ServerStatusJson {
    server: { up: boolean; error_msg: string; };
    controller: {
        latest_local_scan_time: string;
        latest_remote_scan_time: string;
        latest_remote_scan_failed: boolean;
        latest_remote_scan_error: string;
    };
}
```

**Apply to Phase 74:**
- `IServerStatus`: add `storage: { localTotal: number | null; localUsed: number | null; remoteTotal: number | null; remoteUsed: number | null; }`.
- `DefaultServerStatus.storage`: all four `null`.
- `ServerStatus` class: add `storage!: { … }` declaration to match (mirror the `controller!: { … }` block, lines 38-43).
- `fromJson`: add a `storage` block that maps `json.storage.local_total` → `localTotal`, etc. Each field maps with a `?? null` guard in case backend emits `undefined` during rollout. No `new Date(…)` transform — pure numeric passthrough.
- `ServerStatusJson`: add `storage: { local_total: number | null; local_used: number | null; remote_total: number | null; remote_used: number | null; }`.

**Backward-compat note:** The `ServerStatusService.parseStatus()` consumer and the `DefaultServerStatus` connection-waiting initializer in `server-status.service.ts:14-20` don't need changes — `storage` defaults to all-null via the Record default.

---

### `src/angular/src/app/services/files/dashboard-stats.service.ts` — add capacity fields + `combineLatest` merge

**Analog (same-pattern combineLatest in same project):** `src/angular/src/app/pages/files/transfer-table.component.ts:98-116`:
```typescript
const segmentedFiles$ = combineLatest([
    this.viewFileService.filteredFiles,
    this.filterState$.pipe(
        map(s => ({segment: s.segment, subStatus: s.subStatus})),
        distinctUntilChanged((a, b) => a.segment === b.segment && a.subStatus === b.subStatus)
    )
]).pipe(
    map(([files, state]) => { … }),
    shareReplay(1)
);
```

**Current pattern to replace** (`dashboard-stats.service.ts:45-79`):
```typescript
constructor(private viewFileService: ViewFileService) {
    this.viewFileService.files
        .pipe(takeUntil(this.destroy$))
        .subscribe(files => { … });
}
```

**Apply to Phase 74:**
- Add fields to `DashboardStats` (lines 12-20):
  ```typescript
  remoteCapacityTotal: number | null;
  remoteCapacityUsed: number | null;
  localCapacityTotal: number | null;
  localCapacityUsed: number | null;
  ```
- Mirror in `ZERO_STATS` (lines 22-30) — all four `null` (NOT `0`, per D-14 cold-load rule: fallback to tracked-bytes until a non-null pair arrives).
- Constructor: inject `ServerStatusService` alongside `ViewFileService`. Replace the bare `.files.subscribe(…)` with:
  ```typescript
  combineLatest([this.viewFileService.files, this.serverStatusService.status])
      .pipe(takeUntil(this.destroy$))
      .subscribe(([files, status]) => {
          // existing files-derived computation stays as-is
          // then read four capacity values from status.storage.*
      });
  ```
- Both sides (`files` change alone + `status` change alone) trigger a re-emit; the previous value of the other stream is retained by `combineLatest`'s buffering — this satisfies the spec's "file list change preserves capacity / status change preserves counts" test requirement.
- Peak-speed reset logic (lines 55-60) is unchanged.

---

### `src/angular/src/app/pages/files/stats-strip.component.html` — capacity branch per tile

**Analog:** Same file, lines 3-21 (Remote Storage card) and lines 23-41 (Local Storage card). The existing fallback markup is preserved verbatim for the `else` branch.

**Progress-bar pattern to mirror** (lines 14-20):
```html
<div class="stat-progress-wrap">
  <div class="stat-progress-track">
    <div class="stat-progress-fill stat-progress-fill--amber"
         [style.width.%]="stats.totalTrackedBytes > 0 ? (stats.remoteTrackedBytes / stats.totalTrackedBytes * 100) : 0">
    </div>
  </div>
</div>
```

**Sub-line pattern to mirror** (lines 54, Download Speed `Peak:` line):
```html
<div class="stat-sub">Peak: {{ stats.peakSpeedBps | fileSize:1 }}/s</div>
```

**Apply to Phase 74 — Remote tile:**
```html
<div class="stat-card">
  <div class="stat-watermark"><i class="fa fa-cloud"></i></div>
  <div class="stat-header">
    <i class="fa fa-cloud stat-icon stat-icon--amber"></i>
    <span class="stat-label">Remote Storage</span>
  </div>
  @if (stats.remoteCapacityTotal !== null && stats.remoteCapacityUsed !== null) {
    <!-- Capacity branch (D-01/D-02/D-05/D-06/D-07) -->
    <div class="stat-value-row">
      <span class="stat-value">{{ (stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) | number:'1.0-0' }}%</span>
      <span class="stat-unit">of {{ stats.remoteCapacityTotal | fileSize:2 }}</span>
    </div>
    <div class="stat-progress-wrap">
      <div class="stat-progress-track">
        <div class="stat-progress-fill"
             [class.stat-progress-fill--amber]="(stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) < 80"
             [class.stat-progress-fill--warning]="(stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) >= 80 && (stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) < 95"
             [class.stat-progress-fill--danger]="(stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100) >= 95"
             [style.width.%]="stats.remoteCapacityUsed / stats.remoteCapacityTotal * 100">
        </div>
      </div>
    </div>
    <div class="stat-sub">{{ stats.remoteCapacityUsed | fileSize:2 }} used</div>
  } @else {
    <!-- Fallback branch — preserve lines 10-20 verbatim -->
    <div class="stat-value-row">
      <span class="stat-value">{{ stats.remoteTrackedBytes | fileSize:2:'value' }}</span>
      <span class="stat-unit">{{ stats.remoteTrackedBytes | fileSize:2:'unit' }} Tracked</span>
    </div>
    <div class="stat-progress-wrap">
      <div class="stat-progress-track">
        <div class="stat-progress-fill stat-progress-fill--amber"
             [style.width.%]="stats.totalTrackedBytes > 0 ? (stats.remoteTrackedBytes / stats.totalTrackedBytes * 100) : 0">
        </div>
      </div>
    </div>
  }
</div>
```

**Apply to Local tile:** same structure, swap `remoteCapacity*` → `localCapacity*`, swap `stat-progress-fill--amber` (base) → `stat-progress-fill--secondary` in the Local capacity branch (to match the current local tile's base color). Warning and danger classes are color-family-agnostic and apply identically to both sides (D-10).

**Threshold-placement discretion:** the inline `(x/y*100) >= 80` expressions duplicate the percentage calc four times. Planner may refactor into a `remoteCapacityState`/`localCapacityState` derived field (`'normal' | 'warn' | 'danger'`) on `DashboardStats` per CONTEXT.md's Claude's Discretion note.

**Number pipe dependency:** add `DecimalPipe` to `StatsStripComponent.imports` alongside existing `AsyncPipe, FileSizePipe` — the `number:'1.0-0'` pipe requires it.

---

### `src/angular/src/app/pages/files/stats-strip.component.scss` — add warning/danger fill modifiers

**Analog:** Same file, lines 130-142:
```scss
.stat-progress-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease;

  &--amber {
    background: #c49a4a;
  }

  &--secondary {
    background: #9aaa8a;
  }
}
```

**Apply to Phase 74** (add alongside existing modifiers; D-10/D-11 mandate reusing Bootstrap `warning` / `danger` semantic colors — no new design tokens):
```scss
&--warning {
  background: var(--bs-warning, #ffc107);
}

&--danger {
  background: var(--bs-danger, #dc3545);
}
```

**Adjacent precedent for semantic Bootstrap tokens in this codebase:** `badge-failed` styling referenced in CONTEXT.md uses the same `danger`-family color. `$font-family-monospace` already imported from `common/common` (line 1) shows the same Bootstrap-variable-consumption pattern exists here.

**Keep alongside existing `--amber` and `--secondary` rules** (the fallback branch still uses those). Do NOT scope to a new `.stat-progress-fill--capacity` parent selector — the discretion note permits either, but a flat modifier is simpler and matches the existing `--amber`/`--secondary` convention.

---

## Shared Patterns

### Thread-safe property + listener infrastructure (BACKEND)
**Source:** `src/python/common/status.py:33-70` (`StatusComponent` base class — `_create_property`, copy-under-lock notify pattern).
**Apply to:** `StorageStatus` — inherits automatically; no changes to this code.
**Excerpt:**
```python
class StatusComponent(BaseStatus):
    def __init__(self):
        self.__listeners = []
        self.__listeners_lock = Lock()
        self.__properties = []

    @overrides(BaseStatus)
    def _set_property(self, name: str, value: Any):
        super()._set_property(name, value)
        with self.__listeners_lock:
            listeners = list(self.__listeners)
        for listener in listeners:
            listener.notify(name)
```
Setting any of the four new `storage.*` properties fires the existing `CompListener` → `Status._listeners` chain → `StatusStreamHandler` SSE push. Zero new plumbing.

### SSH shell + `shlex.quote` + `SshcpError` try/except (BACKEND)
**Source:** `src/python/controller/delete/delete_process.py:37-48` and `src/python/controller/scan/remote_scanner.py:66-88`.
**Apply to:** remote `df -B1` invocation.
**Rule:** every user-controlled path passed into an SSH command MUST be wrapped in `shlex.quote(…)`. `config.lftp.remote_path` is user-controlled → quote it.

### Silent fallback + WARN log (Phase 73 precedent, applied cross-cuttingly)
**Source:** Phase 73 URL-param fallback pattern (per CONTEXT.md).
**Apply to:** `df` SSH errors and `df` output parse errors in `RemoteScanner`.
**Rule:**
- Catch `SshcpError` and parse exceptions (`IndexError`, `ValueError`, `UnicodeDecodeError`).
- `self.logger.warning(f"df capacity collection failed: {err}")` — log at WARN.
- Return `(None, None)` for capacity.
- Do NOT raise `ScannerError`.
- Do NOT surface via `Status.ServerStatus.error_msg`.
- Next scan cycle is a free retry — no retry-within-call plumbing (per deferred list in CONTEXT.md).

### `combineLatest` multi-stream merge with `takeUntil` cleanup (FRONTEND)
**Source:** `src/angular/src/app/pages/files/transfer-table.component.ts:98-116, 141-152`.
**Apply to:** `DashboardStatsService` constructor, replacing `viewFileService.files.subscribe(…)`.
**Rule:** when a derived stream depends on two or more upstream streams, use `combineLatest([a$, b$]).pipe(takeUntil(destroy$)).subscribe(…)`. This gives the correct "either stream change re-emits with the other's last value" semantics required by D-15 (per-tile independence) and spec (file list change preserves capacity).

### `FileSizePipe` for byte → human formatting (FRONTEND)
**Source:** already used throughout `stats-strip.component.html` (e.g., line 11 `{{ stats.remoteTrackedBytes | fileSize:2:'value' }}`).
**Apply to:** both tiles' "of X.XX TB" (D-06) and "XXX.XX GB used" (D-07).
**Rule:** pass raw bytes; pipe auto-scales and formats. Use precision `2`. Use the `'value'` and `'unit'` format args when splitting value+unit into two spans, or the default (combined) when rendering a single string like `"120.50 GB used"`.

### Angular `@if` / `@else` control flow for per-tile fallback
**Source:** `stats-strip.component.html:1` (existing `@if (stats$ | async; as stats) { … }` outer wrapper) — the project is already on Angular's new control-flow syntax.
**Apply to:** the per-tile capacity vs tracked-bytes branch.
**Rule:** each tile evaluates its own `stats.<side>CapacityTotal !== null && stats.<side>CapacityUsed !== null` guard independently (D-15). No cross-tile coupling.

---

## Test Patterns

### Backend — `StorageStatus` unit tests
**Analog:** `src/python/tests/unittests/test_common/test_status.py:30-55` (`TestStatusComponent.test_property_values`, `test_listeners`).
**Apply:** write `TestStorageStatus` (or fold into existing `TestStatus`) mirroring the property-set + listener-notify assertions. Use `MagicMock()` for the listener per the existing pattern.

### Backend — `SerializeStatusJson.status()` storage-block tests
**Analog:** `src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py:75-97` (`test_controller_status_latest_remote_scan_failed`, `test_controller_status_latest_remote_scan_error`).
**Apply:** copy shape exactly — one test per field, asserting `None` default and asserting numeric passthrough after setting.
```python
def test_storage_remote_total(self):
    serialize = SerializeStatus()
    status = Status()
    out = parse_stream(serialize.status(status))
    data = json.loads(out["data"])
    self.assertIsNone(data["storage"]["remote_total"])

    status.storage.remote_total = 2_000_000_000_000
    out = parse_stream(serialize.status(status))
    data = json.loads(out["data"])
    self.assertEqual(2_000_000_000_000, data["storage"]["remote_total"])
```

### Backend — `df -B1` parser unit tests
**Analog:** no existing parse tests for SSH output — closest is `remote_scanner.py`'s JSON-decode guard. New tests should be standalone (parser function extracted for testability). Test cases: happy path (typical `df -B1` output), malformed output (missing lines), empty output, non-numeric size values. All must return `(None, None)` on failure and log WARN (assert via caplog).

### Frontend — `ServerStatus.fromJson` storage tests
**Analog:** `src/angular/src/app/tests/unittests/services/server/server-status.spec.ts:38-51` (`should correctly initialize controller latest local scan time` — including the null-allowed override pattern).
**Apply:** mirror that pattern for each of the four storage fields; verify null default, numeric round-trip, and missing-key graceful handling.

### Frontend — `DashboardStatsService.combineLatest` merge tests
**Analog:** `src/angular/src/app/tests/unittests/services/files/dashboard-stats.service.spec.ts:185-212` (`should compute remote and local tracked bytes from all files` — TestBed setup + `_files.next(model)` + `tick()` + assertion pattern).
**Apply:** new spec cases (pattern for the planner):
- Status-stream emits a non-null `storage` payload → `remoteCapacityTotal` matches.
- File-list emits with no status change → capacity fields preserved (combineLatest semantics).
- Status emits with no file-list change → counts preserved.
- Both-null status → all four capacity fields stay `null` (cold-load fallback per D-14).
- **Test setup change:** the beforeEach `providers` array (lines 20-30) must add `ServerStatusService` (or a `MockServerStatusService`) since the service is now injected into `DashboardStatsService`.

### Frontend — `StatsStripComponent` threshold rendering tests
**Analog:** `src/angular/src/app/tests/unittests/pages/files/stats-strip.component.spec.ts:67-80` (`MockDashboardStatsService` with `BehaviorSubject<DashboardStats>`).
**Apply:** extend `MockDashboardStatsService` default to include the four capacity fields (all `null`). Add test cases for:
- Fallback mode: `remoteCapacityTotal = null` → old tracked-bytes markup rendered.
- Capacity mode normal: e.g., `total = 1000`, `used = 500` → `50%` rendered, `stat-progress-fill--amber` class on fill.
- Capacity mode warning boundary: `used = 800` → `80%` rendered, `stat-progress-fill--warning` class applied.
- Capacity mode danger boundary: `used = 950` → `95%` rendered, `stat-progress-fill--danger` class applied.
- Per-tile independence: `remoteCapacityTotal = null, localCapacityTotal = 1000, localCapacityUsed = 500` → Remote renders fallback, Local renders capacity.
- Test the 79/80 and 94/95 exact boundaries per CONTEXT.md test checklist.

**E2E:** no new E2E per CONTEXT.md — existing Phase 72/73 dashboard E2E must continue to pass with the new null-default `storage` block in the status JSON.

---

## No Analog Found

*None.* Every file in this phase has a strong in-repo analog.

---

## Metadata

**Analog search scope:**
- `src/python/common/status.py`
- `src/python/web/serialize/serialize_status.py`
- `src/python/controller/controller.py`
- `src/python/controller/scan_manager.py`
- `src/python/controller/scan/{local_scanner,remote_scanner,scanner_process}.py`
- `src/python/controller/delete/delete_process.py`
- `src/angular/src/app/services/server/{server-status.ts,server-status.service.ts}`
- `src/angular/src/app/services/files/dashboard-stats.service.ts`
- `src/angular/src/app/pages/files/{stats-strip,transfer-table}.component.*`
- `src/angular/src/app/tests/unittests/**` (spec files)
- `src/python/tests/unittests/test_common/test_status.py`
- `src/python/tests/unittests/test_web/test_serialize/test_serialize_status.py`

**Files scanned:** ~20 source files + ~5 spec files.

**Pattern extraction date:** 2026-04-19.
