---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 02
subsystem: packaging/ci
tags: [packaging, hatchling, pypi, ci, rel-02]
requires: []
provides:
  - "Valid wheel/sdist member paths (only-include hatch config)"
  - "scripts/verify-python-package.py member-path checker"
  - "verify-python-package CI job gating publish-pypi and build-docker-image"
affects: [119-09 release plan (PyPI publish)]
tech-stack:
  added: []
  patterns: ["hatch only-include lists for flat-layout app modules", "stdlib zipfile/tarfile member scan in CI"]
key-files:
  created:
    - scripts/verify-python-package.py
  modified:
    - src/python/pyproject.toml
    - .github/workflows/ci.yml
decisions:
  - "twine check runs non-strict; no readme/long_description added (RESEARCH Open Q4). Only warnings are missing long_description / content type."
  - "Version lines left at 1.7.4; 119-09 owns the 1.7.5 bump."
  - "Packaging CI job does not stamp the version; it verifies the committed pyproject."
metrics:
  duration: ~15m
  completed: 2026-10-14
  tasks: 2
  files: 3
---

# Phase 119 Plan 02: PyPI packaging fix (REL-02) Summary

Replaced hatch `packages = ["."]` with explicit `only-include` lists for the nine app modules. The wheel now has 82 members with no `./` prefix, down from 200 of 204 members carrying `./`. A stdlib checker script and a per-push CI job now catch this class of failure before a tag.

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Hatch `only-include` config + `scripts/verify-python-package.py` | 2e6068c |
| 2 | `verify-python-package` CI job wired into `publish-pypi` and `build-docker-image` needs | 049a0de |

## Verification (observed output)

The build was run with `build 1.6.1` and hatchling 1.32.4 on Python 3.12.12.

- `python -m build` produced `seedsyncarr-1.7.4-py3-none-any.whl` and `seedsyncarr-1.7.4.tar.gz`.
- `twine check` (twine 7.0.0, non-strict) returned **PASSED with warnings** for both archives. The only warnings were `long_description` missing and `long_description_content_type` missing.
- Checker output:
  ```
  PASS seedsyncarr-1.7.4-py3-none-any.whl members=82
  INFO seedsyncarr-1.7.4-py3-none-any.whl files=82
  PASS seedsyncarr-1.7.4.tar.gz members=81
  TOTAL members=163
  PACKAGE_OK
  ```
  The checker exited 0. The wheel file count is 82, which matches RESEARCH.
- `unzip -l <whl> | grep -c ' \./'` returned `0`.
- Wheel top-level entries: `common` 14, `controller` 25, `lftp` 4, `model` 4, `ssh` 2, `system` 3, `web` 24, `seedsyncarr.py`, `scan_fs.py`, `seedsyncarr-1.7.4.dist-info` 4. No `tests/`, `docs/`, `poetry.lock`, `pyproject.toml` or `PKG-INFO` is present.
- Negative test: the checker was run on crafted archives containing `./common/a.py`, `tests/t.py`, `../evil.py` and `/abs/p.py`. It reported 4 FAIL lines (dot-slash-prefix, forbidden-member, parent-traversal, absolute-path) and exited 1.
- Clean-venv install (Homebrew python3.12, scratchpad venv): `pip install <whl>` succeeded, and `seedsyncarr --help` exited 0 with this output:
  ```
  usage: seedsyncarr [-h] -c CONFIG_DIR [--logdir LOGDIR] [-d] [--exit] --html
                     HTML --scanfs SCANFS
  Seedsyncarr daemon
  ...
  ```
  `import seedsyncarr, controller, web, lftp, model, ssh, system, common, scan_fs` printed `imports ok`.
- Acceptance greps: the `packages = ["."]` count is 0, and the `only-include` count is 2.
- `ruff check .` in src/python and on the new script returned "All checks passed!".
- CI wiring: the YAML parsed with PyYAML and printed `CI_WIRING_OK`. That check also asserted that the job has no `if:` key. `grep -c verify-python-package ci.yml` returned 4.

**Not verified here:** the CI job has not run on GitHub Actions yet, because nothing was pushed. 119-09 Task 1 is the authority for a green CI run at the release gate.

## Deviations from Plan

**1. [Rule 3 - Blocking] Build tooling installed in a scratchpad venv, not the poetry venv**
- **Found during:** Task 1 and Task 2
- **Issue:** The poetry venv has no `build`, `twine` or `yaml` (PyYAML) modules. That venv lives in the shared pypoetry cache, which the main checkout also uses.
- **Fix:** Created `<scratchpad>/tools` (python3.12) and installed `build`, `twine` and `pyyaml` there. Ran the plan's verify commands with that interpreter instead of `poetry run`. The commands are otherwise identical. The project venv was left untouched.
- **Files modified:** none
- **Commit:** n/a

There were no other deviations. The TOML blocks were applied exactly as given in RESEARCH Pattern 7.

## Policy decision: twine strict mode

`twine check` runs non-strict both locally and in CI. No `readme` key was added to `[project]` (RESEARCH Open Q4). PyPI accepts an upload without a long description. Adding one means choosing what to show on the PyPI project page, which can be done later.

## Follow-ups (noted, not in scope)

- The top-level module names (`common`, `model`, `web`, ...) still pollute the site-packages namespace. RESEARCH flags this for the Reliability milestone. It should not be renamed in a patch release.

## Threat Flags

None. The changes cover build configuration, a CI job and a read-only checker. The plan's threat model covers T-119-05/06/07 (mitigated by the checker and only-include) and T-119-SC (accepted).

## Self-Check: PASSED

- FOUND: scripts/verify-python-package.py
- FOUND: src/python/pyproject.toml (only-include x2)
- FOUND: .github/workflows/ci.yml (verify-python-package x4)
- FOUND: commit 2e6068c
- FOUND: commit 049a0de
