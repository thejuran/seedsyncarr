# Phase 97: Medium-Priority Python Coverage - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 3 test files + 1 baseline artifact (RATCHET-01)
**Analogs found:** 3 / 3 (all strong, same-suite analogs)

> **PATH CORRECTION (load-bearing):** CONTEXT.md and the design spec reference test
> paths like `tests/unit/test_common/...` and `tests/integration/test_web/...`. Those
> paths do NOT exist. The real test tree is rooted at `src/python/tests/` with two top
> dirs: `unittests/` (not `unit/`) and `integration/`. Pytest runs with
> `pythonpath = ["."]` from `src/python/`, so imports are `from tests.integration...`
> and `from common import ...`. The planner MUST use the corrected paths below.

| Context path (wrong)                                              | Actual path                                                                       |
|------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `tests/unit/test_common/test_multiprocessing_logger.py`          | `src/python/tests/unittests/test_common/test_multiprocessing_logger.py`          |
| `tests/integration/test_web/test_handler/test_config.py`         | `src/python/tests/integration/test_web/test_handler/test_config.py`              |
| `tests/integration/test_lftp/test_lftp_protocol.py`              | `src/python/tests/integration/test_lftp/test_lftp_protocol.py`                    |

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` (extend) | test (unit, threading) | event-driven / queue-consumer | same file — existing `TestMultiprocessingLogger` class | exact (extend in place) |
| `src/python/tests/integration/test_web/test_handler/test_config.py` (extend) OR `.../unittests/test_web/test_handler/test_config_handler.py` (extend) | test (SSRF guard) | request-response / transform | `test_config_handler.py` `TestConfigHandlerTestSonarrConnection` | exact (socket.getaddrinfo already stubbed there) |
| `src/python/tests/integration/test_lftp/test_lftp_protocol.py` (extend) | test (integration, real lftp binary) | streaming / parser→counter | same file — `TestLftpProtocol` + parser-error harness | role-match (see analog gap note) |
| `.planning/milestones/v1.3.0-COVERAGE-BASELINE.md` (new) | doc artifact (RATCHET-01) | n/a | Makefile `coverage-python` target | n/a — invocation mirror |

---

## Pattern Assignments

### 1. `test_multiprocessing_logger.py` (unit, event-driven, COVMED-01)

**Analog:** the existing class in the SAME file (`src/python/tests/unittests/test_common/test_multiprocessing_logger.py`). Extend it — do not create a new file.

**Imports / class scaffold pattern** (lines 1-23 of the existing file): `unittest.TestCase`, `testfixtures.LogCapture`, `pytest`, `from common import MultiprocessingLogger`, plus the `setUp`/`tearDown` that attach a `StreamHandler` to a named logger. Reuse verbatim.

**Timeout-guard pattern** (existing, line 25 etc.) — the spec MANDATES a timeout guard against thread-scheduling flake. The suite already uses the per-test decorator form:
```python
@pytest.mark.timeout(5)
def test_main_logger_receives_records(self):
```
`pytest-timeout` is a dev dep (`pyproject.toml:28`) and a global `timeout = 60` is set in `[tool.pytest.ini_options]` (pyproject.toml:71). Use the explicit `@pytest.mark.timeout(5)` form to match the existing tests — do not rely on the global.

**Listener-lifecycle drive pattern** (existing, lines 37-46): construct → start child process → `mp_logger.start()` → join child → `time.sleep(0.2)` to let the listener drain → `mp_logger.stop()`. The `stop()` call sets `__listener_shutdown` and `join()`s the thread. Mirror this start/drain/stop ordering for the new branches.

**Source branches to cover** (`src/python/common/multiprocessing_logger.py:67-86`) and how to trigger each from a test:
- **Handler raises during `handle(record)`** (line 75 → outer `except Exception` at 78-83): stashes `sys.exc_info()` into `__listener_exc_info`, logs, sets `__listener_shutdown`, breaks. Trigger by sending a record whose handling raises — e.g. attach a handler to `mp_logger.logger` (the `MPLogger` child) whose `emit`/`handle` raises, then push one record. NOTE: `handle` is called on `self.logger.getChild(record.name)` (line 75), so the failing handler must live on a logger in that child chain.
- **`propagate_exception()` re-raises** (`multiprocessing_logger.py:38-46`): after a handler-raise has been captured, call `mp_logger.propagate_exception()` and assert the original exception type/message is re-raised. Then assert a SECOND call is a no-op (it clears `__listener_exc_info` to `None` at line 45 before raising). Use `with self.assertRaises(...)`.
- **Inner-loop `queue.Empty` does NOT terminate the listener** (lines 76-77): the inner `break` only exits the drain loop; the outer `while not __listener_shutdown` continues. Verify by sending records, sleeping past `__LISTENER_SLEEP_INTERVAL_IN_SECS` (0.1s, line 20) so the queue empties, then sending MORE records and asserting they are still received → proves the listener survived an empty-queue cycle.
- **Clean shutdown** (existing tests already cover via `stop()`): the spec phrases this as "clean shutdown via sentinel value." The actual mechanism is the `threading.Event` (`__listener_shutdown`), not an in-band queue sentinel. Cover by asserting `mp_logger.stop()` joins without raising and `propagate_exception()` is a no-op after a clean run.

**Cross-thread state access:** `__listener_exc_info` is name-mangled and private. Tests assert via the PUBLIC API `propagate_exception()` (raises or no-ops), NOT by reaching into `_MultiprocessingLogger__listener_exc_info`. Matches the global rule "use a module's public API."

**Trivial-fix watch (D-05):** if the outer `except Exception` (line 78) is found to swallow an error that `propagate_exception` should surface, the in-scope fix is to narrow the catch / ensure capture-before-log. Borderline → defer to v1.4.0 with a STATE.md line referencing the red test.

---

### 2. SSRF `_validate_url` (COVMED-02)

**TWO candidate analog locations — recommend extending the UNIT file:**

`_validate_url` is a pure `@staticmethod` (`src/python/web/handler/config.py:55-85`). The richest existing analog is **`src/python/tests/unittests/test_web/test_handler/test_config_handler.py`**, classes `TestConfigHandlerTestSonarrConnection` / `TestConfigHandlerTestRadarrConnection`. That file already has the exact `socket.getaddrinfo` stubbing the spec mandates. The integration file `test_config.py` named in CONTEXT.md is webtest-based (`BaseTestWebApp`) and has NO `_validate_url` coverage today — going through the full bottle stack adds no value for pure-logic SSRF cases (CONTEXT.md D-note: "no bottle stack needed").

**Recommendation:** Add a dedicated `TestValidateUrl` class in `test_config_handler.py` that calls `ConfigHandler._validate_url(...)` directly (it is callable as a staticmethod), reusing the proven `socket` patch pattern. This is simpler and more targeted than the connection-handler indirection.

**socket.getaddrinfo stub pattern** (the load-bearing reusable, from `test_config_handler.py:131-139`):
```python
@patch('web.handler.config.socket')
def test_sonarr_rejects_private_ip(self, mock_socket):
    mock_socket.getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
    mock_socket.gaierror = socket.gaierror
    ...
