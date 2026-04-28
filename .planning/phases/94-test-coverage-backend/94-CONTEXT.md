# Phase 94: Test Coverage -- Backend - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add dedicated tests for 4 previously untested backend paths: SSE streaming integration (COVER-01), webhook end-to-end through the web layer (COVER-04), DeleteRemoteProcess unit tests (COVER-05), and ActiveScanner unit tests (COVER-06).

</domain>

<decisions>
## Implementation Decisions

### SSE Test Harness (COVER-01)
- **D-01:** Use a thin WSGI iterator harness — call `web_app(environ, start_response)` directly to get the SSE generator, iterate it in the test thread. Zero new dependencies.
- **D-02:** Preserve the existing Timer-stop pattern from the skipped tests. The Timer fires during `time.sleep()` inside the generator, sets the stop flag, and the generator exits on the next loop check.
- **D-03:** Build a small helper (e.g., `tests/helpers/wsgi_stream.py`) that constructs the WSGI environ dict and wraps the call. The 3 existing skipped test files (`test_stream_status.py`, `test_stream_model.py`, `test_stream_log.py`) should be unskipped and updated to use this harness.

### Webhook Integration (COVER-04)
- **D-04:** Test to HTTP → controller dispatch boundary only. Mock `webhook_manager`, assert `enqueue_import` called with correct args after `self.test_app.post("/server/webhook/sonarr", ...)`.
- **D-05:** Follow the established `BaseTestWebApp` pattern — `webhook_manager` is already wired as a `MagicMock` by `WebAppBuilder`. This matches how `test_controller.py` tests POST routes.
- **D-06:** Do NOT test through to `WebhookManager.process()` — that path is already covered by existing `test_webhook_manager.py` unit tests. The gap is specifically the Bottle routing + WSGI dispatch layer.

### SSH Mocking for DeleteRemoteProcess (COVER-05)
- **D-07:** Mock `Sshcp` at the module level via `patch('controller.delete.delete_process.Sshcp')`. Matches the pattern used in `test_extract_process.py`.
- **D-08:** Assert exact `rm -rf <shlex.quoted-path>` command string passed to `shell()`. Test `SshcpError` is caught and logged. Verify constructor args (host, port, user, password) forwarded correctly.
- **D-09:** Do NOT use real SSH via Docker — the class logic is `os.path.join` + `shlex.quote`, which doesn't benefit from a live SSH daemon. Integration-level SSH testing is already covered by `test_sshcp.py`.

### ActiveScanner Isolation (COVER-06)
- **D-10:** Mock both `multiprocessing.Queue` and `SystemScanner` via `unittest.mock`. Zero timing dependencies, fully deterministic.
- **D-11:** Cross-process IPC fidelity is `ScannerProcess`'s responsibility (already tested in `test_scanner_process.py`). ActiveScanner tests focus on queue-drain logic, scan scheduling, and result aggregation.
- **D-12:** Test paths: empty queue on first scan, multiple `set_active_files` calls (drain loop), `SystemScannerError` suppression, and the `(files, None, None)` return contract.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — COVER-01, COVER-04, COVER-05, COVER-06 requirement definitions

### SSE Streaming (COVER-01)
- `src/python/web/web_app.py` — SSE streaming implementation, `IStreamHandler` interface, stop-flag mechanism
- `src/python/web/handler/stream_heartbeat.py` — HeartbeatStreamHandler (simplest IStreamHandler example, good reference for test setup)
- `src/python/web/serialize/serialize_status.py` — SerializeStatus used by stream_status handler
- `src/python/web/serialize/serialize_model.py` — SerializeModel used by stream_model handler
- `src/python/web/serialize/serialize_log_record.py` — SerializeLogRecord used by stream_log handler
- `src/python/tests/integration/test_web/test_handler/test_stream_status.py` — Existing skipped SSE test (unskip and update)
- `src/python/tests/integration/test_web/test_handler/test_stream_model.py` — Existing skipped SSE test (unskip and update)
- `src/python/tests/integration/test_web/test_handler/test_stream_log.py` — Existing skipped SSE test (unskip and update)

### Webhook Integration (COVER-04)
- `src/python/web/handler/webhook.py` — WebhookHandler (HMAC validation, title extraction, dispatch)
- `src/python/tests/unittests/test_web/test_webhook_handler.py` — Existing unit tests (298 lines, covers internals — don't duplicate)
- `src/python/tests/integration/test_web/test_web_app.py` — BaseTestWebApp base class for integration tests
- `src/python/web/web_app_builder.py` — WebAppBuilder wires webhook_manager as MagicMock for tests
- `src/python/tests/integration/test_web/test_handler/test_controller.py` — Reference for POST-through-webtest pattern

### DeleteRemoteProcess (COVER-05)
- `src/python/controller/delete/delete_process.py` — DeleteRemoteProcess and DeleteLocalProcess (50 lines)
- `src/python/ssh/sshcp.py` — Sshcp wrapper class (mock target)
- `src/python/tests/integration/test_controller/test_extract/test_extract.py` — Reference for Sshcp mock pattern

### ActiveScanner (COVER-06)
- `src/python/controller/scan/active_scanner.py` — ActiveScanner (52 lines, multiprocessing.Queue + SystemScanner)
- `src/python/controller/scan/scanner_process.py` — ScannerProcess (cross-process IPC, already tested)
- `src/python/tests/unittests/test_controller/test_scan_manager.py` — Reference for scan-related mock patterns
- `src/python/tests/unittests/test_controller/test_scan/test_scanner_process.py` — Reference for scanner mock patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseTestWebApp` (webtest WSGI harness): Base class for webhook integration tests — already wires `webhook_manager` as MagicMock
- `tests/helpers.py` and `tests/utils.py`: Existing test helpers to check before creating new ones
- Existing Timer-stop pattern in skipped SSE tests: Preserve and reuse after switching to WSGI iterator harness

### Established Patterns
- Integration tests inherit `BaseTestWebApp`, use `self.test_app.get/post()` for HTTP assertions
- Unit tests use `unittest.mock.patch` at module level for dependency injection
- `MagicMock` used for controller/manager dependencies across all integration handler tests
- `conftest.py` provides shared pytest fixtures (logger, tmp paths)

### Integration Points
- SSE harness helper must construct a valid Bottle-compatible WSGI environ (PATH_INFO, wsgi.input, etc.)
- Webhook test connects through Bottle routing registered by WebAppBuilder
- DeleteRemoteProcess tests mock `Sshcp` constructor call inside `__init__`
- ActiveScanner tests mock `multiprocessing.Queue` and `SystemScanner` at class level

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following the patterns established in prior phases.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 94-Test Coverage -- Backend*
*Context gathered: 2026-04-28*
