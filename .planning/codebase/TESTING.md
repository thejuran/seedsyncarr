# Testing Patterns

**Analysis Date:** 2026-06-09

## Test Framework

The repo has four distinct test suites. All CI suites run inside Docker containers (see Run Commands).

**Python (backend):**
- Runner: pytest >=9.0.3 with pytest-timeout (>=2.3.1) and pytest-cov (>=7.0.0)
- Config: `src/python/pyproject.toml` (`[tool.pytest.ini_options]`)
  - Global per-test timeout: 60s (`timeout = 60`, `timeout_func_only = false`)
  - `pythonpath = ["."]`, `cache_dir = "/tmp/.pytest_cache"` (keeps cache out of the read-only `/src` bind mount)
- Style: predominantly `unittest.TestCase` classes executed by pytest; `unittest.mock` for mocking; pytest fixtures available via `src/python/tests/conftest.py` for newer tests
- Extra dev deps: `testfixtures` (TempDirectory), `webtest` (WSGI TestApp for Bottle)

**Angular (frontend unit):**
- Runner: Karma 6.4 + Jasmine (jasmine-core ^6.2.0, karma-jasmine ~5.1.0)
- Config: `src/angular/karma.conf.js`
  - Jasmine: `random: false` (deterministic order), `timeoutInterval: 10000`
  - Browsers: `ChromeHeadless` custom launcher with `--no-sandbox --disable-dev-shm-usage`
  - Reporters: `spec`, `kjhtml`; coverage via karma-coverage
- Test entry: `src/angular/src/test.ts` (configured in `angular.json` test target, which file-replaces `environment.ts` → `environment.test.ts`)

**E2E (full stack):**
- Runner: Playwright (`@playwright/test` ^1.48.0)
- Config: `src/e2e/playwright.config.ts`
  - Sequential: `fullyParallel: false`, `workers: 1` (stateful backend)
  - `locale: 'en-US'` pinned (prevents amd64/arm64 sort divergence)
  - Chromium only; `retries: 2` in CI; `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`
  - `baseURL` from `APP_BASE_URL` env (default `http://myapp:8800`)
  - Timeouts: 30s test, expect 10s (CI) / 5s (local)

**Release metadata (scripts):**
- Node built-in test runner: `node --test scripts/verify-release-metadata.test.mjs`
- Script: `npm run test:release-metadata` (root `package.json`)

**Run Commands:**
```bash
make run-tests-python        # Python tests in Docker (pytest -v -p no:cacheprovider)
make run-tests-angular       # Angular tests in Docker (ng test --browsers ChromeHeadless --watch=false --code-coverage)
make run-tests-e2e           # Playwright e2e via src/docker/test/e2e/run_make_target.sh
make coverage-python         # Local: poetry run pytest --cov --cov-report=term-missing --cov-report=html
npm run test:release-metadata  # Root: node --test for release metadata verifier
```

CI (`.github/workflows/ci.yml`) runs: `unittests-release-metadata`, `unittests-python` (via `make run-tests-python`), `unittests-angular`, `lint-python` (`ruff check src/python/` as a SEPARATE gate from pytest), `lint-angular`, and `e2etests-docker-image` (amd64 always; arm64 added on main/tag pushes).

## Test File Organization

**Python** — separate tree mirroring source packages:
```
src/python/tests/
├── conftest.py              # pytest fixtures: test_logger, mock_context, mock_context_with_real_config
├── helpers/__init__.py      # create_test_logger, create_mock_context, create_mock_context_with_real_config
├── utils.py                 # TestUtils (e.g., chmod_from_to)
├── unittests/
│   ├── test_common/         # mirrors src/python/common/
│   ├── test_controller/     # mirrors controller/ (has base.py shared base class)
│   ├── test_lftp/
│   ├── test_model/
│   ├── test_ssh/
│   ├── test_system/
│   ├── test_web/            # incl. test_web/test_handler/
│   └── test_seedsyncarr.py
└── integration/
    ├── test_controller/     # incl. test_extract/
    ├── test_lftp/           # real lftp protocol tests
    └── test_web/            # webtest-based full web app tests
```
Naming: `test_<module>.py`, classes `Test<ClassName>`, methods `test_<behavior>`.

**Angular** — separate tree under `src/angular/src/app/tests/`, mirroring `services/` and `pages/`:
```
src/angular/src/app/tests/
├── unittests/
│   ├── common/              # e.g., is-selected.pipe.spec.ts
│   ├── pages/               # files/, logs/, main/ component specs
│   └── services/            # base/, files/, logs/, server/, settings/, utils/, autoqueue/
├── mocks/                   # mock-rest.service.ts, mock-model-file.service.ts, mock-event-source.ts, ...
└── fixtures/                # mock-model-files.ts (+ .prod.ts stub swapped in by prod fileReplacements in angular.json)
```
Naming: `<name>.spec.ts` matching the source file name.