```
Key details to mirror exactly:
- Patch target is `web.handler.config.socket` (the module-level import at `config.py:4`), NOT `socket` globally.
- `getaddrinfo` returns a list of 5-tuples; the IP string lives at `addr_info[4][0]` (consumed at `config.py:75`). So the return value is `[(None, None, None, None, (<ip_str>, 0))]`.
- **Re-assign `mock_socket.gaierror = socket.gaierror`** after patching — otherwise the `except socket.gaierror` at `config.py:82` references a MagicMock and won't catch. This is the easy-to-miss line; every existing SSRF test sets it.

**gaierror (unresolved hostname) pattern** — to hit `config.py:82-83` ("Cannot resolve hostname"):
```python
mock_socket.getaddrinfo.side_effect = socket.gaierror("name resolution failed")
mock_socket.gaierror = socket.gaierror
```

**Cases to cover (spec line 99 + CONTEXT specifics line 48)** — each is one `getaddrinfo.return_value` with the IP under test, asserting return value:
| Input host resolves to | Expected `_validate_url` return |
|---|---|
| `10.0.0.1` (IPv4 private) — regression baseline | `"URL resolves to a private/reserved IP address"` |
| `127.0.0.1` (IPv4 loopback) | private/reserved msg |
| `169.254.0.1` (IPv4 link-local) | private/reserved msg |
| `fe80::1` (IPv6 link-local) | private/reserved msg |
| `::1` (IPv6 loopback) | private/reserved msg |
| `fc00::1` (IPv6 unique-local) | private/reserved msg |
| `::ffff:10.0.0.1` (IPv6-mapped private IPv4) | **EXPECT private/reserved — see D-01** |
| (getaddrinfo raises gaierror) | `"Cannot resolve hostname"` |
| `8.8.8.8` (valid public) | `None` |
| scheme `ftp://...` / `file://...` (no socket call) | `"Only http and https URLs are allowed"` |
| no hostname (e.g. `http:///path`) | `"Invalid URL: no hostname"` |

