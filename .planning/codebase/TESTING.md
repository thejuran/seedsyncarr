# Testing Patterns

**Analysis Date:** 2026-05-26

SeedSyncarr has three distinct test layers, each with its own framework, config, and conventions:

| Layer | Framework | Location | File Pattern |
|-------|-----------|----------|--------------|
| Angular unit | Karma + Jasmine | `src/angular/src/app/tests/unittests/` and co-located `*.spec.ts` | `*.spec.ts` |
| Python unit + integration | pytest + unittest | `src/python/tests/unittests/`, `src/python/tests/integration/` | `test_*.py` |
| End-to-end | Playwright | `src/e2e/tests/` | `*.spec.ts` (page objects: `*.page.ts`) |
| Release-metadata | node:test | `scripts/verify-release-metadata.test.mjs` | `*.test.mjs` |

Total: 32 Angular spec files, 76 Python test files, 9 e2e spec files.

## Test Framework

### Angular unit tests
- Runner: **Karma 6.4** + **Jasmine 6**, config at `src/angular/karma.conf.js`
- Browser: headless Chrome (`ChromeHeadless` / `ChromeHeadlessCI` launchers)
- Reporters: `spec` + `kjhtml` (HTML reporter retained for browser context)
- Jasmine timeout: 10s for async tests (`timeoutInterval: 10000`)
- Coverage: `karma-coverage` outputs to `src/angular/coverage/`
- Test entry: `src/angular/src/test.ts`
- Tests run in deterministic order: `jasmine: { random: false }`

### Python tests
- Runner: **pytest 9** with **unittest** style classes still dominant
- Config: `[tool.pytest.ini_options]` in `src/python/pyproject.toml`
  - `pythonpath = ["."]` so tests import packages without prefixes
  - `timeout = 60` (per test, via `pytest-timeout`)
  - `cache_dir = "/tmp/.pytest_cache"` (avoids polluting the mounted source volume)
- Coverage: `pytest-cov`, configured in `[tool.coverage.run]` with `branch = true` and `fail_under = 84`
- Test helpers: `webtest` (WSGI integration), `testfixtures` (LogCapture), `unittest.mock`

### End-to-end tests
- Runner: **Playwright** (`@playwright/test`)
- Two playwright configs:
  - `src/e2e/playwright.config.ts` — production e2e against running Docker stack (`http://myapp:8800`)
  - `src/angular/playwright.config.ts` — Angular dev-server e2e against `http://localhost:4200`
- Production e2e settings:
  - `fullyParallel: false`, `workers: 1` — sequential, stateful runs
  - Locale forced to `en-US` to avoid arm64 vs amd64 ICU sort divergence
  - `screenshot: 'only-on-failure'`, `trace: 'on-first-retry'`
  - Test timeout 30s, expect timeout 5s (10s in CI)
- Browser: Chromium only (`devices['Desktop Chrome']` + `--no-sandbox`, `--disable-dev-shm-usage`)

### Release-metadata verifier
- Runner: Node.js built-in `node:test`
- Lives at repo root: `package.json` exposes `npm run test:release-metadata`
- Gates `publish-docker-image` / `publish-pypi` on v* tag pushes

**Run Commands:**
```bash
# Angular unit tests (from src/angular/)
npm test                                      # ng test (Karma watch mode)
make run-tests-angular                        # CI: headless via Docker

# Python tests
make run-tests-python                         # CI: full unit + integration suite in Docker
pytest tests/unittests/test_lftp -v           # ad-hoc, from src/python/

# E2E tests
make run-tests-e2e SEEDSYNCARR_ARCH=amd64     # CI: full Docker stack
cd src/e2e && npm test                        # local against running app
cd src/e2e && npm run test:headed             # with visible browser
cd src/e2e && npm run test:debug              # Playwright inspector

# Release metadata
npm run test:release-metadata                 # from repo root
```

## Test File Organization

**Angular:**
- Two locations used in parallel:
  - **Co-located** next to source: `src/app/pages/settings/option.component.spec.ts`, `src/app/pages/about/about-page.component.spec.ts`
  - **Centralized** mirror tree: `src/app/tests/unittests/services/utils/rest.service.spec.ts`, `src/app/tests/unittests/pages/files/transfer-row.component.spec.ts`
