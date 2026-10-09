---
phase: 118-durable-state
plan: 01
subsystem: common/persist (tests)
tags: [python, pytest, persist, atomic-write, regression, red-first]
requires: []
provides:
  - "TestPersistAtomicWrite RED class pinning the atomic Persist.to_file contract"
  - "118-REL01-EVIDENCE.md RED section (fail-before proof at 99de178)"
affects:
  - "Plan 118-02 (fix must turn the 9 failures GREEN without test edits)"
tech-stack:
  added: []
  patterns:
    - "Failure injection via global os.fsync/os.replace/tempfile.mkstemp patches, with S_ISREG/S_ISDIR discriminators falling through to the real fsync"
key-files:
  created:
    - .planning/phases/118-durable-state/118-REL01-EVIDENCE.md
  modified:
    - src/python/tests/unittests/test_common/test_persist.py
decisions:
  - "Patch only global module attributes (os.fsync, os.replace, tempfile.mkstemp) so pre-fix failures are behavioral AssertionErrors, never harness errors"
  - "PERSIST-01/PERSIST-02 left unchecked in REQUIREMENTS.md: this plan adds RED tests only; the requirements are satisfied when 118-02 lands the fix"
metrics:
  duration: "~10 min"
  completed: 2026-10-09
  tasks: 2
  files: 2
---

# Phase 118 Plan 01: Atomic-write RED regressions for Persist.to_file Summary

Ten-test `TestPersistAtomicWrite` class that pins the atomic-save contract (original intact byte-for-byte, no temp left, original exception unwrapped, directory-fsync failure logged not raised, no content in logs), committed test-only with 9 behavioral RED failures recorded against the unfixed `to_file`.

## Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add TestPersistAtomicWrite RED class (test-only) | `99de178` | `src/python/tests/unittests/test_common/test_persist.py` |
| 2 | Record RED evidence against pre-fix SHA | `054b400` | `.planning/phases/118-durable-state/118-REL01-EVIDENCE.md` |

## Verification (observed)

- `poetry run pytest tests/unittests/test_common/test_persist.py -q -p no:cacheprovider -rf --tb=line` → `9 failed, 8 passed`; all 9 FAILED lines are in `TestPersistAtomicWrite`.
- junit XML: 9 `<failure>` elements, all `AssertionError`; 0 ImportError/AttributeError/ModuleNotFoundError/TypeError.
- Evidence run (persist + config + seedsyncarr tests): `9 failed, 82 passed, 1 warning in 0.16s`; all 7 `TestPersist` tests, `TestConfig::test_to_file` and `TestSeedsyncarrReencrypt::test_enable_existing_plaintext_reencrypts` pass.
- `git diff --stat 62aa868 HEAD -- src/python/common ':!src/python/tests'` → empty.
- `poetry run ruff check src/python/` (0.15.9) and `uvx ruff@0.15.22 check src/python/` → both `All checks passed!`.
- Acceptance greps: 17 `def test_`; no `patch("common.persist`; exactly one `assertLogs("seedsyncarr.Persist"`; file is 259 lines; `git show --stat 99de178` lists only the test file.
- Extra probe: all 17 tests passed in a scratch copy of `src/python` with the RESEARCH Code Example 1 `to_file` substituted, so the RED set is satisfiable by the planned fix. The repo's production file was not touched.

## Deviations from Plan

None in code. One bookkeeping choice: `requirements.mark-complete` was not run for PERSIST-01/PERSIST-02, because this plan only adds failing tests; the requirements are met when Plan 118-02 lands the fix.

The test commit diff shows 4 deleted lines: these are the reordered import block (alphabetized, with `errno`, `stat`, `patch` and `ServiceExit` added). No `TestPersist` test body changed.

## Known Stubs

None. The evidence file's `## GREEN (post-fix)` section is an intentional placeholder (`_(recorded by Plan 118-02)_`) as specified by the plan.

## Threat Flags

None. Tests write only inside per-test `mkdtemp` directories; T-118-01 (no content in logs) is pinned by the directory-fsync test.

## Self-Check: PASSED

- FOUND: src/python/tests/unittests/test_common/test_persist.py
- FOUND: .planning/phases/118-durable-state/118-REL01-EVIDENCE.md
- FOUND: 99de178
- FOUND: 054b400
