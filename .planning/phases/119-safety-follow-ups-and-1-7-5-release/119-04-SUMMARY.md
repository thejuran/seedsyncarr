---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 04
subsystem: controller
tags: [sonarr, radarr, queue-api, completion-gate, backoff, imp-02, proof-lifecycle, malformed-records, fetch-worker, non-blocking]
requires: []
provides:
  - "controller.arr_queue: ArrTarget(+identity), QueueRecord, FetchOutcome, FETCH_IDLE/PENDING/DONE/OVERRUN, ArrQueueClient(start_fetch/poll/abandon/in_flight/enabled_targets)"
  - "controller.completion_gate: Verdict, REASON_LABELS, CompletionGate(evaluate/verdict/invalidate/invalidate_all/holds/label)"
  - "tests: module-level TrickleHandler/start_trickle_server/stop_trickle_server/settle (test_arr_queue) and FakeArrClient (test_completion_gate) for reuse by 119-06"
affects: [119-06, 119-07, 119-09]
tech-stack:
  added: []
  patterns:
    - "daemon worker per target + leaf-lock handoff slot; controller thread never joins/sleeps/waits"
    - "request-start epochs for invalidation fences (not result-consumption counters)"
    - "provisional holds (returned, not registered, DEBUG only) while a first/forced fetch is pending"
key-files:
  created:
    - src/python/controller/arr_queue.py
    - src/python/controller/completion_gate.py
    - src/python/tests/unittests/test_controller/test_arr_queue.py
    - src/python/tests/unittests/test_controller/test_completion_gate.py
  modified: []
decisions:
  - "verdict(name) does not prune other names' holds (only evaluate() does a full-cycle prune), so 119-06's single-name checks cause no hold-clear churn"
  - "A completed-but-stale proving group reports <contributing arr>_unavailable (the arr whose evidence is pre-fence), per the plan's algorithm text"
  - "Verdict.proven() constructor is attached after the dataclass body because it shares its name with the `proven` field"
metrics:
  duration: "~16 min"
  completed: 2026-10-14
  tasks: 2
  files: 4
---

# Phase 119 Plan 04: Arr queue client and completion gate Summary

This plan adds two modules. `ArrQueueClient` reads Sonarr/Radarr `/api/v3/queue/details` on one daemon worker per arr, and the controller thread never waits on it. `CompletionGate` turns those queue snapshots into PROVEN/hold verdicts using exact-basename + downloadId identity, capped backoff, proofs tied to one download and lifecycle, and per-arr request-epoch fences. Nothing is wired into the controller yet; 119-06 and 119-07 do that.

## What was built

**`controller/arr_queue.py`**
- `start_fetch(target)` starts a worker named `ArrQueueFetch-<code>` and returns right away. It returns `None` without starting anything if the URL isn't http/https or if a worker for that arr is still alive (including an abandoned one). So there is never more than one worker per arr, even during a long outage.
- `poll(code)` takes a leaf lock once and does no I/O. It reports DONE and OVERRUN once each per fetch id. A fetch older than `FETCH_DEADLINE_SECS` (20 s) is reported OVERRUN and abandoned, and its late result is discarded by fetch id. `abandon()` and `in_flight()` work as the plan specifies.
- The worker uses `stream=True`, reads in 64 KiB chunks with an 8 MiB cap and a deadline checked after every chunk (the deadline clock starts before the connect), and closes the response on every path. It never touches `.content`, `.text` or `.json()`.
- Malformed records are kept with `valid=False` and a defect code (`missing_download_id` / `bad_status` / `bad_sizeleft`). A non-dict entry or a non-string `outputPath` rejects the whole snapshot.
- Logs contain only the arr label, HTTP status or exception class name. The API key, URL, headers and body never appear in a log line.

**`controller/completion_gate.py`**
- Each `evaluate()` runs this sequence: check the configuration identity (any change resets everything and abandons in-flight fetches) → poll and apply results (always, even with no candidates) → start at most one fetch per arr (on the refresh interval, or early for a fenced arr unless it is in failure backoff) → decide each name → lift fences → update the registry and logs.
- Decisions look at live evidence first. A matching record that doesn't prove the root drops the cached proof. A proving group must come only from fresh arrs, so one responding arr can prove a root alone (D-17), before or after an invalidation. The cached "absence" proof is used only when every enabled arr is fresh.
- Fences are keyed to when a request started (`_PendingFetch.epoch` becomes `_snapshot_epoch`). A response from a request that started before the invalidation therefore stays stale, however late it arrives.
- Backoff after failures steps 30→60→120→240→300 s (cap) and resets on success. Failures include a done-with-no-records result, an overrun, a refused start, and a client that returns IDLE while a fetch is still pending.
- INFO is logged only when a hold starts, changes reason, or clears. Names are sanitized. Provisional holds log at DEBUG only.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 RED | 8194567 | test(119-04): add failing ArrQueueClient fetch-worker, size-cap, deadline and real-socket regressions |
| 1 GREEN | d7e2354 | feat(119-04): add ArrQueueClient ... non-blocking fetch worker handoff (IMP-02) |
| 2 RED | c1f192d | test(119-04): add failing CompletionGate verdict, proof-lifecycle, malformed-record and non-blocking-fetch regressions |
| 2 GREEN | d29a147 | feat(119-04): add CompletionGate with non-blocking fetch scheduling, per-target fenced proofs, backoff and hold registry (IMP-02) |

