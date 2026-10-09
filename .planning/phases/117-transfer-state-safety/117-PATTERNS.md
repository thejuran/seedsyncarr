# Phase 117: Transfer-State Safety - Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** 17 (6 source modified, 2 test files new, 8 test files modified, 1 evidence doc new)
**Analogs found:** 17 / 17 (every file has an in-repo analog. Most are self-analogs, meaning the change extends an existing pattern in the same file.)

All paths are relative to `src/python/` unless stated otherwise. Line numbers are at HEAD `7da18e0`, which has the same code as `2e5be14`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lftp/job_status_parser.py` (B1) | utility (parser) | transform | same file: `MirrorJobParser._parse_connecting_header` :373-380 (peek-before-pop) | exact (self) |
| `lftp/lftp.py` (B2) | service | request-response | same file: `status()` :298-313, `kill()` :344-369 | exact (self) |
| `common/status.py` (B3) | model (status component) | pub-sub (listener notify) | same class: `ControllerStatus` :114-125 | exact (self) |
| `controller/controller.py` (B3) | controller | event-driven (per cycle) | same method: `_update_controller_status` :499-513 | exact (self) |
| `controller/auto_queue.py` (B3) | service | batch (per-cycle sweep) | same method: `process()` :255-322, `__scan_clock` :383-393 | exact (self) |
| `tests/unittests/test_lftp/test_job_status_parser.py` | test | transform | `test_jobs_missing_pget_data_line` :905-933 | exact |
| `tests/unittests/test_lftp/test_lftp_status_contract.py` (NEW) | test | request-response | `tests/unittests/test_lftp/test_lftp_log_sanitization.py` :11-58 + integration counter tests `test_lftp_protocol.py` :761-830 | exact |
| `tests/unittests/test_controller/test_transfer_state_safety.py` (NEW) | test (composed) | event-driven pipeline | `TestAutoQueueComposedPipeline` (`test_auto_queue.py` :1798-1863) + `TestUpdateControllerStatusCapacity._make_controller_with_status` (`test_controller.py` :46-51) + `BaseControllerTestCase` (`base.py`) | role-match (composition of 3) |
| `tests/unittests/test_controller/test_auto_queue.py` | test | batch | same file: `TestAutoQueueStabilityAndSweep._set_scan` :1972-1987, `TestAutoQueueLocalStabilityGate._cycle` :2214-2241 | exact (self) |
| `tests/unittests/test_controller/test_lftp_manager.py` | test | request-response | same file: `test_status_returns_none_on_parser_error` :184-194 | exact (self) |
| `tests/unittests/test_controller/test_controller.py` | test | event-driven | same file: `test_existing_scan_time_fields_still_updated` :123-130 | exact (self) |
| `tests/unittests/test_controller/test_controller_unit.py` | test | event-driven | same file: `TestControllerUpdateStatus` :1011-1042; `TestRestartBurstRegression._make_auto_queue` :1319-1330 | exact (self) |
| `tests/unittests/test_common/test_status.py` | test | pub-sub | same file: `test_default_values` :128-133 | exact (self) |
| `tests/unittests/test_web/test_serialize/test_serialize_status.py` | test | transform | same file: `test_controller_status_latest_remote_scan_time` :62-73 | exact (self) |
| `tests/integration/test_lftp/test_lftp_protocol.py` (4 flips) | test (integration, CI-only) | request-response | same file :761-830 | exact (self) |
| `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md` (NEW) | doc (release-gate evidence) | n/a | `.planning/phases/116-import-safety/116-REL01-EVIDENCE.md` | exact |
| `web/serialize/serialize_status.py` | config/serializer | transform | **NO CHANGE** (D-06). It lists its keys explicitly at :12-20, so leaving it untouched keeps the SSE payload identical. | n/a |

## Pattern Assignments

### `lftp/job_status_parser.py` (parser, transform): B1 peek-before-pop

**Analog (in file):** `MirrorJobParser._parse_connecting_header`, lines 373-380. It already uses a positive match before it pops:
```python
    def _parse_connecting_header(self, result, lines: List[str]) -> LftpJobStatus:
        """Parse mirror header when connecting or getting file list."""
        # There may be a 'Connecting' or 'cd' line ahead, but not always
        if lines and (
                lines[0].startswith("Getting file list") or
                lines[0].startswith("cd ")
        ):
            lines.pop(0)  # pop the connecting line
