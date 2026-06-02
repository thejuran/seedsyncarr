---
phase: 112-defensive-guards-code-hardening
plan: 02
subsystem: application-startup
tags: [startup-warnings, security, logging, webhook, config-fallback, hardening, tdd]
requirements: [GUARD-01, GUARD-02, GUARD-06]

dependency_graph:
  requires: []
  provides:
    - GUARD-01: "[SECURITY] prefix on all four startup warning strings in _emit_startup_warnings"
    - GUARD-02: "accept-any-caller warning suppressed in fail-closed state (require_secret=True)"
    - GUARD-06: "legacy ~/.seedsync fallback warning emitted via configured logger post-_create_logger"
  affects:
    - src/python/seedsyncarr.py
    - src/python/tests/unittests/test_seedsyncarr.py

tech_stack:
  added: []
  patterns:
    - "tuple return from @staticmethod to thread warning out past a pre-logger boundary"
    - "MagicMock + call_args_list assertion style for startup warning matrix tests"

key_files:
  modified:
    - path: src/python/seedsyncarr.py
      description: "_emit_startup_warnings condition fix (GUARD-02) + [SECURITY] prefixes (GUARD-01); _parse_args tuple return + legacy warning string (GUARD-06); __init__ call site unpack + post-logger emission"
    - path: src/python/tests/unittests/test_seedsyncarr.py
      description: "3 new RED/GREEN tests (GUARD-02 matrix x2, GUARD-06 fallback x1); 9 existing _parse_args call sites updated to unpack tuple; patch import added"

decisions:
  - "Implemented Option A (tuple return) for GUARD-06 — warning lands in configured log stream alongside GUARD-01/02 warnings, not on stderr"
  - "Used % string formatting to pre-format the legacy fallback warning message inside _parse_args so it can be emitted via logger.warning(message) without format args post-logger"
  - "Left _parse_args assertRaises(SystemExit) test call site (line 39) unchanged — SystemExit is raised before return so tuple unpacking is never attempted there"
  - "[SECURITY] prefix applied to logger.info else-branch as well (5 total occurrences) for consistent visual style; stays at info level"

metrics:
  duration_minutes: 4
  completed: 2026-06-02
  tasks_completed: 3
  files_modified: 2
---

# Phase 112 Plan 02: GUARD-01/02/06 Startup Warning Hardening Summary

**One-liner:** TDD fix making the webhook warning matrix match runtime behavior (GUARD-02), add [SECURITY] log prominence (GUARD-01), and surface the legacy ~/.seedsync fallback through the configured logger post-_create_logger (GUARD-06).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing GUARD-02 matrix + GUARD-06 fallback tests | 042e212 | test_seedsyncarr.py |
| 2 (GREEN) | Fix GUARD-02 warning correctness + GUARD-01 prominence | 478dfbb | seedsyncarr.py |
| 3 (GREEN) | Surface legacy fallback warning via configured logger (GUARD-06) | d94684c | seedsyncarr.py, test_seedsyncarr.py |

## What Was Built

**GUARD-02 (correctness fix):** Changed `if not config.general.webhook_secret:` to `if not config.general.webhook_secret and not config.general.webhook_require_secret:` on line 374 of `_emit_startup_warnings`. The "accept requests from any caller" warning now fires only when the endpoint actually accepts unauthenticated callers. In the fail-closed state (empty secret + `require_secret=True`), only the 503 warning fires — which accurately reflects `webhook.py:54-60` runtime behavior.

**GUARD-01 (prominence):** Updated all four `logger.warning` strings and the `logger.info` else-branch from `"Security:"` prefix to `"[SECURITY]"` for visual distinctiveness in the log stream. Level unchanged at `logging.warning` / `logging.info`.

**GUARD-06 (fallback surfacing):** Changed `_parse_args` from returning `args` to returning `(args, legacy_fallback_warning: str | None)`. The bare `logging.warning()` call (which fired before `_create_logger` to an unconfigured root logger) was replaced with a % string assignment. The `__init__` call site unpacks the tuple, and `if legacy_fallback_warning: logger.warning(legacy_fallback_warning)` emits the warning after `_create_logger`. Auto-fallback behavior preserved.

**Tests:** 3 new tests: `test_startup_require_secret_without_secret_does_not_warn_accept_any_caller` (GUARD-02 suppression), `test_startup_require_secret_without_secret_warns_503` (GUARD-02 pin), `test_parse_args_emits_legacy_fallback_warning` (GUARD-06). All 9 existing `_parse_args` test call sites updated to unpack the tuple.

## Deviations from Plan

None — plan executed exactly as written. All three guards implemented per their CONTEXT.md decisions (D-05, D-06, D-07, D-11, D-12). Option A chosen for GUARD-06 as directed (D-11 preferred).

## TDD Gate Compliance

- RED commit: `042e212` — `test(112-02): add RED tests for GUARD-02 matrix + GUARD-06 fallback` — confirmed both new behavioral tests failed before implementation
- GREEN commit (Task 2): `478dfbb` — GUARD-02 suppression test turned green
- GREEN commit (Task 3): `d94684c` — GUARD-06 fallback test turned green
- All 22 tests in `test_seedsyncarr.py` pass after Task 3; `assertEqual(3, ...)` count preserved

## Known Stubs

None — all changes are correctness/visibility fixes; no stub data.

## Threat Flags

No new threat surface introduced. GUARD-01/02/06 warnings interpolate only directory paths and posture flags — no secret values logged. The [SECURITY] prefix change is text-only.

## Self-Check: PASSED

- src/python/seedsyncarr.py: FOUND (modified, committed in 478dfbb and d94684c)
- src/python/tests/unittests/test_seedsyncarr.py: FOUND (modified, committed in 042e212 and d94684c)
- Commit 042e212: FOUND (RED test commit)
- Commit 478dfbb: FOUND (GUARD-02/GUARD-01 GREEN)
- Commit d94684c: FOUND (GUARD-06 GREEN)
- All 22 tests PASS
- ruff whole-tree: All checks passed!