**E2E** — page-object model in `src/e2e/tests/`:
```
src/e2e/tests/
├── app.ts                   # App base page object (shared nav helpers)
├── dashboard.page.ts        # Page objects: <area>.page.ts
├── dashboard.page.spec.ts   # Specs: <area>.page.spec.ts (plus csp-canary.spec.ts, settings-*.spec.ts)
├── helpers.ts               # escapeRegex etc.
└── fixtures/
    ├── seed-state.ts        # typed seed API hitting backend command endpoints
    └── csp-listener.ts      # extended `test` fixture (import { test, expect } from './fixtures/csp-listener')
```
URL paths centralized in `src/e2e/urls.ts` (`Paths.DASHBOARD` etc.).

## Test Structure

**Python — dominant unittest.TestCase style** (from `src/python/tests/unittests/test_controller/test_webhook_manager.py`):
```python
class TestWebhookManager(unittest.TestCase):
    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.manager = WebhookManager(context=self.mock_context)

    def test_enqueue_and_process_matching_file(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        result = self.manager.process(self.name_to_root)
        self.assertEqual([("File.A", "File.A")], result)
```

**Python — pytest fixture style for new tests** (`src/python/tests/conftest.py`):
- `test_logger` — configured stdout logger, auto-cleaned in fixture teardown
- `mock_context` — MagicMock context with all lftp/controller/general config attrs pre-populated (see `tests/helpers/__init__.py:create_mock_context` for the full default set)
- `mock_context_with_real_config` — MagicMock context with a REAL `common.Config` object (use when validation/serialization behavior matters)

These helpers are ALSO directly callable from `unittest.TestCase.setUp()` (that is their stated purpose — conftest fixtures are unreachable from unittest style, so import from `tests.helpers`). Note: many older tests still hand-build the mock context inline in `setUp()` (e.g., `test_scan_manager.py`); prefer the helpers for new code.

**Angular — TestBed + describe/beforeEach** (from `tests/unittests/services/utils/rest.service.spec.ts`):
```typescript
describe("Testing rest service", () => {
    let restService: RestService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
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
    });

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
});
```
Patterns: subscriber-count assertion (`subscriberIndex`) to prove the observable emitted; always `httpMock.verify()` at test end.

**E2E — page-object + golden data** (from `src/e2e/tests/dashboard.page.spec.ts`):
```typescript
import { test, expect } from './fixtures/csp-listener';   // NOT from @playwright/test directly

test.describe('Testing dashboard page', () => {
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboardPage = new DashboardPage(page);
        await dashboardPage.navigateTo();
    });

    test('should have a list of files', async () => {
        const golden: FileInfo[] = [ { name: 'clients.jpg', status: '', size: '40 KB' }, /* ... */ ];
        await dashboardPage.waitForAtLeastFileCount(golden.length);
        const files = await dashboardPage.getFiles();
        // Compare order-independent — display order depends on locale sort
    });
});
```
E2E conventions:
- Page objects extend `App` (`src/e2e/tests/app.ts`); `navigateTo()` waits for container visibility BEFORE row visibility (distinguishes "page not loaded" from "no data")
- Locators anchored with `^...$` regex via `escapeRegex` (`src/e2e/tests/helpers.ts`) to avoid prefix collisions (joke vs joke.png)
- Seed state via backend API in `test.beforeAll` using `src/e2e/tests/fixtures/seed-state.ts` (`seedMultiple`, `seedStatus`); targets `'DOWNLOADED' | 'STOPPED' | 'DELETED'`; polls for DISPLAY labels in the badge (Synced/Failed/Deleted), never raw enum names; URL `sub=` params use enum values (`downloading`, `stopped`), not display labels
- Unicode file names in fixtures ('áßç déÀ.mp4', 'üæÒ') — always `encodeURIComponent` file names in URLs
- Extract button is disabled in e2e (no archive fixtures): assert `toBeDisabled()`, don't click

## Mocking

**Python:** `unittest.mock` (MagicMock, patch, ANY)
```python
@patch('controller.scan_manager.ScannerProcess')
@patch('controller.scan_manager.ActiveScanner')
def test_init_creates_scanners_and_processes(self, mock_active_scanner, mock_scanner_process):
    ...
self.manager.logger.info.assert_called_with("Sonarr webhook import enqueued: 'File.A'")
```
- Mock the `context` object (config + logger) via `tests.helpers.create_mock_context()`
- `@patch` at the import site of the module under test (`'controller.scan_manager.ScannerProcess'`)
- Web handler tests use `webtest.TestApp` against the real Bottle app with mocked services (`tests/unittests/test_web/`, `tests/integration/test_web/test_web_app.py`)

**Angular:** hand-written mock classes in `src/angular/src/app/tests/mocks/` (no auto-mocking library)
```typescript
// mocks/mock-model-file.service.ts
export class MockModelFileService {
    _files = new Subject<Immutable.Map<string, ModelFile>>();
    get files(): Observable<Immutable.Map<string, ModelFile>> {
        return this._files.asObservable();
    }
}
```
- Expose a `Subject` backing field (`_files`) so tests can push emissions
- HTTP mocked with `provideHttpClientTesting()` + `HttpTestingController`
- SSE mocked with `mocks/mock-event-source.ts`
- Available mocks: rest, model-file, storage, stream-service-registry, view-file, view-file-options services

