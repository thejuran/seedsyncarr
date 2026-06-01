---
phase: 107
phase_slug: mp-logger-spawn-safety
date: 2026-06-01
nyquist_validation: enabled
source: 107-RESEARCH.md §"Validation Architecture"
---

# Phase 107: MP-Logger Spawn Safety — Validation Strategy

> Nyquist validation strategy. Derived from `107-RESEARCH.md` §"Validation Architecture".
> Requirement: **INFRA-01**.

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing), `unittest.TestCase` style |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd src/python && pytest tests/unittests/test_common/test_multiprocessing_logger.py -v --timeout=30` |
| Full suite command | `make run-tests-python` (Docker CI, amd64 + arm64) |
| Python floor (must hold or rise) | `fail_under` ≥ 88 (3 previously-uncounted tests now counted — holds or rises) |
| Angular / E2E floors (unaffected, must stay green) | Karma `check.global` 83/68/79/83 — untouched this phase |

## Phase Requirements → Test Map

| Req ID | Behavior to validate | Test type | Automated command | Surface |
|--------|----------------------|-----------|-------------------|---------|
| INFRA-01 | spawn-context child logs arrive via the queue (no `SemLock` RuntimeError) | multiprocess integration | `pytest …::test_main_logger_receives_records -v` | `test_multiprocessing_logger.py` ~L215 (updated: module-scope target + spawn ctx) |
| INFRA-01 | spawn child logs under child logger names | multiprocess integration | `pytest …::test_children_names -v` | `test_multiprocessing_logger.py` ~L245 (updated) |
| INFRA-01 | spawn child respects configured log levels | multiprocess integration | `pytest …::test_logger_levels -v` | `test_multiprocessing_logger.py` ~L270 (updated) |
| INFRA-01 (regression) | existing single-process tests still pass (exception capture, propagate, empty-queue, clean-shutdown) | unit | `pytest tests/unittests/test_common/test_multiprocessing_logger.py -v` | L89–188 (unchanged) |
| INFRA-01 (COMPAT) | full Python suite green under fork (Linux default) — no behavior change | suite | `make run-tests-python` | whole suite |

## Spawn-Platform Determinism

The three updated analog tests launch child processes via the logger's stored spawn context
(`multiprocessing.get_context("spawn")`, exposed on the instance per CONTEXT D-02). This means:

- **macOS (spawn default):** tests exercise spawn natively — same as before the fix, but now without the RuntimeError.
- **Linux CI (fork default):** tests exercise spawn **explicitly** — even though the platform default is fork, the tests deterministically use a spawn-context `Process`. This is the regression net D-04 establishes.

A future regression that accidentally creates the queue from a fork context WILL fail these tests on Linux CI, not just macOS. That is the desired, intended behavior.

## Sampling Rate

- **Per-task commit:** `cd src/python && pytest tests/unittests/test_common/test_multiprocessing_logger.py -v --timeout=30`
- **Per-wave merge:** `cd src/python && pytest tests/unittests/test_common/ -v`
- **Phase gate:** full suite green — `make run-tests-python` — before verification.

## Wave 0 Gaps

None — the existing pytest infrastructure (`@pytest.mark.timeout`, `testfixtures.LogCapture`, bounded `join`) covers all phase requirements. No new test files, no new `conftest.py` fixtures, no framework install. The three analog tests are **updated, not created**; no test is deleted or skipped.

## Notes

- The criterion #2 phrase "without modification to the test code" is interpreted per RESEARCH.md: it means *no test was weakened, skipped, or deleted to hide the bug* — not that the test file is byte-identical. The minimal-and-necessary test change is promoting each local `process_1` closure to a module-level picklable target (spawn requires importable targets) and routing child `Process` creation through the exposed spawn context. Assertions and tested behavior are unchanged.
- Out of scope (do NOT fold in): the `except Exception` silent-listener-shutdown gap at `multiprocessing_logger.py:78` (CONCERNS.md). Distinct reliability concern.
