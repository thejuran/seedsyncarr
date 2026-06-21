# Phase 114: Scanner Auto-Recovery - Pattern Map

**Mapped:** 2026-06-21
**Files analyzed:** 5 (3 source modified, 2 test extended)
**Analogs found:** 5 / 5 (all in-file or same-package — this phase wires existing infrastructure, every touched file has a strong local analog)

> **Path-drift note (resolved):** The CONTEXT.md `code_context` block uses shorthand paths (`src/python/sshcp.py`, `src/python/remote_scanner.py`). The RESEARCH.md and the actual files on disk confirm the **real paths** are nested:
> - `src/python/ssh/sshcp.py` (NOT `src/python/sshcp.py`)
> - `src/python/controller/scan/remote_scanner.py` (NOT `src/python/remote_scanner.py`)
> - `src/python/controller/scan/scanner_process.py`
> All paths below are verified against disk. No new source files are created; tests extend existing files.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/ssh/sshcp.py` | config (error-classification constants) | transform (string → bool classification) | the two sibling tuples in the **same file** (`TRANSIENT_ERROR_PATTERNS` / `PERMANENT_ERROR_PATTERNS`, lines 14-22) | exact |
| `src/python/controller/scan/remote_scanner.py` | service (scanner) | request-response w/ bounded retry | the existing `scan()` classification block + the `_is_transient/_is_permanent_ssh_error` matchers in the **same file** (lines 18-28, 88-111) | exact |
| `src/python/seedsyncarr.py` | service (app entrypoint/supervisor) + new pure helper | event-driven (exception → restart decision) | `_detect_incomplete_config` / `_emit_startup_warnings` static helpers (lines 365-400) for the new `_should_auto_restart`; the existing `ServiceRestart`/`main()` loop (lines 184-194, 507-523) for the wiring | exact |
| `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py` | test | request-response (mock-Sshcp call-counter harness) | the existing `ssh_shell` call-counter harness + recoverable-flag asserts in the **same file** (setUp lines 22-36; harness pattern lines 90-101, 345-364, 516-552) | exact |
| `src/python/tests/unittests/test_seedsyncarr.py` | test | pure-function assertion | the `TestSeedsyncarr.test_detect_incomplete_config` + `TestSeedsyncarrStartupWarnings` static-method test classes (lines 141-172, 198-263) | exact |

---

## Pattern Assignments

### `src/python/ssh/sshcp.py` (config / classification tuple) — SCAN-01

**Analog:** the two existing pattern tuples in the same file.

**Add `NAME_RESOLUTION_ERROR_PATTERNS` alongside the existing tuples (mirror the exact comment+tuple style at lines 14-22):**
```python
# Error message prefixes that indicate transient network issues (timeouts,
# connection drops, unreachable hosts). Consumers can use these to decide
# whether a failed SSH operation is worth retrying.
TRANSIENT_ERROR_PATTERNS = ("Timed out", "Connection refused by server")

# Error message prefixes that indicate permanent configuration problems
# (wrong credentials, changed host keys, bad hostnames). These should not
# be retried — the user needs to fix the configuration.
PERMANENT_ERROR_PATTERNS = ("Incorrect password", "Remote host key has changed", "Bad hostname:")
```

**Copy-from instruction:** Add a third module-level tuple in the **same place and style**. `"Bad hostname:"` MUST stay in `PERMANENT_ERROR_PATTERNS` (do NOT move it) — it appears intentionally in BOTH tuples (Pattern 1 in RESEARCH, A3). The single raised string for all three name-resolution conditions is `"Bad hostname: {host}"` — verified at `sshcp.py:97-98` and `:128-129`, where pexpect indices 3 (`Could not resolve hostname`) and 5 (`Name or service not known`) both map to that one message. So the tuple needs only the `"Bad hostname:"` prefix:
```python
NAME_RESOLUTION_ERROR_PATTERNS = ("Bad hostname:",)
```

**Export note:** `remote_scanner.py:10` imports these names from the `ssh` package (`from ssh import Sshcp, SshcpError, TRANSIENT_ERROR_PATTERNS, PERMANENT_ERROR_PATTERNS`). The new tuple must be re-exported the same way the existing two are (check `src/python/ssh/__init__.py` and add `NAME_RESOLUTION_ERROR_PATTERNS` to its export list — same mechanism as the existing tuples).

---

### `src/python/controller/scan/remote_scanner.py` (service / bounded retry) — SCAN-01/02/03

**Analog:** the existing `scan()` classification block (lines 88-111) and the two static matcher helpers (lines 18-28), all in the same file.

**Matcher pattern to copy** (lines 18-28 — add a sibling `_is_name_resolution_ssh_error` with identical shape):
```python
@staticmethod
def _is_transient_ssh_error(error: SshcpError) -> bool:
    """Check if an SSH error is transient (timeout, connection refused, etc.)"""
    msg = str(error)
    return any(pattern in msg for pattern in TRANSIENT_ERROR_PATTERNS)

