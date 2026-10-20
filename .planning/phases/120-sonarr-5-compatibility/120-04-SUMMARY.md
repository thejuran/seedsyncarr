---
phase: 120-sonarr-5-compatibility
plan: 04
subsystem: testing
tags: [sonarr5, queue-details, completion-gate, fixtures]
requires:
  - phase: 120-01
    provides: Sonarr 5 fixture loader (fixture_bytes, fixture_json, queue_target_download_id) and queue fixtures
provides:
  - SON5-02 replay tests of Sonarr 5 queue/details bytes through the real ArrQueueClient and CompletionGate
affects: [120-06]
tech-stack:
  added: []
  patterns:
    - "Raw fixture bytes served via iter_content in 4096-byte chunks to the real client worker"
    - "Client and gate share one callable FakeClock; evaluate -> settle -> evaluate per decision"
key-files:
  created:
    - src/python/tests/unittests/test_sonarr5/test_sonarr5_queue.py
  modified: []
key-decisions:
  - "Assert on Verdict.reason (the real field) instead of the plan's reason_code"
  - "Target root, size and the unrelated record are all derived from the fixtures/manifest so the tests survive the Plan 06 live-capture swap"
requirements-completed: [SON5-02]
duration: ~10min
completed: 2026-10-20
---

# Phase 120 Plan 04: Sonarr 5 queue replay Summary

The Sonarr 5 queue/details fixture bytes go through the real `ArrQueueClient` and `CompletionGate`. The gate holds the tracked download as `still_downloading` on the incomplete snapshot. It releases only after the complete snapshot for the same downloadId arrives, once the 30 s refresh interval has passed. Every negative scenario keeps the hold.

## Accomplishments
- The client reads the raw Sonarr 5 bytes into `QueueRecord`s using the lowercase `sizeleft` key, with records in order and no defects.
- Positive path: the gate holds on the incomplete fixture, then proves the same downloadId from the complete fixture and clears `gate.holds`.
- Negatives: an unrelated root, HTTP 500, a connection error, truncated JSON, a cached proof during an outage, a mixed snapshot, a partially downloaded season pack and a missing queue entry all keep the hold with the expected reason.

## Task Commits
1. **Task 1: Client normalization and hold-then-release replay** - `8842617` (test)
2. **Task 2: Negatives on the captured records** - `6fa5af9` (test)

## Verification (observed)
- `pytest tests/unittests/test_sonarr5 tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py -q -rs`: 129 passed, 1 skipped (the live-source gate for placeholder fixtures, expected until Plan 06), 72 subtests passed
- `test_sonarr5_queue.py` alone: 11 passed
- `ruff check src/python/`: All checks passed
- Acceptance greps: `_json_chunks` 0, `Placeholder.Show` 0, `clock=self.clock` 2, `queue_target_download_id()` 4, `"sonarr_unavailable"` 5, `"no_queue_entry"` 3, `"still_downloading"` 6, `json.dumps` 2 (each with a "synthetic" comment within 3 lines)
- RED observed for both tasks. These tasks only add tests against existing behavior, so RED means a deliberately wrong expectation that was seen to fail and then reverted. The wrong expectations were camelCase `sizeLeft`, proven-on-incomplete, and proven-on-500. No failing-test commit was made.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Verdict attribute is `reason`, not `reason_code`**
- **Found during:** Task 1
- **Issue:** The plan's interface notes listed `Verdict.reason_code`, but the dataclass field is `reason` (`reason_code` is only the parameter name of `Verdict.hold`). The first run failed with an AttributeError.
- **Fix:** The tests assert on `verdict.reason`.
- **Files modified:** src/python/tests/unittests/test_sonarr5/test_sonarr5_queue.py
- **Commit:** 8842617

**2. [Rule 3 - Blocking] FakeClock has no `advance()`**
- **Issue:** The callable `FakeClock` from test_arr_queue only exposes `.now`.
- **Fix:** Added a base-class `advance()` helper that increments `self.clock.now`.

## TDD Gate Compliance
Each task produced one `test(...)` commit. There is no `feat(...)` commit because the plan only adds tests for production behavior that already exists. RED was checked locally each time and was not committed.

## Known Stubs
None. The fixtures are still Plan 01 placeholders. The tests read roots and ids from the fixtures and manifest, so they need no edits when Plan 06 swaps in live captures.

## Self-Check: PASSED
- FOUND: src/python/tests/unittests/test_sonarr5/test_sonarr5_queue.py
- FOUND: 8842617, 6fa5af9
