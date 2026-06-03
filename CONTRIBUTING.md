# Contributing to SeedSyncarr

We welcome contributions! Here is how to get involved.

## Reporting Bugs

Open a [bug report](https://github.com/thejuran/seedsyncarr/issues/new?template=bug_report.yml) using the issue template. Include your installation type, version, and steps to reproduce.

## Requesting Features

Open a [feature request](https://github.com/thejuran/seedsyncarr/issues/new?template=feature_request.yml) describing the problem you want to solve.

## Development Setup

### Prerequisites

- Python 3.11 or 3.12 (CI runs 3.12)
- Node.js 22+
- [Poetry](https://python-poetry.org/) for Python dependency management
- Docker (for running the full stack and E2E tests)

### Getting Started

1. Fork and clone the repository
2. Install Python dependencies: `cd src/python && poetry install`
3. Install Angular dependencies: `cd src/angular && npm install`
4. Run Python unit tests: `make run-tests-python`
5. Run Angular unit tests: `make run-tests-angular`

### Code Quality Checks

- **Python lint**: `ruff check src/python`
- **Python format check**: `ruff format --check src/python`
- **Angular lint**: `cd src/angular && npm run lint`
- **E2E tests** (requires Docker): `make run-tests-e2e`

## Pull Requests

1. Branch off `main`
2. Keep PRs focused — one feature or fix per PR
3. Ensure all tests pass: `make run-tests-python` and `make run-tests-angular`
4. Run `ruff check src/python`, `ruff format --check src/python`, and `cd src/angular && npm run lint` before submitting
5. Describe what changed and why in the PR description

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md).
