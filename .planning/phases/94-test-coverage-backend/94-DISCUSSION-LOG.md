# Phase 94: Test Coverage -- Backend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 94-test-coverage-backend
**Areas discussed:** SSE test harness, Webhook integration depth, SSH mocking strategy, ActiveScanner isolation

---

## SSE Test Harness

| Option | Description | Selected |
|--------|-------------|----------|
| Thin WSGI iterator | Direct web_app(environ, start_response) call. Zero deps, Timer-stop compatible, exercises real WSGI path. | ✓ |
| httpx WSGITransport | Lazy streaming client. Requires restructuring tests to collect N chunks instead of Timer-stop. | |
| Threading + waitress | Live server in daemon thread. Production-closest but port-allocation risk in CI Docker. | |

**User's choice:** Thin WSGI iterator (recommended option)
**Notes:** Preserves existing Timer-stop pattern from skipped tests. Helper module constructs WSGI environ dict.

---

## Webhook Integration Depth

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP → dispatch boundary | Mock webhook_manager, assert enqueue_import called. Follows BaseTestWebApp pattern, closes routing-layer gap. | ✓ |
| Full flow through process() | Real WebhookManager, call process() after POST. Proves queue handoff but duplicates existing unit coverage. | |

**User's choice:** HTTP → dispatch boundary (recommended option)
**Notes:** Existing test_webhook_handler.py (298 lines) already covers internals. Gap is Bottle routing + WSGI dispatch layer only.

---

## SSH Mocking Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mock Sshcp via patch | patch('controller.delete.delete_process.Sshcp'). Assert rm -rf command, SshcpError handling. Matches project pattern. | ✓ |
| Real SSH via Docker | Integration test with actual SSH container. Proves file removal but heavy setup for 50 lines of join+quote logic. | |
| Paramiko stub | Replace pexpect with paramiko for testability. Not in pyproject.toml — scope creep. | |

**User's choice:** Mock Sshcp via patch (recommended option)
**Notes:** Matches pattern in test_extract_process.py. COVER-05 targets command construction + error handling, not SSH transport.

---

## ActiveScanner Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Mock Queue + mock SystemScanner | Deterministic, zero timing deps, matches project MagicMock pattern. Cross-process IPC tested elsewhere. | ✓ |
| Real Queue + mock SystemScanner | Exercises actual queue-drain behavior but needs sleep guard to avoid feeder-thread flakiness. | |
| Real subprocesses | Full cross-process fidelity. Slow, flaky, zombie risk, contradicts project pattern. | |

**User's choice:** Mock Queue + mock SystemScanner (recommended option)
**Notes:** Cross-process IPC is ScannerProcess's responsibility (already tested in test_scanner_process.py).

---

## Claude's Discretion

None — all areas were discussed and decided by the user.

## Deferred Ideas

None — discussion stayed within phase scope.
