---
phase: 117-transfer-state-safety
plan: 04
subsystem: lftp-parser
tags: [python, lftp, parser, peek-before-pop, b1]
requires:
  - 117-01 (B1 RED regressions)
  - 117-03 (RED evidence)
provides:
  - "RegexPatterns.is_chunk_data predicate (CHUNK_AT / CHUNK_AT2 / CHUNK_GOT)"
  - "RegexPatterns.JOB_HEADER guard pattern"
  - "Peek-before-pop at audit sites #2, #9, #10"
affects:
  - 117-07 (GREEN evidence; copies the deferred-site record below)
tech-stack:
  added: []
  patterns: ["peek-before-pop: consume a follower line only on a positive anchored-regex match"]
key-files:
  created: []
  modified:
    - src/python/lftp/job_status_parser.py
decisions:
  - "Predicate lives as a @staticmethod RegexPatterns.is_chunk_data (one definition, two call sites)"
  - "A trailing \\chunk with no data line is tolerated instead of raising (same root cause as the pget case)"
metrics:
  duration: ~10m
  completed: 2026-10-08
  tasks: 2
  files: 1
requirements: [XFER-01]
---

# Phase 117 Plan 04: Parser peek-before-pop (B1) Summary

The `jobs -v` parser now consumes a follower line only when it positively matches the expected shape, so a pget with no status line, a `\chunk` with no data line, or a mirror-empty line followed by a job header can no longer swallow the next job's header.

## Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | `is_chunk_data` predicate; peek at pget data line (#2) and `\chunk` data line (#10) | eaa4847 | src/python/lftp/job_status_parser.py |
| 2 | `JOB_HEADER` guard on the mirror-empty follower (#9) | 292c496 | src/python/lftp/job_status_parser.py |

## Verification (observed)

- `pytest tests/unittests/test_lftp -q` after Task 2: **4 failed, 133 passed**. All 4 failures are `test_lftp_status_contract.py::TestLftpStatusBoundary::*`, which test `lftp.py` (owned by Plan 05) and are listed as RED-at-baseline in `117-REL01-EVIDENCE.md`.
- `pytest test_job_status_parser.py test_job_status_parser_components.py`: **114 passed**, 0 failed.
- The five B1 regressions pass: `test_jobs_pget_no_data_line_followed_by_pget_header`, `test_jobs_pget_no_data_line_followed_by_mirror_header`, `test_jobs_chunk_without_data_line_followed_by_mirror_header`, `test_jobs_chunk_without_data_line_followed_by_chunk`, `test_jobs_mirror_empty_followed_by_header_containing_getting_file_list`. `test_queue_and_jobs_4`, `test_jobs_missing_pget_data_line`, `test_parse_header_consumes_sftp_line` also pass.
- Whole-tree `ruff check src/python/`: `All checks passed!`
- Grep checks: `"Missing data line for chunk"` = 0; `is_chunk_data` = 3; `JOB_HEADER` = 2; `"Getting file list" in lines[0]` = 1.
- `git diff --stat HEAD~2 HEAD`: only `src/python/lftp/job_status_parser.py`.

## Deferred parser sites (D-09)

These audit sites are recorded and deliberately left unchanged:

- **#1 pget sftp-line check** (`"sftp" in lines[0]` in `PgetJobParser.parse_header`). When it misfires, a later parse step almost always raises loudly, so it does not cause a silent job loss.
- **#6 QueueParser line-3 unconditional pop.** It assumes lftp always prints "Now executing:" or "Queue is stopped." when a job is active.
- **#8 `\transfer` with no data line** (`_handle_file_transfer`, consume-then-raise). After B2 this shows up as "status unavailable", never as a lost job. Revisit if NAS logs show "Missing chunk data for filename".

## Deviations from Plan

- **Two commits instead of one.** Task 1 was committed on its own (`fix(117-04): pget and chunk data lines ...`) to follow the per-task commit protocol. Task 2 uses the commit subject the plan specified.
- **Count correction, no code change.** The plan expected 2 Plan-05 contract failures in `test_lftp`. The actual number is 4, and all 4 are RED at the baseline in `117-REL01-EVIDENCE.md`. None of them are parser tests.

## Known Stubs

None.

## Threat Flags

None. T-117-01 is mitigated by anchored positive-match peeking and the `JOB_HEADER` guard. No new log lines were added, and `JOB_HEADER` is a linear regex.

## Self-Check: PASSED

- src/python/lftp/job_status_parser.py: FOUND
- eaa4847: FOUND
- 292c496: FOUND