```

**Defect site 1 (pget data line), lines 273-281.** The pop is unconditional:
```python
        # Data line may not exist
        result_at = None
        result_at2 = None
        result_got = None
        if lines:
            data_line = lines.pop(0)
            result_at = RegexPatterns.CHUNK_AT.search(data_line)
            result_at2 = RegexPatterns.CHUNK_AT2.search(data_line)
            result_got = RegexPatterns.CHUNK_GOT.search(data_line)
```
Change it to `if lines and _is_chunk_data(lines[0]):`. Keep the three `None` defaults so the "no data line" path still builds `TransferState(None…)`.

**Defect site 2 (`\chunk` follower), lines 654-660:**
```python
        # Chunk header line (ignore with next line)
        result = RegexPatterns.CHUNK_HEADER.search(line)
        if result:
            if not lines:
                raise ValueError("Missing data line for chunk '{}'".format(line))
            lines.pop(0)
            return True
```
Change it to `if lines and _is_chunk_data(lines[0]): lines.pop(0)` and then `return True`. Drop the `raise`: a trailing `\chunk` is now tolerated (RESEARCH, "Behavior change inherent to fix #10").

**Site 3 (optional, MIRROR_EMPTY follower), lines 642-652:**
```python
        result = RegexPatterns.MIRROR_EMPTY.search(line)
        if result:
            name = result.group("name")
            if lines:
                if ("Getting file list" in lines[0] or
                        lines[0].startswith("cd ") or
                        lines[0] == "{}:".format(name) or
                        lines[0].startswith("mkdir ")):
                    lines.pop(0)
            return True
```
Add a header guard so a `[N] ` header line is never popped. The `in` substring check must stay, because real output depends on it (`test_queue_and_jobs_4`).

**Regex constants to reuse:** `RegexPatterns.CHUNK_AT` (:71-79), `CHUNK_AT2` (:82-87) and `CHUNK_GOT` (:90-99). All three are anchored with `^` + `QUOTED_FILE_NAME`, so a `[N] …` header can never match them. Put the new `_is_chunk_data` helper as a module-level function or a `RegexPatterns` staticmethod near those constants. No new regex is needed except the optional linear `^\[\d+\]\s` header guard.

**Do NOT touch:** `_handle_file_transfer` :583-603 (site #8). Its consume-then-raise is loud and is deferred under D-09.

---

### `lftp/lftp.py` (service, request-response): B2 None contract

**Imports (lines 1-12):** `Optional` is already imported, as is `LftpJobStatusParserError`. No import changes are needed.
```python
from typing import Callable, Union, List, Optional
...
from common import AppError, sanitize_log_value
from .job_status_parser import LftpJobStatus, LftpJobStatusParser, LftpJobStatusParserError

# How many status errors are allowed before error propagates out
MAX_CONSECUTIVE_STATUS_ERRORS = 2
```

**Defect site, `status()` lines 298-313:**
```python
    def status(self) -> List[LftpJobStatus]:
        out = self.__run_command("jobs -v")
        try:
            statuses = self.__job_status_parser.parse(out)
            self.__consecutive_status_errors = 0
        except LftpJobStatusParserError:
            self.__consecutive_status_errors += 1
            if self.__consecutive_status_errors <= MAX_CONSECUTIVE_STATUS_ERRORS:
                self.logger.warning(f"Ignoring status error (count={self.__consecutive_status_errors})")
                statuses = []          # <-- B2: becomes `return None`
            else:
                raise
        return statuses
