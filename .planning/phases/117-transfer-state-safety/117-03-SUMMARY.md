---
phase: 117-transfer-state-safety
plan: 03
subsystem: release-gate evidence
tags: [evidence, rel-01, red-first, pytest, ruff]
requires:
  - 117-01 (B1/B2 RED tests)
  - 117-02 (B3 RED tests)
provides:
  - "RED half of the REL-01 gate-1 fail-before/pass-after evidence for XFER-01..05"
affects:
  - "Plan 117-07 (fills the GREEN section)"
  - "Phase 118 (consumes REL-01 gate 1)"
tech-stack:
  added: []
  patterns:
    - "Failure types taken from the junit XML of the same invocation as the -rf summary"
key-files:
  created:
    - .planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md
  modified: []
decisions:
  - "FAILED lines carry the node ID verbatim from -rf plus the junit failure message, because this pytest's -rf --tb=line summary prints no exception text"
metrics:
  duration: ~10 min
  completed: 2026-10-08
  tasks: 1
  files: 1
requirements: [XFER-01, XFER-02, XFER-03, XFER-04, XFER-05]
---

# Phase 117 Plan 03: RED evidence for XFER-01..05 Summary

The RED run of the phase quick-run file set is recorded in `117-REL01-EVIDENCE.md`, in the Phase 116 format. It ran at RED SHA `05f03ae`, whose production tree (`src/python/lftp`, `common`, `controller`, excluding tests) is byte-identical to `7da18e0`. Result: **`26 failed, 464 passed, 1 warning in 1.39s`**. The GREEN section is left `pending` for Plan 117-07.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Run the RED quick run against unfixed code and record the evidence | 06c3ffb | 117-REL01-EVIDENCE.md |

## Verification (observed)

- `git diff --stat 7da18e0 HEAD -- src/python/lftp src/python/common src/python/controller ':!src/python/tests'` printed nothing (0 lines), so the production tree is unfixed.
- Quick run: `26 failed, 464 passed, 1 warning in 1.39s`. This matches the expected 5 + 4 + 9 + 4 + 4 = 26 and the orchestrator's post-merge run.
- Exception types in the junit XML: 24 `AssertionError`, 2 `lftp.job_status_parser.LftpJobStatusParserError` (`test_jobs_pget_no_data_line_followed_by_pget_header`, `test_jobs_chunk_without_data_line_followed_by_chunk`). None is ImportError, AttributeError or TypeError.
- Whole-tree ruff (`ruff check <worktree>/src/python/`, ruff 0.15.9): `All checks passed!`
- Acceptance greps on the evidence file:
  - `^FAILED` = 26, of which `LftpJobStatusParserError` = 2 and `AssertionError` = 24.
  - The table has 26 data rows covering XFER-01..05.
  - The `## GREEN (post-fix) — Plan 117-07` heading is present, followed by `pending`.
  - The file is 139 lines (min 60).
- The commit touches only `117-REL01-EVIDENCE.md`, and its subject starts with `docs(117-03):`.

## Deviations from Plan

**1. [Environment] Main checkout's Poetry interpreter used instead of `poetry run`**
- `poetry run` in a worktree creates a fresh empty venv. The exact command was `/Users/julianamacbook/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12/bin/python -m pytest <plan's arguments> --junitxml=<scratchpad>/117-red.xml`, run from the worktree's `src/python` so it tested the worktree's code. Ruff came from `ruff` on PATH. The evidence file records this.

**2. [Format] FAILED line suffixes come from the junit XML**
- This pytest version's `-rf --tb=line` short summary prints only node IDs. To meet the acceptance criterion that every FAILED line names its exception type, each line is the verbatim node ID plus ` - ` and the first line of that test's junit `<failure message>` from the same run. One long `LftpJobStatus` repr is truncated with `...`. The evidence file states this.

**3. [Process] Worktree base corrected at start**
- The worktree HEAD was `f8c94e9`, an ancestor of the required base, so it was hard-reset to `05f03ae` before any work. The tree was clean, so nothing was lost.

## Known Stubs

The GREEN section and the new-contract test table are intentionally `pending`. Plan 117-07 fills them.

## Self-Check: PASSED
- FOUND: .planning/phases/117-transfer-state-safety/117-REL01-EVIDENCE.md
- FOUND commit: 06c3ffb