The current guard is `addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local` (`config.py:78`). Python's `ipaddress` treats `::ffff:10.0.0.1` — write the `::ffff:10.0.0.1` test RED first to discover whether the current check blocks it.

**Trivial-fix (D-01/D-02, IN-SCOPE if RED):** if `::ffff:10.0.0.1` is NOT blocked, add an unmap-and-recheck before the final `return None`. Minimal shape: detect `addr.ipv4_mapped` and re-run the four checks against the unmapped IPv4. <10 lines, no public-API change, strengthens an existing security guard → in-scope per D-01. Do NOT add DNS-rebind handling (out of scope, see `config.py:59-62`).

**Error-message assertion style** (from the analogs): existing tests use `self.assertIn("private", body["error"])` and `self.assertIn("Only http and https", body["error"])`. For direct `_validate_url` tests, assert against the returned string directly (e.g. `self.assertIn("private/reserved", result)`).

---

### 3. LFTP `JobStatusParser` ValueError recovery (COVMED-03)

**Analog:** `src/python/tests/integration/test_lftp/test_lftp_protocol.py` `TestLftpProtocol` (real lftp binary harness, per D-03). Extend in place.

**ANALOG GAP (load-bearing — flag for planner):** The existing integration tests drive errors through *real lftp behavior* — `test_queue_dir_wrong_file_type` (lines 646-664), `test_queue_file_wrong_file_type` (667-684), `test_queue_missing_file` (687-702) all queue something invalid and assert `LftpError` ("Access failed" / "No such file") via `raise_pending_error()`. **None of them exercise `LftpJobStatusParserError` or the `__consecutive_status_errors` counter** (`lftp.py:303-313`). The real lftp binary produces well-formed `jobs -v` output, so a real-binary test CANNOT deterministically inject a *malformed parser line*. 

**The counter logic to cover** (`src/python/lftp/lftp.py:298-313`):
```python
def status(self) -> List[LftpJobStatus]:
    out = self.__run_command("jobs -v")
    try:
        statuses = self.__job_status_parser.parse(out)
        self.__consecutive_status_errors = 0          # reset on success
    except LftpJobStatusParserError:
        self.__consecutive_status_errors += 1          # increment on error
        if self.__consecutive_status_errors <= MAX_CONSECUTIVE_STATUS_ERRORS:
            self.logger.warning(f"Ignoring status error (count={self.__consecutive_status_errors})")
            statuses = []                              # swallow, return empty
        else:
            raise                                      # MAX (=2) exceeded → propagate
```
`MAX_CONSECUTIVE_STATUS_ERRORS = 2` (`lftp.py:12`). 3rd consecutive error raises.