```
Change the return type to `Optional[List[LftpJobStatus]]` and update the docstring. Keep the warning log. It contains only the counter, so it needs no sanitization.

**`kill()` lines 344-357** (the only production consumer without a `None` guard):
```python
        job_to_kill = None
        for status in self.status():
            if status.name == name:
```
Before the loop, add `statuses = self.status()`. If it is `None`, raise `LftpJobStatusParserError(...)`. Do not put the job name into the exception message unsanitized. Any log line that names the job must use `sanitize_log_value(name)`, as lines 356/362/365 already do. The raise is caught by the existing handler in `command_processor.py:139`, which returns the generic "Lftp error" response.

---

### `common/status.py` (model, pub-sub): B3 new clock properties

**Analog (same class), lines 114-125:**
```python
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
Add `latest_successful_local_scan_time` and `latest_successful_remote_scan_time` the same way: one `_create_property` line each and one `= None` init each. Do NOT add them to `SerializeStatusJson`.

---

### `controller/controller.py` (controller, per-cycle): B3 success clock writes

**Analog (same method), `_update_controller_status` lines 499-513:**
```python
        if remote_scan is not None:
            self.__context.status.controller.latest_remote_scan_time = remote_scan.timestamp
            self.__context.status.controller.latest_remote_scan_failed = remote_scan.failed
            self.__context.status.controller.latest_remote_scan_error = remote_scan.error_message
            if remote_scan.total_bytes is not None and remote_scan.used_bytes is not None:
                ...
        if local_scan is not None:
            self.__context.status.controller.latest_local_scan_time = local_scan.timestamp
```
Add `if not remote_scan.failed:` / `if not local_scan.failed:` guards that set the success clocks. Leave the UI-clock lines exactly as they are (D-06). The `not .failed` guard copies `ModelPipeline.feed_model_builder` (`controller/model_pipeline.py:157-160`):
```python
        if remote_scan is not None and not remote_scan.failed:
            self._model_builder.set_remote_files(remote_scan.files)
        if local_scan is not None and not local_scan.failed:
            self._model_builder.set_local_files(local_scan.files)
```

**`None` guard to leave unchanged,** `_update_active_file_tracking` :433-436. It is already correct for B2:
```python
        if lftp_statuses is not None:
            self.__active_downloading_file_names = [
                s.name for s in lftp_statuses if s.state == LftpJobStatus.State.RUNNING
            ]
```

---

### `controller/auto_queue.py` (service, per-cycle batch): B3 stability on the success clock

**Clock reads to split, lines 260-267:**
```python
        scan_time = AutoQueue.__scan_clock(
            self.__context.status.controller.latest_remote_scan_time)
        local_scan_time = AutoQueue.__scan_clock(
            self.__context.status.controller.latest_local_scan_time)
        if self.__stability_seconds > 0 and scan_time is not None:
            self.__update_remote_size_history(model_files, scan_time)
        if self.__local_stability_seconds > 0 and local_scan_time is not None:
            self.__update_local_idle_history(model_files, local_scan_time)
```
Keep `scan_time` on the UI clock, because the cooldown at :316-321 uses it and must not change. Add `remote_stable_time` and `local_stable_time`, both read through `__scan_clock` from the new `latest_successful_*` properties. Use those two in the two `__update_*_history` calls and in `sweep_accept` (:274-288: `scan_time is None`, `scan_time - entry[1]`, `local_scan_time is None`, `local_scan_time - entry[1]`).

**Cooldown that must stay on `scan_time`, lines 316-321:**
```python
            if scan_time is not None:
                last_attempt = self.__last_queue_attempt.get(name)
                if last_attempt is not None and \
                        scan_time - last_attempt < AutoQueue.REQUEUE_COOLDOWN_SECONDS:
                    continue
                self.__last_queue_attempt[name] = scan_time
```

