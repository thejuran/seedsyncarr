# Testing Patterns

**Analysis Date:** 2026-06-02

This repo has **three** distinct test layers, each with its own runner, location, and CI job. Match the layer you are working in.

| Layer | Framework | Location | Count | CI job |
|-------|-----------|----------|-------|--------|
| Python unit + integration | pytest (+ unittest.TestCase) | `src/python/tests/` | ~77 `test_*.py` files | `unittests-python` |
| Python lint | ruff | `src/python/` | n/a | `lint-python` (separate gate) |
| Angular unit | Karma + Jasmine | `src/angular/src/app/tests/` | ~40 `*.spec.ts` files | `unittests-angular` |
| Angular lint | eslint | `src/angular/` | n/a | `lint-angular` |
| End-to-end | Playwright | `src/e2e/tests/` | ~10 `*.spec.ts` files | `e2etests-docker-image` (amd64 + arm64) |
| Release-metadata | `node --test` | `scripts/` | 1 | `unittests-release-metadata` |

All test/lint jobs are defined in `.github/workflows/ci.yml`. `build-docker-image` depends on all unit-test + lint jobs; `e2etests-docker-image` gates image publish.

---

## Python Tests (pytest)

### Framework

- **Runner:** pytest `^9.0.3` with `pytest-timeout` and `pytest-cov` (dev extras in `src/python/pyproject.toml`)
- **Config:** `[tool.pytest.ini_options]` in `src/python/pyproject.toml` — `pythonpath = ["."]`, per-test `timeout = 60`, `cache_dir = "/tmp/.pytest_cache"` (kept off the host-mounted read-only `/src` volume)
- **Assertion styles coexist:** both classic `unittest.TestCase` (`self.assertEqual`) and plain `pytest` function-style tests. New tests may use either; the fixture layer supports both.

### Run Commands

```bash
make run-tests-python        # Build devenv image + run pytest in docker compose (canonical / CI path)
make coverage-python         # cd src/python && poetry run pytest --cov --cov-report=term-missing --cov-report=html
ruff check src/python/       # Separate lint gate — run this too before calling a Python phase done
```
The containerized command is `pytest -v -p no:cacheprovider` (`src/docker/test/python/Dockerfile` CMD). Tests run against a bind-mounted **read-only** `/src` volume.

### Test File Organization

Tests live in a **separate tree** mirroring the source package layout, split by kind:
```
src/python/tests/
├── conftest.py              # shared pytest fixtures
├── utils.py                 # shared test utilities
├── helpers/                 # importable setup helpers (callable from TestCase.setUp too)
│   ├── __init__.py          # create_test_logger, create_mock_context, ...
│   └── wsgi_stream.py
├── unittests/
│   ├── test_controller/     # mirrors src/python/controller/
│   ├── test_model/          # mirrors src/python/model/
│   ├── test_web/            # mirrors src/python/web/
│   ├── test_lftp/
│   └── test_ssh/
└── integration/
    ├── test_controller/
    ├── test_lftp/
    └── test_web/test_handler/   # one file per web handler
```
- **Naming:** files `test_*.py`; `unittest.TestCase` subclasses named `TestX`; methods `test_*` (`tests/unittests/test_controller/test_auto_queue.py`).
- **Unit vs integration:** `tests/unittests/` mock collaborators; `tests/integration/` exercise real lftp/web/controller wiring.

### Test Structure (TestCase style)

```python
import unittest
from unittest.mock import MagicMock, ANY

from common import overrides, PersistError, Config
from controller import AutoQueue, AutoQueuePattern, IAutoQueuePersistListener

class TestAutoQueuePattern(unittest.TestCase):
    def test_pattern(self):
        aqp = AutoQueuePattern(pattern="file.one")
        self.assertEqual(aqp.pattern, "file.one")
```
- Interface stubs in tests implement the real interface and use `@overrides(IInterface)` to guarantee signature conformance (`TestAutoQueuePersistListener` in `test_auto_queue.py`).

### Fixtures & Mocking (Python)

The fixture system is dual-mode by design (documented in `src/python/tests/conftest.py` and `tests/helpers/__init__.py`):

