---
phase: 124-model-stream-overflow-recovery
plan: 03
subsystem: api
tags: [tdd, strm-02, sse, model-stream, resync, convergence]

# Dependency graph
requires:
  - phase: 124-01
    provides: Recorded STRM-01 reproduction and the "proceed to STRM-02 fix" verdict, plus ModelStreamClient/server_snapshot/open_sse_stream test helpers
  - phase: 124-02
    provides: "StreamQueue.clear() and Controller.resync_model_files(discard_backlog), proven atomic (D-03) and bounded (D-05)"
provides:
  - "ModelStreamHandler.get_value() resync gate: detects a dropped-event delta and resends a fresh model-init on the same connection instead of the next stale backlog event (D-02)"
  - "Coalesced pending-resync state (single bool, never a list of snapshots) absorbing any number of drops before delivery into exactly one resync (D-04)"
  - "Rate-limited server-log warning on resync count (1, 101, 201...), counts only, no file names (D-08)"
  - "Unit-level (real Controller/real lock) and WSGI-level (real generator/real SerializeModel) convergence tests, both committed RED before the fix and GREEN after"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Second early-return gate in a streaming handler's get_value(), strictly before the realtime-event early-return, mirroring the existing initial-model-init early-return idiom"
    - "Rebaseline the coalescing counter INSIDE the lock-protected discard callback, not after the lock releases, so a drop racing the resync itself is absorbed by the same snapshot instead of triggering an immediate second resync"

key-files:
  created: []
  modified:
    - src/python/web/handler/stream_model.py
    - src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py
    - src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py
    - src/python/tests/integration/test_web/test_handler/test_stream_model.py

key-decisions:
  - "_discard_backlog rebaselines _last_seen_dropped by reading get_dropped_count() INSIDE the same __model_lock acquisition the discard runs under (not after resync_model_files returns), because every model mutation that could drop an event also runs under __model_lock -- this is exact, not merely an approximation of Pitfall 4's fix"
  - "The resync warning counts resyncs (_resync_count % 100 == 1), not raw drops -- drops are already logged by StreamQueue.put() itself; the new warning is the user-visible 'this tab was resynced' signal"
  - "No frontend change: model-init already does a full-map replace unconditionally, confirmed by the WSGI-level test running through real SerializeModel/real Bottle serialization (not just asserted by code reading)"

patterns-established:
  - "ModelStreamHandler._discard_backlog(self): self.model_listener.clear(); self._last_seen_dropped = self.model_listener.get_dropped_count() -- passed as the discard_backlog callable to Controller.resync_model_files, keeping controller/ at zero imports from web/"

requirements-completed: [STRM-02]

# Metrics
duration: ~40min
completed: 2026-10-27
---

# Phase 124 Plan 03: ModelStreamHandler Overflow Resync Summary

**A stalled browser tab's model-stream now resyncs to a fresh `model-init` on the same SSE connection the first time `get_value()` runs after a queue overflow, proven to converge by a real-Controller unit test and a real-WSGI-generator integration test that both failed before the fix and pass after, with coalesced pending state and a resync-count-rate-limited warning.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-10-27T10:23:00Z (approx.)
- **Completed:** 2026-10-27T11:03:00Z
- **Tasks:** 3 completed
- **Files modified:** 4 (1 production, 3 test)

## Accomplishments
- `ModelStreamHandler.get_value()` gained a second early-return gate, strictly before `get_next_event()`, that detects a `get_dropped_count()` delta and resends a fresh `model-init` via `Controller.resync_model_files(self._discard_backlog)` in place of the next stale backlog event.
- `_discard_backlog()` clears the listener and rebaselines the dropped-count baseline inside the same `__model_lock` acquisition the resync runs under, so a drop that races the resync itself is folded into that same snapshot instead of triggering an immediate second resync.
- Pending-resync state is a single bool (`_resync_pending`) — proven by a direct test that no handler attribute ever holds a list of snapshots.
- The resync warning is rate-limited by resync count (`_resync_count % 100 == 1`, so resyncs 1 and 101 log, 2-100 do not), logs only integer counts, and never contains a file name.
- Two independent convergence tests, both committed RED (failing on the real divergence/assertion, no import/collection errors) before any production edit, then GREEN after: a real-`Controller`/real-`__model_lock` unit test (`TestModelStreamConvergence`) and a real-Bottle-WSGI-generator integration test (`test_stalled_consumer_converges_after_overflow`) that drives the actual `/server/stream` route and real `SerializeModel` serialization.
- `stream_status.py`, `stream_log.py`, and the Angular frontend are untouched (D-06); the 124-01 reproduction test still passes unchanged (D-01).