**Normaliser to reuse, `__scan_clock` lines 383-393.** It handles both `datetime` and epoch floats. Docstrings to update: the class docstring at :164-176 ("Stability is measured against latest_remote_scan_time …", "(latest_local_scan_time)") and the comment at :255-259.

---

### `tests/unittests/test_lftp/test_job_status_parser.py` (test): B1 regressions

**Analog:** `test_jobs_missing_pget_data_line`, lines 905-933. It already contains a pget with no data line. Copy its structure exactly: triple-quoted indented output, `LftpJobStatusParser().parse(output)`, golden `LftpJobStatus` objects, `total_transfer_state = TransferState(None, None, None, None, None)`, then compare length and list equality:
```python
        parser = LftpJobStatusParser()
        statuses = parser.parse(output)
        golden_job1 = LftpJobStatus(job_id=3,
                                    job_type=LftpJobStatus.Type.MIRROR,
                                    state=LftpJobStatus.State.RUNNING,
                                    name="c -o c",
                                    flags="-c")
        golden_job1.total_transfer_state = LftpJobStatus.TransferState(None, None, None, None, None)
        ...
        golden_jobs = [golden_job1, golden_job2]
        self.assertEqual(len(golden_jobs), len(statuses))
        statuses_jobs = [j for j in statuses if j.state == LftpJobStatus.State.RUNNING]
        self.assertEqual(golden_jobs, statuses_jobs)
```
Class: `TestLftpJobStatusParser(unittest.TestCase)`, with `setUp` setting `self.maxDiff = None` (lines 7-10). Imports are at lines 1-4. The fixture text for the 5 regression shapes is in RESEARCH §Code Examples. Avoid `assertRaises` RED shapes: write the GREEN expectation (golden equality), so the old code fails with `LftpJobStatusParserError` or `AssertionError`. A parser error escaping from a test shows up as an error rather than an `AssertionError`. The evidence doc must note this for the pget→pget and `\chunk`→`\chunk` cases.

---

### `tests/unittests/test_lftp/test_lftp_status_contract.py` (NEW, test): B2 boundary + kill-on-None

**Primary analog:** `tests/unittests/test_lftp/test_lftp_log_sanitization.py`.

Imports and harness (lines 11-14, 37-58):
```python
import unittest
from unittest.mock import MagicMock, patch

from lftp import LftpJobStatus
...
def _make_lftp_with_mocked_process():
    from lftp import Lftp
    with patch('pexpect.spawn') as mock_spawn:
        mock_proc = MagicMock()
        mock_proc.isalive.return_value = True
        mock_proc.before = b""
        mock_proc.after = b""
        mock_proc.expect.return_value = 0
        mock_spawn.return_value = mock_proc
        lftp = Lftp(address="localhost", port=22, user="testuser", password="testpass")
    return lftp
```
Copy this helper into the new file rather than importing it across test modules. The repo has no shared conftest for it.

The kill-test shape comes from the same file, lines 69-80 (`lftp.status = MagicMock(return_value=[])`, `assertLogs("Lftp", level="DEBUG")`). For kill-on-None, use `MagicMock(return_value=None)`, then `assertRaises(LftpJobStatusParserError)` and assert that `_Lftp__run_command` was not called with `kill`/`queue --delete`.

**Boundary-sequence analog:** `tests/integration/test_lftp/test_lftp_protocol.py:21-29` (`_MALFORMED_JOBS_OUTPUT`) and :769-777, which use the real parser through a patched `__run_command`:
```python
        with patch.object(self.lftp, "_Lftp__run_command",
                          return_value=_MALFORMED_JOBS_OUTPUT):
            self.assertEqual([], self.lftp.status())   # becomes assertIsNone
            self.assertEqual([], self.lftp.status())
            with self.assertRaises(LftpJobStatusParserError):
                self.lftp.status()
```
Copy the `_MALFORMED_JOBS_OUTPUT` constant verbatim (final line `bad string uh oh`). Loop over `lftp.lftp.MAX_CONSECUTIVE_STATUS_ERRORS` rather than hardcoding 2. Use a `side_effect` function to script the sequence `err, err, err(raise), ok, err, err, ""→[]`.