- **pytest fixtures** (`conftest.py`): `test_logger`, `mock_context`, `mock_context_with_real_config`. Requested by name as test-function arguments. The `test_logger` fixture handles handler teardown.
- **Importable helpers** (`tests/helpers/__init__.py`): `create_test_logger`, `create_mock_context`, `create_mock_context_with_real_config`. These back the fixtures **and** can be called directly from `unittest.TestCase.setUp()` (solving conftest fixtures being unreachable by TestCase tests). Prefer these helpers over hand-rolling a `MagicMock` context.

```python
# pytest style
def test_ssh_key_mode(mock_context):
    mock_context.config.lftp.use_ssh_key = True
    ...

# TestCase style
def setUp(self):
    self.context = create_mock_context()
```

- **Mocking:** stdlib `unittest.mock` (`MagicMock`, `ANY`). `create_mock_context()` returns a `MagicMock` pre-populated with the full `config.lftp` / `config.controller` / `config.general` attribute tree, overridable per test. Use `create_mock_context_with_real_config()` when a real `Config` object's validation/serialization behavior is needed instead of MagicMock attribute access.
- Other dev test deps: `testfixtures`, `webtest` (WSGI), `pexpect`-based integration for lftp.

### Coverage (Python)

- Enforced by `[tool.coverage.report] fail_under = 88`, `branch = true` (`src/python/pyproject.toml`). `tests/*` and `docs/*` omitted; excludes `pragma: no cover`, `if __name__ == "__main__"`, `pass`.
- HTML report → `src/python/htmlcov/` via `make coverage-python`.

---

## Angular Tests (Karma + Jasmine)

### Framework

- **Runner:** Karma `^6.4.4` with `@angular-devkit/build-angular`, browser Chrome / ChromeHeadlessCI (`src/angular/karma.conf.js`)
- **Assertion/spec:** Jasmine `^6.2.0` (`describe` / `it` / `expect`), `@types/jasmine`
- Async tests use Angular's `fakeAsync` + `TestBed`; `jasmine.timeoutInterval = 10000`, `random: false` (deterministic order)

### Run Commands

```bash
make run-tests-angular           # Build env image + run Karma in docker compose (CI path)
cd src/angular && npm test        # ng test (local watch)
cd src/angular && npm run lint     # eslint --max-warnings 0 (separate gate)
```

### Test File Organization

Specs are **NOT** co-located with source. They live in a dedicated mirror tree:
```
src/angular/src/app/
├── services/...                       # production code
├── pages/...                          # a few component specs co-locate (e.g. settings/*.spec.ts)
└── tests/
    ├── mocks/                         # reusable mock services
    │   ├── mock-rest.service.ts
    │   ├── mock-view-file.service.ts
    │   ├── mock-stream-service.registry.ts
    │   └── mock-event-source.ts
    ├── fixtures/                      # static datasets
    │   ├── mock-model-files.ts        # populated fixture (dev/test)
    │   └── mock-model-files.prod.ts   # empty stub, swapped in via angular.json fileReplacements (prod)
    └── unittests/
        ├── services/...               # mirrors app/services/ layout
        ├── pages/...
        └── common/
```
- **Naming:** `<source-name>.spec.ts` (`rest.service.spec.ts` ↔ `rest.service.ts`).
- **Mock-fixture hygiene (Phase 106, v1.3.0):** mock fixtures were relocated out of `services/` into `app/tests/fixtures/`, and a prod stub is swapped at build time via `angular.json` `fileReplacements` (parallel to the existing `environment.ts → environment.prod.ts` swap). Mock model data is gated by `environment.useMockModel` (true in dev, false in prod), consumed only by `view-file.service.ts`. When adding test data, place it under `app/tests/fixtures/`, not under `services/`. See `.planning/milestones/v1.3.0-phases/106-mock-fixture-bundle-hygiene/106-PATTERNS.md`.

