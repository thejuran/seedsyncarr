<!-- generated-by: gsd-doc-writer -->
# Testing

SeedSyncarr has three distinct test suites: Python unit and integration tests (pytest), Angular unit tests (Karma + Jasmine), and end-to-end tests against a built Docker image (Playwright).

---

## Test Framework and Setup

### Python Tests — pytest

- **Framework:** pytest `>=9.0.3` with `pytest-timeout` and `pytest-cov`
- **Config:** `[tool.pytest.ini_options]` in `src/python/pyproject.toml`
- **Timeout per test:** 60 seconds
- **Helper fixtures:** `src/python/tests/conftest.py` — provides `test_logger`, `mock_context`, and `mock_context_with_real_config` fixtures shared across all pytest-style tests

Tests are run inside a Docker container via `make run-tests-python`. The container builds the Python dev environment before execution.

### Angular Unit Tests — Karma + Jasmine

- **Framework:** Karma `^6.4.4` + Jasmine `^6.1.0`
- **Config:** `src/angular/karma.conf.js`
- **Browser:** Chrome (headless in CI using the `ChromeHeadlessCI` launcher)
- **Timeout per async test:** 10 seconds (`jasmine.timeoutInterval`)

Tests are run inside a Docker container via `make run-tests-angular`.

### End-to-End Tests — Playwright

- **Framework:** `@playwright/test` `^1.48.0`
- **Config:** `src/e2e/playwright.config.ts`
- **Browser:** Chromium (Desktop Chrome profile)
- **Base URL:** `http://myapp:8800` (or `APP_BASE_URL` env var)
- **Concurrency:** Single worker, sequential execution (`fullyParallel: false`)
- **Retries in CI:** 2

E2e tests run against a fully built Docker image via `make run-tests-e2e`. The image must be built first (`make docker-image`).

---

## Running Tests

### Python Unit and Integration Tests

```bash
# Runs inside Docker — builds the devenv image first
make run-tests-python
```

### Angular Unit Tests

```bash
# Runs inside Docker — builds the Angular test image first
make run-tests-angular
```

To run Angular tests directly without Docker (requires local Node.js and Chrome):

```bash
cd src/angular
npm test
```

For watch mode (interactive development):

```bash
cd src/angular
npm test
# karma.conf.js has autoWatch: true by default (singleRun: false)
```

### End-to-End Tests

E2e tests require a built staging Docker image. You must supply `STAGING_REGISTRY`, `STAGING_VERSION`, and `SEEDSYNCARR_ARCH`.

```bash
# Build the Docker image first
make docker-image STAGING_REGISTRY=<registry> STAGING_VERSION=<build-number>

# Then run e2e tests
make run-tests-e2e \
  STAGING_REGISTRY=<registry> \
  STAGING_VERSION=<build-number> \
  SEEDSYNCARR_ARCH=amd64
```

To run e2e tests directly with Playwright (requires the app to be running at the configured base URL):

```bash
cd src/e2e
npx playwright test
```

### Release Metadata Verifier

```bash
npm run test:release-metadata
```

This focused Node test suite covers the release metadata guard used by tag publishing workflows.

---

## Writing New Tests

### Python Tests

- **Location:** `src/python/tests/unittests/` and `src/python/tests/integration/`
- **Naming convention:** `test_*.py` files; test functions prefixed with `test_`
- **Fixtures:** Request shared fixtures from `src/python/tests/conftest.py` by name — `test_logger`, `mock_context`, `mock_context_with_real_config`
- **Existing pattern:** Most tests subclass `unittest.TestCase` with a `setUp()` method; new tests may use pytest-style functions with fixtures instead

### Angular Unit Tests

- **Location:** `src/angular/src/app/tests/unittests/`
- **Naming convention:** `*.spec.ts`
- **Structure:** Organized by type — `pages/`, `services/`, `common/`
- **Shared config:** `src/angular/src/tsconfig.spec.json` extends the root tsconfig and includes all `**/*.spec.ts` files automatically

### End-to-End Tests

- **Location:** `src/e2e/tests/`
- **Naming convention:** `*.spec.ts`
- **Page objects:** Each page has a companion page-object file (e.g., `dashboard.page.ts` alongside `dashboard.page.spec.ts`) — use these for element selectors and navigation helpers rather than interacting with the DOM directly in tests

---

## Coverage Requirements

### Python

Coverage is enforced via `pytest-cov` with configuration in `src/python/pyproject.toml`:

| Type | Threshold |
|------|-----------|
| Combined (lines + branches) | 84% (`fail_under = 84`) |

Branch coverage is enabled (`branch = true`). Coverage source is the entire `src/python/` directory, excluding `tests/` and `docs/`.

Coverage reports are written to `src/python/htmlcov/`.

### Angular

Coverage is collected by `karma-coverage` and reported to `src/angular/coverage/` (HTML format). No minimum threshold is configured in `karma.conf.js`.

### End-to-End

No coverage threshold is configured for the Playwright e2e suite.

---

## CI Integration

Tests are run in the **CI** workflow (`.github/workflows/ci.yml`) on every push to `main` and on all pull requests targeting `main`.

| Job | Trigger | Command |
|-----|---------|---------|
| `unittests-release-metadata` | push/PR to `main` | `npm run test:release-metadata` |
| `unittests-python` | push/PR to `main` | `make run-tests-python` |
| `unittests-angular` | push/PR to `main` | `make run-tests-angular` (15-minute timeout) |
| `e2etests-docker-image` | after Docker image is built | `make run-tests-e2e` (runs on both `amd64` and `arm64`) |

The Docker image build (`build-docker-image`) depends on the Python, Angular, and release metadata unit test jobs, both lint jobs, and the release metadata guard. On non-tag runs the guard completes as a no-op; on `v*` tag runs it verifies release metadata before release-capable jobs continue. End-to-end tests are gated behind a successful image build and run in parallel on `ubuntu-latest` (amd64) and `ubuntu-24.04-arm` (arm64).

In CI, Playwright retries failing tests up to 2 times and uses a 10-second assertion timeout (vs 5 seconds locally). Screenshots are captured on failure; traces are saved on first retry.
