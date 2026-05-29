---
phase: 97-medium-priority-python-coverage
plan: 04
subsystem: lftp-status-recovery-testing
tags: [coverage, python, lftp, parser, error-recovery, integration-test, COVMED-03]
requires:
  - "97-01 (coverage baseline anchor — wave dependency)"
provides:
  - "Integration coverage of Lftp.status() consecutive-error counter (lftp.py:298-313)"
  - "Real-parser proof that malformed `jobs -v` makes the genuine LftpJobStatusParser.parse() raise (truth #1)"
affects:
  - "Phase 100 CI threshold ratchet (these tests raise covered lines in lftp.py status() recovery branch — countable only in the containerized real-lftp run)"
tech-stack:
  added: []
  patterns:
    - "White-box recovery test: scoped `with patch.object(self.lftp, '_Lftp__run_command', return_value=<malformed>)` so the REAL parser runs against malformed input (NOT a parse() stub) — proves malformed→raise end-to-end"
    - "Controller-counter isolation: `with patch.object(self.lftp._Lftp__job_status_parser, 'parse', side_effect=[...])` to drive only the consecutive-error counter logic"
    - "Counter-reset asserted purely through public status() return values (no name-mangled counter read)"
    - "All patches context-manager scoped so they are removed before tearDown's real-binary exit()"
key-files:
  created: []
  modified:
    - "src/python/tests/integration/test_lftp/test_lftp_protocol.py"
decisions:
  - "Real-parser test patches `_Lftp__run_command` (NOT parse) to feed the malformed fixture so the genuine parser raises — Codex-corrected split that fixes the prior false-positive parse-stub"
  - "No source change to lftp.py: the reset line (lftp.py:305) is already on the success path; D-05 trivial-fix NOT triggered (validated by an off-tree logic check against the real Lftp.status() bytecode + real parser)"
  - "Integration tests written correctly but NOT executed on host: the real-lftp suite needs the lftp binary + sshd + `testgroup`, none present on host; setUpClass errors with KeyError('testgroup'). Must be validated in CI / `make run-tests-python`. No fabricated pass."
metrics:
  duration: ~25m
  completed: 2026-05-29
requirements: [COVMED-03]
---

# Phase 97 Plan 04: LFTP JobStatusParser Error-Recovery Counter Coverage Summary

Added four integration tests to `TestLftpProtocol` covering the previously-untested
`Lftp.status()` consecutive-error recovery path (`lftp.py:298-313`): one REAL-parser test
that proves a malformed `jobs -v` makes the genuine `LftpJobStatusParser.parse()` raise
`LftpJobStatusParserError` (via `_Lftp__run_command` injection, NOT a `parse()` stub — the
Codex-corrected fix for the prior false-positive coverage), plus three controller-counter
tests proving the counter increments and swallows while `<= MAX_CONSECUTIVE_STATUS_ERRORS`
(=2), re-raises on the 3rd consecutive error, and resets to 0 on a subsequent success. No
`lftp.py` change was needed (the reset line at 305 is already on the success path). COVMED-03
test code is complete; the real-lftp integration suite could **not be executed on this host**
(no lftp binary / sshd / `testgroup`) and **must be validated in CI / the test container** —
this is reported honestly below, not marked as a local pass.

## What Was Built

Extended `src/python/tests/integration/test_lftp/test_lftp_protocol.py` (per D-03, integration
layer, reusing the real-`Lftp` fixture from `setUp`):

- **Import + fixture constant:** added `from unittest.mock import patch`, added
  `LftpJobStatusParserError` to the existing `from lftp import ...` line, and a module-level
  `_MALFORMED_JOBS_OUTPUT` constant (the `bad string uh oh` block reused from
  `tests/unittests/test_lftp/test_job_status_parser.py::test_raises_error_on_bad_status`).

