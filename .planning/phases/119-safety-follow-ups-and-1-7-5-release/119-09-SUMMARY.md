---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 09
subsystem: release
status: complete
tags: [release, version-bump, dependabot, changelog, release-notes, rel-03, owner-checkpoint]
requires: [119-01, 119-02, 119-03, 119-04, 119-05, 119-06, 119-07, 119-08, 119-12]
provides:
  - "1.7.5 version metadata across package.json, both package-lock.json files, src/angular/package.json, pyproject.toml"
  - "Dependabot roll-ins #93 (source-map-js 1.2.2), #123 (cryptography 50.0.2), #124 (pytz 2026.5)"
  - "CHANGELOG [1.7.5] and plain-English 1.7.5 release notes"
  - "119-REL03-EVIDENCE.md (RED/GREEN, full suite, ruff 0.15.22, packaging, green CI run on PR #127, owner decision)"
affects: [119-10]
key-files:
  created:
    - .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md
  modified:
    - package.json
    - package-lock.json
    - src/angular/package.json
    - src/angular/package-lock.json
    - src/python/pyproject.toml
    - src/python/poetry.lock
    - src/docker/build/docker-image/Dockerfile
    - src/python (arr API-key change-detection identity: opaque in-memory tokens)
    - CHANGELOG.md
    - release-notes.md
decisions:
  - "Owner approved 1.7.5 as drafted (2026-10-15): notes wording, rollback to 1.7.4 with .pre-1.7.5 suffix, close #123/#124 after tag, #126 left out"
  - "CI run on the release tree via branch release/1.7.5 + PR #127 (no publish on PR); green on cbd99dc"
  - "Docker image installs Poetry 2.3.4 in an isolated /opt/poetry venv instead of an unpinned system pip install"
  - "Arr API-key change detection uses opaque in-memory per-key tokens, no hashing of the key (CodeQL py/weak-sensitive-data-hashing)"
  - "Root package-lock.json version was stale at 1.7.2; bumped to 1.7.5 with the rest"
metrics:
  started: 2026-10-15T10:20:13Z
  completed: 2026-10-15
  tasks_completed: 3
  tasks_total: 3
---

# Phase 119 Plan 09: 1.7.5 release prep and REL-03 evidence Summary

1.7.5 metadata, the three D-21 Dependabot roll-ins, CHANGELOG and plain-English release notes are committed, and the REL-03 evidence (RED reproduced for every test commit plus two mutation REDs, GREEN, 1685-test host suite, ruff 0.15.22, PACKAGE_OK) is recorded. CI ran on branch `release/1.7.5` via PR #127 and is green on head `cbd99dc` (run 38726397226, CodeQL 38726392573); two release-gate catches (Docker build Poetry/cffi clash, CodeQL weak-hash alert) were fixed on the way. The owner approved publishing 1.7.5 as drafted. No tag exists; tag, merge and publish are 119-10.

## Tasks

| Task | Name | Commit | Result |
|------|------|--------|--------|
| 1 | Version bumps, Dependabot roll-ins, CHANGELOG, release notes | 0306b27 | `verify-release-metadata.mjs 1.7.5` passed; RELEASE_META_OK |
| 2 | REL-03 gate evidence | 85248e8 | RED/GREEN/suite/ruff/package recorded; CI URL added at Task 3 completion |
| 3 | Owner approval checkpoint (+ CI fixes) | 6a323ee, cbd99dc, docs commit | Owner: approve as drafted; CI green on PR #127 |

## Verification observed

