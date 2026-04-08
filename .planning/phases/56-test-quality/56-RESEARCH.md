# Phase 56: Test Quality - Research

**Researched:** 2026-04-08
**Domain:** Python (pytest) test assertions + Playwright E2E unhappy paths
**Confidence:** HIGH

## Summary

Phase 56 improves the test suite in two dimensions. First, Python unit and integration tests that currently pass with only structural assertions (that code did not crash, that `pass` stubs were used in test-helper base classes, or that a while-loop spun until completion with no outcome check) must be strengthened to assert on observable outcomes. Second, all existing E2E tests exercise the happy path only — files are served from a live remote container, config is pre-set to valid values, and every test navigates to a working app. There is no E2E test that submits a bad config, breaks connectivity, or triggers an error toast.

The coverage threshold is already set at `fail_under = 84` in `pyproject.toml`. Phase 55 (Code Hardening) may change some source code, so the principal risk here is regression — the threshold must still pass after any assertion additions or source refactors.

**Primary recommendation:** Identify Python tests with no assertions beyond "it ran" and add `assertEqual`/`assertIn`/`assertRaises` checks on return values or state. For E2E, add one new spec that submits a deliberately-broken config (bad remote address or invalid Sonarr URL) and asserts the UI renders an error state, using the existing Docker E2E infrastructure.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARD-03 | Test coverage has no meaningful gaps; assertions verify behavior (not just "no crash") | Weak assertions identified in integration/test_lftp, integration/test_controller, unittests/test_controller/test_auto_queue — see Findings below |
| HARD-04 | E2E tests cover real user workflows including unhappy paths | All existing E2E specs exercise the configured-and-running happy path; no spec triggers or checks an error state |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | ^7.4.4 (pinned in pyproject.toml) | Python test runner | Already in use |
| pytest-cov | ^7.0.0 | Coverage enforcement | Already in use; `fail_under = 84` set |
| testfixtures | ^10.0.0 | Log capture, comparison helpers | Already in use |
| webtest | ^3.0.7 | In-process HTTP handler testing | Already in use for web handler tests |
| Playwright (TypeScript) | configured in e2e/playwright.config.ts | Browser automation E2E | Already in use; chromium-only in CI |
| Karma + Jasmine | karma.conf.js | Angular unit test runner | Already in use for `make run-tests-angular` |

### No New Libraries Needed
The existing toolchain is sufficient. This phase is about writing better tests, not introducing infrastructure.

## Architecture Patterns

### Python Test Structure
```
src/python/tests/
├── unittests/
│   ├── test_model/         # model state, ModelFile, diff logic
│   ├── test_lftp/          # job status parser (pure logic — no real lftp)
│   ├── test_web/
│   │   ├── test_auth.py
│   │   ├── test_webhook_handler.py
│   │   ├── test_handler/   # one file per handler
│   │   └── test_serialize/ # serialization round-trips
│   └── test_controller/    # ScanManager, AutoQueue, WebhookManager, etc.
└── integration/
    ├── test_lftp/          # real lftp against sshd in container
    ├── test_web/           # real web app in-process
    └── test_controller/    # real controller + extract logic
```

Tests run via Docker: `make run-tests-python` builds `seedsyncarr/run/python/devenv`, then runs pytest inside the container with sshd alongside for integration tests.

### E2E Test Structure
```
src/e2e/tests/
├── app.spec.ts           # title, nav links, default route
├── about.page.spec.ts    # nav active, version display
├── dashboard.page.spec.ts # file list, action buttons, state-based enable/disable
├── settings.page.spec.ts # nav active only (minimal)
├── autoqueue.page.spec.ts # add/remove patterns, persistence, alphabetical order
└── bulk-actions.spec.ts  # checkbox selection, header checkbox, keyboard shortcuts,
                          # bulk action bar display, confirm modals
```

All specs run against a live Docker compose stack: the SeedSyncarr image (`myapp`), an SSH remote server with test files (`remote`), and a configure container that pre-sets all valid config via curl.

### Pattern: Asserting on Return Values (Python)
```python
# Source: [ASSUMED] — standard pytest/unittest pattern
# BEFORE (weak):
while self.lftp.status():
    pass  # just waits; never asserts outcome

# AFTER (strong):
while self.lftp.status():
    pass
self.assert_local_equals_remote()  # already present in test_lftp — model for others
```