---

### `tests/unittests/test_controller/test_transfer_state_safety.py` (NEW, composed test)

Three analogs are composed here:

1. **Real model chain:** `TestAutoQueueComposedPipeline` (`test_auto_queue.py:1810-1863`). Real `Model` + `ModelBuilder` + `ModelDiffUtil`, `controller` as a MagicMock with `get_model_files*` side effects, `_build_and_apply` mirroring `ModelPipeline.build_and_apply_model`, and `_queued_filenames()` read from `queue_command.call_args_list`:
```python
        self.model = Model()
        self.model.set_base_logger(self.logger)
        self.builder = ModelBuilder()
        self.builder.set_base_logger(self.logger)
        self.builder.set_downloaded_files(set())
        ...
    def _build_and_apply(self):
        if not self.builder.has_changes():
            return
        new_model = self.builder.build_model()
        for diff in self.ModelDiffUtil.diff_models(self.model, new_model):
            ...
```
   Alternative: build a real `ModelPipeline(context, persist, model, model_lock, model_builder, scan_manager, lftp_manager, file_op_manager, logger)` (`model_pipeline.py:33-57`) and call `update_model()`. Its collaborators are injected, so the B2 path runs through the real `feed_model_builder` `None` guard (:163-164).

2. **Real Status + Controller without full init:** `test_controller.py:46-51`:
```python
    def _make_controller_with_status(self):
        controller = Controller.__new__(Controller)
        ctx = MagicMock()
        ctx.status = Status()
        controller._Controller__context = ctx
        return controller
```
   Build `ScannerResult(timestamp=..., files=[...], failed=True/False)` (signature in `controller/scan/scanner_process.py:42-54`). Share `ctx.status` with the AutoQueue context (`aq_ctx.status = ctx.status`) so that AutoQueue reads the clocks the controller wrote.

3. **Controller with mocked managers:** `BaseControllerTestCase` (`tests/unittests/test_controller/base.py:9-63`). It patches `controller.controller.{ModelBuilder,LftpManager,ScanManager,FileOperationManager,MultiprocessingLogger,MemoryMonitor}` and provides `_make_controller_started()`. In the B2 controller-level variant, set `self.mock_lftp_manager.status.return_value` per cycle, then assert `self.mock_model_builder.set_lftp_statuses` was not called and `self.mock_scan_manager.update_active_files` still received the frozen list.

**RED rule (Pitfall 2):** B2 downstream RED must go through the **real** `Lftp.status` (mocked pexpect + `_MALFORMED_JOBS_OUTPUT`) and a real `LftpManager` (`patch('controller.lftp_manager.Lftp', return_value=real_lftp)`). `__run_command` should be a function that returns the scripted output only for `cmd == "jobs -v"`, because `LftpManager.__init__` (`lftp_manager.py:57-69`) issues `set` commands (Pitfall 4). B3 RED must assert on queue commands, not on the new attributes.

---

### `tests/unittests/test_controller/test_auto_queue.py` (test): B3 helpers + D-03/D-04/D-05

**Setup sites that need the two new fields initialized to `None`:**

| Class | setUp line | Status object type | Effect if not initialized |
|---|---|---|---|
| `TestAutoQueue` | :297-298 | MagicMock | `float(MagicMock()) == 1.0`, a fake clock |
| `TestAutoQueueCommandOrigin` | :1777-1778 | MagicMock | same |
| `TestAutoQueueComposedPipeline` | :1826-1827 | MagicMock | same |
| `TestAutoQueueStabilityAndSweep` | :1945-1950 | **plain `_ControllerStatus` class** | **`AttributeError`** after the fix |
| `TestAutoQueueLocalStabilityGate` | :2189-2194 | **plain `_ControllerStatus` class** | **`AttributeError`** after the fix |
| `TestRestartBurstRegression._make_auto_queue` (`test_controller_unit.py:1328-1329`) | — | MagicMock | stability is 0 there, so harmless. Initialize anyway for consistency. |