- `node scripts/verify-release-metadata.mjs 1.7.5`: passed (6 checks).
- `poetry run pytest tests/unittests/test_common -q`: 187 passed (after the cryptography/pytz bumps).
- `npm ls source-map-js`: 1.2.2 on both paths; `npm audit --audit-level=high`: no source-map-js finding.
- RED: e645508 4 failed; 32250fb 11 failed + 2 collection errors; 8194567 / c1f192d collection errors (ModuleNotFoundError); 7a73d8b 15 failed; 7bf68b2 28 failed; 907ada9 10 failed; e28a0a0 7 failed. Mutation runs: 21fa7bd launch-window AssertionError; d7e2354 synchronous-worker pytest-timeout.
- GREEN: all groups 0 failed. Full host suite: 1685 passed. Ruff 0.15.22: All checks passed. Package: PACKAGE_OK (seedsyncarr-1.7.5).
- CI on PR #127, head `cbd99dc`: https://github.com/thejuran/seedsyncarr/actions/runs/38726397226 success (`gh run view` observed: 9 gate jobs success, 5 publish jobs skipped); CodeQL run 38726392573 success.
- Task 3 verify: `actions/runs/` present in evidence (2 hits); `git tag -l v1.7.5` empty.
- NOT verified: Dependabot #93 closing (alert still `open`; GitHub rescans once the change reaches `main` in 119-10).

## Deviations from Plan

1. **[Rule 3 - Blocking] Test paths in the plan were wrong for two files.** `test_controller_handler.py` and `test_serialize_model.py` live under `tests/unittests/test_web/`; used the real paths.
2. **[Rule 3 - Blocking] `build` is not in the project venv.** Built the package in a scratch venv with `pip install build twine`, the same as CI.
3. **[Rule 2] Root `package-lock.json` was at 1.7.2.** Bumped to 1.7.5 so every version field matches.
4. **CI not run (orchestrator instruction overrides plan Task 2 step 6).** The plan says to push and wait for CI. The orchestrator said not to push, so CI is recorded as pending and listed as an awaited item at the checkpoint. As a result, Task 2's automated verify (`grep actions/runs/`) does not pass yet.

5. **[Rule 3 - Blocking] Docker image build failed in CI.** Unpinned `pip3 install poetry` into the system interpreter pulled cffi 2.1.1; `poetry install` with `virtualenvs.create=false` then failed downgrading cffi while running on it. Fixed by installing Poetry 2.3.4 into an isolated `/opt/poetry` venv (commit 6a323ee; recorded in cbd99dc's message).
6. **[Rule 2 - Security] CodeQL high alert py/weak-sensitive-data-hashing** on the arr API-key change-detection fingerprint (SHA-256, then HMAC in 6a323ee). Fixed in cbd99dc with opaque in-memory per-key counter tokens; the raw key is never stored in the identity or logged. 94 targeted tests pass; ruff clean; CodeQL green.
7. **CI ran via branch + PR** (`release/1.7.5`, PR #127) per owner item (d), so the gates ran without publishing `:dev` or docs.

8. **REL-02 / REL-03 left unchecked in REQUIREMENTS.md.** Both require the PyPI publish, and REL-03 also requires the image smoke test and NAS verification, all of which happen in 119-10. They are marked complete there.

## Assumption Drift (advisory)

- **Found during Task 2.** The plan expected the 119-03 file-operation-manager tests to fail with TypeError at `32250fb`. They actually failed with ModuleNotFoundError, because the file imports `controller.root_reservation` at module level. The mutation run at `21fa7bd` provides the behavioural RED for the launch window.
- **Found during Task 2.** The plan expected the synchronous-worker mutation to fail the elapsed-time assertions. Instead the calling thread blocked outright, and pytest-timeout stopped it at 60 s. This is the same defect in a stronger form.
- **Found during Task 1.** Dependabot opened PR #126 (npm_and_yarn group) after D-21. It is not in the plan and was left out, pending the owner's decision.

## Owner decision

2026-10-15, verbatim: "Approve as drafted" — items (a) limitation/cleanup wording as drafted, (b) rollback to 1.7.4 with .pre-1.7.5 suffix, (c) close #123/#124 after the tag with a "rolled into 1.7.5" comment, (e) leave #126 out. Item (d): CI via branch + PR (chosen). Also recorded in 119-REL03-EVIDENCE.md.

## Self-Check: PASSED

- FOUND: .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md
- FOUND: 0306b27, 85248e8, 7b1f67d, 6a323ee, cbd99dc
- `git tag -l v1.7.5`: empty (no tag)
