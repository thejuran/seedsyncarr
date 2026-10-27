---
phase: 124-model-stream-overflow-recovery
plan: 01
subsystem: testing
tags: [strm-01, reproduction, sse, stream-queue, test-harness]

# Dependency graph
requires: []
provides:
  - Recorded, repeatable reproduction of the model-stream overflow (STRM-01) with an explicit go verdict for STRM-02
  - Recorded D-06 evidence that the status stream is self-healing under overflow (no code change)
  - ModelStreamClient test helper (wire-format reducer mirroring ModelFileService.parseEvent) and server_snapshot() for comparing client vs. server model state
  - open_sse_stream() stall-capable SSE harness (non-draining WSGI body) for future integration-level stall tests
affects: [124-02, 124-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test-only wire-format client reducer mirrors a frontend reducer exactly, so tests assert against real SSE strings instead of Python object equality"
    - "Stalled-consumer reproduction via direct StreamQueue/listener mutation under the real __model_lock, no WSGI machinery required"

key-files:
  created:
    - src/python/tests/helpers/model_stream_client.py
    - src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py
  modified:
    - src/python/tests/helpers/wsgi_stream.py

key-decisions:
  - "Reproduction done at the WebResponseModelListener/StreamQueue boundary directly (call add_file/remove_file > maxsize times without draining), not through the WSGI generator — simpler, deterministic, and sufficient for STRM-01 (RESEARCH.md Pitfall 3 option a)"
  - "D-06 status-stream evidence recorded with no code change, confirming the existing full-snapshot-per-event design already self-heals"

patterns-established:
  - "ModelStreamClient (tests/helpers/model_stream_client.py): Python mirror of the frontend's four parseEvent reducer rules, for future convergence tests in 124-02/124-03"

requirements-completed: []  # STRM-01 reproduced and recorded here; closure of the requirement itself is tracked at phase level once 124-02/124-03 land the fix

# Metrics
duration: ~35min
completed: 2026-10-27
---

# Phase 124 Plan 01: Model-Stream Overflow Reproduction Summary

**Reproduced the model-stream overflow with a real Controller/Model/listener (no fix yet): 501 dropped events, 500 missing files, 1 ghost file surviving — no existing recovery guarantee found, so STRM-02 proceeds to 124-02/124-03.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-10-27T01:24:56Z (STATE.md phase-start timestamp)
- **Completed:** 2026-10-27T01:30:06Z
- **Tasks:** 2 completed
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- Built a wire-format SSE test client (`ModelStreamClient`) that mirrors the frontend's `ModelFileService.parseEvent` reducer exactly, plus `server_snapshot()` for apples-to-apples client/server comparison and `parse_sse_events()` for parsing raw SSE chunks.
- Extended `wsgi_stream.py` with `open_sse_stream()`, a non-draining SSE stream opener for later stall-capable integration tests (Wave 0 gap from VALIDATION.md).
- Reproduced the STRM-01 overflow with a real `Controller`/`Model`/`__model_lock` and a registered `WebResponseModelListener` that is never drained, recording the exact divergence between the client's reconstructed model and the server's current model.
- Recorded D-06 evidence that the status stream is already self-healing under overflow (no code change needed).

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire-format client reducer and non-draining SSE stream opener** - `003a26b` (test)
2. **Task 2: STRM-01 reproduction test, D-06 status evidence, and the recorded verdict** - see commit hash in final response (test)

**Plan metadata:** SUMMARY.md committed together with Task 2 (test-only plan; no separate `docs` commit needed beyond the plan-metadata commit noted in the completion report)

## Files Created/Modified
- `src/python/tests/helpers/model_stream_client.py` - `ModelStreamClient`, `parse_sse_events`, `server_snapshot` (test-only wire-format reducer + comparison helper)
- `src/python/tests/helpers/wsgi_stream.py` - added `open_sse_stream()` (non-draining SSE opener); `collect_sse_chunks` and `make_wsgi_environ` unchanged
- `src/python/tests/unittests/test_web/test_handler/test_stream_model_overflow.py` - `TestModelStreamOverflowReproduction` (STRM-01) and `TestStatusStreamSelfHealingEvidence` (D-06)

## STRM-01 Reproduction Evidence

**Test node id:** `tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamOverflowReproduction::test_stalled_listener_overflow_diverges_from_server_model`

**Pytest output line:**
```
tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestModelStreamOverflowReproduction::test_stalled_listener_overflow_diverges_from_server_model PASSED [ 50%]
============================== 2 passed in 0.15s ===============================
```

**Reproduction setup:** a real `Controller` (from `BaseControllerTestCase`) with a real `Model` and real `__model_lock`; `ghost.txt` added to the model; a real `WebResponseModelListener` registered via `get_model_files_and_add_listener` and never drained (the stalled consumer); `_flood()` then mutates the model directly under `__model_lock` — `remove_file("ghost.txt")` followed by 1500 `add_file(file-0000..file-1499)` calls — producing 1501 model events with maxsize=1000.

**Recorded numbers:**
- `dropped = 501` (`listener.get_dropped_count() == 501`)
- `queued = 1000` (`listener.get_queue_size() == 1000`, `<= get_maxsize()`)
- `missing = 500` — the client's reconstructed model is missing exactly `file-0000` through `file-0499` (`sorted(set(server) - set(client.files)) == ["file-0000", ..., "file-0499"]`)
- `ghost present` — `"ghost.txt"` remains in the client's reconstructed model (`client.files`) but is correctly absent from the server's current model (`server`), because the dropped event was the `remove_file("ghost.txt")` event itself (the oldest of the 1501, dropped first)
- `client.files != server` confirmed directly

**Observed outcome:** after draining every event the stalled listener actually kept and applying it through the same reducer rules the real frontend (`ModelFileService.parseEvent`) uses, the reconstructed client model **diverges** from the server's current model. This matches the pre-discussion code reading in `124-CONTEXT.md`: `StreamQueue.put` drops the oldest event on overflow with only a count/log, `ModelStreamHandler` sends `model-init` once at connect and never again, and the frontend's reconnect fallback only fires after 30s with no events (`stream-service.registry.ts`) — which does not occur while updates keep flowing, so a stalled/throttled tab never self-corrects today.

Verdict: no existing recovery guarantee for the model stream; proceed to STRM-02 fix (124-02, 124-03).

## D-06 Status Stream Evidence

**Test node id:** `tests/unittests/test_web/test_handler/test_stream_model_overflow.py::TestStatusStreamSelfHealingEvidence::test_overflowed_status_listener_still_delivers_latest_snapshot`

An overflowed `StatusListener` (1200 `notify()` calls against the default `maxsize=1000`) drops exactly 200 events (`get_dropped_count() == 200`) and, after draining, the last of the 1000 surviving events `is` the very last snapshot produced (`snapshots[-1]`). Because `StatusListener.notify()` always `put()`s a **full** `Status.copy()` (never a delta), any drop simply discards a stale snapshot — the next successfully delivered snapshot is always fully current. **No status-stream production code was changed.**

## Decisions Made
- Reproduced the overflow at the `WebResponseModelListener`/`StreamQueue` boundary directly (mutating the model under the real lock without draining the listener) rather than through the WSGI generator, per RESEARCH.md's Pitfall 3 option (a): simpler, deterministic, and sufficient for a "recorded, repeatable" STRM-01 test. The stall-capable `open_sse_stream()` helper was still built in Task 1 as the Wave 0 gap closer for 124-02/124-03's higher-fidelity integration test, per VALIDATION.md.
- `_flood()`'s event ordering (`remove_file("ghost.txt")` first, then 1500 adds) was chosen deliberately so the dropped-oldest-first semantics of `StreamQueue` would drop the remove event itself, producing a ghost file in the client's view — a concrete, demonstrable divergence rather than only a missing-file count.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were met on the first pass:
- `src/python/tests/helpers/` contains exactly the new/extended files (`git diff --name-only` for Task 1 touched only that directory)
- `ruff check src/python/` (whole tree) exits clean
- `git status --porcelain -- src/python | grep -v 'src/python/tests/'` prints nothing — no production code was modified in this plan
- The full `tests/unittests/test_web/` suite (358 tests) passes with no regressions

## Issues Encountered

None. The worktree's Poetry virtualenv had no dependencies installed on first use (fresh worktree, separate virtualenv from the main checkout); resolved by running `poetry install --no-root` once before running any tests — not a plan deviation, just worktree environment setup.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- STRM-01 is satisfied: the overflow is reproduced by a repeatable automated test, the divergence is recorded with exact numbers, and the go verdict for STRM-02 is written here before any production code change exists in this phase.
- 124-02 and 124-03 (the STRM-02 fix: `StreamQueue.clear()`, `Controller.resync_model_files()`, and the `ModelStreamHandler.get_value()` resync gate) are unblocked and should proceed as planned — this plan found no existing recovery guarantee that would close STRM-02 with no code change.
- `ModelStreamClient`, `parse_sse_events`, `server_snapshot`, and `open_sse_stream` are all available in `src/python/tests/helpers/` for 124-02/124-03's convergence and integration tests.
- No blockers.

---
*Phase: 124-model-stream-overflow-recovery*
*Completed: 2026-10-27*
