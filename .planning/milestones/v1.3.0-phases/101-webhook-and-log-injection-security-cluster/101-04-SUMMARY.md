---
phase: 101-webhook-and-log-injection-security-cluster
plan: "04"
subsystem: controller/security
tags: [cwe-117, log-injection, sanitize, webhook, command, tdd]
dependency_graph:
  requires: [sanitize_log_value-helper]
  provides: [webhook-command-log-injection-closed]
  affects: [101-05-PLAN]
tech_stack:
  added: []
  patterns: [log-output-only-sanitization, tdd-red-green]
key_files:
  created: []
  modified:
    - src/python/controller/webhook_manager.py
    - src/python/controller/controller.py
    - src/python/tests/unittests/test_controller/test_webhook_manager.py
    - src/python/tests/unittests/test_controller/test_controller.py
decisions:
  - "D-01: only the log variable is wrapped; queue/matching/return/persist/callback values stay raw"
  - "D-02: apply helper only to provably remote-/user-tainted log sites (webhook/command cluster)"
  - "D-03 (re-derived): webhook/command cluster = webhook_manager:37,76 + controller:790,792,760,975,1075,1069"
metrics:
  duration: "~19m"
  completed: "2026-05-31T22:40:40Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 101 Plan 04: Webhook/Command Log Injection Cluster (CWE-117) Summary

**One-liner:** Replaced 3 inline `.replace()` newline-escape copies and wrapped 5 additional unsanitized log sites with `sanitize_log_value()` across `webhook_manager.py` and `controller.py`, closing CWE-117 for the entire webhook/command taint cluster (8 sites total).

## What Was Built

Applied the shared `sanitize_log_value()` helper (built in Plan 01) to the webhook/command taint cluster — log sinks fed directly by *arr webhook payloads and by user-supplied command file names.

### webhook_manager.py (Sites 1-2)

- Updated import: `from common import Context, sanitize_log_value`
- **Site 37 (enqueue_import):** Replaced `file_name.replace("\n", "\\n").replace("\r", "\\r")` with `sanitize_log_value(file_name)` — now also escapes ESC (0x1B) and all other C0 controls
- **Site 76 (process drain loop):** Same replacement as site 37
- Queue put/get, `name_to_root.get(file_name.lower())` lookup, and returned `(root_name, file_name)` tuple all stay RAW

### controller.py (Sites 3-8)

- Updated import on line 19: added `sanitize_log_value` to `from common import Context, AppError, MultiprocessingLogger, sanitize_log_value`
- **Site 760 (ModelError debug):** Wrapped `root_name` in `sanitize_log_value(root_name)` — remote-scanner-sourced name, D-03 site
- **Site 790 (inline replacement):** Replaced `matched_name.replace(...)` inline copy with `sanitize_log_value(matched_name)` — behavior-neutral refactor
- **Site 792 (same log call):** Wrapped `root_name` in `sanitize_log_value(root_name)` in `"Recorded webhook import: '{}' (child: '{}')"` — newly sanitized (root_name is remote-scanner-sourced via `child.name`)
- **Site 975 (auto-delete success):** Wrapped `file_name` in `sanitize_log_value(file_name)` in `"Auto-deleted local file '{}'"` — webhook-triggered import path terminal line
- **Site 1075 (command dispatch):** Wrapped `command.filename` in `sanitize_log_value(command.filename)` in `"Received command {} for file {}"` — user-supplied via URL path / bulk JSON, unauthenticated when `api_token` is empty
- **Site 1069 (_notify_failure):** Changed `self.logger.warning("Command failed. {}".format(_msg))` to use `sanitize_log_value(_msg)` — `_msg` is built from `command.filename` by callers (e.g. line 1080 `"File '{}' not found".format(command.filename)`)
- **Line 1071 on_failure callback stays RAW:** `_callback.on_failure(_msg, _code)` unchanged — log-output-only, client-facing message/return path unmodified

### Tests Added

**test_webhook_manager.py (3 new tests):**
- `test_enqueue_sanitizes_newlines_in_log`: CRLF in file_name -> `\r`/`\n` tokens in log, no literal newline
- `test_enqueue_sanitizes_escape_char_in_log`: ESC (0x1b) in file_name -> `\x1b` in log (catches C0 coverage gap the old inline `.replace()` missed — was the RED failure)
- `test_queue_value_unchanged_with_newline`: CRLF-bearing file_name matching a model entry returns RAW matched tuple

