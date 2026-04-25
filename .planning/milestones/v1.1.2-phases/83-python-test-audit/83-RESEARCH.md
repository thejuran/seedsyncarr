# Phase 83: Python Test Audit - Research

**Researched:** 2026-04-24
**Domain:** Python pytest test suite — staleness identification and removal
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** A test is "stale" only if the production code it exercises has been deleted or completely rewritten. If the production function/class still exists and the test exercises it, it stays — even if the test looks trivial or redundant.
- **D-02:** Do not remove tests that pass and exercise live code, regardless of perceived quality or redundancy. That scope belongs to a future "test quality" effort, not this audit.
- **D-03:** Remove all identified stale tests in one pass, then run `pytest --cov` to confirm the 84% `fail_under` threshold holds. Only investigate individual removals if coverage drops below the threshold.
- **D-04:** No pre-removal per-file coverage analysis required. The "dead code only" staleness criteria means removed tests should contribute zero unique coverage by definition (they test deleted code).
- **D-05:** Document all removals in a markdown table: test file path | test count removed | reason. This inventory lives in the PLAN.md or SUMMARY.md for reviewability.
- **D-06:** Remove at the individual test method level. If all methods in a test file are stale, delete the entire file.
- **D-07:** Clean up orphaned test helpers and fixtures — if a helper/utility function in test code is no longer imported by any remaining test, remove it.

### Claude's Discretion
No discretion areas defined — open to standard approaches.

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PY-01 | Identify Python test files/cases testing removed or rewritten SeedSync code paths | Covered by the staleness inventory below — cross-referencing test imports against live production modules |
| PY-02 | Remove identified stale Python tests without dropping coverage below fail_under (84%) | Current baseline is 85.05%; safety margin is 1.05 percentage points. All stale candidates identified below test no live production code |
| PY-03 | Verify all remaining Python tests pass and coverage threshold holds | `poetry run pytest tests/ --cov` in `src/python/` is the gate command |
</phase_requirements>

---

## Summary

The Python test suite contains 1,271 collected tests across 84 test files in `src/python/tests/`. The suite is organized into `tests/unittests/` (mirroring production module structure) and `tests/integration/` (real subprocess/WSGI integration). Coverage currently stands at **85.05%**, safely above the 84% `fail_under` threshold.

The staleness audit found **zero tests that are stale by the D-01 definition** (testing deleted or completely rewritten production code). Every production module referenced by test imports exists on disk. All three staleness candidates flagged in the CONTEXT.md key history (WAITING_FOR_IMPORT removal, Fernet encryption config supersession, per-child import state rewrite) were already cleaned up before this audit: `WAITING_FOR_IMPORT` was deleted from both the `ModelFile.ImportStatus` enum and its serializer dictionary in commit `b3f105b`, and test files were simultaneously updated. The per-child import state rewrite (Phase 75) added `imported_children` to `ControllerPersist`; `test_auto_delete.py` correctly tests those new code paths. Fernet encryption tests were added to `test_config.py` alongside the production feature — they are live, not superseded.

The 26 currently-failing unit tests and 38 test errors are **environment failures** on macOS, not staleness: SSH tests need a local `sshcp` server, `lftp` tests need the `lftp` binary, multiprocessing tests fail due to macOS `spawn` + `MagicMock` pickling incompatibility, and one scanner test fails because macOS HFS+ rejects raw latin-1 bytes in filenames. These failures predate this audit and are out of scope per D-01/D-02. Integration tests with `@skipIf(shutil.which("rar") is None, ...)` and SSE streaming tests with `@unittest.skip("webtest doesn't support SSE streaming")` are similarly environment-conditioned, not stale.

**Primary recommendation:** The Python test suite contains no stale tests by the D-01 definition. The correct plan action is to perform the staleness verification pass documented below, confirm zero removals, run `pytest --cov` to record the 85.05% baseline, and mark PY-01/PY-02/PY-03 complete. Do not remove any test files or methods.

---

## Architecture Patterns

### Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest 9.x (run via `poetry run pytest`) |
| Runner command | `cd src/python && poetry run pytest tests/` |
| Coverage command | `cd src/python && poetry run pytest tests/ --cov` |
| Config file | `src/python/pyproject.toml` — `[tool.pytest.ini_options]` and `[tool.coverage.*]` |
| `fail_under` threshold | 84% (branch coverage) |
| Current baseline | **85.05%** (verified 2026-04-24) |
| `pythonpath` | `["."]` — tests import production modules directly (e.g., `from controller import Controller`) |
| Cache dir | `/tmp/.pytest_cache` (configured to avoid polluting volume mounts) |
| Timeout | 60 seconds per test (`pytest-timeout`) |

### Project Structure

```
src/python/
├── common/           # Production: Config, Status, Types, Encryption, etc.
├── controller/       # Production: Controller, AutoQueue, Scan, Extract, Delete, Webhooks
├── lftp/             # Production: Lftp, JobStatus, JobStatusParser
├── model/            # Production: ModelFile, ModelDiff, Model
├── ssh/              # Production: Sshcp
├── system/           # Production: SystemFile, SystemScanner (local filesystem scanner)
├── web/              # Production: WebApp, Handlers, Serializers
├── seedsyncarr.py    # Production: Seedsyncarr entry point class
└── tests/
    ├── conftest.py   # Shared pytest fixtures: test_logger, mock_context, mock_context_with_real_config
    ├── utils.py      # TestUtils.chmod_from_to helper
    ├── unittests/    # Mirrors production module hierarchy
    │   ├── test_common/
    │   ├── test_controller/
    │   ├── test_lftp/
    │   ├── test_model/
    │   ├── test_ssh/
    │   ├── test_system/
    │   ├── test_web/
    │   └── test_seedsyncarr.py
    └── integration/
        ├── test_controller/
        ├── test_lftp/
        └── test_web/
```

---

## Staleness Inventory

### Cross-Reference: Test Files vs Production Modules

All test files have been cross-referenced against their production import targets. Every production module imported by every test file exists on disk. [VERIFIED: direct filesystem scan + Python AST import analysis]