### Test Structure (Jasmine + TestBed)

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

    it("should create an instance", () => {
        expect(restService).toBeDefined();
    });
});
```
(Source: `src/angular/src/app/tests/unittests/services/utils/rest.service.spec.ts`)

### Mocking (Angular)

- **HTTP:** `provideHttpClientTesting()` + `HttpTestingController`. Set expectations with `httpMock.expectOne(url).flush(body[, {status, statusText}])` or `.error(new ErrorEvent(...))`, then assert and call `httpMock.verify()`.
- **Async:** wrap the `it` body in `fakeAsync(() => { ... })`; subscribe and assert synchronously after `flush`.
- **Service mocks:** reusable fakes in `src/angular/src/app/tests/mocks/` (e.g. `mock-rest.service.ts`, `mock-view-file.service.ts`) supplied via TestBed `providers`/`useClass`.
- **What to mock:** HTTP, DOM/storage, stream registries, and cross-service collaborators. **What not to mock:** the service under test and pure value objects (`WebReaction`, pipes).

### Coverage (Angular)

Enforced in `src/angular/karma.conf.js` `coverageReporter.check.global`:
- statements 83, branches 68, functions 79, lines 83. HTML report → `src/angular/coverage/`.

---

## End-to-End Tests (Playwright)

### Framework

- **Runner:** Playwright `@playwright/test` against a running Docker image (chromium, Desktop Chrome).
- **Two configs:** `src/e2e/playwright.config.ts` (canonical, `baseURL` from `APP_BASE_URL` default `http://myapp:8800`) and `src/angular/playwright.config.ts`. Tests run from `src/e2e/`.

### Run Commands

```bash
make run-tests-e2e            # Full docker harness (CI path; amd64 + arm64 on main/tags)
cd src/e2e && npm test         # playwright test
cd src/e2e && npm run test:headed | test:debug
```

### Config & Determinism

`src/e2e/playwright.config.ts`:
- `fullyParallel: false`, `workers: 1`, retries `2` in CI / `0` local — **stateful sequential** tests.
- `locale: 'en-US'` forced to prevent arm64/amd64 ICU sort divergence. Tests that assert file ordering sort order-independently (`dashboard.page.spec.ts` sorts both actual and golden before comparing) — preserve this; do not assert raw display order.
- `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`; `timeout: 30000`, `expect.timeout` 10s CI / 5s local.

### Structure

- **Page Object Model:** `src/e2e/tests/*.page.ts` classes extend a base `App` (`dashboard.page.ts`, `settings.page.ts`); specs are `*.page.spec.ts` / `*.spec.ts`.
- **Fixtures:** `src/e2e/tests/fixtures/` — `seed-state.ts` (typed backend seed helpers hitting real `/server/command/*` endpoints), `csp-listener.ts` (extends `test`/`expect` to fail on CSP violations). Import `test`/`expect` from the CSP fixture, not bare `@playwright/test`, when CSP enforcement matters.
- **Shared helpers:** `src/e2e/tests/helpers.ts` (`escapeRegex`), `src/e2e/urls.ts` (`Paths`).

### E2E Conventions (project memory — must follow)

- URL `sub=` params use **enum values** (`downloading`, `stopped`), not display labels (`Syncing`, `Failed`). Status display labels (`Synced`, `Failed`, `Deleted`) are mapped in `seed-state.ts` and rendered by `transfer-row.component.ts`; seed helpers poll for the **display** string in the DOM but drive state via enum endpoints.
- The bulk-bar **Extract** button is disabled in E2E (no archive fixtures): assert `toBeDisabled()`, do not click it.
- E2E is **not** covered by the Angular eslint config (`eslint.config.js` ignores `e2e/`).

---

## Release-Metadata Tests

- `npm run test:release-metadata` → `node --test scripts/verify-release-metadata.test.mjs` (CI job `unittests-release-metadata`). Guards that `package.json` / `pyproject.toml` versions match the release tag.

---

## Common Patterns Summary

**Async testing:**
- Python: stdlib mocks; per-test 60s timeout via `pytest-timeout`.
- Angular: `fakeAsync(() => { ...; httpMock.expectOne(url).flush(...); expect(...); httpMock.verify(); })`.
- E2E: `async ({ page }) => { await expect(locator).toBeVisible(); }` with explicit `waitFor`/`waitForFunction` over fixed sleeps.

**Error testing:**
- Python: assert the mapped HTTP status / raised `AppError` subclass.
- Angular: flush an error response (`.flush("Not found", {status: 404})` or `.error(new ErrorEvent(...))`) and assert `reaction.success === false` plus `reaction.errorMessage`.

---

*Testing analysis: 2026-06-02*