@staticmethod
def _is_permanent_ssh_error(error: SshcpError) -> bool:
    """Check if an SSH error is a permanent config problem (wrong password, bad host, etc.)"""
    msg = str(error)
    return any(pattern in msg for pattern in PERMANENT_ERROR_PATTERNS)
```

**Core pattern being replaced — the EXACT classification + raise at lines 88-111** (the shared retry helper wraps this `self.__ssh.shell(...)` call AND the install md5sum `:155` + copy `:180` ops; ONLY `df` at `:138` stays untouched per Pitfall 3):
```python
try:
    out = self.__ssh.shell("{} {}".format(
        shlex.quote(self.__remote_path_to_scan_script),
        shlex.quote(self.__remote_path_to_scan))
    )
except SshcpError as e:
    self.logger.warning("Caught an SshcpError: {}".format(str(e)))
    recoverable = True
    # Any scanner errors are fatal, regardless of transience
    if "SystemScannerError" in str(e):
        recoverable = False
    # Permanent SSH errors (wrong password, host key changed, bad
    # hostname) are always fatal — retrying won't help.
    elif self._is_permanent_ssh_error(e):
        recoverable = False
    # Before the first successful scan, non-transient errors are
    # fatal so the user is prompted to correct them. Transient
    # network issues (timeouts, connection refused) are retried.
    elif self.__first_run and not self._is_transient_ssh_error(e):
        recoverable = False
    raise ScannerError(
        Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()),
        recoverable=recoverable
    )
```

**Install-path call sites the SHARED helper also wraps** (`_install_scanfs`, lines 149-187 — KEEP the existing surrounding `try/except SshcpError` blocks; wrap only the SSH op invocation):
```python
# md5sum check (:154-165) — the op at :155:
out = self.__ssh.shell("md5sum {} | awk '{{print $1}}' || echo".format(
    shlex.quote(self.__remote_path_to_scan_script)))
# ... existing except converts to:
#   ScannerError(Localization.Error.REMOTE_SERVER_INSTALL.format(str(e).strip()),
#                recoverable=self._is_transient_ssh_error(e))

# copy (:179-187) — the op at :180:
self.__ssh.copy(local_path=self.__local_path_to_scan_script,
                remote_path=self.__remote_path_to_scan_script)