- The centralized tree mirrors the source structure under `src/app/`
- Shared mocks live at `src/app/tests/mocks/` (e.g., `mock-rest.service.ts`, `mock-model-file.service.ts`, `mock-event-source.ts`)
- When adding a new spec: prefer the centralized mirror under `src/app/tests/unittests/` for services and shared components; co-locate only for tightly-coupled page-level specs

**Python:**
```
src/python/tests/
├── __init__.py
├── conftest.py                # Shared pytest fixtures (test_logger, mock_context, mock_context_with_real_config)
├── utils.py                   # TestUtils — chmod_from_to, etc.
├── helpers/
│   ├── __init__.py            # create_test_logger, create_mock_context, create_mock_context_with_real_config
│   └── wsgi_stream.py
├── unittests/
│   ├── test_common/
│   ├── test_controller/
│   │   ├── test_extract/
│   │   └── test_scan/
│   ├── test_lftp/
│   ├── test_model/
│   ├── test_ssh/
│   ├── test_system/
│   └── test_web/
│       ├── test_handler/
│       └── test_serialize/
└── integration/
    ├── test_controller/
    │   └── test_extract/
    ├── test_lftp/
    └── test_web/
```
- The directory tree under `tests/unittests/` and `tests/integration/` mirrors `src/python/`
- Each test directory has an `__init__.py` (treated as a regular package, not namespace)
- Integration tests in `tests/integration/test_controller/` may be skipped on arm64 because the `rar` binary is amd64/i386-only (`@unittest.skipIf(shutil.which("rar") is None, ...)`)

**E2E:**
```
src/e2e/tests/
├── app.ts                     # Base App page object
├── helpers.ts                 # escapeRegex
├── about.page.ts / .spec.ts
├── autoqueue.page.ts / .spec.ts
├── csp-canary.spec.ts         # CSP violation canary
├── dashboard.page.ts / .spec.ts
├── logs.page.ts / .spec.ts
├── settings.page.ts / .spec.ts
├── settings-error.spec.ts
├── settings-fields.spec.ts
├── app.spec.ts
└── fixtures/
    ├── csp-listener.ts        # Test fixture extending base test
    └── seed-state.ts          # Test data seeding helpers
```
- Page-object pattern: every page has a `<name>.page.ts` extending `App` (`src/e2e/tests/app.ts`)
- Specs only call methods on the page object, never raw `page.locator(...)` (except in canary tests)
- Shared fixtures live under `tests/fixtures/`

**Naming:**
- Angular: `<component>.spec.ts` — mirrors the source filename
- Python: `test_<module>.py` — mirrors the source module
- E2E: `<page>.page.spec.ts` for page tests, `<feature>.spec.ts` for cross-page

## Test Structure

**Angular (Jasmine):**
```typescript
describe("BulkActionsBarComponent", () => {
    let component: BulkActionsBarComponent;
    let fixture: ComponentFixture<BulkActionsBarComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [BulkActionsBarComponent]   // standalone component
        }).compileComponents();

        fixture = TestBed.createComponent(BulkActionsBarComponent);
        component = fixture.componentInstance;
    });

    describe("Visibility", () => {
        it("should not show bar when no files are selected", () => {
            expect(component.hasSelection).toBe(false);
        });
    });
});
```
- Top-level `describe` per component / service
- Nested `describe` blocks group related assertions (`Visibility`, `Action counts`, `Click handlers`, `Edge cases`, `Performance`)
- `beforeEach` creates a fresh `TestBed` per test
- Section dividers (`// =====...`) separate logical groups inside large specs

**Python (unittest style — dominant):**
```python
class TestLftpJobStatusParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_size_to_bytes(self):
        self.assertEqual(345, LftpJobStatusParser._size_to_bytes("345"))
```
- Subclass `unittest.TestCase`
- `setUp` / `tearDown` lifecycle methods
- Assertions use `self.assertEqual(expected, actual)` — expected value comes first
- Apply `@overrides(unittest.TestCase)` decorator to `setUp` / `tearDown` when emphasizing the override

**Python (pytest style — newer tests):**
```python
def test_something(test_logger, mock_context):
    mock_context.config.lftp.use_ssh_key = True
    # ...
```
- Function-style tests accept fixtures by name
- Fixtures defined in `src/python/tests/conftest.py`
- Mix-and-match: `unittest.TestCase` methods can still use `@pytest.mark.timeout(5)` decorators (see `src/python/tests/unittests/test_common/test_multiprocessing_logger.py:25`)

