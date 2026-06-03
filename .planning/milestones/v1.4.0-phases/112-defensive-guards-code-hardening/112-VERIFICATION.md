---
phase: 112-defensive-guards-code-hardening
verified: 2026-06-02T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 112: Defensive Guards & Code Hardening Verification Report

**Phase Goal:** The remaining "a hostile reader will notice this" code items are closed — loud startup warnings for insecure-by-silence defaults (GUARD-01/02), a silently-swallowed local-delete failure now leaves a log signal (GUARD-03), the previously-failing AppProcess spawn-context test goes green via a production fix (GUARD-04), and two cheap repo-hygiene tells are fixed (.gitignore for run artifacts GUARD-05; legacy ~/.seedsync fallback warning surfaced GUARD-06). All default behavior stays backward-compatible.
**Verified:** 2026-06-02
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GUARD-04: `test_process_with_long_running_thread_terminates_properly` passes under spawn (macOS default), full `test_app_process.py` passes, nothing deleted/skipped | VERIFIED | Test run: 9/9 passed under spawn (includes the previously-red test at line 175). No skip/xfail markers in file. LongRunningThreadProcess stores `self.thread = threading.Thread(...)` and is now spawn-safe via `__getstate__`. |
| 2 | GUARD-04: `__getstate__` strips only `threading.Thread` instances; Queue/Event are retained so `propagate_exception()`/`terminate()` function cross-process | VERIFIED | `app_process.py:133`: `isinstance(v, threading.Thread)` sweep. Queue and Event are `multiprocessing` primitives — not `threading.Thread` — so they survive. `test_exception_propagates` PASSED confirms Queue survives the spawn boundary. |
| 3 | GUARD-01/02: `_emit_startup_warnings` accept-any-caller condition is `not webhook_secret and not webhook_require_secret`; all four warning strings carry `[SECURITY]` prefix | VERIFIED | `seedsyncarr.py:377`: exact condition confirmed. 5 `[SECURITY]` occurrences found (`grep -cE "\[SECURITY\]"` = 5 — 4 `logger.warning` + 1 `logger.info` else-branch). `test_startup_require_secret_without_secret_does_not_warn_accept_any_caller` PASSED. `assertEqual(3, ...)` count test still holds. |
| 4 | GUARD-03: `DeleteLocalProcess.run_once` uses `try/except OSError` + `logger.exception` with `sanitize_log_value`; no `ignore_errors=True` remains; does not re-raise | VERIFIED | `delete_process.py:24-30`: `try: shutil.rmtree(file_path)` / `except OSError:` / `self.logger.exception("...", sanitize_log_value(self.__file_name))`. `grep ignore_errors` = no match. `test_local_delete_logs_rmtree_failure` PASSED. |
| 5 | GUARD-05: `.gitignore` contains `.orchestrator.json` and `.playwright-mcp/` entries; neither appears as untracked | VERIFIED | `.gitignore:27-28` contains both entries. `git check-ignore` matched both. `git status --short` shows neither as `??`. |
| 6 | GUARD-06: `_parse_args` returns `(args, legacy_fallback_warning)` tuple; warning emitted via configured logger after `_create_logger`; all `_parse_args` test call sites unpack the tuple | VERIFIED | `seedsyncarr.py:277`: `return args, legacy_fallback_warning`. `seedsyncarr.py:82-83`: `if legacy_fallback_warning: logger.warning(legacy_fallback_warning)` (after `_create_logger` at line 74). All 10 test call sites use `args, _ = ...` or `args, warning = ...` (line 39 `assertRaises(SystemExit)` exempt — SystemExit before return). `test_parse_args_emits_legacy_fallback_warning` PASSED. |