# ... existing except converts to the SAME REMOTE_SERVER_INSTALL ScannerError.
```

**Copy-from instructions:**
- **Preserve the immediate-raise recoverable logic exactly** (Pitfall 4). Factor the lines 95-110 classification (the `recoverable = True` … `raise ScannerError(...)` body) into a private helper `__to_scanner_error(e)` that returns the correctly-flagged `ScannerError`. The main-scan non-retried branch (transient timeout/refused, `SystemScannerError`, or any permanent error) calls this helper so `__first_run`-aware recoverable values stay byte-for-byte identical (including transient-after-first-run → `recoverable=True`). The install path KEEPS its own existing except blocks verbatim (`recoverable=self._is_transient_ssh_error(e)`) — do not refactor them.
- **Use ONE shared retry helper for all three call sites** (RESEARCH "Don't Hand-Roll" + Pattern 2). Add a private `__ssh_call_with_name_resolution_retry(self, ssh_call, op_label)` that takes a zero-arg callable + a short literal label, runs `for attempt in range(1, self.__SCAN_MAX_ATTEMPTS + 1)`, returns `ssh_call()` on success, and on `SshcpError`: if `not self._is_name_resolution_ssh_error(e)` → `raise` (re-raise unchanged); if `attempt < cap` → sleep backoff + `continue`; else (name-resolution exhausted) → `raise` (re-raise unchanged). The helper NEVER builds a `ScannerError` — it only re-raises the original `SshcpError`, so each caller's existing except converts it on its own path (main scan → `__to_scanner_error` / `REMOTE_SERVER_SCAN`; install → `REMOTE_SERVER_INSTALL`). Wrap the main scan call (`:89-92`), the md5sum op (`:155`), and the copy op (`:180`) with this helper via lambdas that close over the existing quoted strings/kwargs.
- **Retry condition is strictly** `self._is_name_resolution_ssh_error(e)` — **name-resolution ONLY** (Pitfall 2). Do NOT include `_is_transient_ssh_error` in the retry gate. `Timed out` / `Connection refused by server` are transient but each can block up to the Sshcp 180s per-command timeout, so retrying them in-scan would stack multiple 180s windows and break the existing first-run AND install timeout/refused tests — they keep their existing immediate-raise (main scan: recoverable per `__first_run`; install: recoverable per `_is_transient_ssh_error`) and recover on the next ~30s scan interval. `Incorrect password` / `Remote host key has changed` are NOT in the name-resolution tuple either, so they also hit the immediate-raise branch unchanged. `_is_transient_ssh_error` is referenced ONLY inside `__to_scanner_error`'s classification and the existing `_install_scanfs` excepts — never in the `retryable` gate.
- **Main-scan exhaustion branch (SCAN-03) must reproduce today's raise byte-for-byte.** After the `try` that calls the helper, an `except SshcpError as e` checks `if self._is_name_resolution_ssh_error(e): raise ScannerError(Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()), recoverable=False)` (the exhausted name-resolution case) else `raise self.__to_scanner_error(e)`:
  ```python
  raise ScannerError(
      Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()),
      recoverable=False)
  ```
  Same `Localization.Error.REMOTE_SERVER_SCAN.format(...)` message, `recoverable=False`. This is the SCAN-03 contract — the downstream chain (`scanner_process.run_loop` re-raise → propagation → `seedsyncarr.py:186-187`) is preserved.
- **Install exhaustion surface (SCAN-03) is byte-for-byte via the UNCHANGED `_install_scanfs` except:** on name-resolution exhaustion the helper re-raises the `SshcpError`, the existing except raises `ScannerError(Localization.Error.REMOTE_SERVER_INSTALL.format(str(e).strip()), recoverable=self._is_transient_ssh_error(e))` → `recoverable=False` for `"Bad hostname:"` with the unchanged message. A persistently-wrong hostname at startup/post-restart still surfaces and is bounded — without burning RECOV-01 budget on a blip.
- **Class-level constants** (convention is `__UPPER` mangled, per `Sshcp.__TIMEOUT_SECS` at `sshcp.py:28`). Add e.g. `__SCAN_MAX_ATTEMPTS`, `__SCAN_BACKOFF_BASE_SECS`, `__SCAN_BACKOFF_CEILING_SECS`, `__SCAN_BACKOFF_JITTER` as class attributes on `RemoteScanner` (research recommends 3 / 1.0 / 4.0 / 0.2 — Claude's discretion per D-02). Because only fast-failing name-resolution is retried, the worst-case in-scan backoff stack is small (~3s) on both the scan and install paths.
- **Imports:** `remote_scanner.py` does NOT currently import `time` or `random`; the retry helper adds `import time` (and `import random` for jitter) at the top per import-order convention. Add `NAME_RESOLUTION_ERROR_PATTERNS` to the existing `from ssh import ...` line at `:10`. (Ruff whole-tree gate will flag an unused import — Pitfall 5.)
- **Logging convention:** use lazy `%`-style logging in the shared helper (the `df` branch at `:141-145` already does: `self.logger.warning("df output parse failed for '%s': %r", ...)`). Do NOT use f-strings or `.format()` in the new log lines (Pitfall 5 / Security V7 — ruff + CWE-117). For any path/host value logged, follow the `sanitize_log_value` convention already used at `:124-126`.
- **Shutdown-aware backoff (Pitfall 1):** a bare `time.sleep(backoff)` blocks the scanner child from honoring its terminate Event (`AppProcess.terminate()` polls 1s before SIGTERM — `app_process.py`). 114-01-PLAN chose option (a): a bare `time.sleep` with a low `__SCAN_BACKOFF_CEILING_SECS = 4.0` ceiling plus a documented accepted-tradeoff comment in the ONE shared helper (so it applies to both the scan and install paths), rather than wiring a terminate Event into the spawn-pickled `RemoteScanner`.

**Existing-test guardrails this change must keep green** (Pitfall 2/3 — exact call counts AND the name-resolution-only invariant; all of these use timeout/permanent errors, never name-resolution, so the retry gate is False and they raise on attempt 1 with their exact call counts):
- `test_raises_recoverable_error_on_first_run_timeout` (~`:334`), `test_raises_recoverable_error_on_first_run_connection_refused` (~`:366`), `test_recovers_after_first_run_timeout` (`:401`, asserts 4 calls) — these prove transient timeout/refused are NOT retried in-scan and keep their existing immediate-raise + next-interval recovery. They must pass UNCHANGED.
- INSTALL-path guards (timeout/permanent, NOT name-resolution → not retried, raise on attempt 1 unchanged): `test_raises_nonrecoverable_error_on_md5sum_error` (~`:240`), `test_raises_recoverable_error_on_md5sum_timeout` (`:470`), `test_raises_recoverable_error_on_copy_timeout` (`:492`), `test_raises_nonrecoverable_error_on_failed_copy` (`:671`), `test_calls_correct_ssh_md5sum_command` (~`:145`, asserts 3 calls), `test_installs_scan_script_on_first_scan` (`:79`), `test_skips_install_on_md5sum_match` (`:177`). The shared helper must NOT re-run install/df when the main scan retries, and must NOT re-run the main scan/df when an install op retries.
- `test_recovers_from_failed_ssh` (`:631`, asserts 6 calls), `test_df_command_quotes_remote_path` (`:798`), `test_raises_nonrecoverable_error_on_wrong_password_after_first_run` (`:516`), `test_raises_nonrecoverable_error_on_host_key_change_after_first_run` (`:554`).

---

### `src/python/seedsyncarr.py` (supervisor + new pure helper) — RECOV-01

**Analog (for the NEW pure helper `_should_auto_restart`):** the existing static-method helpers `_detect_incomplete_config` and `_emit_startup_warnings`.

**`_detect_incomplete_config` pattern (lines 365-372)** — the template for a small, pure, unit-testable `@staticmethod` that takes plain inputs and returns a decision:
```python
@staticmethod
def _detect_incomplete_config(config: Config) -> bool:
    config_dict = config.as_dict()
    for sec_name in config_dict:
        for key in config_dict[sec_name]:
            if Seedsyncarr.__CONFIG_DUMMY_VALUE == config_dict[sec_name][key]:
                return True
    return False