```python
# BEFORE (weak):
def test_add_listener(self):
    listener = DummyModelListener()
    self.model.add_listener(listener)
    # no assertion — only tests it does not raise

# AFTER (strong):
def test_add_listener(self):
    listener = DummyModelListener()
    listener.file_added = MagicMock()
    self.model.add_listener(listener)
    self.model.add_file(ModelFile("probe", False))
    listener.file_added.assert_called_once()  # assert listener was actually registered
```

### Pattern: E2E Error State Test (Playwright)
```typescript
// Source: [ASSUMED] — standard Playwright pattern against existing E2E infra
// Correct unhappy path: submit bad config, assert error feedback is visible

test('should show error when remote address is unreachable', async ({ page }) => {
    // Set remote_address to a host that does not exist
    await page.request.get(
        `${baseURL}/server/config/set/lftp/remote_address/nonexistent.invalid`
    );
    await page.request.post(`${baseURL}/server/command/restart`);

    // Wait for the app to come back up
    await page.waitForTimeout(2000);
    await page.goto(Paths.SETTINGS);

    // The connection error should surface somewhere in the UI
    // (check for error toast, status indicator, or error message element)
    const errorVisible = await page.locator('.notification.danger, [data-status="error"]')
        .isVisible({ timeout: 10000 });
    expect(errorVisible).toBe(true);
});
```

**Note on E2E unhappy path approach:** The configure container already shows the pattern — it calls `/server/config/set/...` via the public API. An unhappy-path test can either (a) call the config API with invalid values directly in the test, or (b) create a new E2E spec that navigates the Settings page UI and submits bad values. Option (a) is lower-risk and more reliable in Docker CI.

### Anti-Patterns to Avoid

- **`pass`-only test helper stubs are fine.** The `DummyListener`, `DummyCommandCallback`, `TestAutoQueuePersistListener` classes use `pass` in their interface implementations — this is correct. The weak-assertion problem is in the *test methods* that call into these helpers without asserting outcomes.
- **Do not delete the `assert_local_equals_remote` call** in `test_lftp.py` integration tests. Those assertions are the whole point of the download tests and are already strong.
- **Do not raise the coverage threshold** arbitrarily. Threshold is at 84%; the task is to maintain it post-Phase 55 changes, not to push it higher.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP response testing | Custom HTTP client | `webtest.TestApp` (already used) | Already wired into all handler tests |
| Coverage reporting | Custom scripts | `pytest-cov --cov-report` | Already configured in pyproject.toml |
| Playwright page interactions | Raw `page.evaluate()` everywhere | Page Object Model (already used) | All pages have `.page.ts` objects; extend those |
| Config API calls in E2E | Reimplementing curl logic | `page.request.get()/post()` | Playwright's request context, no extra dep |

## Findings: Current Weak-Assertion Sites

### Python — Known Weak Spots

**1. `test_model/test_model.py` — `test_add_listener`**
- File: `src/python/tests/unittests/test_model/test_model.py` line 88
- Issue: Calls `self.model.add_listener(listener)` with no assertion
- Fix: Add a file, assert `listener.file_added` was called (the pattern is already used one method later in `test_remove_listener`)
- Confidence: HIGH [VERIFIED: codebase grep]

**2. `integration/test_controller/test_controller.py` — `DummyListener` and `DummyCommandCallback` stubs**
- File: lines 23–44
- Note: These are interface stubs, not test methods. The `pass` bodies are correct.
- The actual integration test methods in this file call `assert_local_equals_remote()` and do real filesystem assertions — these are strong. No action needed here.
- Confidence: HIGH [VERIFIED: read file]

**3. `integration/test_lftp/test_lftp.py` — download tests**
- File: lines 88–164 (test_download_1 through test_download_4)
- Pattern: `while self.lftp.status(): pass` then `self.assert_local_equals_remote()`
- These tests already have strong assertions via `assert_local_equals_remote()`. The `pass` in the while loop is iteration logic, not a missing assertion. These are already good.
- Confidence: HIGH [VERIFIED: read file]

**4. `unittests/test_controller/test_auto_queue.py` — TestAutoQueuePersistListener**
- File: lines 84–89
- Note: This is an interface stub class, not a test method. The `pass` bodies are correct.
- The actual test methods below it (e.g., `test_add_pattern`, `test_listener_pattern_added`) use `assertEqual` and `MagicMock.assert_called_once_with` — these are strong.
- Confidence: HIGH [VERIFIED: read file]

**5. `unittests/test_web/test_handler/test_controller_handler.py` — `pass` in timeout simulation side effects**
- File: lines 51, 478
- These `pass` bodies are intentional no-op side effects for mock controllers simulating a stuck controller. They are correct and necessary.
- The test methods themselves (`test_action_timeout_returns_504`, `test_timeout_returns_504_error`) DO assert on status codes and body content. These are strong.
- Confidence: HIGH [VERIFIED: read file]

