---
phase: 117-transfer-state-safety
plan: 07
subsystem: release-evidence
tags: [evidence, rel-01, green, full-suite, ruff, validation]
requires: ["117-04", "117-05", "117-06", "117-08"]
provides:
  - "117-REL01-EVIDENCE.md GREEN section (pass-after half of REL-01 gate 1 for XFER-01..05)"
  - "117-VALIDATION.md signed off (nyquist_compliant: true)"
affects:
  - Phase 118 REL-01 release gate
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - .planning/phases/117-transfer-state-safety/117-07-SUMMARY.md
  modified:
    - .planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md
    - .planning/phases/117-transfer-state-safety/117-VALIDATION.md
decisions:
  - "New-contract count is 34, not the plan's estimated 32: Plan 06 added 6 success-clock tests instead of 4"
  - "The four macOS spawn-context failures from deferred-items.md are pre-existing/environmental: they sit in the Phase 116 baseline files with identical counts"
metrics:
  duration: ~15m
  completed: 2026-10-08
  tasks: 2
  files: 2
requirements: [XFER-01, XFER-02, XFER-03, XFER-04, XFER-05]
---

# Phase 117 Plan 07: GREEN evidence and validation sign-off Summary

Host-side pass-after evidence for Phase 117 is recorded at post-fix SHA `d7c76bc`. All 26 RED regressions pass, the full host suite has no new failures against the Phase 116 baseline, whole-tree ruff is clean, and the validation strategy is signed off pending CI.

## Observed results

- **Targeted run** (26 RED names via `-k`): `26 passed, 133 deselected, 1 warning in 0.14s`. All 26 `PASSED` lines are in the evidence file verbatim.
- **Quick run** (Plan 03 ten-path set): `524 passed, 1 warning in 0.77s`, 0 failed. Delta vs RED (`26 failed, 464 passed`): 464 + 26 flipped + 34 new = 524.
- **New-contract tests**: 34 new functions, all passing (05: 7, 06: 7, 08: 20), plus the extended `test_default_values`. Preservation set: `10 passed`.
- **Full host suite** part 1 (four baseline files ignored): `1471 passed, 2 warnings in 40.88s`, 0 failed / 0 errors. Part 2 (each baseline file under a 60 s alarm): sshcp `11 failed`; scanner_process `3 failed, 1 passed, 3 errors`; system scanner `1 failed, 19 passed`; extract_process `6 failed` (pytest-timeout). Total 21 failed / 3 errors, equal to the Phase 116 baseline: no new failures.
- **Ruff** (whole tree, 0.15.9): `All checks passed!`
- No tag on HEAD; `src/python/pyproject.toml` unchanged since `7da18e0` (version 1.7.2).

## Recorded for Phase 118 (in the evidence file)

- Fix commit SHAs per plan: 04 `eaa4847`/`292c496`, 05 `d313ff3`, 06 `7cfa98f`, 08 `4bc2b79`/`0d5b1b8`/`a96e160`.
- Deferred parser sites D-09 #1, #6, #8.
- CI-only: the 4 integration counter tests. Plan 05 flipped 10 assertions in them (its action text said 8).
- Timeout semantics, Plan 08 submitted-unobserved protection, and the codex review history. Codex passes 1-3 were fixed by plan revisions. The pass-4 finding (LFTP command-stream resync after a timeout) was owner-accepted and moved to backlog Phase 999.2.
- macOS `spawn` failures from `deferred-items.md` classified as pre-existing/environmental.

## Stop-during-status-failure effect (for the owner)

If you press Stop while lftp status is temporarily unavailable (a tolerated parse error or a `jobs -v` timeout), Stop now returns the generic "Lftp error" instead of reporting success. Nothing is marked stopped, and you can retry Stop once status recovers. Before this phase, Stop could report success while lftp kept downloading.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | a4e6387 | docs(117-07): record GREEN targeted and quick-run evidence |
| 2 | fd58986 | docs(117-07): record GREEN evidence and sign off validation |

## Deviations from Plan

- **Two commits instead of one.** The plan put both files in one Task 2 commit. Task 1's evidence was committed on its own, following the per-task commit protocol. The Task 2 commit has the plan's subject and touches exactly the two planned files.
- **Interpreter.** In a worktree, `poetry run` creates an empty venv, so every run used the main checkout's Poetry interpreter (the same approach as the RED run). That interpreter has pytest-timeout, so `test_extract_process.py` ended as 6 timeout failures, not 6 hangs. The count is unchanged.
- **New-contract count 34 vs the planned 32.** The plan's estimate was reconciled against the SUMMARYs: Plan 06 added 2 extra success-clock cases. The arithmetic matches the observed 524.

## Known Stubs

None.

## Threat Flags

None. These are documentation-only changes.

## Self-Check: PASSED

- FOUND: 117-REL01-EVIDENCE.md, 117-VALIDATION.md, 117-07-SUMMARY.md
- FOUND: a4e6387, fd58986