```

**Copy-from instruction:** Extract the restart-budget decision into a `@staticmethod` matching this shape, e.g. `_should_auto_restart(consecutive_restarts: int, cap: int, current_run_start: Optional[datetime], reset_secs: int, now: datetime) -> tuple[bool, bool]` — pure (no I/O, no side effects), returns a `(should_restart, reset_applied)` tuple. This mirrors how `_detect_incomplete_config`/`_emit_startup_warnings` are pure and therefore unit-testable without spinning the `run()` loop (RESEARCH Wave 0 note). Place restart-cap/reset constants as module-level constants in `seedsyncarr.py` next to `main()` (research Open Question 2 — local to this file, not `Constants`).

**Analog (for the WIRING) — the existing `AppError` catch (lines 184-190):**
```python
try:
    controller_job.propagate_exception()
except AppError as exc:
    if not self.context.args.exit:
        self.context.status.server.up = False
        self.context.status.server.error_msg = str(exc)
        Seedsyncarr.logger.exception("Caught exception")
    else:
        raise
```

**The proven `ServiceRestart` raise pattern already in `run()` (lines 192-194):**
```python
# Check if a restart is requested
if web_app_builder.server_handler.is_restart_requested():
    raise ServiceRestart()
```

**The `main()` restart loop that survives `ServiceRestart` (lines 507-523):**
```python
def main():
    """Entry point for pip-installed seedsyncarr command."""
    if sys.hexversion < 0x03050000:
        sys.exit("Python 3.5 or newer is required to run this program.")
    while True:
        try:
            app = Seedsyncarr()
            app.run()
        except ServiceExit:
            break
        except ServiceRestart:
            Seedsyncarr.logger.info("Restarting...")
            continue
        except Exception:
            Seedsyncarr.logger.exception("Caught exception")
            raise
    Seedsyncarr.logger.info("Exited successfully")