- **`test_status_real_parser_raises_on_malformed_output` (REAL parser, truth #1):** patches
  `_Lftp__run_command` to return the malformed fixture so the GENUINE
  `LftpJobStatusParser.parse()` runs and raises. Does **not** stub `parse`. Asserts the 1st and
  2nd consecutive real-parser failures return `[]` (counter `<= 2`, swallowed) and the 3rd
  re-raises `LftpJobStatusParserError` (counter `> 2`). Proves malformed→raise AND the re-raise
  path end-to-end.

- **`test_status_parser_error_increments_and_swallows` (controller counter):** parse-stub
  raises twice; both `status()` calls return `[]` (counter `-> 1`, `-> 2`, both `<= MAX`).

- **`test_status_parser_error_exceeds_max_reraises` (controller counter):** parse-stub raises
  three times; 1st/2nd swallowed, 3rd re-raises (`count -> 3 > MAX`).

- **`test_status_parser_error_counter_resets_on_success` (controller counter):** parse-stub
  sequence is `[err, err, success([]), err, err]`; asserts the two post-success errors are again
  swallowed (return `[]`) rather than re-raising — proving the success path reset the counter
  (had it not reset, the next error would be count 3 and re-raise). Asserted purely via public
  `status()` return values (no `_Lftp__consecutive_status_errors` read).

All four tests are `@pytest.mark.timeout(5)` (matching the suite) and use context-manager-scoped
patches so they are removed before `tearDown`'s real-binary `exit()`.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | REAL-parser test (truth #1) + controller increment/swallow/re-raise | `ba64f37` | `src/python/tests/integration/test_lftp/test_lftp_protocol.py` |
| 2 | Cover counter reset on subsequent success | `d0329c4` | `src/python/tests/integration/test_lftp/test_lftp_protocol.py` |

## Verification

**Ran on host (no lftp/sshd needed):**
- `poetry run python -m py_compile .../test_lftp_protocol.py` → COMPILE OK
- `poetry run pytest .../test_lftp_protocol.py -k "real_parser or parser_error" --collect-only -q`
  → **4/36 tests collected** (all four COVMED-03 tests collect; `@pytest.mark.timeout(5)` marker
  registered after `poetry install`, no `PytestUnknownMarkWarning`).
- `poetry run pytest tests/unittests/test_lftp/test_job_status_parser.py -k "bad_status" -q`
  → **1 passed** — confirms the reused malformed fixture genuinely makes the REAL parser raise.
- Acceptance greps: the real-parser test references `parse` only in its docstring/comments and
  patches `_Lftp__run_command` (NOT `parse`); the reset test contains no
  `_Lftp__consecutive_status_errors` read.

**Off-tree logic check (throwaway, NOT committed):** exercised the REAL `Lftp.status()` bytecode
and a REAL `LftpJobStatusParser` against the malformed fixture by instantiating `Lftp` via
`object.__new__` (bypassing the subprocess spawn) and wiring only the attributes `status()`
touches. All four behaviors passed — the parser logged
`LftpJobStateParser error: ... 'bad string uh oh'` (proving the real parser ran and raised),
the counter swallowed at 1/2, re-raised at 3, and reset on success. This validates the test
*logic* against the real source; it does NOT substitute for the real-lftp run.

**NOT run on host — must be validated in CI / container:**
- `poetry run pytest .../test_lftp_protocol.py -k "real_parser or parser_error" -q`
  → **3 errors / 1 error** at `setUpClass`: `KeyError: "getgrnam(): name not found: 'testgroup'"`.
  The host lacks the `lftp` binary (`/usr/bin/lftp`), a reachable sshd on `localhost:22`, and the
  `testgroup` account that the real-lftp harness requires (per the environment note and
  97-01-SUMMARY's identical host caveat). **This is an environment limitation, not a test defect**
  — the per-test logic never executes because `TestLftpProtocol.setUpClass` aborts first. These
  tests MUST be run via `make run-tests-python` / the `seedsyncarr_test_python` container in CI.
  **No passing run is claimed for the integration tests in this environment.**

The plan's `<verification>` (`-k "real_parser or parser_error"` exits 0) is therefore **NOT
verified locally** — it is expected to pass only in the containerized real-lftp environment per
the CI matrix. Flagged for the orchestrator's verification step and CI to confirm.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provisioned locked project dependencies to register the timeout marker**
- **Found during:** Task 1 verification
- **Issue:** A fresh poetry venv was created on collect; `pytest-timeout` (a declared,
  lockfile-pinned dev dependency) was absent, so `@pytest.mark.timeout(5)` raised
  `PytestUnknownMarkWarning`.
- **Fix:** Ran `poetry install` — installs already-committed, lockfile-pinned deps only (NOT a
  `poetry add` of an unverified package, so the Rule-3 package-install slopsquat exclusion does
  not apply). Re-collection showed the marker registered with no warning.
- **Files modified:** None tracked (lockfile unchanged; only the gitignored venv).
- **Commit:** n/a

No other deviations. No `lftp.py` source change: the counter-reset line (`lftp.py:305`) is
already on the success path, so the D-05 trivial-fix posture was checked and NOT triggered.

## Authentication Gates

None.

## Known Stubs

None. The controller-counter tests intentionally stub `parse()` (correct, scoped to counter
logic per the plan); truth #1 is proven by the real-parser test which does NOT stub `parse`.
These are deliberate, plan-mandated test doubles, not placeholder stubs.

## Threat Flags

None. No new network endpoint, auth path, file access pattern, or schema change was introduced —
this plan is test-only. The threat-model entry T-97-04-01 (DoS via consecutive parse errors) is
exercised by the new tests as designed (transient malformed status swallowed `<= 2`, persistent
`> 2` surfaces).

## Notes for Orchestrator

- **STATE.md and ROADMAP.md were NOT modified** by this executor (per the objective — orchestrator
  owns those writes after the wave).
- **Integration tests are written but unexecuted on host.** The orchestrator's verifier (and CI)
  must run them in the real-lftp container (`make run-tests-python`). The plan's verification gate
  is intentionally NOT marked as locally passed — do not treat collection-only as a functional
  pass for the integration assertions.
- COVMED-03 test code is complete and covers all four documented points (malformed→real parser
  raises; increment/swallow `<= 2`; `> 2` re-raise; reset-on-success).

## Self-Check: PASSED

- Modified file exists: FOUND `src/python/tests/integration/test_lftp/test_lftp_protocol.py`
- Task 1 commit exists: FOUND `ba64f37`
- Task 2 commit exists: FOUND `d0329c4`
- All four COVMED-03 tests collect (`4/36 tests collected`)
- Parser unit test (real parser raises on malformed fixture) PASSED
- Integration-test execution honestly reported as host-blocked (setUpClass KeyError: testgroup) — no fabricated pass