## Task Commits

Each task was committed atomically:

1. **Task 1: RED unit-level convergence, coalescing, bounded and warning tests** - `a169f57` (test)
2. **Task 2: RED WSGI-level stalled-consumer convergence test** - `3411e50` (test)
3. **Task 3: GREEN resync gate in ModelStreamHandler.get_value()** - `52da527` (fix)

**Plan metadata:** this SUMMARY.md commit (below)

## Files Created/Modified
- `src/python/web/handler/stream_model.py` - `ModelStreamHandler.get_value()` resync gate; `_discard_backlog()`; `__init__` state (`_last_seen_dropped`, `_resync_pending`, `_resync_count`, `self.logger`)
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py` - `TestModelStreamConvergence` (real Controller, real lock, real `ModelStreamHandler`): `test_stalled_tab_converges_to_server_model_after_overflow`, `test_first_value_after_overflow_is_model_init`, `test_no_stale_or_duplicate_events_after_resync`, `test_overflow_before_initial_init_still_converges`
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py` - `TestModelStreamHandlerResync` (mocked Controller): `test_no_resync_without_drops`, `test_drop_triggers_single_model_init_resync`, `test_multiple_drops_coalesce_into_one_resync`, `test_resync_pending_state_is_bounded`, `test_resync_warning_rate_limited_by_resync_count`, `test_drop_during_resync_is_absorbed`
- `src/python/tests/integration/test_web/test_handler/test_stream_model.py` - `test_stalled_consumer_converges_after_overflow` (real WSGI generator, real `SerializeModel`, `open_sse_stream`-based stall)

## RED Results

### Unit-level (Task 1)

Precondition checked first: 124-02-SUMMARY.md confirms `StreamQueue.clear()` and `Controller.resync_model_files(discard_backlog)` exist and are proven atomic/bounded — unblocking this plan's wiring work.

RED pytest run (before any production edit), in this worktree at `src/python`:
```
poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_overflow.py tests/unittests/test_web/test_handler/test_stream_model_handler.py -q -k "Convergence or Resync"
...
FAILED tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_first_value_after_overflow_is_model_init
FAILED tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_no_stale_or_duplicate_events_after_resync
FAILED tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_overflow_before_initial_init_still_converges
FAILED tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_stalled_tab_converges_to_server_model_after_overflow
FAILED tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_drop_during_resync_is_absorbed
FAILED tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_drop_triggers_single_model_init_resync
FAILED tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_multiple_drops_coalesce_into_one_resync
FAILED tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_resync_pending_state_is_bounded
FAILED tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_resync_warning_rate_limited_by_resync_count
9 failed, 1 passed, 17 deselected in 1.11s
```
Exit code was exactly `1`. Every failure was an `AssertionError` on the expected convergence/behavior assertion (e.g. `'model-init' not found in ['model-added']`, client-vs-server divergence dicts, `resync_model_files` not called) — no `ERROR`, `ImportError`, `ModuleNotFoundError`, `NameError`, `SyntaxError`, or `AttributeError` line anywhere in the log (checked by grep). The one expected pass, `test_no_resync_without_drops`, passed as planned (it asserts pre-existing no-drop behavior, unaffected by the missing fix).

Second verify command (reproduction + pre-existing handler tests + the one new passing test):
```
poetry run pytest tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamOverflowReproduction tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandler "tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_no_resync_without_drops" -q
13 passed in 0.14s
```
`git log --oneline -1` after this commit (`a169f57`) was the unit-level `test(124-03)` commit; `git diff HEAD~1 --name-only` touched only the two test files (no `src/python/web/` file).

### WSGI-level (Task 2)

RED pytest run (before any production edit):
```
poetry run pytest tests/integration/test_web/test_handler/test_stream_model.py -q -k stalled_consumer
...
FAILED tests/integration/test_web/test_handler/test_stream_model.py::TestModelStreamHandler::test_stalled_consumer_converges_after_overflow
1 failed, 4 deselected, 1 warning in 1.75s
```
Exit code was exactly `1`. The failure was on the `client`-vs-`server` `assertEqual` (`AssertionError: {'file-0000': {...}} != {'ghost.txt': {...}}`, diff ~992KB — the 500-missing-files/1-ghost-present divergence reconstructed through the real WSGI generator and real `SerializeModel`), with no `ImportError`/`ModuleNotFoundError`/`NameError`/`SyntaxError`/`AttributeError`/`ERROR` line in the log.

