# Phase 88: Python Test Fixes -- Medium & Cleanup - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 9 specific, documented Python test defects: add missing XSS prevention test, fix scanner busy-wait race conditions, replace real `time.sleep` with mock time or events (~4s savings), fix TemporaryDirectory cleanup, move implicit bottle imports to module level, fix logger handler leaks across 5 files, replace sleep sync with `job.join`, add sleep to ~25 busy-wait loops, and fix conditional assertion that silently skips.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User elected to skip discussion — all implementation decisions are at Claude's discretion. Requirements are fully specified in REQUIREMENTS.md (PYFIX-11 through PYFIX-19) with exact file locations and bug descriptions. No ambiguity in what needs fixing.

Key areas left to Claude:
- **D-01:** XSS prevention test approach for PYFIX-11 — test HTML special chars (`<>"'&`) are escaped in meta tag output
- **D-02:** Scanner busy-wait fix strategy for PYFIX-12 — deterministic synchronization replacing race-prone busy-waits
- **D-03:** Sleep replacement scope for PYFIX-13 — mock `time.sleep` vs `threading.Event` vs targeted per-file; must save 4+ seconds
- **D-04:** TemporaryDirectory cleanup method for PYFIX-14 — `addCleanup(_tmpd.cleanup)` or context manager
- **D-05:** Bottle import restructuring for PYFIX-15 — move from inside closures to module level
- **D-06:** Logger handler cleanup strategy for PYFIX-16 — centralized conftest fixture vs per-file tearDown/removeHandler across 5 files
- **D-07:** Job sync replacement for PYFIX-17 — `job.join(timeout=5.0)` replacing `time.sleep`
- **D-08:** Busy-wait sleep injection for PYFIX-18 — sleep interval size (0.01s–0.1s) for ~25 loops in test_lftp.py
- **D-09:** Conditional assertion fix for PYFIX-19 — ensure assert always executes at `test_job_status_parser_components.py:199`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test Audit Findings
- `.planning/REQUIREMENTS.md` — PYFIX-11 through PYFIX-19 requirement definitions with file locations and bug descriptions

### Phase 87 Context (predecessor)
- `.planning/phases/87-python-test-fixes-critical-warning/87-CONTEXT.md` — Prior decisions on resource cleanup approach (context managers, addCleanup) and logger infrastructure

### Affected Test Files
- `src/python/tests/unittests/test_web/test_web_app.py` — PYFIX-11 XSS prevention test (existing meta tag tests at line 135+)
- `src/python/tests/unittests/test_controller/test_scan*.py` — PYFIX-12 scanner busy-wait race conditions
- `src/python/tests/unittests/test_controller/test_extract/test_dispatch.py` — PYFIX-13 real `time.sleep` (6 occurrences)
- `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py` — PYFIX-13 real `time.sleep` (4 occurrences)
- `src/python/tests/unittests/test_common/test_job.py` — PYFIX-13/17 real `time.sleep` (2 occurrences), replace with `job.join(timeout=5.0)`
- `src/python/tests/unittests/test_common/test_multiprocessing_logger.py` — PYFIX-13 real `time.sleep` (6 occurrences)
- `src/python/tests/unittests/test_web/test_handler/test_controller_handler.py` — PYFIX-13 real `time.sleep` (2 occurrences)
- `src/python/tests/unittests/test_lftp/test_lftp.py` — PYFIX-18 ~25 busy-wait loops without sleep (line 115+ handler leak)
- `src/python/tests/unittests/test_job_status_parser_components.py` — PYFIX-19 conditional assertion (line 199)
- `src/python/tests/conftest.py` — PYFIX-16 logger handler leak (already partially fixed by Phase 87 PYFIX-07)
- `src/python/tests/integration/test_lftp/test_lftp.py` — PYFIX-16 handler leak (line 41+)
- `src/python/tests/integration/test_web/test_web_app.py` — PYFIX-16 handler leak (line 25+)
- `src/python/tests/integration/test_controller/test_controller.py` — PYFIX-16 handler leak (line 358+)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/python/tests/conftest.py` — shared fixtures, partially fixed in Phase 87 (PYFIX-07)
- `src/python/tests/utils.py` — shared test utilities
- Existing meta tag tests in `test_web_app.py` (line 135+) — pattern for PYFIX-11

### Established Patterns
- Python tests use `unittest.TestCase` with `setUp/tearDown`
- pytest runner with conftest.py fixtures
- Coverage enforced at 85.05% via `fail_under`
- Docker-based test execution via `make run-tests-python`
- Phase 87 used context managers and `addCleanup` for resource cleanup

### Integration Points
- All fixes must pass `make run-tests-python` (1262 tests)
- Coverage must remain at or above 85.05% fail_under threshold
- CI runs on both amd64 and arm64
- Success criteria: test suite must run 4+ seconds faster after PYFIX-13

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for all fixes.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 88-python-test-fixes-medium-cleanup*
*Context gathered: 2026-04-24*