Note: RESEARCH Pitfall 1 describes all of these as MagicMock. The two stability classes actually use a bare class (`class _ControllerStatus: pass`), so a missing field raises instead of silently reading 1.0. Either way the fields must be set in setUp. Initializing them is harmless on old code, so it can land in the RED wave.

**`_set_scan` helper, lines 1972-1987.** Add a `failed=False` kwarg. Set `latest_remote_scan_time` every time, and set `latest_successful_remote_scan_time` only when not failed. For a failed scan, leave `model_files` unchanged: `ModelPipeline` does not apply failed results, so the model keeps its stale sizes.
```python
    def _set_scan(self, scan_time, remote_size, local_size=None,
                  state=ModelFile.State.DEFAULT):
        f = ModelFile(self.FILE, False)
        ...
        self.model_files = [f]
        self.context.status.controller.latest_remote_scan_time = scan_time
        if self.model_listener is not None:
            ...
```

**`_cycle` helper, lines 2214-2241.** Also set `latest_successful_local_scan_time = local_scan_time` (and add a `failed=` kwarg for D-05). Keep the remote-clock lockstep at :2229-2235, because the cooldown depends on it.

**Test-method shape:** `test_new_file_not_queued_until_remote_size_stable`, :1992-2021 (sequence of `_set_scan` + `auto_queue.process()` + `assertEqual(n, self._queued_count(), msg)`, then a final `command.action == Controller.Command.Action.QUEUE` check). New D-03/D-04 cases go in `TestAutoQueueStabilityAndSweep` (remote) and `TestAutoQueueLocalStabilityGate` (local).

---

### `tests/unittests/test_controller/test_lftp_manager.py` (test): None pass-through

**Analog (same file), lines 184-194:**
```python
    @patch('controller.lftp_manager.Lftp')
    def test_status_returns_none_on_parser_error(self, mock_lftp_class):
        """Test that status() returns None on LftpJobStatusParserError."""
        mock_lftp = MagicMock()
        mock_lftp.status.side_effect = LftpJobStatusParserError("Parse failed")
        mock_lftp_class.return_value = mock_lftp
        manager = LftpManager(self.mock_context)
        result = manager.status()
        self.assertIsNone(result)
```
For the new case, `mock_lftp.status.return_value = None` → `assertIsNone`. Also add the converse: `[]` passes through as `[]` (`assertEqual([], result)`). Both are "new" tests that pass on both old and new code.

---

### `tests/unittests/test_controller/test_controller.py` and `test_controller_unit.py` (test): success-clock writes

**Analog:** `test_controller.py:123-130`, which uses a real `Status` and a real `ScannerResult`:
```python
    def test_existing_scan_time_fields_still_updated(self):
        c = self._make_controller_with_status()
        ts = datetime.now()
        scan = ScannerResult(timestamp=ts, files=[], failed=False,
                             total_bytes=2_000_000_000_000, used_bytes=1_300_000_000_000)
        c._update_controller_status(scan, None)
        self.assertEqual(ts, c._Controller__context.status.controller.latest_remote_scan_time)
```
Prefer this harness (real `ScannerResult`) for the new success-clock assertions. **Caution with `test_controller_unit.py:1031-1039`:** `local_scan = MagicMock()` does not set `.failed`, so `local_scan.failed` is a truthy MagicMock and the success clock would *not* be set. Any new assertion in `TestControllerUpdateStatus` must set `scan.failed = False`/`True` explicitly, as `test_remote_scan_updates_status` does at :1017.

---

### `tests/unittests/test_common/test_status.py` and `test_serialize_status.py` (test)