**Summary:** After careful inspection, the existing Python tests are better quality than the surface grep suggested. The `pass` occurrences are almost entirely in interface stub classes and intentional mock side effects, not in test method bodies. The planner should focus on:
1. `test_add_listener` (no assertion)
2. A survey pass over other `def test_*` methods that end without an `assert` or mock verification call

### E2E — Confirmed Happy-Path-Only Coverage

All existing specs (`app.spec.ts`, `about.page.spec.ts`, `dashboard.page.spec.ts`, `settings.page.spec.ts`, `autoqueue.page.spec.ts`, `bulk-actions.spec.ts`) exercise:
- Navigation and page load
- File list display
- Button enable/disable based on file state
- AutoQueue CRUD
- Bulk selection, banner, keyboard shortcuts, confirm modals

None exercise:
- Invalid or missing config
- Connection failure to remote
- Sonarr/Radarr webhook rejection
- Error toast or error indicator being rendered
- [VERIFIED: codebase read of all spec files]

## Common Pitfalls

### Pitfall 1: Confusing Interface Stubs with Weak Test Assertions
**What goes wrong:** Grep for `pass` in test files finds many `pass` bodies in `DummyListener` and `DummyCommandCallback` classes, which are interface stub classes, not test methods.
**Why it happens:** Python requires `pass` to mark an abstract method override that does nothing.
**How to avoid:** Only fix `pass` or empty-body patterns inside `def test_*` methods. Never remove required interface stubs.
**Warning signs:** If a `pass` is in a class named `Dummy*`, `Fake*`, or `Mock*`, it is an interface stub.

### Pitfall 2: Raising Coverage Threshold Beyond 84%
**What goes wrong:** Adding new test files without corresponding source coverage can inadvertently drop the threshold check, or artificially raising the threshold creates phantom failures.
**Why it happens:** `fail_under = 84` in pyproject.toml is the gate. New test files are excluded via `omit = ["tests/*"]`.
**How to avoid:** Run `make run-tests-python` before and after changes to confirm threshold still passes. Do not change `fail_under`.

### Pitfall 3: E2E Unhappy Path Leaves App in Broken State
**What goes wrong:** A test that sets remote_address to an invalid value must restore valid config or run in isolation — otherwise subsequent tests see a misconfigured app.
**Why it happens:** E2E tests share a running app container (no per-test app restart).
**How to avoid:** Restore valid config at the end of the unhappy-path test (in `afterEach` or at the end of the test body), or put the unhappy-path test in a separate spec file that runs last, or restart the app after the test.
**Warning signs:** If dashboard tests start failing with "remote scan did not complete", the app was left in a broken state.

### Pitfall 4: E2E Configure Container Race Condition
**What goes wrong:** Adding a new spec that reconfigures the app mid-suite can race with the configure container's initial setup or the remote scan that other tests depend on.
**Why it happens:** `run_tests.sh` waits for remote scan to complete before running playwright — but only once, at the start. Mid-suite reconfigs re-trigger this wait for subsequent tests.
**How to avoid:** Use `page.request` to call the config API directly (already the pattern in `setup_seedsyncarr.sh`). Add explicit `waitFor` for server status and scan completion after any restart.

### Pitfall 5: `make run-tests-angular` Uses Docker + Karma
**What goes wrong:** Angular tests run via `docker-compose` with ChromeHeadlessCI in a container — not with `ng test` locally. "Run the angular tests" means the full Docker build pipeline.
**Why it happens:** This is the CI-equivalent target.
**How to avoid:** When verifying angular tests pass, use `make run-tests-angular` (not `ng test` locally).

## Code Examples

### Minimal Strong Assertion Pattern (Python)
```python
# Source: existing pattern in test_model.py test_remove_listener (line 94)
def test_add_listener(self):
    listener = DummyModelListener()
    listener.file_added = MagicMock()
    self.model.add_listener(listener)
    self.model.add_file(ModelFile("probe", False))
    listener.file_added.assert_called_once_with(ModelFile("probe", False))
```

### E2E Page Request Pattern for Config Changes
```typescript
// Source: [ASSUMED] — standard Playwright API, mirrors setup_seedsyncarr.sh
const response = await page.request.get(
    'http://myapp:8800/server/config/set/lftp/remote_address/invalid.host'
);
expect(response.ok()).toBe(true);
```