```

**Copy-from instructions (RECOV-01, D-03):**
- **`ServiceRestart` gains keyword-only `auto`/`reset` flags WITHOUT breaking the message contract** (codex HIGH finding). Add `__init__(self, *args, auto: bool = False, reset: bool = False)` that calls `super().__init__(*args)` FIRST (the `*args` passthrough — NOT a bare `super().__init__()` — preserves the inherited Exception message so `str(ServiceRestart("restart requested")) == "restart requested"`), then stores `self.auto`/`self.reset`. Flags are keyword-only (after `*args`) so a positional message can never be misread as the `auto` flag. The existing `test_common/test_error.py` tests (`test_message_preserved`, `test_caught_by_app_error_handler`) MUST stay green unchanged.
- **The restart counter + `current_run_start` timestamp live in `main()`** — it is the only scope that survives a `ServiceRestart` (each loop constructs a fresh `Seedsyncarr()`). Add `consecutive_restarts` + `current_run_start` locals. The decision is evaluated AT FAILURE TIME inside `run()` using the current run's age (not a precomputed `restart_budget` bool); on the `except ServiceRestart as restart` branch, NORMALIZE the counter ONLY for auto restarts: `if getattr(restart, "auto", False): consecutive_restarts = 1 if getattr(restart, "reset", False) else consecutive_restarts + 1` (reset-at-cap → fresh budget of 1, NOT cap+1 — finding 2); a UI restart (`auto=False`) leaves the counter unchanged (finding 1). Keep the existing `except ServiceExit: break` and `except Exception: ... raise` arms unchanged.
- **The `run()` `AppError` catch decides restart-vs-surface at failure time.** When `not args.exit`, call `should_restart, reset_applied = Seedsyncarr._should_auto_restart(consecutive_restarts, restart_cap, run_start, restart_reset_secs, datetime.now())`. If `should_restart` → `raise ServiceRestart(auto=True, reset=reset_applied)` (routes into the existing machinery — the outer `except Exception` at `:199-224` terminates/joins jobs, persists, then re-raises to `main()`, exactly like the UI restart at `:194`). When the budget is genuinely exhausted → fall through to the **byte-for-byte current** `:186-187` surface (`status.server.up = False` + `error_msg = str(exc)` + `logger.exception(...)`). Keep the `else: raise` (args.exit) arm unchanged.
- **No new crash surface, no infinite loop** (Anti-Patterns): the cap-exhausted path is today's behavior; never `raise ServiceRestart()` unconditionally. The UI restart at `:194` stays a bare `ServiceRestart()` (auto=False, reset=False).

---

### `src/python/tests/unittests/test_controller/test_scan/test_remote_scanner.py` (test) — SCAN-01/02/03

**Analog:** the existing mock-Sshcp call-counter harness in the same file.

**setUp — patch `Sshcp` at the import site (lines 22-36):**
```python
def setUp(self):
    ssh_patcher = patch('controller.scan.remote_scanner.Sshcp')
    self.addCleanup(ssh_patcher.stop)
    self.mock_ssh_cls = ssh_patcher.start()
    self.mock_ssh = self.mock_ssh_cls.return_value
    ...
    # Ssh to return mangled binary by default
    self.mock_ssh.shell.return_value = b'error'
```

**Call-counter harness — sequence scan outcomes by call index (lines 345-359, the `test_recovers_after_first_run_timeout` shape):**
```python
self.ssh_run_command_count = 0

def ssh_shell(*args):
    self.ssh_run_command_count += 1
    if self.ssh_run_command_count == 1:
        # md5sum check
        return b''
    elif self.ssh_run_command_count == 2:
        # first scan attempt - timeout
        raise SshcpError("Timed out")
    else:
        # later tries
        return json.dumps([]).encode()
self.mock_ssh.shell.side_effect = ssh_shell
```

**Copy-op harness — drive the install copy separately (lines 492-514, 671-689):**
```python
def ssh_copy(*args, **kwargs):
    raise SshcpError("Bad hostname: somehost")   # install-time name-resolution blip on copy
self.mock_ssh.copy.side_effect = ssh_copy
```

**Recoverable-flag assertion (lines 361-364):**
```python
with self.assertRaises(ScannerError) as ctx:
    scanner.scan()
self.assertEqual(Localization.Error.REMOTE_SERVER_SCAN.format("Timed out"), str(ctx.exception))
self.assertTrue(ctx.exception.recoverable)
```

**Permanent-error regression guard to copy for the "name-res NOT over-generalized" tests (lines 531-552):**
```python
def ssh_shell(*args):
    self.ssh_run_command_count += 1
    if self.ssh_run_command_count == 1:
        return local_md5.encode()          # md5sum check
    elif self.ssh_run_command_count == 2:
        return json.dumps([]).encode()     # first scan succeeds
    elif self.ssh_run_command_count == 3:
        return b""                         # df call (silent fallback)
    elif self.ssh_run_command_count == 4:
        raise SshcpError("Incorrect password")  # second scan - permanent
    else:
        return json.dumps([]).encode()