**E2E (Playwright):**
```typescript
test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    test('should have all the action buttons', async () => {
        await dashboardPage.selectFileByName(TEST_FILE);
        await expect(dashboardPage.getActionBar().locator('button.action-btn')).toHaveCount(5);
    });
});
```
- Use custom `test` import from `./fixtures/csp-listener` rather than `@playwright/test` — this enforces CSP-violation checking by default
- Page object instantiated in `beforeEach`
- Assertions use Playwright's `expect()` with web-first auto-retry (`toBeVisible`, `toHaveText`, `toBeEnabled`, `toBeDisabled`)

## Mocking

**Angular — Jasmine SpyObj:**
```typescript
mockConnectedService = jasmine.createSpyObj("ConnectedService", [], {
    connected: connectedSubject.asObservable()
});

mockNotificationService = jasmine.createSpyObj("NotificationService", ["show", "hide"], {
    notifications: new BehaviorSubject([]).asObservable()
});

spyOn(component.queueAction, "emit");
expect(component.queueAction.emit).toHaveBeenCalledWith(jasmine.arrayContaining(["file1"]));
```
- `jasmine.createSpyObj(name, methodNames, properties)` for mock services
- `spyOn(target, 'method')` for spying on EventEmitter `.emit`
- Argument matchers: `jasmine.arrayContaining`, `jasmine.any`, `jasmine.objectContaining`
- Cast spy back to inspect calls: `(component.emit as jasmine.Spy).calls.mostRecent().args[0]`

**Angular — HTTP testing:**
```typescript
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        RestService,
        LoggerService,
    ]
});
httpMock = TestBed.inject(HttpTestingController);
restService = TestBed.inject(RestService);

restService.sendRequest("/server/request").subscribe(...);
httpMock.expectOne("/server/request").flush("success");
httpMock.verify();
```
- Use `provideHttpClient()` + `provideHttpClientTesting()` (Angular 21 functional providers)
- `fakeAsync(() => { ... })` wraps async logic for synchronous test execution
- Always call `httpMock.verify()` at end of each `it` to assert no pending requests

**Angular — Component inputs:**
- For OnPush components in DOM tests, use `fixture.componentRef.setInput("name", value)` before `detectChanges` so the component is marked dirty
- For computed-property tests, manually trigger `component.ngOnChanges({ ... })` with `SimpleChange` instances

**Angular — Pre-built mocks:**
- Located in `src/angular/src/app/tests/mocks/`
- Examples: `MockRestService`, `MockModelFileService`, `MockViewFileService`, `MockStorageService`, `MockEventSource`
- Provide via TestBed: `{provide: RestService, useClass: MockRestService}`

**Python — unittest.mock:**
```python
from unittest.mock import MagicMock, patch, PropertyMock, ANY

self.context = MagicMock()
self.controller = MagicMock()
self.controller.get_model_files_and_add_listener.side_effect = capture_listener
```
- `MagicMock()` is the default for unknown collaborators
- `patch(...)` / `@patch(...)` for replacing imports
- `PropertyMock` for property getters
- `ANY` sentinel for "don't care" arguments
- `side_effect` for dynamic behavior

**Python — shared mock helpers (conftest fixtures):**
- `test_logger` — sets up stdout logging, cleans up handler in teardown
- `mock_context` — `MagicMock()` context with all of `config.lftp.*`, `config.controller.*`, `config.general.*`, `args.*` pre-populated with sensible defaults
- `mock_context_with_real_config` — same shape but with a real `Config()` object so validation runs

**Python — WSGI integration:**
- Use `webtest.TestApp(wsgi_app)` to drive the Bottle app in-process; no real HTTP
- Build the app via `WebAppBuilder(context, controller, auto_queue_persist, MagicMock()).build()`

**E2E — fixtures:**
- The `csp-listener` fixture (`src/e2e/tests/fixtures/csp-listener.ts`) extends Playwright's base `test` to:
  - Auto-capture `securitypolicyviolation` events and console CSP errors
  - Fail any test that records a CSP violation, UNLESS the test opts in with `test.use({ allowViolations: true })`