- `test_status.py:128-133` (`test_default_values`): add `assertEqual(None, status.controller.latest_successful_*_scan_time)`. Classed as a "new" test.
- `test_serialize_status.py:62-73`: real `Status()` → `parse_stream(SerializeStatus().status(status))` → `json.loads(out["data"])`. New test: set both success clocks to a tz-aware datetime, then assert `set(data["controller"].keys()) == {"latest_local_scan_time", "latest_remote_scan_time", "latest_remote_scan_failed", "latest_remote_scan_error"}`. This passes on both old and new code and guards D-06.

---

### `tests/integration/test_lftp/test_lftp_protocol.py` (4 flips, CI-only)

Lines 761-830: `test_status_real_parser_raises_on_malformed_output`, `test_status_parser_error_increments_and_swallows`, `test_status_parser_error_exceeds_max_reraises` and `test_status_parser_error_counter_resets_on_success`. Flip every tolerated-error `self.assertEqual([], self.lftp.status())` to `self.assertIsNone(self.lftp.status())`. The *success* line at :826 (parse stub returns `[]`) **stays** `assertEqual([], …)`, because it is the genuine-empty preservation case. Update the docstrings ("swallowed (return [])" → "reported unavailable (None)"). Keep `@pytest.mark.timeout(5)`.

---

### `.planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md` (NEW, doc)

**Analog:** `.planning/phases/116-import-safety/116-REL01-EVIDENCE.md`. Copy its section skeleton exactly:

```markdown
# Phase 117 REL-01 gate-1 evidence (fail-before / pass-after)

RED run executed against pre-fix code at `<sha>` (branch `safety-patch-1.7.4`, before the RED test commit). No file under `src/python/lftp/`, `src/python/common/` or `src/python/controller/` was modified.

## RED (pre-fix) — Plan 117-01

**Command** (phase quick run, plus `-rf --tb=line`; per-test messages taken from `--junitxml` of the same command):

    cd src/python && poetry run pytest \
      tests/unittests/test_lftp \
      tests/unittests/test_controller/test_auto_queue.py \
      ... (the RESEARCH quick-run file list + the two new files)
      -q -p no:cacheprovider -rf --tb=line

**Failures** (N; state each failure's type. 116 was all AssertionError):

    FAILED tests.unittests....::test_name - AssertionError: ...

**Summary line:** `N failed, M passed, ... in Xs`

**Ruff** (`poetry run ruff check <abs>/src/python/`, whole tree): `All checks passed!`

**Preservation tests passing on pre-fix code** (part of the M passed): `...`

| # | Failing test | Requirement | Decision |
|---|--------------|-------------|----------|
| 1 | `test_...` | XFER-01 | D-07, D-08 |

## GREEN (post-fix) — Plan 117-0X

Post-fix commit: `<sha>`. ...

**Targeted regressions** (`-v -k "<names joined by ' or '>"`): <PASSED lines> + summary line

**Quick run** (same command as RED): `... passed`. Account for the delta vs RED (N failed + M passed).

**Full host suite.** Two-part run (every file except the four baseline files via `--ignore`; then the baseline files separately). Report totals vs the 21 failed / 3 errors baseline.

**Ruff** (whole tree): `All checks passed!`
```

Phase 117 additions to the 116 format, per RESEARCH Pitfall 2:
- Add a **"New-contract tests (pass on both / not regressions)"** list: kill-on-None, success-clock set, serializer keys unchanged, `LftpManager` `None`/`[]` pass-through, defaults.
- The failure-type line must tolerate `LftpJobStatusParserError` raised out of a test (B1 pget→pget and `\chunk`→`\chunk` RED shapes), which pytest reports as an error, not an `AssertionError`. State this explicitly and confirm that none are ImportError, AttributeError or TypeError.
- Add a **CI-only** note: the 4 integration flips in `test_lftp_protocol.py` are verified in CI `unittests-python`, not on the host.
- Add a deferred-sites record (D-09): B1 audit sites #1, #6 and #8.

