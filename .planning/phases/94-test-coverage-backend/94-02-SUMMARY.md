---
phase: 94-test-coverage-backend
plan: "02"
subsystem: python-tests
tags:
  - testing
  - coverage
  - webhook
  - delete-remote
  - active-scanner
dependency_graph:
  requires: []
  provides:
    - COVER-04 webhook integration tests
    - COVER-05 DeleteRemoteProcess unit tests
    - COVER-06 ActiveScanner unit tests
  affects:
    - src/python/tests/integration/test_web/test_handler/
    - src/python/tests/unittests/test_controller/
tech_stack:
  added: []
  patterns:
    - BaseTestWebApp integration test pattern
    - Module-level patch via addCleanup pattern
    - stdlib queue.Queue as multiprocessing.Queue substitute
key_files:
  created:
    - src/python/tests/integration/test_web/test_handler/test_webhook.py
    - src/python/tests/unittests/test_controller/test_delete_process.py
    - src/python/tests/unittests/test_controller/test_scan/test_active_scanner.py
  modified: []
decisions:
  - "Used stdlib queue.Queue via side_effect=lambda: queue.Queue() to replace multiprocessing.Queue, avoiding pickle serialization issues with MagicMock in the ActiveScanner tests"
  - "Patch target for Queue is controller.scan.active_scanner.multiprocessing.Queue (not multiprocessing.Queue) because active_scanner imports as 'import multiprocessing'"
  - "Accessed webhook_manager via name-mangled attribute _WebhookHandler__webhook_manager rather than refactoring WebhookHandler to expose it publicly"
metrics:
  duration: "~8m"
  completed_date: "2026-04-28"
  tasks_completed: 3
  files_created: 3
  tests_added: 13
---

# Phase 94 Plan 02: Backend Test Coverage Gaps Summary

**One-liner:** 13 new tests closing COVER-04/05/06 coverage gaps: webhook Bottle-dispatch integration, DeleteRemoteProcess SSH construction and error handling, ActiveScanner queue-drain and error suppression.

## What Was Built

Three new test files targeting previously untested backend paths:

**Task 1 — Webhook integration (5 tests, commit b69e7c8)**
`src/python/tests/integration/test_web/test_handler/test_webhook.py`

Tests the Bottle routing + WSGI dispatch layer from HTTP POST through to `webhook_manager.enqueue_import`. Inherits `BaseTestWebApp` (same pattern as `test_controller.py`). Accesses the MagicMock webhook manager via the Python name-mangled attribute `_WebhookHandler__webhook_manager`. No HMAC header needed because `Config().general.webhook_secret` defaults to empty, so `_verify_hmac()` short-circuits.

Covers:
- Sonarr Download event — enqueues with `("Sonarr", basename(sourcePath))`
- Radarr Download event — enqueues with `("Radarr", basename(sourcePath))`
- Sonarr Test event — returns 200, no enqueue
- Sonarr Grab event — returns 200, no enqueue
- Radarr Test event — returns 200, no enqueue

**Task 2 — DeleteRemoteProcess unit tests (4 tests, commit c512609)**
`src/python/tests/unittests/test_controller/test_delete_process.py`

Patches `controller.delete.delete_process.Sshcp` at module level (not `ssh.Sshcp`) since `delete_process.py` uses `from ssh import Sshcp`. Follows the `setUp`/`addCleanup` pattern from `test_extract_process.py`.

Covers:
- Sshcp constructor called with correct host/port/user/password kwargs
- Sshcp constructor called with `password=None`
- `run_once()` issues `rm -rf <shlex.quote(path)>` via `shell()`
- `SshcpError` caught and logged, not re-raised

**Task 3 — ActiveScanner unit tests (4 tests, commit 563fb35)**
`src/python/tests/unittests/test_controller/test_scan/test_active_scanner.py`

Patches `controller.scan.active_scanner.multiprocessing.Queue` with `side_effect=lambda: queue.Queue()`, replacing the multiprocessing queue with a stdlib in-process queue. This avoids pickle serialization issues when MagicMock objects flow through `multiprocessing.Queue`. Patches `SystemScanner` at module level.

Covers:
- Empty queue: `scan()` returns `([], None, None)` on first call
- Single `set_active_files` then `scan()` returns the scanned file
- Multiple `set_active_files` calls: drain loop discards old lists, uses last
- `SystemScannerError` suppressed, returns `([], None, None)`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All tests exercise real logic paths via mocks. No placeholder assertions.

## Threat Flags

None. Test-only phase, no production code changes, no new attack surface.

## Self-Check: PASSED

Files created:
- FOUND: src/python/tests/integration/test_web/test_handler/test_webhook.py
- FOUND: src/python/tests/unittests/test_controller/test_delete_process.py
- FOUND: src/python/tests/unittests/test_controller/test_scan/test_active_scanner.py

Commits:
- FOUND: b69e7c8 (test(94-02): add webhook integration tests through Bottle web layer)
- FOUND: c512609 (test(94-02): add DeleteRemoteProcess unit tests)
- FOUND: 563fb35 (test(94-02): add ActiveScanner unit tests)

Test results: 13/13 passed in combined run.