- The `seed-state` fixture (`src/e2e/tests/fixtures/seed-state.ts`) seeds files into known statuses (DELETED, DOWNLOADED, STOPPED) via app APIs before the test runs

**What to Mock:**
- External processes: `pexpect`, `subprocess`, network calls
- File-system writes when the test does not need persistence
- Loggers (use real logger to stdout for visibility, but `MagicMock()` is OK when logs are not asserted)
- HTTP clients (Angular `HttpClient` via `HttpTestingController`; Python `requests` via `unittest.mock.patch`)

**What NOT to Mock:**
- The class under test
- `Config`, `Status`, `Persist` plain-data objects — use real instances
- `WebReaction`, `ViewFile`, `ModelFile` — these are dumb DTOs; instantiate them directly
- Bottle / Webtest pipeline — exercise the real WSGI stack
- Immutable.js / dataclass-like Python objects

## Fixtures and Factories

**Python (conftest.py fixtures):**
- `test_logger` — function-scoped; yields a real logger, removes handler on teardown
- `mock_context` — depends on `test_logger`; returns a MagicMock context with full config tree
- `mock_context_with_real_config` — returns context with a real `Config()` object

Backing functions in `tests/helpers/__init__.py` are ALSO callable directly from `unittest.TestCase.setUp()` so both styles share the same mock-builder code:
```python
from tests.helpers import create_test_logger, create_mock_context
```

**Python (integration test data):**
- `tests/integration/test_controller/test_controller.py` builds a real local + remote dir tree under `tempfile.mkdtemp()` via `my_mkdir`, `my_touch`, `create_archive` static methods
- The `rar` binary must be on `$PATH`; entire test class is skipped on arm64 (`@unittest.skipIf(shutil.which("rar") is None, ...)`)

**Angular (inline factories):**
- View files built via `new ViewFile({ name: "file1", isQueueable: true, ... })` at the top of `describe`
- Helpers like `setInputsAndDetectChanges(visibleFiles, selectedFiles)` defined inside each `describe` block
- Large file sets generated in-loop for performance tests (see `BulkActionsBarComponent` perf section, 500-file case)

**E2E (page objects + seed):**
- Page objects: `dashboard.page.ts`, `settings.page.ts`, etc. — extend `App` base class
- `FileInfo` interface (`{ name, status, size }`) describes expected golden data
- Comparisons are order-independent (sorted client-side) because Chromium `localeCompare` differs between amd64 and arm64 ICU builds

**Location:**
- Python: `tests/conftest.py`, `tests/helpers/`
- Angular: inline in spec files, shared mocks in `src/app/tests/mocks/`
- E2E: `src/e2e/tests/fixtures/`

## Coverage

**Python:**
- Target: 84% (`fail_under = 84` in `pyproject.toml`)
- Branch coverage enabled (`branch = true`)
- Excludes `tests/*` and `docs/*`
- Excludes lines matching `pragma: no cover`, `if __name__ == .__main__.`, `pass`
- HTML report: `htmlcov/` (per `[tool.coverage.html]`)

**Angular:**
- Coverage via `karma-coverage`, HTML output to `src/angular/coverage/`
- No enforced threshold in CI (yet)

**E2E:**
- Not measured — behavioral coverage only

**View Coverage:**
```bash
# Python
cd src/python && pytest --cov=. --cov-report=html
open htmlcov/index.html

# Angular
cd src/angular && ng test --code-coverage
open coverage/index.html
```

## Test Types

**Unit Tests:**
- Angular: per-component / per-service tests with mocked collaborators
- Python: per-class tests, often in `unittest.TestCase` style; pure-logic tests prefer pytest functions
- Cover happy-path, error paths, edge cases, regression cases (tagged with phase IDs like `FIX-01 D-09`)

**Integration Tests:**
- Python only — `tests/integration/test_lftp/`, `test_controller/`, `test_web/`
- Use real `lftp`, `rar`, `webtest` WSGI stack, real Bottle app
- Integration tests in `test_controller/` build real filesystem trees in tempdirs
- `test_lftp/` requires a running SSH server (provided via the docker `remote` service)

**E2E Tests:**
- Playwright against the running Docker stack (`myapp`, `remote`, `chrome`)
- Sequential, single worker — tests share state
- Drive UI through page objects; never reach into Angular internals
- Locale forced to `en-US`; comparisons order-independent across architectures

