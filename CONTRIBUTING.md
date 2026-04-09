# Contributing to SeedSyncarr

We welcome contributions! Here is how to get involved.

## Reporting Bugs

Open a [bug report](https://github.com/thejuran/seedsyncarr/issues/new?template=bug_report.yml) using the issue template. Include your installation type, version, and steps to reproduce.

## Requesting Features

Open a [feature request](https://github.com/thejuran/seedsyncarr/issues/new?template=feature_request.yml) describing the problem you want to solve.

## Development Setup

### Prerequisites

- Python 3.11+ (CI runs 3.12)
- Node.js 22+
- Docker (for running the full stack and E2E tests)

### Getting Started

1. Fork and clone the repository
2. Install Python dependencies: `cd src/python && poetry install`
3. Install Angular dependencies: `cd src/angular && npm install`
4. Run Python tests: `make run-tests-python`
5. Run Angular tests: `make run-tests-angular`

### Code Style

- **Python**: Formatted with [ruff](https://docs.astral.sh/ruff/). Run `ruff check src/python` and `ruff format src/python`.
- **Angular/TypeScript**: Linted with ESLint. Run `npm run lint` in `src/angular`.

## Pull Requests

1. Branch off `main`
2. Keep PRs focused — one feature or fix per PR
3. Ensure all tests pass before submitting
4. Describe what changed and why in the PR description

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md).