## Shared Patterns

### `None` = unavailable, guard with `is not None`, never `or []`
**Sources:** `controller/model_pipeline.py:163-164`, `controller/controller.py:433`, `controller/lftp_manager.py:140-155`
**Apply to:** `lftp.py` (`status`, `kill`) and every new test assertion
```python
        if lftp_statuses is not None:
            self._model_builder.set_lftp_statuses(lftp_statuses)
```

### Apply only on successful scans (`not .failed`)
**Source:** `controller/model_pipeline.py:157-162`
**Apply to:** `controller.py` success-clock writes, and the `failed=` kwarg on the test helpers

### CWE-117 log sanitization
**Source:** `lftp/lftp.py:356, 362, 365` (`sanitize_log_value(name)`), imported at :8 (`from common import AppError, sanitize_log_value`)
**Apply to:** any new or changed log line in `lftp.py` that contains a job name or lftp output. Do not log raw `out`.

### Name-mangled white-box test access
**Source:** `test_lftp_protocol.py:769` (`patch.object(self.lftp, "_Lftp__run_command", ...)`), `test_controller.py:50` (`controller._Controller__context = ctx`), `base.py:58` (`_Controller__started`)
**Apply to:** both new test files. This is the accepted convention, so no public test hooks are needed.

### Test style
`unittest.TestCase` classes run under pytest. `unittest.mock` (`MagicMock`, `patch`, `patch.object`) is used in scoped `with` blocks or as `@patch` decorators. Assertion messages are passed as the third arg (`assertEqual(0, n, "reason")`). Logger setup and teardown follow `test_auto_queue.py:1931-1933, 1968-1970`.

## Conventions

Derived with `gsd-tools verify conventions --derive --scope src/python`:

| Axis | Dominant | Share | Entropy | Status |
|---|---|---|---|---|
| file-name casing | (none; snake 39 / camel 29 / other 45) | 40% | 0.986 | contested hotspot |
| identifier casing | (none; camel 425 / Pascal 283) | 55% | 0.605 | contested hotspot |
| export style | cjs | 100% (n=34) | 0 | named contract (tool artefact, see note) |
| import style | — | n=2 | — | insufficient data |
| py wildcard import | explicit | 100% (n=73) | 0 | named contract |
| py import relativity | (none; relative 48 / absolute 26) | 65% | 0.935 | contested hotspot |

**Contested hotspots (author's choice).** The deriver counts non-Python assets under `src/python`, so the casing and export axes are not meaningful for this phase. In practice every Python file touched here is snake_case with PascalCase classes and snake_case functions. Match the local file. Import relativity is split by directory. Inside a package (`lftp/lftp.py` → `from .job_status_parser import …`) imports are relative. Across packages and in tests (`from lftp import …`, `from controller.controller import Controller`, `from tests.unittests.test_controller.base import BaseControllerTestCase`) they are absolute. New tests must use the absolute form. The repo's prototype intentional split is the CJS<->SDK dual resolver of the GSD tooling (`bin/lib/**` uses CJS, `sdk/src/**` uses ESM). It does not apply to this Python-only phase, but the same rule holds: follow the directory's local style.

## No Analog Found

None. Every file has an in-repo analog. The weakest match is `test_transfer_state_safety.py`, which has no single analog and composes three harnesses (listed above). RESEARCH §Code Examples covers its scenario design.

## Metadata

**Analog search scope:** `src/python/lftp/`, `src/python/controller/`, `src/python/common/status.py`, `src/python/web/serialize/`, `src/python/tests/unittests/test_lftp/`, `src/python/tests/unittests/test_controller/`, `src/python/tests/unittests/test_common/`, `src/python/tests/unittests/test_web/test_serialize/`, `src/python/tests/integration/test_lftp/`, `.planning/phases/116-import-safety/`
**Files scanned:** 18
**Pattern extraction date:** 2026-10-08
