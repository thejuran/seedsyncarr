---
phase: 122-safety-acceptance-and-logging-fixes
plan: 01
subsystem: logging
tags: [logging, completion-gate, tdd, regression, log-injection]

# Dependency graph
requires:
  - phase: 120-sonarr-5-compatibility
    provides: "Live-capture finding that 'Completion hold cleared' misleads evidence review (120-CAPTURE-NOTES.md)"
provides:
  - "CompletionGate._clear_hold(name, drop_reason=None) split: 'cleared' reserved for proof-based release, 'dropped (<reason>)' for prune and no-arr-enabled removals"
  - "D-18 regression pair pinning the cleared-vs-dropped wording, including log-injection sanitization of the dropped root name"
affects: [122-SAFE01-EVIDENCE, "Phase 122 plan 02+ (shares the completion-gate log wording as cited evidence source)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reason-qualified single logging chokepoint (drop_reason parameter), same shape as Controller.__defer_auto_delete"

key-files:
  created: []
  modified:
    - src/python/controller/completion_gate.py
    - src/python/tests/unittests/test_controller/test_completion_gate.py

key-decisions:
  - "Internal shape: optional drop_reason keyword on the existing _clear_hold method (Claude's Discretion per CONTEXT.md), not a new method or class split"
  - "drop_reason values are fixed module literals, never sanitized (only root names pass through sanitize_log_value)"

patterns-established:
  - "drop_reason=None keeps existing 'cleared' wording byte-identical; a reason string switches to 'dropped (<reason>)' — mirrors __defer_auto_delete's reason-string chokepoint pattern"

requirements-completed: [LOG-02]

# Metrics
duration: 8min
completed: 2026-10-22
---

# Phase 122 Plan 01: Completion Gate Dropped-vs-Cleared Logging Summary

**Split `CompletionGate._clear_hold` so "cleared" means only the proof-based release and "dropped (reason)" covers the prune and no-arr-enabled removals, test-first (RED then GREEN).**

## Performance

- **Duration:** 8 min
- **Started:** 2026-10-22T13:49:39Z
- **Completed:** 2026-10-22T13:52:59Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Renamed and flipped the two existing hold-removal tests to assert the D-17 "dropped" wording and the absence of "cleared", and added a log-injection regression pinning `sanitize_log_value` on the dropped-line root name — all three failed with `AssertionError` against the pre-fix code (RED), and every other test in the file (61) stayed green
- Added an optional `drop_reason` parameter to `_clear_hold`; the no-arr path (`_run` step 2) and the prune path now pass fixed reason literals, while the proof-based release call in `_record` is untouched and still logs the byte-identical "cleared" wording
- All 67 tests in `test_completion_gate.py` pass (GREEN); whole-tree `ruff check src/python/` is clean

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — rename and flip the prune/no-arr hold tests, add sanitize regression** - `589752a` (test)
2. **Task 2: GREEN — add drop_reason to _clear_hold and pass the D-17 reasons** - `adb4000` (fix)

**Plan metadata:** (this commit, to follow)

## Files Created/Modified
- `src/python/controller/completion_gate.py` - `_clear_hold(name, drop_reason=None)`: `None` logs unchanged "Completion hold cleared for '%s'"; a reason logs "Completion hold dropped for '%s' (%s)". No-arr path passes `drop_reason="no Sonarr/Radarr integration enabled"`; prune path passes `drop_reason="no longer a queue candidate"`; `_record`'s proof-based release call is unchanged.
- `src/python/tests/unittests/test_controller/test_completion_gate.py` - `test_hold_dropped_when_no_longer_candidate` (renamed from `test_hold_cleared_when_no_longer_candidate`), `test_hold_dropped_when_no_arr_enabled` (renamed from `test_no_targets_clears_existing_holds`), both flipped to assert the exact dropped wording and the absence of "hold cleared"; `test_hold_cleared_when_proven` extended to assert the absence of "hold dropped"; new `test_dropped_line_sanitizes_root_name` pins `sanitize_log_value` on a root name containing a newline.

## Decisions Made
- Followed CONTEXT.md's Claude's-Discretion guidance: a `drop_reason` keyword parameter on the existing single method, not separate methods, since all three call sites already funnel through one private method and no test calls `_clear_hold` directly.
- `drop_reason` strings are module literals passed by the two call sites in `_run`; they are never interpolated from untrusted input, so no additional sanitization was added for them (only the root name uses `sanitize_log_value`, unchanged from before).

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched the plan's `<action>` and acceptance criteria exactly; no Rule 1-4 deviations were needed.

## Verification Evidence

### RED (Task 1) — before the fix

Command: `cd src/python && poetry run pytest tests/unittests/test_controller/test_completion_gate.py -p no:cacheprovider -q -k "dropped or proven"`

```
...F.FF                                                               [100%]
=================================== FAILURES ===================================
____________ TestHoldRegistry.test_dropped_line_sanitizes_root_name ____________
    def test_dropped_line_sanitizes_root_name(self):
        name = "Evil\nRoot"
        _decide(self.gate, {name: 1, "Other": 1})
        self.gate.evaluate({"Other": 1})
        self.assertEqual({"Other": "no_queue_entry"}, self.gate.holds)
        expected = "Completion hold dropped for '" + sanitize_log_value(name) + "' (no longer a queue candidate)"
>       self.assertEqual(1, sum(1 for line in self.info() if line == expected))
E       AssertionError: 1 != 0

____________ TestHoldRegistry.test_hold_dropped_when_no_arr_enabled ____________
    def test_hold_dropped_when_no_arr_enabled(self):
        ...
>       self.assertEqual(
            1,
            sum(1 for line in self.info()
                if line == "Completion hold dropped for '" + ROOT + "' (no Sonarr/Radarr integration enabled)")
        )
E       AssertionError: 1 != 0

_________ TestHoldRegistry.test_hold_dropped_when_no_longer_candidate __________
    def test_hold_dropped_when_no_longer_candidate(self):
        ...
>       self.assertEqual(
            1,
            sum(1 for line in self.info()
                if line == "Completion hold dropped for '" + ROOT + "' (no longer a queue candidate)")
        )
E       AssertionError: 1 != 0

3 failed, 4 passed, 60 deselected, 3 warnings, 3 subtests passed in 0.18s
```

Full-file run (`-q`, no `-k` filter) at the same pre-fix state: `3 failed, 64 passed` — exactly the 3 new/renamed tests failed, with `AssertionError` (not `ImportError`/`TypeError`), confirming they fail for the intended reason against the current single-message `_clear_hold`.

### GREEN (Task 2) — after the fix

Command: `cd src/python && poetry run pytest tests/unittests/test_controller/test_completion_gate.py -p no:cacheprovider -q`

```
67 passed, 3 warnings, 15 subtests passed in 1.22s
```

Command: `ruff check src/python/` (whole tree, separate CI gate per project convention)

```
All checks passed!
```

### Acceptance criteria checks (all run and observed)

- `grep -c "def test_hold_dropped_when_no_longer_candidate\|def test_hold_dropped_when_no_arr_enabled\|def test_dropped_line_sanitizes_root_name" ...` → `3`
- `grep -c "def test_hold_cleared_when_no_longer_candidate\|def test_no_targets_clears_existing_holds" ...` → `0`
- `grep -c "Completion hold cleared for '%s'" src/python/controller/completion_gate.py` → `1`
- `grep -c "Completion hold dropped for '%s' (%s)" src/python/controller/completion_gate.py` → `1`
- `grep -c 'drop_reason="no longer a queue candidate"'` → `1`; `grep -c 'drop_reason="no Sonarr/Radarr integration enabled"'` → `1`
- `git log --format=%s -2` → `fix(122-01): ...` on top of `test(122-01): ...` (RED strictly older than GREEN)
- No file deletions in either commit (`git diff --diff-filter=D --name-only HEAD~1 HEAD` empty both times)
- Grepped `_clear_hold(` and `CompletionGate(` call sites across the whole `src/python` tree outside the two modified files (`test_sonarr5_queue.py`, `test_controller_unit.py`, `test_auto_queue.py`, `controller.py`) — none assert on "hold cleared"/"hold dropped" wording and none call `_clear_hold` directly, so the signature-compatible change (`drop_reason` defaults to `None`) does not affect them.

**Not run as part of this plan's gate:** the phase-level full `tests/unittests` suite (122-VALIDATION.md's "full suite command", owned by the wave-completion gate, not this plan's per-task `<verify>`) was additionally kicked off for extra corroboration but hung (no progress for ~5h20m, ~5 CPU-hours) and was killed by the orchestrator, so it produced no result. The same hang hit the base-commit run, so it predates this change; full-suite comparison is deferred to the Plan 03 gate / PR CI. It is not required by this plan's acceptance criteria, which are the two commands above, both confirmed green.

## Final wording of all three lines

- Release (unchanged): `Completion hold cleared for '<root>'`
- Prune: `Completion hold dropped for '<root>' (no longer a queue candidate)`
- No arr: `Completion hold dropped for '<root>' (no Sonarr/Radarr integration enabled)`

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

LOG-02's code and regression are complete; the SAFE-01 evidence capture (this phase's other plans) can now quote trustworthy "dropped"/"cleared" lines per CONTEXT.md's Specific Ideas note. No blockers for 122-02+ (disjoint files).

---
*Phase: 122-safety-acceptance-and-logging-fixes*
*Completed: 2026-10-22*

## Self-Check: PASSED

- FOUND: src/python/controller/completion_gate.py
- FOUND: src/python/tests/unittests/test_controller/test_completion_gate.py
- FOUND: .planning/phases/122-safety-acceptance-and-logging-fixes/122-01-SUMMARY.md
- FOUND commit: 589752a (test(122-01))
- FOUND commit: adb4000 (fix(122-01))
