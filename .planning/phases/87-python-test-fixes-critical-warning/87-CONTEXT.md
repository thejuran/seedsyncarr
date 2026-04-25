# Phase 87: Python Test Fixes -- Critical & Warning - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 10 specific, documented Python test defects: 2 critical false-coverage bugs (thread target called instead of passed, assertion-less test) and 8 warning-level issues (temp file leaks, mock confusion, permission escalation, logger fixture leak, implicit imports, resource leaks from bare open()).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User elected to skip discussion -- all implementation decisions are at Claude's discretion. Requirements are fully specified in REQUIREMENTS.md (PYFIX-01 through PYFIX-10) with exact file locations and bug descriptions. No ambiguity in what needs fixing.

Key areas left to Claude:
- **D-01:** Fix strategy for PYFIX-01 (thread target bug) and PYFIX-02 (assertion-less test) -- fix in place vs rewrite
- **D-02:** Resource cleanup approach for PYFIX-03/04/09/10 -- context managers, addCleanup, or tmpdir fixtures
- **D-03:** Logger infrastructure fix for PYFIX-07 (conftest handler leak) and PYFIX-08 (implicit ANY import) -- fixture vs setUp/tearDown
- **D-04:** Permissions fix scope for PYFIX-06 -- chmod scoping strategy
- **D-05:** Mock restructuring approach for PYFIX-05 (class vs instance confusion)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test Audit Findings
- `.planning/REQUIREMENTS.md` -- PYFIX-01 through PYFIX-10 requirement definitions with file locations and bug descriptions

### Affected Test Files
- `src/python/tests/unittests/test_controller/test_extract/test_extract_process.py` -- PYFIX-01 thread target bug (line 182)
- `src/python/tests/unittests/test_controller/test_lftp_manager.py` -- PYFIX-02 assertion-less test (line 83)
- `src/python/tests/unittests/test_config.py` -- PYFIX-03 (line 503) and PYFIX-04 (line 413) temp file leaks
- `src/python/tests/unittests/test_status_handler.py` -- PYFIX-05 mock class vs instance
- `src/python/tests/unittests/test_lftp.py` -- PYFIX-06 group-writable permissions (line 24)
- `src/python/tests/conftest.py` -- PYFIX-07 logger fixture handler leak
- `src/python/tests/` -- PYFIX-08 implicit ANY import (3+ files, grep for side-effect imports)
- `src/python/tests/integration/` -- PYFIX-09 bare open(os.devnull) in 2 integration tests
- `src/python/tests/` -- PYFIX-10 bare open() in create_large_file helper

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/python/tests/conftest.py` -- shared fixtures, target of PYFIX-07 fix
- `src/python/tests/utils.py` -- shared test utilities, potential home for fixed helpers

### Established Patterns
- Python tests use `unittest.TestCase` with `setUp/tearDown`
- `pytest` runner with `conftest.py` fixtures
- Coverage enforced at 85.05% via `fail_under`
- Docker-based test execution via `make run-tests-python`

### Integration Points
- All fixes must pass `make run-tests-python` (1262 tests)
- Coverage must remain at or above 85.05% fail_under threshold
- CI runs on both amd64 and arm64

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches for all fixes.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 87-python-test-fixes-critical-warning*
*Context gathered: 2026-04-24*
