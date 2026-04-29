---
phase: 93-ci-docker-hardening
plan: "01"
subsystem: ci
tags: [ci, security, docker, github-actions, supply-chain]
dependency_graph:
  requires: []
  provides: [hardened-ci-workflow, sha-pinned-actions, least-privilege-permissions, python-test-cache]
  affects: [.github/workflows/ci.yml, Makefile]
tech_stack:
  added: []
  patterns: [least-privilege-permissions, sha-pinned-actions, registry-cache]
key_files:
  created: []
  modified:
    - .github/workflows/ci.yml
    - Makefile
decisions:
  - "Workflow-level permissions locked to contents: read; per-job write grants only where required"
  - "All 13 mutable action refs pinned to 40-char SHA hashes (11 checkout, 3 setup-python, 1 setup-node)"
  - "publish-github-release now depends on publish-docker-image to prevent tag race"
  - "unittests-python gets packages: write for registry cache push in CI"
  - "PYTHON_TEST_CACHE_REGISTRY shell-conditional pattern: empty = no cache flags (dev), non-empty = registry cache (CI)"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-28"
  tasks_completed: 2
  files_modified: 2
---

# Phase 93 Plan 01: CI & Docker Hardening — CI Workflow Summary

**One-liner:** Least-privilege GitHub Actions permissions with SHA-pinned actions, fixed release dependency chain, and registry-based Docker build cache for Python tests.

## What Was Built

### Task 1: Harden CI workflow permissions, pin actions to SHA, fix job ordering

**CISEC-01 — Least-privilege permissions:**
- Replaced workflow-level `contents: write, packages: write` with `contents: read`
- Added per-job `permissions:` blocks only where write access is needed:
  - `unittests-python`: `packages: write` (GHCR cache push)
  - `build-docker-image`: `packages: write` (staging image push)
  - `publish-docker-image`: `packages: write` (release image push)
  - `publish-docker-image-dev`: `packages: write` (dev image push)
  - `publish-github-release`: `contents: write` (GitHub Release creation)
  - `publish-docs`: `contents: write` (gh-pages branch push)
  - `publish-pypi`: kept existing `id-token: write` unchanged
- Jobs with no write needs (`unittests-angular`, `lint-python`, `lint-angular`, `e2etests-docker-image`) inherit read-only

**CISEC-02 — SHA-pinned actions:**
- Pinned all 11 `actions/checkout@v4` → `@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1`
- Pinned all 3 `actions/setup-python@v5` → `@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0`
- Pinned 1 `actions/setup-node@v4` → `@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0`
- Already-pinned actions unchanged: docker/setup-qemu-action, docker/setup-buildx-action, peaceiris/actions-gh-pages, pypa/gh-action-pypi-publish

**CISEC-03 — Fix publish-github-release job ordering:**
- Added `publish-docker-image` to `publish-github-release` needs chain
- Prevents GitHub Release tag from referencing a Docker image that hasn't been published yet

**CISEC-04 — Python test image registry cache:**
- Added GHCR login step to `unittests-python` job
- Added `Set staging registry env variable` step (same pattern as build-docker-image)
- Changed `make run-tests-python` to `make run-tests-python PYTHON_TEST_CACHE_REGISTRY=${{ env.staging_registry }}`

### Task 2: Add conditional cache flags to Makefile tests-python target

- Replaced bare `docker build` in `tests-python` with shell-conditional `CACHE_FLAGS` approach
- When `PYTHON_TEST_CACHE_REGISTRY` is unset (local dev): `CACHE_FLAGS=""`, no change in behavior
- When set in CI: passes `--cache-from type=registry,ref=...:cache-python-test --cache-to type=registry,ref=...:cache-python-test,mode=max`
- Mirrors the existing `docker-image` target pattern (already uses registry cache)
- `$(DOCKER)` macro expands to `DOCKER_BUILDKIT=1 docker` which enables BuildKit required for type=registry cache

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 20023e8 | feat(93-01): harden CI permissions, pin actions to SHA, fix job ordering |
| 2 | 0fa2d57 | feat(93-01): add conditional registry cache to Makefile tests-python target |

## Verification Results

| Check | Result |
|-------|--------|
| YAML validity (js-yaml) | PASS |
| No unpinned actions remaining | PASS |
| Workflow-level permissions = contents: read only | PASS |
| unittests-python has packages: write | PASS |
| build-docker-image has packages: write | PASS |
| publish-docker-image has packages: write | PASS |
| publish-docker-image-dev has packages: write | PASS |
| publish-github-release has contents: write | PASS |
| publish-docs has contents: write | PASS |
| publish-github-release needs includes publish-docker-image | PASS |
| PYTHON_TEST_CACHE_REGISTRY in ci.yml | PASS |
| PYTHON_TEST_CACHE_REGISTRY in Makefile | PASS |
| cache-from type=registry in tests-python | PASS |
| cache-to type=registry in tests-python | PASS |
| cache-python-test ref in tests-python | PASS |

## Deviations from Plan

None — plan executed exactly as written. The plan acceptance criteria noted "9 or 10" for checkout pins; the actual count is 11 because the original file had 11 `checkout@v4` usages (all 11 jobs have checkout). All 11 were correctly pinned.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary changes introduced. The changes harden the existing CI trust boundaries:
- T-93-01, T-93-02, T-93-03: Mitigated by SHA pinning (CISEC-02)
- T-93-04: Mitigated by least-privilege permissions (CISEC-01)
- T-93-05: Mitigated by needs chain fix (CISEC-03)

## Known Stubs

None.

## Self-Check: PASSED

- `.github/workflows/ci.yml` exists and is modified
- `Makefile` exists and is modified
- Commit 20023e8 exists: `git log --oneline` confirms
- Commit 0fa2d57 exists: `git log --oneline` confirms