**test_controller.py (4 new tests in 2 test classes):**
- `TestCheckWebhookImportsSanitization.test_recorded_import_log_is_sanitized`: CRLF in root_name -> escaped in "Recorded webhook import" log (site 792 RED failure)
- `TestCheckWebhookImportsSanitization.test_recorded_import_persist_value_is_raw`: `add_imported_child` receives RAW lowercased matched_name (D-01 invariant)
- `TestProcessCommandsSanitization.test_notify_failure_log_is_sanitized`: CRLF in command.filename -> escaped in "Command failed." warning log (site 1069 RED failure)
- `TestProcessCommandsSanitization.test_notify_failure_callback_receives_raw_msg`: `on_failure` callback receives RAW `_msg` (log-output-only invariant)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | webhook_manager failing CWE-117 tests | 2ab422c | test_webhook_manager.py |
| 1 GREEN | Replace inline escapes in webhook_manager with sanitize_log_value | 87b45ea | webhook_manager.py |
| 2 RED | controller failing CWE-117 tests (webhook + command sites) | 1ceef53 | test_controller.py |
| 2 GREEN | Route controller webhook/command log sites through sanitize_log_value | 75478ec | controller.py |

## Deviations from Plan

None — plan executed exactly as written.

Note: The tests for `test_recorded_import_log_is_sanitized` and `test_recorded_import_persist_value_is_raw` were initially written with `matched_name` as the CRLF-bearing value, which already passed RED (because the inline `.replace()` at site 790 already escaped matched_name). The test was updated during RED to use `root_name` as the CRLF-bearing value (site 792 — not yet sanitized), which correctly failed RED. This is a test-correctness fix within the RED phase, not a plan deviation.

## Verification Results

Per-site gate results (all pass):

| Gate | Expected | Actual |
|------|----------|--------|
| webhook_manager sanitize_log_value total | 3 | 3 |
| webhook_manager sanitize_log_value(file_name) | 2 | 2 |
| webhook_manager no inline leftover | CLEAN | CLEAN |
| controller sanitize_log_value total | >=7 | 7 |
| controller sanitize_log_value(matched_name) | 1 | 1 |
| controller sanitize_log_value(root_name) | 2 | 2 |
| controller sanitize_log_value(file_name) | 1 | 1 |
| controller sanitize_log_value(command.filename) | 1 | 1 |
| controller sanitize_log_value(_msg) | 1 | 1 |
| controller no matched_name inline leftover | CLEAN | CLEAN |
| 'Recorded webhook import' message-anchored | present | present |
| 'Command failed.' message-anchored | present | present |

- 16 test_webhook_manager tests pass (13 existing + 3 new)
- 24 test_controller tests pass (19 existing + 4 new [2 tests in 2 classes = actual 4 methods])
- Total: 40 tests pass in both test files combined

## TDD Gate Compliance

- RED gate Task 1: commit `2ab422c` — `test(101-04): add failing CWE-117 sanitization tests for webhook_manager (RED)` — ESC (0x1b) test fails as expected
- GREEN gate Task 1: commit `87b45ea` — `feat(101-04): replace inline newline-escape copies with sanitize_log_value in webhook_manager (GREEN)` — 16 tests pass
- RED gate Task 2: commit `1ceef53` — `test(101-04): add failing CWE-117 sanitization tests for controller webhook/command sites (RED)` — root_name site 792 and _msg site 1069 fail as expected
- GREEN gate Task 2: commit `75478ec` — `feat(101-04): route controller webhook/command log sites through sanitize_log_value (GREEN)` — 40 tests pass

## Known Stubs

None.

## Threat Flags

No new security surface introduced. This plan only wraps existing log sinks in a sanitizer. No new network endpoints, auth paths, file access patterns, or schema changes.

## Hand-off Note

Auto-delete timer cluster (controller.py:229,820,841,848,866,876,897,926,948) and model-layer remote-scanner log sites (model/model.py:81,97,112) still log remote-derived names unsanitized — Plan 05 closes them. The `sanitize_log_value(file_name)==1` gate in this plan is Plan-04-scoped; Plan 05 will add more `file_name` wraps and re-gate at its own count.

## Self-Check: PASSED

- [x] `src/python/controller/webhook_manager.py` — contains `sanitize_log_value` (3 occurrences: import + 2 calls)
- [x] `src/python/controller/controller.py` — contains `sanitize_log_value` (7 occurrences: import + 6 calls)
- [x] `src/python/tests/unittests/test_controller/test_webhook_manager.py` — contains `test_enqueue_sanitizes_newlines_in_log`, `test_enqueue_sanitizes_escape_char_in_log`, `test_queue_value_unchanged_with_newline`
- [x] `src/python/tests/unittests/test_controller/test_controller.py` — contains `TestCheckWebhookImportsSanitization`, `TestProcessCommandsSanitization`
- [x] Commit 2ab422c exists (Task 1 RED)
- [x] Commit 87b45ea exists (Task 1 GREEN)
- [x] Commit 1ceef53 exists (Task 2 RED)
- [x] Commit 75478ec exists (Task 2 GREEN)
- [x] 40 tests pass in test_webhook_manager.py + test_controller.py