**The parser-error trigger** — `LftpJobStatusParser.parse` wraps any internal `ValueError` (raised in ~30 places, e.g. `job_status_parser.py:432,514,579`) into `LftpJobStatusParserError` at `job_status_parser.py:723-726`:
```python
except ValueError as e:
    self.logger.error(...)
    raise LftpJobStatusParserError("Error parsing lftp job status")
```
A known-malformed `jobs -v` block already exists as a fixture in `test_job_status_parser.py:935-946` (ends with `bad string uh oh`) — reuse that shape as the malformed input.

**Recommended injection strategy (D-03/D-04, all four points):** The deterministic way to drive the counter through a `Lftp` instance is to make `jobs -v` return malformed output. Two options for the planner to choose at plan time:
- **(a) Patch the private command runner** — `unittest.mock.patch.object(self.lftp, '_Lftp__run_command', return_value=<malformed_jobs_output>)` then call `self.lftp.status()` repeatedly. Call #1 and #2 → returns `[]`, counter at 1 then 2. Call #3 → `with self.assertRaises(LftpJobStatusParserError)`. Then flip the patch to a valid (empty) `jobs -v` output and assert `status()` succeeds and the counter is reset (a subsequent malformed call returns `[]` again, proving reset to 0). Reaching into the name-mangled `_Lftp__run_command` couples to a private method — acceptable for a white-box recovery test but call it out in plan review.
- **(b) Patch the parser** — `patch.object(self.lftp._Lftp__job_status_parser, 'parse', side_effect=[LftpJobStatusParserError(...), LftpJobStatusParserError(...), LftpJobStatusParserError(...), []])` and assert the same increment→max-raise→reset sequence. This isolates the controller-counter behavior from parser internals and is the cleaner of the two.