Pre-existing integration tests in the same file:
```
poetry run pytest tests/integration/test_web/test_handler/test_stream_model.py -q -k "not stalled_consumer"
4 passed, 1 deselected, 1 warning in 3.83s
```
`git log --oneline -1` after this commit (`3411e50`) was the WSGI-level `test(124-03)` commit; `git diff HEAD~1 --name-only` touched only the integration test file.

## GREEN Results

Task-level targeted gate (both new test files + integration file), after the GREEN commit:
```
poetry run pytest tests/unittests/test_web/ tests/unittests/test_controller/ tests/integration/test_web/test_handler/test_stream_model.py -q \
  --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py \
  --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py
1335 passed, 1 warning, 19 subtests passed in 44.22s
```
(The two `--ignore`d files are the pre-existing macOS-host-only multiprocessing hang documented in 124-02-SUMMARY and the executor's known-issue note — unrelated to this plan's files, confirmed passing in the Docker run below.)

Whole-tree ruff:
```
ruff check src/python/
All checks passed!
```

Acceptance-criteria greps:
```
grep -c "self.controller.resync_model_files(self._discard_backlog)" src/python/web/handler/stream_model.py  -> 1
grep -n "get_dropped_count() != self._last_seen_dropped" src/python/web/handler/stream_model.py  -> line 88
grep -n "get_next_event()" src/python/web/handler/stream_model.py  -> line 105 (88 < 105: ordering correct)
git log --oneline -- src/python/web/handler/stream_status.py src/python/web/handler/stream_log.py src/angular | grep -c '124-'  -> 0
```

### Plan-level gate (full local suite + whole-tree ruff + Docker)

