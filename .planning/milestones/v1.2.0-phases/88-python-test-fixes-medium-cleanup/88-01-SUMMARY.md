---
phase: 88-python-test-fixes-medium-cleanup
plan: "01"
subsystem: python-tests
tags: [test-quality, xss, cleanup, logger-leak, tdd]
dependency_graph:
  requires: []
  provides: [PYFIX-11, PYFIX-14, PYFIX-15, PYFIX-16-partial, PYFIX-19]
  affects: [python-unittest-suite, python-integration-suite]
tech_stack:
  added: []
  patterns: [addCleanup-tmpdir, module-level-import, unconditional-assertion, teardown-handler-removal]
key_files:
  created: []
  modified:
    - src/python/tests/unittests/test_web/test_web_app.py
    - src/python/tests/unittests/test_web/test_auth.py
    - src/python/tests/unittests/test_lftp/test_job_status_parser_components.py
    - src/python/tests/integration/test_lftp/test_lftp.py
    - src/python/tests/integration/test_web/test_web_app.py
    - src/python/tests/integration/test_controller/test_controller.py
decisions:
  - "Use self.addCleanup(_tmpd.cleanup) (not try/finally) for TemporaryDirectory cleanup — matches Python idiom for test resource management"
  - "Place import bottle with third-party imports at module level — consistent with PEP 8 import ordering"
  - "Remove if match: guard entirely rather than using assertTrue — assertIsNotNone provides clearer failure message"
  - "Use @overrides decorator on tearDown in integration/test_web/test_web_app.py — consistent with BaseTestWebApp setUp pattern"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-24"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 88 Plan 01: Python Test Fixes Medium & Cleanup Summary

**One-liner:** Fixed 5 medium-priority test defects — XSS meta tag verification, deterministic TemporaryDirectory cleanup at 12 call sites, module-level bottle import, unconditional CHUNK_AT assertion, and logger handler removal in 3 integration test tearDowns.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | XSS test, TemporaryDirectory cleanup, bottle import, conditional assertion | 4c2d309 | test_web_app.py (unit), test_auth.py, test_job_status_parser_components.py |
| 2 | Logger handler cleanup in 3 integration test files | b9aa9c2 | test_lftp.py (int), test_web_app.py (int), test_controller.py (int) |

## Changes by Requirement

### PYFIX-11: XSS prevention test
Added `test_meta_tag_escapes_html_special_chars` to `TestWebAppMetaTagInjection`. The test uses token `'<script>"alert(1)'&'` (all 5 HTML special chars), asserts `<script>` is absent from response, and asserts the fully-escaped form via `html.escape(xss_token, quote=True)` is present in the meta tag. Added `import html as html_mod` at module level to support the expected-value computation.

### PYFIX-14: TemporaryDirectory cleanup
Added `self.addCleanup(_tmpd.cleanup)` immediately after each `app, _tmpd = _make_web_app_with_index(...)` call. All 12 call sites now have deterministic cleanup (11 existing tests + 1 new XSS test).

### PYFIX-15: Module-level bottle import
Moved `import bottle` to module level in `test_auth.py`, grouped with third-party imports between `unittest.mock` and `webtest`. Removed duplicate `import bottle` from inside both `_capture()` closures — closures still reference `bottle.request` correctly via the module-level name.

### PYFIX-19: Unconditional CHUNK_AT assertion
In `test_parse_chunk_at_no_speed_eta`, replaced `if match:` guard with `self.assertIsNotNone(match, "CHUNK_AT regex must match line without speed/eta")`. The three subsequent assertions (`state = ...`, `assertIsNone(state.speed)`, `assertIsNone(state.eta)`) are now at method body level and always execute.

### PYFIX-16 (partial): Logger handler removal in integration tests
Applied the Phase 87 pattern (Phase 87 conftest.py PYFIX-07) to 3 integration test files:
- `integration/test_lftp/test_lftp.py`: renamed `handler` to `self._test_handler`; added `logging.getLogger().removeHandler(self._test_handler)` as first line of existing `tearDown`
- `integration/test_web/test_web_app.py`: renamed `handler` to `self._test_handler`; added new `tearDown` method (class had none) with `logging.getLogger().removeHandler(self._test_handler)`
- `integration/test_controller/test_controller.py`: renamed `handler` to `self._test_handler`; added `logging.getLogger(TestController.__name__).removeHandler(self._test_handler)` as first line of existing `tearDown`

## Deviations from Plan

### Auto-added items

**1. [Rule 2 - Missing import] Added `import html as html_mod` to test_web_app.py**
- **Found during:** Task 1 (PYFIX-11)
- **Issue:** The XSS test needed to compute the expected escaped value; `html` module was not imported in the test file
- **Fix:** Added `import html as html_mod` at the top of the import block (standard library section)
- **Files modified:** src/python/tests/unittests/test_web/test_web_app.py
- **Commit:** 4c2d309

**2. [Rule 2 - Consistency] Used @overrides decorator on new tearDown in integration/test_web/test_web_app.py**
- **Found during:** Task 2
- **Issue:** The class's setUp uses `@overrides(unittest.TestCase)`; the new tearDown should be consistent
- **Fix:** Added `@overrides(unittest.TestCase)` to the new tearDown
- **Files modified:** src/python/tests/integration/test_web/test_web_app.py
- **Commit:** b9aa9c2

## Known Stubs

None.

## Threat Flags

None. The XSS test (PYFIX-11) adds coverage for the existing `html.escape` call at `web_app.py:222`; no new attack surface introduced.

## Self-Check: PASSED

Files exist:
- src/python/tests/unittests/test_web/test_web_app.py — FOUND
- src/python/tests/unittests/test_web/test_auth.py — FOUND
- src/python/tests/unittests/test_lftp/test_job_status_parser_components.py — FOUND
- src/python/tests/integration/test_lftp/test_lftp.py — FOUND
- src/python/tests/integration/test_web/test_web_app.py — FOUND
- src/python/tests/integration/test_controller/test_controller.py — FOUND

Commits exist:
- 4c2d309 — FOUND
- b9aa9c2 — FOUND
