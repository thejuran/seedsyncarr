# Phase 83: Python Test Audit - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Identify and remove stale Python backend tests that no longer exercise current SeedSyncarr behavior. The test suite should contain only tests for code paths that exist and are reachable in the current codebase.

</domain>

<decisions>
## Implementation Decisions

### Staleness Criteria
- **D-01:** A test is "stale" only if the production code it exercises has been deleted or completely rewritten. If the production function/class still exists and the test exercises it, it stays — even if the test looks trivial or redundant.
- **D-02:** Do not remove tests that pass and exercise live code, regardless of perceived quality or redundancy. That scope belongs to a future "test quality" effort, not this audit.

### Coverage Safety Net
- **D-03:** Remove all identified stale tests in one pass, then run `pytest --cov` to confirm the 84% `fail_under` threshold holds. Only investigate individual removals if coverage drops below the threshold.
- **D-04:** No pre-removal per-file coverage analysis required. The "dead code only" staleness criteria means removed tests should contribute zero unique coverage by definition (they test deleted code).

### Inventory Format
- **D-05:** Document all removals in a markdown table: test file path | test count removed | reason (e.g., "tests module X deleted in v3.0"). This inventory lives in the PLAN.md or SUMMARY.md for reviewability.

### Removal Granularity
- **D-06:** Remove at the individual test method level. If all methods in a test file are stale, delete the entire file.
- **D-07:** Clean up orphaned test helpers and fixtures — if a helper/utility function in test code is no longer imported by any remaining test, remove it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test Infrastructure
- `src/python/pyproject.toml` — pytest config, coverage settings, fail_under threshold
- `src/python/tests/conftest.py` — Shared fixtures and test configuration
- `src/python/tests/utils.py` — Shared test utilities

### Production Code (verify against)
- `src/python/web/` — Web handlers (test targets for test_web/)
- `src/python/controller/` — Controller logic (test targets for test_controller/)
- `src/python/lftp/` — LFTP integration (test targets for test_lftp/)
- `src/python/model/` — Data models (test targets for test_model/)
- `src/python/ssh/` — SSH operations (test targets for test_ssh/)
- `src/python/common/` — Shared utilities (test targets for test_seedsyncarr.py)

### Requirements
- `.planning/REQUIREMENTS.md` — PY-01, PY-02, PY-03 requirements for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Test Suite Structure
- 1,271 Python tests across ~24k lines of test code
- `tests/unittests/` — Unit tests organized by module (test_lftp, test_web, test_model, test_ssh, test_controller)
- `tests/integration/` — Integration tests (test_web, test_lftp, test_controller)
- `tests/conftest.py` and `tests/utils.py` — Shared test infrastructure

### Established Patterns
- `unittest.TestCase` base class throughout
- `MagicMock` for service/controller mocking
- WebTest `TestApp` wrapper for WSGI endpoint testing
- Coverage enforced at 84% via `fail_under` in pyproject.toml

### Key History (staleness sources)
- SeedSync → SeedSyncarr rebrand (v1.0.0, Phase 53) — module renames possible
- UI overhauls (v3.0, M003, M006, v1.1.0) — backend handlers may have changed
- Security hardening (v3.1, v3.2, M002) — auth/webhook handlers rewritten
- Sonarr/Radarr integration (v1.7, v1.8) — new controller logic added
- WAITING_FOR_IMPORT enum removed (v1.1.1, Phase 80) — tests referencing it are stale
- Fernet encryption added (v1.1.1, Phase 81) — may have superseded config tests
- Per-child import state (v1.1.1, Phase 75) — auto-delete logic rewritten

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 83-python-test-audit*
*Context gathered: 2026-04-24*