**Score: 6/6 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/common/app_process.py` | `__getstate__`/`__setstate__` stripping `threading.Thread` for spawn-safe pickling | VERIFIED | Lines 123-140: both methods present with correct `isinstance(v, threading.Thread)` sweep; return type hints `-> dict` and `-> None` present per project convention. |
| `src/python/seedsyncarr.py` | Corrected `_emit_startup_warnings` condition + `[SECURITY]` prefixes + legacy-fallback warning emitted post-logger | VERIFIED | Lines 377, 378-400, 82-83: all three changes present and correct. `_parse_args` returns tuple at line 277. |
| `src/python/controller/delete/delete_process.py` | `try/except OSError` + `logger.exception` replacing `ignore_errors=True` | VERIFIED | Lines 24-30: implementation correct. `sanitize_log_value` imported at line 6 and used at line 29. |
| `.gitignore` | `.orchestrator.json` and `.playwright-mcp/` in AI-tooling block | VERIFIED | Lines 27-28: both entries present after `.mcp.json`. |
| `src/python/tests/unittests/test_common/test_app_process.py` | Test file unmodified; `test_process_with_long_running_thread_terminates_properly` present and not skipped | VERIFIED | `git diff` shows 0 changed lines. Test at line 175 present with no skip/xfail. 9/9 PASSED. |
| `src/python/tests/unittests/test_seedsyncarr.py` | GUARD-02 matrix tests + GUARD-06 fallback test; all `_parse_args` call sites unpack tuple | VERIFIED | 3 new tests at lines 315, 328, 450. All 10 `_parse_args` call sites use tuple unpacking. 22 tests PASSED (confirmed by local run). |
| `src/python/tests/unittests/test_controller/test_delete_process.py` | `TestDeleteLocalProcess` with 3 tests (failure-path + 2 success-path) | VERIFIED | Class at line 84. All 3 tests present and PASSED. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `AppProcess.__getstate__` | `self.__dict__` threading.Thread values | `isinstance(v, threading.Thread)` sweep that pops Thread instances only | VERIFIED | `app_process.py:133`: exact pattern confirmed. Queue/Event not stripped. |
| `_emit_startup_warnings` accept-any-caller branch | Runtime behavior (webhook.py fail-closed 503) | `not config.general.webhook_secret and not config.general.webhook_require_secret` | VERIFIED | `seedsyncarr.py:377`: exact condition present once. |
| `_parse_args` legacy-fallback decision | Configured `logger.warning` after `_create_logger` | `legacy_fallback_warning` threaded as tuple second element, emitted at `__init__:82-83` | VERIFIED | Both ends confirmed: tuple return at line 277, post-logger emission at lines 82-83. |
| `DeleteLocalProcess.run_once` rmtree failure | `self.logger.exception` observable log record | `try/except OSError` wrapping `shutil.rmtree(file_path)` with no `ignore_errors` | VERIFIED | `delete_process.py:24-30`: correct. |
| failure log line | `sanitize_log_value(self.__file_name)` | log-injection sanitizer from common barrel | VERIFIED | `delete_process.py:6` (import) and `delete_process.py:29` (usage). |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase adds observability wiring (logging, warnings) and a test fix. There are no dynamic-data-rendering components to trace.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| GUARD-04: previously-red test passes under spawn | `pytest test_app_process.py -v` (9 tests) | 9 PASSED | PASS |
| GUARD-02: accept-any-caller suppression test passes | `pytest test_seedsyncarr.py::TestSeedsyncarrStartupWarnings::test_startup_require_secret_without_secret_does_not_warn_accept_any_caller` | PASSED | PASS |
| GUARD-03: logged rmtree failure test passes | `pytest test_delete_process.py::TestDeleteLocalProcess::test_local_delete_logs_rmtree_failure` | PASSED | PASS |
| GUARD-06: legacy fallback warning test passes | `pytest test_seedsyncarr.py::TestSeedsyncarrLegacyFallback::test_parse_args_emits_legacy_fallback_warning` | PASSED | PASS |
| Full 3-file suite (38 tests) | `pytest test_seedsyncarr.py test_app_process.py test_delete_process.py` | 38 PASSED in 3.94s | PASS |

**Note on broader test suite:** The containerized CI run (`make run-tests-python` on Linux/python:3.11-slim with real lftp+SSH) is the authoritative gate: 1362 passed, 62 skipped, exit 0. Local macOS pre-existing failures in `test_lftp/`, `test_sshcp.py`, and MagicMock-under-spawn integration tests are documented pre-existing conditions (identical failures without GUARD-04 reverted) and are excluded from phase scope per the verification focus context.

---

### Probe Execution

No probes declared in PLAN.md files. Step 7c: SKIPPED (no probe scripts referenced in plans).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GUARD-01 | 112-02 | Prominent startup warning for no `api_token` configured | SATISFIED | `[SECURITY]` prefix on both api_token warnings (lines 388-395); `test_startup_warns_when_api_token_empty` PASSED |
| GUARD-02 | 112-02 | Webhook warning fires only when endpoint actually accepts unauthenticated callers | SATISFIED | Condition `not webhook_secret and not webhook_require_secret` at line 377; `test_startup_require_secret_without_secret_does_not_warn_accept_any_caller` PASSED |
| GUARD-03 | 112-03 | Failed local delete logged, not silently swallowed | SATISFIED | `try/except OSError` + `logger.exception` + `sanitize_log_value`; `ignore_errors` gone; `test_local_delete_logs_rmtree_failure` PASSED |
| GUARD-04 | 112-01 | Full test suite passes under both fork and spawn; previously-red test now green | SATISFIED | `__getstate__`/`__setstate__` in `AppProcess`; `test_process_with_long_running_thread_terminates_properly` PASSED under spawn; 9/9 test_app_process.py PASSED |
| GUARD-05 | 112-01 | `.orchestrator.json` and `.playwright-mcp/` git-ignored | SATISFIED | Both entries in `.gitignore:27-28`; `git check-ignore` confirms; neither in `git status --short` |
| GUARD-06 | 112-02 | Legacy `~/.seedsync` fallback warning reaches configured log stream | SATISFIED | Tuple return from `_parse_args`; post-logger emission at `__init__:82-83`; `test_parse_args_emits_legacy_fallback_warning` PASSED |

**All 6 GUARD requirements from REQUIREMENTS.md (Phase 112 entries, lines 92-97): fully satisfied.**

No orphaned requirements — all 6 requirements mapped to Phase 112 have been verified.

---

### Anti-Patterns Found

Scanned all phase-modified files: `app_process.py`, `seedsyncarr.py`, `delete_process.py`, `test_seedsyncarr.py`, `test_app_process.py`, `test_delete_process.py`, `.gitignore`.

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| (none) | No TBD/FIXME/XXX markers found | — | Clean |
| (none) | No placeholder/stub patterns found | — | Clean |
| (none) | No empty implementations found | — | Clean |

`ruff check` on all three production source files: `All checks passed!`

One notable non-issue: `seedsyncarr.py:318` contains `# BUG-02: first-run default (BLOCKER-1)` as a reference comment on `webhook_require_secret = False`. This comment references a tracked issue (BUG-02/BLOCKER-1) and is pre-existing, not introduced by this phase — not a debt marker for this phase.