Full local suite with coverage (excluding the same documented local-only exclusions as 124-02, none of which touch this plan's files):
```
poetry run pytest --cov --cov-report=term-missing -q \
  --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py \
  --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py \
  --ignore=tests/unittests/test_ssh/test_sshcp.py \
  --ignore=tests/integration \
  --deselect=tests/unittests/test_system/test_scanner.py::TestSystemScanner::test_scan_file_with_latin_chars
Required test coverage of 88.0% reached. Total coverage: 89.99%
1873 passed, 1 deselected, 1 warning, 77 subtests passed in 55.15s
```
`web/handler/stream_model.py` coverage: 59 statements, 0 missed, 12 branches, 1 partial (99%) — every new branch (resync gate, rate-limit modulo) is exercised.

Whole-tree ruff (plan-level, same command, re-confirmed clean): `All checks passed!`

**Docker, CI-equivalent (`make run-tests-python`), run in this worktree — available on this host (Docker 29.4.3):**
```
make run-tests-python
...
= 1986 passed, 62 skipped, 1 warning, 77 subtests passed in 106.73s (0:01:46) ==
seedsyncarr_test_python exited with code 0
```
All new tests confirmed passing inside the Docker container, including the two tests that are excluded from the local host run (they pass in Docker, where the multiprocessing/testgroup/APFS environment gaps don't apply):
```
tests/integration/test_web/test_handler/test_stream_model.py::TestModelStreamHandler::test_stalled_consumer_converges_after_overflow PASSED
tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_drop_during_resync_is_absorbed PASSED
tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_drop_triggers_single_model_init_resync PASSED
tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_multiple_drops_coalesce_into_one_resync PASSED
tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_no_resync_without_drops PASSED
tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_resync_pending_state_is_bounded PASSED
tests/unittests/test_web/test_handler/test_stream_model_handler.py::TestModelStreamHandlerResync::test_resync_warning_rate_limited_by_resync_count PASSED
tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_first_value_after_overflow_is_model_init PASSED
tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_no_stale_or_duplicate_events_after_resync PASSED
tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_overflow_before_initial_init_still_converges PASSED
tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamConvergence::test_stalled_tab_converges_to_server_model_after_overflow PASSED
```

### Commit order

```
git log --oneline
52da527 fix(124-03): resync model stream with a fresh model-init after queue overflow (STRM-02)
3411e50 test(124-03): add failing WSGI stalled-consumer convergence test (STRM-02)
a169f57 test(124-03): add failing unit-level model-stream convergence tests (STRM-02)
```
Both `test(124-03)` RED commits (`a169f57`, `3411e50`) precede the `fix(124-03)` GREEN commit (`52da527`), satisfying the plan's gate ordering.

## Requirement Close-out

- **STRM-01** (reproduce first): closed in 124-01 with a recorded, repeatable reproduction (501 dropped, 500 missing files, 1 ghost file) and the "no existing recovery guarantee, proceed to STRM-02" verdict. This plan's `test_stalled_listener_overflow_diverges_from_server_model` still passes unchanged (D-01), confirmed above.
- **STRM-02** (convergence with bounded buffering): closed by this plan. A stalled tab's `get_value()` now detects a dropped-event delta and resends a fresh `model-init` via the atomic `Controller.resync_model_files` (D-02, D-03); repeated drops before delivery coalesce into exactly one resync via a single bool (D-04); the queue never exceeds `maxsize` and the pending state is never a growing collection (D-05, asserted directly by `test_resync_pending_state_is_bounded` and the queue-size assertions in the convergence tests); the resync is silent to the user and logs a resync-count-rate-limited, counts-only warning (D-08). Proven by two independent "fails before, passes after" tests — real-Controller unit-level and real-WSGI-generator integration-level — both committed RED before the fix and GREEN after.
- **D-06** (status/log streams untouched): confirmed by `git log --oneline -- src/python/web/handler/stream_status.py src/python/web/handler/stream_log.py src/angular | grep -c '124-'` returning `0`.
- **D-07** (automated tests only, no NAS sandbox session): this phase is web-server-only and touches no transfer/import/delete path; no NAS sandbox session was run or needed. All proof is the automated test evidence recorded above (local + Docker CI-equivalent).

Phase 124 (Model-Stream Overflow Recovery) is now fully closed at the plan level: STRM-01 (124-01) and STRM-02 (124-02 primitives + 124-03 wiring) both satisfied with recorded, repeatable, fails-before/passes-after evidence.

## Decisions Made
- See `key-decisions` in frontmatter: `_discard_backlog` rebaselines the dropped-count baseline *inside* the lock (exact, not an approximation of the RESEARCH.md sketch's post-lock re-read); the resync warning counts resyncs, not raw drops; no frontend change, confirmed by the WSGI-level test running through real serialization rather than only by code reading.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' acceptance criteria were met on the first pass:
- Both RED commits (`a169f57`, `3411e50`) landed strictly before the GREEN commit (`52da527`)
- `git diff HEAD~1 --name-only` for each RED commit touched only test files; the GREEN commit touched only `src/python/web/handler/stream_model.py`
- Whole-tree `ruff check src/python/` stayed clean after every commit
- `stream_status.py`, `stream_log.py`, and `src/angular` were never touched by any `124-` commit

## Issues Encountered

None specific to this plan's logic. One worktree-environment setup action was required (not a plan deviation, consistent with 124-01/124-02's prior notes): this fresh worktree's Poetry virtualenv had zero dependencies installed on first use; resolved by running `poetry install` once before running any tests.

The local full-suite and targeted gates exclude the same pre-existing, macOS-host-only failures documented in 124-02-SUMMARY (`test_extract_process.py`, `test_scanner_process.py` multiprocessing hang; `test_sshcp.py` testgroup dependency; one APFS Latin-1 byte-sequence test). None of these files were touched by this plan. All of them, plus every new test this plan added, were confirmed passing in the Docker `make run-tests-python` run recorded above — nothing was claimed as passing without actually running it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- STRM-02 is closed: the model stream now resyncs a stalled tab to a fresh `model-init` on the same connection, proven by tests that failed before the fix and pass after, at both the unit and WSGI/integration level.
- Phase 124 (Model-Stream Overflow Recovery) has no further plans; both roadmap requirements (STRM-01, STRM-02) are satisfied with recorded evidence.
- The `controller/` package still has zero imports from `web/` (the `Callable[[], None]` lock-bridge pattern from 124-02 was reused unchanged, not extended).
- No blockers.

## Self-Check: PASSED

All modified files confirmed present on disk:
- `src/python/web/handler/stream_model.py` - FOUND
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py` - FOUND
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_handler.py` - FOUND
- `src/python/tests/integration/test_web/test_handler/test_stream_model.py` - FOUND

All three task commits confirmed present in `git log --oneline -5`:
- `a169f57` - test(124-03): add failing unit-level model-stream convergence tests (STRM-02) - FOUND
- `3411e50` - test(124-03): add failing WSGI stalled-consumer convergence test (STRM-02) - FOUND
- `52da527` - fix(124-03): resync model stream with a fresh model-init after queue overflow (STRM-02) - FOUND

RED strictly before GREEN confirmed: `a169f57` and `3411e50` both precede `52da527` in `git log` order.

---
*Phase: 124-model-stream-overflow-recovery*
*Completed: 2026-10-27*