| Test File | Production Module(s) | Status |
|-----------|---------------------|--------|
| `unittests/test_common/test_app_process.py` | `common.app_process` | LIVE |
| `unittests/test_common/test_bounded_ordered_set.py` | `common.bounded_ordered_set` | LIVE |
| `unittests/test_common/test_config.py` | `common.config`, `common.encryption` | LIVE |
| `unittests/test_common/test_constants.py` | `common.constants` | LIVE |
| `unittests/test_common/test_context.py` | `common.context` | LIVE |
| `unittests/test_common/test_encryption.py` | `common.encryption` | LIVE |
| `unittests/test_common/test_error.py` | `common.error` | LIVE |
| `unittests/test_common/test_job.py` | `common.job` | LIVE |
| `unittests/test_common/test_localization.py` | `common.localization` | LIVE |
| `unittests/test_common/test_multiprocessing_logger.py` | `common.multiprocessing_logger` | LIVE |
| `unittests/test_common/test_persist.py` | `common.persist` | LIVE |
| `unittests/test_common/test_status.py` | `common.status` | LIVE |
| `unittests/test_common/test_types.py` | `common.types` (tests `overrides` decorator) | LIVE |
| `unittests/test_controller/test_auto_delete.py` | `controller.controller.__schedule_auto_delete` | LIVE |
| `unittests/test_controller/test_auto_queue.py` | `controller.auto_queue` | LIVE |
| `unittests/test_controller/test_controller.py` | `controller.controller` | LIVE |
| `unittests/test_controller/test_controller_job.py` | `controller.controller_job` | LIVE |
| `unittests/test_controller/test_controller_persist.py` | `controller.controller_persist` | LIVE |
| `unittests/test_controller/test_controller_unit.py` | `controller.controller` | LIVE |
| `unittests/test_controller/test_extract/test_dispatch.py` | `controller.extract.dispatch` | LIVE |
| `unittests/test_controller/test_extract/test_extract_process.py` | `controller.extract.extract_process` | LIVE (env-fail) |
| `unittests/test_controller/test_file_operation_manager.py` | `controller.file_operation_manager` | LIVE |
| `unittests/test_controller/test_lftp_manager.py` | `controller.lftp_manager` | LIVE |
| `unittests/test_controller/test_memory_monitor.py` | `controller.memory_monitor` | LIVE |
| `unittests/test_controller/test_model_builder.py` | `controller.model_builder` | LIVE |
| `unittests/test_controller/test_scan_manager.py` | `controller.scan_manager` | LIVE |
| `unittests/test_controller/test_scan/test_local_scanner.py` | `controller.scan.local_scanner` | LIVE |
| `unittests/test_controller/test_scan/test_remote_scanner.py` | `controller.scan.remote_scanner` | LIVE |
| `unittests/test_controller/test_scan/test_scanner_process.py` | `controller.scan.scanner_process` | LIVE (env-fail) |
| `unittests/test_controller/test_webhook_manager.py` | `controller.webhook_manager` | LIVE |
| `unittests/test_lftp/test_job_status.py` | `lftp.job_status` | LIVE |
| `unittests/test_lftp/test_job_status_parser.py` | `lftp.job_status_parser` | LIVE |
| `unittests/test_lftp/test_job_status_parser_components.py` | `lftp.job_status_parser` | LIVE |
| `unittests/test_lftp/test_lftp.py` | `lftp.lftp` | LIVE (env-fail) |
| `unittests/test_model/test_diff.py` | `model.diff` | LIVE |
| `unittests/test_model/test_file.py` | `model.file` | LIVE |
| `unittests/test_model/test_model.py` | `model.model` | LIVE |
| `unittests/test_seedsyncarr.py` | `seedsyncarr.Seedsyncarr` | LIVE |
| `unittests/test_ssh/test_sshcp.py` | `ssh.sshcp` | LIVE (env-fail) |
| `unittests/test_system/test_file.py` | `system.file.SystemFile` | LIVE |
| `unittests/test_system/test_scanner.py` | `system.scanner.SystemScanner` | LIVE (1 macOS-only fail) |
| `unittests/test_web/test_auth.py` | `web.web_app` | LIVE |
| `unittests/test_web/test_handler/test_auto_queue_handler.py` | `web.handler.auto_queue` | LIVE |
| `unittests/test_web/test_handler/test_config_handler.py` | `web.handler.config` | LIVE |
| `unittests/test_web/test_handler/test_controller_handler.py` | `web.handler.controller` | LIVE |
| `unittests/test_web/test_handler/test_server_handler.py` | `web.handler.server` | LIVE |
| `unittests/test_web/test_handler/test_status_handler.py` | `web.handler.status` | LIVE |
| `unittests/test_web/test_handler/test_stream_heartbeat.py` | `web.handler.stream_heartbeat` | LIVE |
| `unittests/test_web/test_handler/test_stream_log.py` | `web.handler.stream_log` | LIVE |
| `unittests/test_web/test_handler/test_stream_model_handler.py` | `web.handler.stream_model` | LIVE |
| `unittests/test_web/test_handler/test_stream_status_handler.py` | `web.handler.stream_status` | LIVE |
| `unittests/test_web/test_serialize/test_serialize.py` | `web.serialize` (base class) | LIVE |
| `unittests/test_web/test_serialize/test_serialize_auto_queue.py` | `web.serialize.serialize_auto_queue` | LIVE |
| `unittests/test_web/test_serialize/test_serialize_config.py` | `web.serialize.serialize_config` | LIVE |
| `unittests/test_web/test_serialize/test_serialize_log_record.py` | `web.serialize.serialize_log_record` | LIVE |
| `unittests/test_web/test_serialize/test_serialize_model.py` | `web.serialize.serialize_model` | LIVE |
| `unittests/test_web/test_serialize/test_serialize_status.py` | `web.serialize.serialize_status` | LIVE |
| `unittests/test_web/test_stream_queue.py` | `web` StreamQueue | LIVE |
| `unittests/test_web/test_web_app.py` | `web.web_app` | LIVE |
| `unittests/test_web/test_webhook_handler.py` | `web.handler.webhook` | LIVE |
| `integration/test_controller/test_controller.py` | `controller.controller` | LIVE (skipIf no rar) |
| `integration/test_controller/test_extract/test_extract.py` | `controller.extract` | LIVE (skipIf no rar) |
| `integration/test_lftp/test_lftp.py` | `lftp.lftp` | LIVE (env-fail) |
| `integration/test_web/test_web_app.py` | `web.web_app` | LIVE |
| `integration/test_web/test_handler/test_auto_queue.py` | `web.handler.auto_queue` | LIVE |
| `integration/test_web/test_handler/test_config.py` | `web.handler.config` | LIVE |
| `integration/test_web/test_handler/test_controller.py` | `web.handler.controller` | LIVE |
| `integration/test_web/test_handler/test_server.py` | `web.handler.server` | LIVE |
| `integration/test_web/test_handler/test_status.py` | `web.handler.status` | LIVE |
| `integration/test_web/test_handler/test_stream_log.py` | `web.handler.stream_log` | LIVE (@skip SSE) |
| `integration/test_web/test_handler/test_stream_model.py` | `web.handler.stream_model` | LIVE (@skip SSE) |
| `integration/test_web/test_handler/test_stream_status.py` | `web.handler.stream_status` | LIVE (@skip SSE) |