self.mock_ssh.shell.side_effect = ssh_shell

scanner.scan()  # succeeds
with self.assertRaises(ScannerError) as ctx:
    scanner.scan()
self.assertFalse(ctx.exception.recoverable)
```

**Copy-from instructions:**
- New MAIN-SCAN tests: **name_resolution_retry_recovers_main_scan** (raise `SshcpError("Bad hostname: somehost")` on attempts N-1, succeed on attempt N → `scan()` returns, assert sleep called N-1 times), **name_resolution_retry_exhausts_main_scan** (`Bad hostname:` every attempt → `assertRaises(ScannerError)` with `assertFalse(ctx.exception.recoverable)` and the unchanged `Localization.Error.REMOTE_SERVER_SCAN.format(...)` message), **name_resolution_retry_bounded_main_scan** (assert `self.mock_ssh.shell` main-scan call count for that scan never exceeds `MAX_ATTEMPTS`), **name-resolution-classified** (`_is_name_resolution_ssh_error` returns True for `"Bad hostname: x"`, False for `"Incorrect password"` / `"Timed out"` / `"Connection refused by server"`), **transient_timeout_not_retried_in_scan** (`"Timed out"` on the first main-scan attempt → `scan()` raises immediately on attempt 1 with `recoverable=True`, `time.sleep` NOT called, main-scan shell invocation count == 1 — pins the name-resolution-only invariant / finding 2).
- New INSTALL-path tests (`__install_done=false` — the path that runs at startup + after every auto-restart; selectable via `-k install_name_resolution_recovers / install_name_resolution_bounded / install_timeout_unchanged`): **install_name_resolution_recovers** (md5sum-op variant: a fresh scanner, the md5sum check raises `SshcpError("Bad hostname: somehost")` k times then returns a non-matching md5 so the copy runs and succeeds, the main scan returns → `scan()` returns with NO ScannerError, sleep called k times; AND a copy-op variant via `self.mock_ssh.copy.side_effect` raising Bad hostname k times then succeeding), **install_name_resolution_bounded** (md5sum-op variant: the md5sum check raises `Bad hostname:` forever → `assertRaises(ScannerError)`, assert the md5sum-op call count never exceeds the cap, `assertFalse(ctx.exception.recoverable)`, message equals `Localization.Error.REMOTE_SERVER_INSTALL.format("Bad hostname: ...")`; AND a copy-op variant asserting the copy attempt count is bounded and the same REMOTE_SERVER_INSTALL recoverable=False surface), **install_timeout_unchanged** (md5sum-op variant: `SshcpError("Timed out")` → `scan()` raises immediately on attempt 1 with `Localization.Error.REMOTE_SERVER_INSTALL.format("Timed out")` and `recoverable=True`, `time.sleep` NOT called, md5sum-op count == 1; AND a copy-op timeout variant mirroring `test_raises_recoverable_error_on_copy_timeout`).
- **Patch `time.sleep` to make backoff instant** (no existing precedent in this suite; standard mock at the module under test):
  ```python
  with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
      files, _, _ = scanner.scan()
      self.assertEqual(2, mock_sleep.call_count)  # 3 attempts → 2 backoff sleeps
  ```
- **Do NOT touch** `test_raises_recoverable_error_on_first_run_timeout` (`:334`), `test_raises_recoverable_error_on_first_run_connection_refused` (`:366`), `test_recovers_after_first_run_timeout` (`:401`), `test_raises_nonrecoverable_error_on_wrong_password_after_first_run` (`:516`), `test_raises_nonrecoverable_error_on_host_key_change_after_first_run` (`:554`), `test_raises_recoverable_error_on_md5sum_timeout` (`:470`), `test_raises_recoverable_error_on_copy_timeout` (`:492`), `test_raises_nonrecoverable_error_on_md5sum_error` (`:240`), `test_raises_nonrecoverable_error_on_failed_copy` (`:671`), or the call-count tests (`:145`, `:631`) — they must pass UNCHANGED (Pitfall 2/3 regression net proving transient/permanent are not retried in-scan and that install/df call counts are preserved because their errors are not name-resolution).

---

### `src/python/tests/unittests/test_seedsyncarr.py` (test) — RECOV-01

**Analog:** the existing pure-static-method test classes.

**`test_detect_incomplete_config` (lines 141-155) — the template for asserting a pure helper across input variations:**
```python
def test_detect_incomplete_config(self):
    config = Seedsyncarr._create_default_config()
    ...
    self.assertFalse(Seedsyncarr._detect_incomplete_config(config))
    config.lftp.remote_address = incomplete_value
    self.assertTrue(Seedsyncarr._detect_incomplete_config(config))
