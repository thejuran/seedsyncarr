<!-- generated-by: gsd-doc-writer -->
# Development

This guide covers local setup, build commands, code style, branch conventions, and the PR process for contributors working on SeedSyncarr.

## Local Setup

SeedSyncarr has two independently developed components: a Python backend and an Angular frontend. Both must be set up to work on the full stack.

**Prerequisites**

- Python `>=3.11,<3.13` (CI runs 3.12)
- Node.js `22+`
- Docker and Docker Compose (required for running the full stack and E2E tests)
- [Poetry](https://python-poetry.org/) for Python dependency management

**Steps**

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/thejuran/seedsyncarr.git
   cd seedsyncarr
   ```

2. Install Python dependencies:
   ```bash
   cd src/python && poetry install
   ```

3. Install Angular dependencies:
   ```bash
   cd src/angular && npm install
   ```

4. Copy the example environment file if one is present and fill in your local values. See [CONFIGURATION.md](CONFIGURATION.md) for all available settings.

The Python backend runs via Docker in normal operation. To build the Docker image locally:

```bash
make docker-image STAGING_REGISTRY=localhost:5000 STAGING_VERSION=dev
```

## Build Commands

### Makefile targets

| Command | Description |
|---|---|
| `make docker-image` | Build and push multi-arch Docker image to the staging registry |
| `make docker-image-release` | Promote a staged image to the release registry (requires `RELEASE_REGISTRY` and `RELEASE_VERSION`) |
| `make tests-python` | Build the Python test Docker environment |
| `make run-tests-python` | Build and run Python unit tests inside Docker |
| `make tests-angular` | Build the Angular test Docker environment |
| `make run-tests-angular` | Build and run Angular unit tests inside Docker |
| `make run-tests-e2e` | Run end-to-end tests against a staged Docker image (requires `STAGING_VERSION` and `SEEDSYNCARR_ARCH`) |
| `make coverage-python` | Run Python tests with coverage report (terminal + HTML output) |
| `make clean` | Remove the build directory |

### Angular scripts (`src/angular/`)

| Command | Description |
|---|---|
| `npm run build` | Production build of the Angular app (`ng build`) |
| `npm start` | Start the Angular dev server (`ng serve`) |
| `npm test` | Run Angular unit tests with Karma (`ng test`) |
| `npm run lint` | Lint all TypeScript source files with ESLint |
| `npm run e2e` | Run Playwright end-to-end tests |

## Code Style

### Python

The Python codebase (`src/python/`) is linted and formatted with [ruff](https://docs.astral.sh/ruff/) (`>=0.4.0`).

```bash
# Check for lint issues
ruff check src/python/

# Auto-format
ruff format src/python/
```

CI enforces the lint check in the `lint` job of `.github/workflows/ci.yml` on every push and pull request to `main`.

### Angular / TypeScript

The Angular codebase (`src/angular/`) is linted with ESLint, configured in `src/angular/eslint.config.js`. The config uses `typescript-eslint` with recommended rules plus project-specific overrides (max line length of 140, double quotes, semicolons required).

```bash
cd src/angular && npm run lint
```

ESLint is also enforced in CI in the same `lint` job.

### Editor settings

`src/angular/.editorconfig` defines:
- `indent_style = space`, `indent_size = 4`
- `charset = utf-8`
- `insert_final_newline = true`
- `trim_trailing_whitespace = true`

Configure your editor to respect `.editorconfig` to stay consistent with these settings.

## Branch Conventions

All feature branches must be cut from `main`, which is the default and only long-lived branch.

- Branch off `main` for every change: `git checkout -b feat/my-feature`
- Keep branches focused — one feature or fix per branch
- No formal prefix convention is documented beyond branching from `main`

## PR Process

1. Cut a branch from `main` and make your changes.
2. Ensure all tests pass locally: `make run-tests-python` and `make run-tests-angular`.
3. Ensure linting passes: `ruff check src/python/` and `cd src/angular && npm run lint`.
4. Open a pull request against `main` with a clear description of what changed and why.
5. Keep the PR focused — one feature or fix per PR.
6. CI will automatically run Python unit tests, Angular unit tests, lint checks, and Docker image build. All checks must pass before merge.
7. Address reviewer feedback before the PR is merged.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for additional guidelines including how to report bugs and request features.