**What to Mock:**
- Python: process spawning (ScannerProcess, LFTP), SSH, the context/config/logger
- Angular: all HTTP, EventSource/SSE streams, sibling services

**What NOT to Mock:**
- Python: `Config` behavior when validation matters (use `mock_context_with_real_config`); Bottle routing in handler tests (webtest hits the real app)
- E2E: nothing — full Docker stack with a real lftp remote container

## Fixtures and Factories

**Python:**
- `src/python/tests/helpers/__init__.py` — context/logger factories (importable from both pytest and unittest styles)
- `src/python/tests/helpers/wsgi_stream.py` — WSGI stream helper for SSE tests
- `src/python/tests/utils.py` — `TestUtils.chmod_from_to` for permission tests
- `src/python/tests/unittests/test_controller/base.py` — shared base for controller tests
- `testfixtures.TempDirectory` used where real dirs are needed (e.g., `test_multiprocessing_logger.py`)

**Angular:**
- `src/angular/src/app/tests/fixtures/mock-model-files.ts` — dev fixture data; `mock-model-files.prod.ts` is an empty stub swapped in by prod `fileReplacements` in `src/angular/angular.json` so fixtures never ship

**E2E:**
- `src/e2e/tests/fixtures/seed-state.ts` — drives backend into known states via `/server/command/*` endpoints; applies a 100 B/s rate limit before STOPPED seeding so `stop` catches files mid-transfer
- `src/e2e/tests/fixtures/csp-listener.ts` — extends Playwright `test` to fail on CSP violations
- Remote file fixtures baked into the e2e remote Docker image (`make run-remote-server` for local dev)

## Coverage

**Python** (`src/python/pyproject.toml` `[tool.coverage.*]`):
- `fail_under = 88`, `branch = true`, `show_missing = true`
- Omits `tests/*`, `docs/*`; excludes `pragma: no cover`, `__main__` blocks, bare `pass`
- HTML output to `htmlcov/`
- View: `make coverage-python` (runs `poetry run pytest --cov --cov-report=term-missing --cov-report=html` from `src/python/`)

**Angular** (`src/angular/karma.conf.js` `coverageReporter.check.global`):
- statements 83 / branches 68 / functions 79 / lines 83
- Enforced in CI because the Docker test CMD passes `--code-coverage` (`src/docker/test/angular/Dockerfile`)
- HTML output to `src/angular/coverage/`

**E2E:** no coverage; HTML report to `src/e2e/playwright-report/` (`open: 'never'`).

## Test Types

**Unit Tests (Python):** `src/python/tests/unittests/` — per-class tests with mocked context; run with everything else by the Docker pytest invocation (no marker separation; the container CMD is plain `pytest -v -p no:cacheprovider` from `/src`).

**Integration Tests (Python):** `src/python/tests/integration/` — real lftp protocol (`test_lftp/`), real extraction (`test_controller/test_extract/`), full web app via webtest (`test_web/`). The python test container includes a local sshd + test user so SSH-dependent tests run for real.

**Unit Tests (Angular):** `src/angular/src/app/tests/unittests/` — services, components (pages/), pipes (common/).

**E2E Tests:** `src/e2e/tests/*.spec.ts` — Playwright against the built Docker image plus an lftp remote container; run via `make run-tests-e2e` (orchestrated by `src/docker/test/e2e/run_make_target.sh`); CI runs amd64 always, arm64 on main/tags.

**Script Tests:** `scripts/verify-release-metadata.test.mjs` — node built-in test runner.

## Common Patterns

**Async Testing (Angular):** `fakeAsync(() => { ... })` wrapper + `HttpTestingController.flush()`; count emissions with a local `subscriberIndex` variable and assert the count after flushing.

**Async Testing (E2E):** prefer `page.waitForFunction` / `locator.waitFor({ state: 'visible' })` with explicit timeouts over fixed sleeps; e.g., `DashboardPage.waitForAtLeastFileCount` waits for row count AND non-empty cell text.

**Error Testing (Python):** flush error responses through webtest and assert status; logger assertions via `self.manager.logger.info.assert_any_call(...)`.

**Error Testing (Angular):** flush HTTP errors and assert the service-level reaction object:
```typescript
httpMock.expectOne("/server/request").flush("Not found", {status: 404, statusText: "Bad Request"});
// then assert reaction.success === false and reaction.errorMessage
```

**Timeout discipline (Python):** every test is bounded by the global 60s pytest-timeout; do not write tests that legitimately need longer — restructure instead.

**Build verification for Python phases:** run BOTH `pytest` and `ruff check src/python/` (whole tree) — CI gates them separately.

---

*Testing analysis: 2026-06-09*