## Verification (observed)

- RED evidence for REL-03: both test files failed at collection with `ModuleNotFoundError: No module named 'controller.arr_queue'` / `'controller.completion_gate'` before their implementation commits.
- `pytest test_arr_queue.py test_completion_gate.py -q -p no:cacheprovider`: **91 passed, 19 subtests passed in 3.61 s**. `test_arr_queue.py` alone passed 27 tests in about 2.4 s on six consecutive runs.
- Thread-hygiene run (`-k "real_socket or stalled or never_blocks" -s`): 4 passed in 2.18 s, with no thread warnings.
- Whole-tree `ruff check src/python/`: **All checks passed**.
- Import smoke check printed `OK`.
- No-wait grep (`.join(`, `time.sleep`, `.wait(`) across both modules: 0.
- Every acceptance-criteria grep in both tasks matches its target count. `.poll(` (line 254) and `start_fetch(` (line 219) both come before the first `_proofs.get` (line 347).
- Test counts: 27 in `test_arr_queue.py` (needs ≥20), 64 in `test_completion_gate.py` (needs ≥47). Line counts: 713 and 1038.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `verdict()` must not clear other names' holds**
- **Found during:** Task 2
- **Issue:** The plan defines `verdict(name, size) == evaluate({name: size})[name]`. But `evaluate()` removes every name that isn't in the candidate set from the registry. A single-name `verdict()` call from 119-06's CommandProcessor would therefore clear every other hold, logging a burst of "hold cleared" INFO lines and blanking the UI reasons from 119-07.
- **Fix:** Both methods share `_run(candidates, prune)`. `evaluate` prunes and `verdict` does not. Polling, starting fetches, the decision and the non-blocking guarantee are the same for both.
- **Files:** `src/python/controller/completion_gate.py`. Covered by `test_verdict_does_not_clear_other_holds`.
- **Commit:** d29a147

**2. [Rule 1 - Bug] `Verdict.proven` field and `Verdict.proven()` constructor share one name**
- **Found during:** Task 2
- **Issue:** Defining `@staticmethod proven()` inside the frozen dataclass body makes it the default value of the `proven` field, which raises "non-default argument follows default argument".
- **Fix:** The constructor is attached with `setattr` after the class body. Instances still read the boolean field (it lives in the instance dict) and `Verdict.proven()` still builds a proven verdict. The public API is unchanged.
- **Commit:** d29a147

**3. [Rule 3 - Blocking] Trickle-server teardown could join handler threads with no time limit**
- **Found during:** Task 1
- **Issue:** The first two full runs took about 37 s, all of it inside `test_poll_reports_overrun_without_blocking_real_socket`. Six later runs took about 2.4 s and the slow case never came back. The only wait in that path with no time limit was `server_close()` joining handler threads.
- **Fix:** Set `server.block_on_close = False`. Handler threads are daemons and stop on their own once `stop_event` is set. Waiting for workers still goes through the 5 s-bounded `settle()`.
- **Files:** `src/python/tests/unittests/test_controller/test_arr_queue.py`
- **Commit:** d7e2354

**4. [Process] TDD RED commit for Task 1 as well**
- Task 1's `<action>` asked for one `feat` commit. Following the project note (tests committed first as `test(119-04)` for REL-03 evidence), Task 1 also got a separate RED commit.

**5. [Rule 3 - Environment] Worktree Poetry venv**
- The new worktree had no Poetry environment. I ran `poetry install --no-root` to install the existing locked dependencies only; no packages were added.

## Assumption Drift (advisory)

- **Found during:** Task 2, `test_verdict_is_nonblocking_and_returns_provisional_hold_for_fenced_pending_target`
- **Planned:** That test's prose expects `hold("sonarr_unavailable")` right after invalidation, when the proof came from Radarr.
- **Actual:** The plan's algorithm (step 5: "`<code>_unavailable` for the first non-fresh target that contributed a record") gives `radarr_unavailable`, because Radarr's pre-fence record is the evidence waiting on a refresh. The test asserts `radarr_unavailable` (provisional, not registered).
- **Why:** The algorithm text is the normative spec. Reporting the arr that actually holds the stale evidence also keeps the hold provisional while that arr's forced refresh is pending, instead of attributing it to an unrelated arr. 119-06 only depends on the hold being returned immediately (428), which is unchanged.

## Deferred Issues (out of scope)

- 9 failures and 3 errors in the controller suite on this macOS host, all in `test_extract/test_extract_process.py` and `test_scan/test_scanner_process.py`: multiprocessing child processes hit the 2 s pytest-timeout. These files don't import or reference the new modules (grep confirmed), and this plan changed no existing file. I did not re-run them on the base commit to confirm they were already failing. Not fixed. The other 815 controller tests pass.

## Known Stubs

None. As planned, the modules are not wired into the controller yet; 119-06 handles CommandProcessor/AutoQueue and 119-07 handles the model holds and lifecycle invalidation.

## Requirements

IMP-02 is only partly delivered here (the evidence foundation). It is not marked complete because the controller wiring lands in 119-06/119-07.

## Self-Check: PASSED

- FOUND: src/python/controller/arr_queue.py
- FOUND: src/python/controller/completion_gate.py
- FOUND: src/python/tests/unittests/test_controller/test_arr_queue.py
- FOUND: src/python/tests/unittests/test_controller/test_completion_gate.py
- FOUND commits: 8194567, d7e2354, c1f192d, d29a147