```

**`TestSeedsyncarrStartupWarnings` (lines 198-263) — MagicMock-based static-method testing pattern:**
```python
Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
mock_logger.warning.assert_called_once()
```

**Copy-from instructions:**
- Test the NEW pure `_should_auto_restart(...)` directly (no `run()`/`main()` spin), mirroring `test_detect_incomplete_config`'s call-and-assert style, unpacking the `(should_restart, reset_applied)` tuple: **restart-within-cap** (`consecutive < cap`, run too young → `(True, False)`), **restart-cap-exhausted** (`consecutive >= cap`, run too young → `(False, False)`), **restart-reset / restart-reset-at-cap** (a `current_run_start` older than `reset_secs` → `(True, True)` even at the cap — finding 1), **restart-fresh-budget** (post-reset counter of 1, run too young → `(True, False)` — finding 2). Use `datetime` inputs (import `datetime, timedelta`; pass `now`/`current_run_start` explicitly to keep the helper pure and time-independent).
- **ServiceRestart constructor-compatibility tests (codex HIGH regression net):** import `ServiceRestart` and assert `str(ServiceRestart("restart requested")) == "restart requested"` with `.auto is False` / `.reset is False` (positional message preserved, flags default False); `ServiceRestart()` → empty message, both flags False; `ServiceRestart(auto=True, reset=True)` → both flags True. These pin the `*args` + keyword-only design.
- **Counter-normalization test:** assert the main()-side rule maps a reset-at-cap auto restart (consecutive=cap, auto=True, reset=True) to a next-counter of **1** (NOT cap+1), `auto=True, reset=False` → consecutive+1, and `auto=False` (UI) → unchanged.
- Imports already present in the file: `from unittest.mock import MagicMock, patch`, `from seedsyncarr import Seedsyncarr`, `from common import Config`. Add `from datetime import datetime, timedelta` and `from common import ServiceRestart` for the reset-threshold and constructor-compatibility tests.
- New test classes follow the existing naming convention `class TestSeedsyncarr...(unittest.TestCase):` (e.g. `TestSeedsyncarrAutoRestart`).

---

## Shared Patterns

### Error classification (substring-match on prefix tuples)
**Source:** `src/python/ssh/sshcp.py:14-22` (tuples) + `src/python/controller/scan/remote_scanner.py:18-28` (matchers)
**Apply to:** SCAN-01 (new `NAME_RESOLUTION_ERROR_PATTERNS` tuple + `_is_name_resolution_ssh_error` matcher). Classification stays centralized in `ssh/sshcp.py`; matchers are `@staticmethod` substring checks. Do NOT introduce regex or scatter classification into the helper body.

### One shared bounded retry helper (don't write two loops)
**Source:** no existing analog as a loop, but the constituent parts (constants convention, classification, raise shape, logging) all have in-repo analogs.
**Apply to:** SCAN-02. Factor the name-resolution retry into ONE private `__ssh_call_with_name_resolution_retry(ssh_call, op_label)` used by the main scan call AND the install md5sum/copy ops. Identical retry/backoff/exhaustion semantics with a single implementation; the helper only re-raises `SshcpError` so each caller's existing except produces its own localized surface.

### Recoverable/fatal signaling (reuse the existing flag, don't invent)
**Source:** `src/python/controller/scan/scanner_process.py:13-22` (`ScannerError(message, recoverable=...)`) consumed at `:95-98` (`run_loop` re-raises when `not e.recoverable`)
**Apply to:** SCAN-02/03 — the main-scan exhaustion raise is `ScannerError(REMOTE_SERVER_SCAN, recoverable=False)`; the install exhaustion surfaces via the unchanged `_install_scanfs` except as `ScannerError(REMOTE_SERVER_INSTALL, recoverable=False)`; the recovered-blip path returns normally and never raises. No new exception type, no new status field.
```python
except ScannerError as e:
    # Non-recoverable errors continue up as a fatal error
    if not e.recoverable:
        raise
    result = ScannerResult(timestamp=timestamp_start, files=[], failed=True, error_message=str(e))