**Release Metadata:**
- Node `node:test` runner; verifies `package.json`, `pyproject.toml`, and CHANGELOG.md versions agree on `v*` tag pushes

## Common Patterns

**Async Testing (Angular):**
```typescript
it("should send http GET on sendRequest", fakeAsync(() => {
    let subscriberIndex = 0;
    restService.sendRequest("/server/request").subscribe({
        next: reaction => {
            subscriberIndex++;
            expect(reaction.success).toBe(true);
        }
    });
    httpMock.expectOne("/server/request").flush("success");

    expect(subscriberIndex).toBe(1);
    httpMock.verify();
}));
```
- Wrap in `fakeAsync(() => { ... })` and use `tick(ms)` to advance virtual time
- Use `flush("data")` on HttpTestingController, not `next()` — `flush` simulates the full response cycle

**Async Testing (Playwright):**
- Use `await expect(locator).toBeVisible()` rather than `await locator.isVisible()` — the former auto-retries
- Use `expect.poll(() => cspViolations.length).toBeGreaterThan(0)` for non-locator assertions that need retry
- Always `await page.goto(...)` then wait for a known-stable selector before assertions

**Async Testing (Python multiprocessing):**
```python
@pytest.mark.timeout(5)
def test_main_logger_receives_records(self):
    p_1 = multiprocessing.Process(target=process_1, args=(mp_logger,))
    with LogCapture("...") as log_capture:
        p_1.start()
        mp_logger.start()
        p_1.join(timeout=2)
        time.sleep(0.2)
        mp_logger.stop()
        log_capture.check(...)
```
- Apply `@pytest.mark.timeout(N)` to bound multi-process tests
- Use `testfixtures.LogCapture` to assert on log records
- Always `join(timeout=...)` and `time.sleep(...)` to give the child process room to flush

**Error Testing (Python):**
```python
def test_total_transfer_state_fails_on_queued(self):
    status = LftpJobStatus(job_id=-1, job_type=..., state=LftpJobStatus.State.QUEUED, name="", flags="")
    with self.assertRaises(TypeError) as context:
        status.total_transfer_state = LftpJobStatus.TransferState(...)
    self.assertTrue("Cannot set transfer state on job of type queue" in str(context.exception))
```
- `with self.assertRaises(ExceptionType) as context:`
- Inspect message via `str(context.exception)`

**Error Testing (Angular HTTP):**
```typescript
httpMock.expectOne("/server/request").flush(
    "Not found",
    { status: 404, statusText: "Bad Request" }
);
// or for a network error:
httpMock.expectOne("/server/request").error(new ErrorEvent("mock error"));
```

**OnPush Component DOM Tests:**
- Use `fixture.componentRef.setInput("inputName", value)` (not direct assignment) to mark the component dirty
- Then trigger `component.ngOnChanges({ ... })` and `fixture.detectChanges()`

**Regression Tests:**
- Reference the phase or issue ID in the `describe` / `it` title
  (e.g., `"FIX-01 DELETED union regression (D-09 coverage)"` in `bulk-actions-bar.component.spec.ts:371`)
- This lets future readers find the original investigation via grep

**Test Data Conventions (E2E):**
- File names used for golden data: `clients.jpg`, `documentation.png`, `illusion.jpg`, `goose`, `joke`, `crispycat`, `testing.gif`, `áßç déÀ.mp4`, `üæÒ` — covers Unicode and various sizes
- Status enum values (not display labels) used in URL params: `downloading`, `stopped` — NOT `Syncing` / `Failed`
- Bulk Extract button is `toBeDisabled()` in e2e (no archive fixtures are seeded) — never click it

## CI Integration

CI runs in `.github/workflows/ci.yml`:
1. `unittests-release-metadata` — Node tests on the release-metadata script
2. `unittests-python` — `make run-tests-python` (Docker)
3. `unittests-angular` — `make run-tests-angular` (Docker)
4. `lint-python` — `ruff check src/python/`
5. `lint-angular` — `npm run lint` (ESLint, `--max-warnings 0`)
6. `build-docker-image` — gates on (1)-(5)
7. `e2etests-docker-image` — matrix: amd64 always, arm64 only on main/tags

E2E timeouts: 45 min per arch. Unit tests: 15 min. Lint: 10 min.

---

*Testing analysis: 2026-05-26*