### E2E Error State Assertion
```typescript
// Source: [ASSUMED] — standard Playwright locator pattern
// Check for danger notification visible on page
await expect(page.locator('.notification.danger')).toBeVisible({ timeout: 10000 });
```

## Environment Availability

> E2E tests require Docker. Python tests require Docker (for lftp/sshd integration tests).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | `make run-tests-python`, `make run-tests-angular`, `make run-tests-e2e` | ✓ (assumed — all prior phases ran CI) | — | None — all test make targets require Docker |
| Python/poetry | Local coverage check (`make coverage-python`) | ✓ | poetry on devenv image | Run in Docker |

**Note:** `make run-tests-python` and `make run-tests-angular` are the two commands the success criteria specifies. Both run inside Docker containers. The arm64 rar package caveat is a known tech debt item (logged in STATE.md) — CI runs amd64.

## Validation Architecture

> `workflow.nyquist_validation` key is absent from .planning/config.json — treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Python framework | pytest 7.4.4 with pytest-cov 7.0.0 |
| Python config | `src/python/pyproject.toml` `[tool.pytest.ini_options]` |
| Python quick run | `make run-tests-python` (Docker — no local shortcut) |
| Python full suite | `make run-tests-python` (same — runs all tests in container) |
| Angular framework | Karma + Jasmine |
| Angular config | `src/angular/karma.conf.js` |
| Angular run | `make run-tests-angular` (Docker) |
| E2E framework | Playwright (TypeScript) |
| E2E config | `src/e2e/playwright.config.ts` |
| E2E run | `make run-tests-e2e` (requires STAGING_VERSION + SEEDSYNCARR_ARCH env vars) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARD-03 | Python assertions verify observable outcomes | unit/integration | `make run-tests-python` | ✅ (existing tests; some need strengthening) |
| HARD-03 | Coverage threshold still passes | coverage gate | `make run-tests-python` (exits non-zero if < 84%) | ✅ |
| HARD-04 | At least one E2E unhappy-path test | e2e | `make run-tests-e2e` | ❌ Wave 0 — new spec needed |

### Sampling Rate
- **Per task commit:** `make run-tests-python` (for Python assertion changes)
- **Per wave merge:** `make run-tests-python` + `make run-tests-angular`
- **Phase gate:** All three test make targets green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/e2e/tests/error-state.spec.ts` — covers HARD-04 (E2E unhappy path)

## Security Domain

> This phase does not introduce new security surfaces. It adds tests. ASVS checks are not applicable.

## Sources

### Primary (HIGH confidence)
- Codebase direct read — `src/python/tests/**` and `src/e2e/tests/**` — all test files read in this session
- `src/python/pyproject.toml` — coverage threshold `fail_under = 84` confirmed
- `src/docker/test/e2e/configure/setup_seedsyncarr.sh` — E2E config API pattern confirmed
- `src/e2e/playwright.config.ts` — Playwright config confirmed

### Secondary (MEDIUM confidence)
- Playwright `page.request` API for in-test config calls [ASSUMED] — standard Playwright pattern, consistent with official docs

### Tertiary (LOW confidence)
- None

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The E2E unhappy-path test can restore valid config by calling the config API at the end of the test and restarting the app, without breaking subsequent specs | Common Pitfalls / Code Examples | If restart takes too long or leaves the app in a bad state, subsequent tests may fail — mitigate with explicit wait for `server_up` and `remote_scan_done` |
| A2 | Playwright `page.request.get()` is available in the Playwright version installed in the E2E container | Code Examples | If the Playwright version is old enough to not have the request fixture, the pattern needs adjustment — but `@playwright/test` is installed via npm in the E2E Dockerfile, likely recent |

## Open Questions (RESOLVED)

1. **Which Python test methods have no assertions?**
   - RESOLVED: Only `test_add_listener` in `test_model.py` is genuinely assertion-free. Others are intentional "no crash" tests, timeout-based lifecycle tests, or use `log_capture.check()`. Plan Task 1 targets only `test_add_listener`.

2. **What UI element represents the error state in the Settings page?**
   - RESOLVED: `.test-result` div with `[class.text-danger]` binding from `settings-page.component.html`. Plan Task 2 uses Playwright locator for `.test-result.text-danger` after clicking "Test Connection" with an unreachable Sonarr URL.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing toolchain read from repo
- Architecture: HIGH — all test files and Docker compose configs read directly
- Pitfalls: MEDIUM/HIGH — known issues from code inspection; E2E error-state UI element uncertainty is LOW
- Weak assertion findings: HIGH — confirmed by direct file reads

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable codebase — no fast-moving dependencies)