```

### SCAN-03 user-facing surface (preserve byte-for-byte)
**Source:** `src/python/seedsyncarr.py:184-188` (`status.server.up = False` + `error_msg = str(exc)`) + `src/python/common/status.py` `ServerStatus.up`/`error_msg`
**Apply to:** SCAN-03 (both the scan-exhaustion REMOTE_SERVER_SCAN and install-exhaustion REMOTE_SERVER_INSTALL paths) + RECOV-01 cap-exhausted path. This exact pair of assignments is the only error surface; all paths route to it after their bounds exhaust. Do not change the localized message formats or these field semantics.

### Restart machinery (reuse `ServiceRestart` → `main()` `continue`)
**Source:** `src/python/common/error.py:14-18` (`ServiceRestart(AppError)`) + `src/python/seedsyncarr.py:192-194` (raise) + `:507-523` (`main()` catch → `continue`)
**Apply to:** RECOV-01. Add only the counter/cap/reset around this existing path, plus keyword-only `auto`/`reset` flags on `ServiceRestart` (via `__init__(self, *args, auto=False, reset=False)` with `super().__init__(*args)` to preserve the message contract). The full restart (terminate jobs, join, persist, re-init) is already implemented at `run()` `:199-224`.

### Pure static helper convention (testability)
**Source:** `src/python/seedsyncarr.py:365-400` (`_detect_incomplete_config`, `_emit_startup_warnings`) tested at `test_seedsyncarr.py:141-263`
**Apply to:** the new `_should_auto_restart(...)` — extract the restart decision into a pure `@staticmethod` so RECOV-01 is unit-testable without spinning `run()`/`main()`.

### Logging + log-injection safety
**Source:** `src/python/controller/scan/remote_scanner.py:124-126` (`sanitize_log_value` on untrusted values) + `:141-145` (lazy `%`-style logging)
**Apply to:** all new retry/restart log lines (including the shared helper's attempt-counter line). Lazy `%`-style logging (ruff/perf + matches codebase); `sanitize_log_value` for any path/host text (CWE-117 / Security V7). Never log the password.

### Command-injection guard (do not rebuild the quoted command)
**Source:** `src/python/controller/scan/remote_scanner.py:89-92,155` (`shlex.quote` on args) + the `copy(local_path=, remote_path=)` kwargs at `:180`
**Apply to:** the shared retry helper wraps the SAME already-quoted `self.__ssh.shell(...)` calls and the copy kwargs via lambdas that close over the existing strings. Do NOT reconstruct the command string inside the helper (Security V5). Regression guard: `test_df_command_quotes_remote_path` (`test_remote_scanner.py:798`).

---

## No Analog Found

None. Every touched file has a strong in-file or same-package analog — consistent with the phase's "wire together existing infrastructure" mandate. The single piece of genuinely new code (the shared bounded retry helper) has no exact analog as a *loop*, but its constituent parts (constants convention, classification, raise shape, logging) all have in-repo analogs cited above. There is **no existing retry/backoff helper** anywhere in `src/python/` (confirmed — CONTEXT D-02, RESEARCH); the planner should grab backoff defaults from RESEARCH Pattern 2 (Claude's discretion: 3 attempts / 1s→2s→4s exp / ±20% jitter / ≤4s ceiling).

---

## Metadata

**Analog search scope:** `src/python/ssh/`, `src/python/controller/scan/`, `src/python/common/`, `src/python/` (entrypoint), `src/python/tests/unittests/` (test_controller/test_scan, test_seedsyncarr, test_ssh, test_common)
**Files scanned (read in full or targeted):** `ssh/sshcp.py`, `controller/scan/remote_scanner.py`, `controller/scan/scanner_process.py`, `common/error.py`, `seedsyncarr.py` (run/main/static-helper regions), `tests/unittests/test_controller/test_scan/test_remote_scanner.py` (harness + key tests, incl. install md5sum/copy timeout tests), `tests/unittests/test_seedsyncarr.py` (static-helper test classes), `tests/unittests/test_common/test_error.py` (ServiceRestart message contract)
**Project conventions verified:** no `CLAUDE.md` in working dir; `.claude/skills/` and `.agents/skills/` contain only `aidesigner-frontend` (frontend skill, not applicable to this Python backend phase). CI runs `ruff check src/python/` as a SEPARATE gate from pytest (Pitfall 5 — every task must run both).
**Pattern extraction date:** 2026-06-21
