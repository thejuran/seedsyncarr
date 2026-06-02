---
phase: 109
slug: controller-decomposition
date: 2026-06-01
requirement_ids: [ARCH-01]
source: 109-RESEARCH.md §"Validation Architecture"
---

# Phase 109: Controller Decomposition — Validation Strategy

> Derived from `109-RESEARCH.md` §"Validation Architecture". This is a behavior-preserving
> refactor: the **existing** Python test suite is the entire regression net (ARCH-01 criterion #3).
> No new test files are required — Wave 0 has zero coverage gaps.

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9 + unittest |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.report]`) |
| Quick run command | `cd src/python && pytest tests/unittests/test_controller/ -v` |
| Full suite / coverage gate | `make run-tests-python` (Docker) |
| Coverage floor | `fail_under = 88` (must hold or rise — ARCH-01 criterion #5) |

## Phase Requirements → Test Map

| Req ID | Behavior under test | Test type | Automated command | Exists? |
|--------|---------------------|-----------|-------------------|---------|
| ARCH-01 | Public API unchanged (constructor, start/exit, command entry points, model accessors) | Integration + unit | `make run-tests-python` | Yes |
| ARCH-01 | Thread-safety invariants (WR-02 TOCTOU, lock ordering, release-before-subprocess) | Unit | `pytest tests/unittests/test_controller/test_auto_delete.py -v` | Yes |
| ARCH-01 | mock.patch binding-site preserved (D-05) — `controller.controller.{ModelBuilder,LftpManager,ScanManager,FileOperationManager}` patch targets still fire | Unit | `pytest tests/unittests/test_controller/ -v` | Yes |
| ARCH-01 | Name-mangled internals still accessible (`_Controller__*` methods/fields tests reach) | Unit | `pytest tests/unittests/test_controller/ -v` | Yes |
| ARCH-01 | Coverage ≥ 88% | Coverage gate | `make run-tests-python` | Yes |

## Sampling Rate (per D-06 three-plan staging)

- **Per task / per commit:** `cd src/python && pytest tests/unittests/test_controller/ tests/integration/test_controller/ -v`
- **Per plan completion (109-01, 109-02, 109-03):** `make run-tests-python` — full suite green is the gate before the plan is considered done.
- **Phase gate:** Full suite green (`make run-tests-python`) with `fail_under ≥ 88` before `/gsd:verify-work`.

## Wave 0 Gaps

None. Existing test infrastructure covers all phase requirements; the suite is the regression net and must pass **unmodified** (ARCH-01 criterion #3). Any test change required to make the refactor pass is a signal the refactor broke the public/internal contract — fix the code, never the test.

## Validation Notes specific to this refactor

- **The dunder entry points stay on `Controller`.** Tests reach `_Controller__execute_auto_delete`, `_Controller__schedule_auto_delete`, `_Controller__process_commands`, `_Controller__check_webhook_imports`, and mangled fields (`_Controller__pending_auto_deletes`, `_Controller__model`, `_Controller__model_lock`, `_Controller__shutdown_event`, `_Controller__active_downloading_file_names`). These must remain defined on `Controller`; collaborators hold the extracted logic the coordinator delegates to. A test failing with `AttributeError: ... has no attribute '_Controller__...'` means a dunder was wrongly relocated.
- **Collaborators store injected locks under single-underscore names** (`self._model_lock`), never `self.__model_lock` (which would mangle to `_<Collaborator>__model_lock` — a different object than the one tests inspect).
- **Managers are constructed in `Controller.__init__` in `controller.py`** (not inside any collaborator) so `patch('controller.controller.X')` still binds.