This is genuinely a hybrid (uses the real-binary fixture's `Lftp` setUp but injects the malformed status), NOT a pure end-to-end real-lftp test. CONTEXT.md D-03 expects integration-layer; option (a)/(b) keeps the integration `Lftp` object while making the failure deterministic. If the planner prefers a true unit test, the parser-only error is already covered by `test_job_status_parser.py:945` and the counter could instead be tested in a new `unittests/test_lftp/` test against a `Lftp` with a stubbed run-command — but D-03 says integration, so default to extending `test_lftp_protocol.py`.

**Four points to assert (D-04):**
1. Malformed `jobs -v` → `parse()` raises `LftpJobStatusParserError` (parser side, fixture from `test_job_status_parser.py:935`).
2. `Lftp.status()` increments `__consecutive_status_errors` and returns `[]` while count ≤ 2.
3. 3rd consecutive (count > `MAX_CONSECUTIVE_STATUS_ERRORS`) → `status()` re-raises `LftpJobStatusParserError`.
4. A subsequent SUCCESSFUL `status()` resets the counter to 0 (`lftp.py:305`).

**Fixture teardown caveat:** `TestLftpProtocol.tearDown` (lines 123-126) calls `self.lftp.raise_pending_error()` then `self.lftp.exit()`. If a test patches `__run_command`, ensure the patch is removed (context-manager or `addCleanup`) before teardown so `exit()` runs against the real binary. Prefer `with patch.object(...)` scoping over decorators that outlive the assertion.

**Timeout marker:** match the suite — every active integration test uses `@pytest.mark.timeout(5)`.

**Trivial-fix watch (spec line 112 / D-05):** if the counter does NOT reset on success, the in-scope fix is the single `self.__consecutive_status_errors = 0` line (already present at `lftp.py:305` — verify it is reached). If a real defect needs >10 lines, defer to v1.4.0.

---

## Shared Patterns

### Test framework conventions (apply to all three plans)
**Source:** every test file under `src/python/tests/`
- `unittest.TestCase` classes (NOT bare pytest functions), `self.assertEqual` / `self.assertIn` / `self.assertRaises` assertions.
- `@pytest.mark.timeout(5)` on any test that drives threads, real subprocesses, or polling loops.
- `from common import ...` and `from lftp import ...` absolute imports (works because `pythonpath = ["."]`, pyproject.toml:70).
- `testfixtures.LogCapture` for asserting log records (see `test_multiprocessing_logger.py:41`).

### socket.getaddrinfo stubbing (SSRF)
**Source:** `src/python/tests/unittests/test_web/test_handler/test_config_handler.py:131-139`
**Apply to:** all COVMED-02 cases. Patch `web.handler.config.socket`, set `getaddrinfo.return_value`/`.side_effect`, and ALWAYS re-assign `mock_socket.gaierror = socket.gaierror`.

### Mocking private name-mangled members
**Source:** `test_lftp_manager.py:184-194` (patches `controller.lftp_manager.Lftp`); pattern for COVMED-03 white-box: `patch.object(obj, '_ClassName__member', ...)`.
**Apply to:** COVMED-03 if injecting at `_Lftp__run_command` or `_Lftp__job_status_parser`.

---

## RATCHET-01 — Baseline capture (cross-cutting, runs BEFORE any new test)

**Goal:** record current Python (line+branch) and Angular coverage verbatim into
`.planning/milestones/v1.3.0-COVERAGE-BASELINE.md`, committed before phase-97 tests land (D-06).

**Existing invocation to mirror** (do NOT invent a new command):
- **Makefile target** (`Makefile:138-139`):
  ```make
  coverage-python:
      cd ${SOURCEDIR}/python && poetry run pytest --cov --cov-report=term-missing --cov-report=html
  ```
- **CI invocation** (`src/docker/test/python/Dockerfile:60`): `CMD ["pytest", "-v", "-p", "no:cacheprovider"]` inside the `seedsyncarr_test_python` container (compose: `src/docker/test/python/compose.yml`). The real-lftp + sshd setup lives in `entrypoint.sh`, so the LFTP integration coverage only materializes inside that container — capture the baseline via the containerized run (`make run-tests-python`) if LFTP integration lines must count, or note that `make coverage-python` (host poetry) omits the real-lftp integration suite.

**Coverage config (already wired — DO NOT change in this phase; it is the Phase-100 ratchet target):** `src/python/pyproject.toml`
- `[tool.coverage.run]` `branch = true`, `source = ["."]`, `omit = ["tests/*", "docs/*"]` (lines 79-85).
- `[tool.coverage.report]` `fail_under = 84` (line 88) — current Python bar. CONTEXT.md §code_context cites the v1.1.2 baseline as 85.05%; the live config floor is 84. Record BOTH the configured `fail_under` and the freshly-measured total in the baseline file so Phase 100 has an unambiguous "before".
- `[tool.pytest.ini_options]` `timeout = 60` (line 71).

**Do not ratchet `fail_under` in this phase** — that is Plan 100-03. RATCHET-01 only captures and commits the numbers.

---

## No Analog Found

None. All three test targets have strong same-suite analogs. The one structural gap (not a missing analog) is documented inline above: **the LFTP integration suite has no existing example of driving `LftpJobStatusParserError` / the consecutive-error counter** — it only drives real-lftp `LftpError` paths — so COVMED-03 must introduce a deterministic malformed-status injection (parser or `__run_command` patch) rather than copy an existing error-driving test verbatim.

---

## Metadata

**Analog search scope:** `src/python/tests/unittests/`, `src/python/tests/integration/`, `src/python/{common,web,lftp}/`, `Makefile`, `src/python/pyproject.toml`, `src/docker/test/python/`.
**Files scanned:** 11 (3 source-under-test, 5 analog tests, Makefile, pyproject.toml, Dockerfile/compose/entrypoint).
**Pattern extraction date:** 2026-05-28