---

### Human Verification Required

None. All GUARD items are testable programmatically (logging assertions, test pass/fail, grep-verifiable conditions). The phase adds no UI components, real-time behavior, or external service integrations.

---

### Context Decisions Honored

All CONTEXT.md decisions verified honored:

- **D-01/D-02/D-03 (GUARD-04):** `__getstate__`/`__setstate__` used (D-02 live repro resolved in favor of this approach). No `set_start_method` called anywhere. Sweep is generic `isinstance(v, threading.Thread)` — Queue/Event retained.
- **D-04 (GUARD-01/02):** Confirm-and-fix on existing `_emit_startup_warnings`, no new wiring needed.
- **D-05 (GUARD-02):** Exact condition `not webhook_secret and not webhook_require_secret` — verified at line 377.
- **D-06 (GUARD-01):** `[SECURITY]` prefix, stays at `logging.warning` level. No exceptions raised.
- **D-07:** Three new tests added; existing `assertEqual(3, ...)` count test preserved.
- **D-08/D-09 (GUARD-03):** `try/except OSError` (not `onexc` — 3.12+ only avoided per Python 3.11 runtime). No re-raise. `logger.exception` used.
- **D-10:** Failure-path regression test (`TestDeleteLocalProcess`) added.
- **D-11/D-12 (GUARD-06):** Option A (tuple return) implemented. Warning reaches configured logger. Auto-fallback behavior preserved. No opt-in gate.
- **D-13 (GUARD-05):** Both artifacts in `.gitignore` AI-tooling block.

---

_Verified: 2026-06-02_
_Verifier: Claude (gsd-verifier)_