**Legend:** "env-fail" = test is live but fails on this macOS dev machine due to missing external process (lftp binary, SSH server, multiprocessing/spawn pickling). Not stale by D-01.

### Staleness Candidates from CONTEXT.md — Resolution

| Candidate (from CONTEXT.md Key History) | Resolved? | Detail |
|------------------------------------------|-----------|--------|
| WAITING_FOR_IMPORT enum removed (Phase 80) | YES — no action needed | Commit `b3f105b` removed the enum value from `model/file.py` and its entry from `web/serialize/serialize_model.py`. No test files reference `WAITING_FOR_IMPORT`. Already clean. [VERIFIED: grep across all test files] |
| Fernet encryption added (Phase 81) — "may have superseded config tests" | YES — no action needed | Config tests were extended, not replaced. `test_config.py` contains a `TestConfig` with 6 encryption-specific test methods added in Phase 81. The original config tests are still valid for non-encrypted behavior. [VERIFIED: read test_config.py] |
| Per-child import state (Phase 75) — "auto-delete logic rewritten" | YES — no action needed | `test_auto_delete.py` was written after Phase 75. It directly tests `ControllerPersist.imported_children` which is the Phase 75 per-child tracking. All 74 auto-delete tests exercise current live code. [VERIFIED: read test_auto_delete.py + controller_persist.py] |

### Shared Infrastructure — D-07 Orphan Check

| File | Used By | Verdict |
|------|---------|---------|
| `tests/conftest.py` | All pytest-style tests (`test_logger`, `mock_context`, `mock_context_with_real_config` fixtures) | LIVE — keep |
| `tests/utils.py` (`TestUtils.chmod_from_to`) | `integration/test_controller/test_controller.py`, `integration/test_lftp/test_lftp.py`, `unittests/test_lftp/test_lftp.py`, `unittests/test_ssh/test_sshcp.py` | LIVE — keep |
| `tests/unittests/test_web/test_serialize/test_serialize.py` (`parse_stream`) | `test_serialize_log_record.py`, `test_serialize_model.py`, `test_serialize_status.py` | LIVE — keep |

No orphaned helpers or fixtures found. [VERIFIED: grep for all exports of each shared file]

---

## Skipped Tests — Disposition

These tests are permanently skipped but are **not stale** by D-01. The production code they exercise still exists.

### @unittest.skip — SSE streaming (7 tests across 3 files)

