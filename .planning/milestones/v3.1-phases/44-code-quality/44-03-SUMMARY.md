---
phase: 44-code-quality
plan: 03
subsystem: web-api-correctness
tags: [http-methods, rest, security, type-annotations, rate-limiter]
dependency_graph:
  requires: []
  provides: [POST/DELETE mutation endpoints, instance-level rate limiter, specific return type annotations]
  affects: [src/python/web/handler/controller.py, src/python/web/web_app.py, src/python/controller/controller.py, src/angular/src/app/services/files/model-file.service.ts, src/angular/src/app/services/utils/rest.service.ts]
tech_stack:
  added: []
  patterns: [POST for state-changing operations, DELETE for destructive operations, instance-level mutable state, specific type annotations]
key_files:
  created: []
  modified:
    - src/python/web/web_app.py
    - src/python/web/handler/controller.py
    - src/python/controller/controller.py
    - src/angular/src/app/services/utils/rest.service.ts
    - src/angular/src/app/services/files/model-file.service.ts
    - src/angular/src/app/tests/unittests/services/files/model-file.service.spec.ts
decisions:
  - "POST for queue/stop/extract (CODE-09): these are state-changing operations; GET requests can be unintentionally triggered by browser prefetch and crawlers"
  - "DELETE for delete_local/delete_remote (CODE-09): semantically correct HTTP verb for destructive operations"
  - "Instance-level _bulk_request_times and _bulk_rate_lock (CODE-03): class-level state is shared across all handler instances; per-instance rate limiting is the correct semantics for request isolation"
  - "Import ScannerResult from .scan and ExtractStatusResult/ExtractCompletedResult from .extract to enable precise return type annotations (CODE-06): replaces opaque Optional[object] with domain-specific types"
  - "RestService.post() and RestService.delete() follow same pipe(map, catchError, shareReplay) pattern as sendRequest() — zero behavioral divergence, just different HTTP verb"
metrics:
  duration_seconds: 224
  completed_date: 2026-02-24
  tasks_completed: 2
  files_modified: 6
  tests_run: 425
  tests_passed: 425
---

# Phase 44 Plan 03: HTTP Method Correctness and Rate Limiter Instance Isolation Summary

**One-liner:** POST/DELETE for all mutation endpoints replacing improper GET; rate limiter state moved from class-level to per-instance; controller return types narrowed from Optional[object] to domain-specific ScannerResult/ExtractStatusResult/ExtractCompletedResult.

## What Was Built

### Task 1: Backend — POST/DELETE Routes and Instance-Level Rate Limiter

**web_app.py** — Added `add_delete_handler` method:
```python
def add_delete_handler(self, path: str, handler: Callable):
    self.delete(path)(handler)
```

**controller.py (web handler)** — Three changes:
1. `add_routes` now uses `add_post_handler` for queue/stop/extract and `add_delete_handler` for delete_local/delete_remote (was: `add_handler` = GET for all five)
2. `__init__` now initializes `self._bulk_request_times: List[float] = []` and `self._bulk_rate_lock = Lock()` (was: class-level declarations)
3. `_check_bulk_rate_limit` now references `self._bulk_request_times` and `self._bulk_rate_lock` (was: `ControllerHandler._bulk_request_times` and `ControllerHandler._bulk_rate_lock`)

**controller/controller.py** — Imported `ScannerResult` from `.scan` and `ExtractStatusResult`, `ExtractCompletedResult` from `.extract`; updated:
- `_collect_scan_results` return type: `Tuple[Optional[object], Optional[object], Optional[object]]` → `Tuple[Optional[ScannerResult], Optional[ScannerResult], Optional[ScannerResult]]`
- `_collect_extract_results` return type: `Tuple[Optional[object], List]` → `Tuple[Optional[ExtractStatusResult], List[ExtractCompletedResult]]`

### Task 2: Frontend — POST/DELETE in Angular Service

**rest.service.ts** — Added `post()` and `delete()` methods following the same `pipe(map, catchError, shareReplay)` pattern as `sendRequest()`.

**model-file.service.ts** — Changed five command methods:
- `queue()`: `sendRequest(url)` → `post(url)`
- `stop()`: `sendRequest(url)` → `post(url)`
- `extract()`: `sendRequest(url)` → `post(url)`
- `deleteLocal()`: `sendRequest(url)` → `delete(url)`
- `deleteRemote()`: `sendRequest(url)` → `delete(url)`

**model-file.service.spec.ts** — Updated 10 tests (5 pairs):
- "should send a GET on X command" → "should send a POST/DELETE on X command"
- "should send correct GET requests on X command" → "should send correct POST/DELETE requests on X command"
- Added `expect(req.request.method).toBe("POST"/"DELETE")` assertions to all command tests

## Test Results

- Python unit tests (test_controller_handler.py): 38/38 passed
- Angular unit tests: 387/387 passed

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All 6 modified files exist. Both task commits (a50a6ec, 714dcaf) confirmed in git log.