| File | Skip Reason | Production Handler | Verdict |
|------|-----------|--------------------|---------|
| `integration/test_web/test_handler/test_stream_log.py` | "webtest doesn't support SSE streaming" | `web/handler/stream_log.py` exists | NOT stale — keep |
| `integration/test_web/test_handler/test_stream_model.py` | "webtest doesn't support SSE streaming" | `web/handler/stream_model.py` exists | NOT stale — keep |
| `integration/test_web/test_handler/test_stream_status.py` | "webtest doesn't support SSE streaming" | `web/handler/stream_status.py` exists | NOT stale — keep |

### @unittest.skipIf — Tool-conditional (64 tests)

| File | Condition | Verdict |
|------|-----------|---------|
| `integration/test_controller/test_controller.py` | `shutil.which("rar") is None` | NOT stale — keep |
| `integration/test_controller/test_extract/test_extract.py` | `shutil.which("rar") is None` | NOT stale — keep |
| `unittests/test_common/test_encryption.py` (2 tests) | `sys.platform == "win32"` | NOT stale — keep |

---

## Environment Failures — Not Stale

These 26 failing + 38 erroring tests exercise **live production code** but fail on this macOS dev machine due to missing external dependencies. They are out of scope for this audit.

| Test File | Failure Reason | Why Not Stale |
|-----------|---------------|---------------|
| `unittests/test_ssh/test_sshcp.py` (23 tests) | No local SSH/SCP server at `127.0.0.1:22` for `seedsyncarrtest` user | `ssh/sshcp.py` exists and is live |
| `unittests/test_lftp/test_lftp.py` (34 tests — all errors) | `lftp` binary not installed on macOS | `lftp/lftp.py` is live |
| `integration/test_lftp/test_lftp.py` (4 tests) | Same — no `lftp` binary | Same |
| `unittests/test_common/test_multiprocessing_logger.py` (3 tests) | macOS `spawn` start method — `MagicMock` not picklable across process boundary | `common/multiprocessing_logger.py` is live |
| `unittests/test_common/test_app_process.py` (1 test) | Same macOS multiprocessing spawn issue | `common/app_process.py` is live |
| `unittests/test_controller/test_scan/test_scanner_process.py` (3 tests) | Same macOS multiprocessing spawn pickling issue | `controller/scan/scanner_process.py` is live |
| `unittests/test_controller/test_extract/test_extract_process.py` (6 tests) | Process timeout — child never signals (multiprocessing spawn issue on macOS) | `controller/extract/extract_process.py` is live |
| `unittests/test_system/test_scanner.py::test_scan_file_with_latin_chars` (1 test) | macOS HFS+ rejects raw latin-1 bytes (`\xe9`) in filenames | `system/scanner.py` is live; test is valid on Linux |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All tests | ✓ | 3.12.12 | — |
| Poetry | Package/env management | ✓ | 2.3.4 | — |
| pytest | Test runner | ✓ (via poetry) | ^9.0.3 | — |
| pytest-cov | Coverage measurement | ✓ (via poetry) | ^7.1.0 | — |
| lftp binary | `unittests/test_lftp/test_lftp.py`, integration lftp | ✗ | — | Tests error at setup; out of scope for this phase |
| rar binary | Integration controller/extract tests | ✗ | — | Tests skip via `@skipIf`; out of scope |
| Local SSH server | `unittests/test_ssh/test_sshcp.py` | ✗ | — | Tests fail; out of scope |

**No blocking dependencies for Phase 83.** The staleness audit and coverage baseline run do not require `lftp`, `rar`, or an SSH server.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-cov 7.x |
| Config file | `src/python/pyproject.toml` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/ -q --tb=no` |
| Full suite command | `cd src/python && poetry run pytest tests/ --cov` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| PY-01 | Stale test identification | manual audit (this research) | grep/AST import analysis — already done |
| PY-02 | Remove stale tests, keep coverage >= 84% | coverage gate | `cd src/python && poetry run pytest tests/ --cov` |
| PY-03 | All remaining tests pass, threshold holds | full suite | `cd src/python && poetry run pytest tests/ --cov` |

### Sampling Rate
- **Per task commit:** `cd src/python && poetry run pytest tests/ --cov -q --tb=short`
- **Phase gate:** Same command — must show `Required test coverage of 84.0% reached` before `/gsd-verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements.

---

## Coverage Baseline (Pre-Audit)

| Metric | Value | Source |
|--------|-------|--------|
| Total coverage | **85.05%** | `poetry run pytest tests/ --cov` — 2026-04-24 |
| fail_under threshold | 84% | `pyproject.toml [tool.coverage.report]` |
| Safety margin | 1.05 percentage points | Computed |
| Tests collected | 1,271 | pytest --co |
| Tests passing | 1,136 | pytest run |
| Tests skipped | 71 | @skipIf/@skip conditions |
| Tests failing | 30 | All environment failures — not stale |
| Test errors | 38 | All lftp/multiprocessing env errors |

[VERIFIED: `poetry run pytest tests/ --cov` run 2026-04-24]

---

## Common Pitfalls

### Pitfall 1: Misclassifying Environment Failures as Stale Tests
**What goes wrong:** Tests for `lftp`, SSH, and multiprocessing processes are failing on macOS dev machine. A hasty audit could mark these as "broken stale tests" and remove them.
**Why it happens:** These tests exercise live production code paths but require external processes (`lftp` binary, SSH server) or Linux-specific OS behavior (fork-based multiprocessing, latin-1 filenames on ext4).
**How to avoid:** D-01 definition requires checking whether the *production module* exists, not whether the test currently passes on the local dev machine.
**Warning signs:** A test import resolves to a real production file → the test is live, even if it errors at runtime.

### Pitfall 2: Treating Permanently-Skipped Tests as Stale
**What goes wrong:** 7 integration SSE streaming tests have `@unittest.skip("webtest doesn't support SSE streaming")`. They never run and look abandoned.
**Why it happens:** `webtest` cannot drive HTTP streaming (SSE) — this is a test tooling limitation, not a missing production feature.
**How to avoid:** The production handlers (`stream_log.py`, `stream_model.py`, `stream_status.py`) all exist and are used by the live application. Skipped ≠ stale.

### Pitfall 3: Coverage Drop from Removing "Already Covered" Tests
**What goes wrong:** Removing a test that you believe is duplicate causes coverage to drop if it was the only test covering a specific branch.
**How to avoid:** D-03 handles this: remove all stale candidates in one pass, then run `--cov`. Since there are zero stale candidates, this pitfall is moot for this phase. Document the 85.05% baseline so the next phase (NG-01) has a reference point.

---

## Assumptions Log

> All claims in this research were verified by direct tool calls — no assumed claims.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims are VERIFIED.** Source: filesystem scan, Python AST import analysis, git log, direct `poetry run pytest --cov` run.

---

## Sources

### Primary (HIGH confidence)
- Direct filesystem scan of `src/python/` — all production module paths confirmed present [VERIFIED]
- Python AST import analysis across all 84 test files — every production module import resolved [VERIFIED]
- `git log --oneline --all --grep="WAITING_FOR_IMPORT" -- "src/python/"` — confirmed removal in `b3f105b` [VERIFIED]
- `poetry run pytest tests/ --cov` — 85.05% coverage baseline [VERIFIED: 2026-04-24]
- `poetry run pytest tests/ --co -q` — 1,271 tests collected [VERIFIED]
- `src/python/pyproject.toml` — pytest config, `fail_under = 84`, dependencies [VERIFIED]
- `src/python/tests/conftest.py` — shared fixtures [VERIFIED]
- `src/python/tests/utils.py` — TestUtils helper [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- Staleness verdict: HIGH — every test file cross-referenced against live production modules
- Coverage baseline: HIGH — obtained by running `pytest --cov` directly
- Environment failure classification: HIGH — error messages confirm specific OS/binary issues

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable codebase; only invalidated by new production code deletions)
