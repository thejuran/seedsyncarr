---
phase: 82-release-prep-retro-v110-notes-v111-tag
plan: "03"
subsystem: docs
tags: [changelog, release-notes, version-bump, v1.1.1]
dependency_graph:
  requires: [82-01, 82-02]
  provides: [v1.1.1-changelog-entry, v1.1.1-release-notes, version-bump-1.1.1]
  affects: [CHANGELOG.md, release-notes.md, package.json, src/angular/package.json, src/angular/package-lock.json, src/python/pyproject.toml]
tech_stack:
  added: []
  patterns: [keep-a-changelog, npm-version-bump]
key_files:
  created: []
  modified:
    - CHANGELOG.md
    - release-notes.md
    - package.json
    - src/angular/package.json
    - src/angular/package-lock.json
    - src/python/pyproject.toml
decisions:
  - "Root package.json had no version field — added 'version': '1.1.1' as first key per D-09"
  - "Used replace_all on pyproject.toml to update both [project] and [tool.poetry] version fields simultaneously"
  - "Ran npm install --package-lock-only to regenerate package-lock.json without downloading packages"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-22T20:22:55Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 6
---

# Phase 82 Plan 03: v1.1.1 CHANGELOG Entry, Release Notes, and Version Bump Summary

**One-liner:** v1.1.1 CHANGELOG entry with Added/Fixed/Security sections, release-notes.md populated for CI, and all four version files bumped from 1.0.0 to 1.1.1.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write v1.1.1 CHANGELOG entry and populate release-notes.md | c0b0531 | CHANGELOG.md, release-notes.md |
| 2 | Bump version strings from 1.0.0 to 1.1.1 across all version files | 3a81af3 | package.json, src/angular/package.json, src/angular/package-lock.json, src/python/pyproject.toml |

## What Was Built

**Task 1:**
- Added `## [1.1.1] - 2026-04-22` entry to CHANGELOG.md above v1.1.0 entry (newest-first ordering).
- Entry has `### Added` (optional Fernet encryption at rest for config secrets), `### Fixed` (bulk-actions bar Re-Queue from Remote + auto-delete pack safety), `### Security` (basic-ftp DoS advisory).
- Added `[1.1.1]: https://github.com/thejuran/seedsyncarr/compare/v1.1.0...v1.1.1` at bottom above existing [1.1.0] and [1.0.0] links.
- Overwrote placeholder `release-notes.md` with v1.1.1 GitHub Release body: summary sentence + same Added/Fixed/Security sections + `**Full changelog:**` link. Ready for `--notes-file` in CI publish-deb-package job.

**Task 2:**
- Root `package.json`: added `"version": "1.1.1"` as first key (field was absent per RESEARCH.md Pitfall 1).
- `src/angular/package.json`: bumped `"version"` from `"1.0.0"` to `"1.1.1"` (flows to Angular app via `version.ts`).
- `src/python/pyproject.toml`: bumped both `[project]` (line 7) and `[tool.poetry]` (line 45) version fields from `1.0.0` to `1.1.1`.
- `src/angular/package-lock.json`: regenerated via `npm install --package-lock-only`; lockfile now shows seedsyncarr at version `1.1.1`.

## Verification Results

All acceptance criteria passed:

- `grep '## \[1.1.1\] - 2026-04-22' CHANGELOG.md` — match found
- `grep '### Fixed' CHANGELOG.md` — match found
- `grep '### Security' CHANGELOG.md` — match found
- `grep '\[1.1.1\]: https://github.com/thejuran/seedsyncarr/compare/v1.1.0...v1.1.1' CHANGELOG.md` — match found
- v1.1.1 entry at line 7, v1.1.0 entry at line 22 — correct newest-first ordering
- `grep 'Re-Queue from Remote' release-notes.md` — match found
- `grep '"version": "1.1.1"' package.json` — match found
- `grep '"version": "1.1.1"' src/angular/package.json` — match found
- `grep 'version = "1.1.1"' src/python/pyproject.toml` — 2 matches (both [project] and [tool.poetry])
- `grep '1.0.0' package.json src/angular/package.json src/python/pyproject.toml` — only dependency version specifiers (testfixtures>=11.0.0), not version fields — CLEAN
- `grep -A1 '"name": "seedsyncarr"' src/angular/package-lock.json` — shows `"version": "1.1.1"` — CLEAN
- No phase references in CHANGELOG.md or release-notes.md — 0 matches
- No internal items (pytest-cache, Playwright CSP, arm64 rar, WAITING_FOR_IMPORT) in changelog — 0 matches

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — all changes are documentation and config version strings only (T-82-06 and T-82-07 accepted per threat model).

## Self-Check: PASSED

- CHANGELOG.md contains `## [1.1.1] - 2026-04-22`: FOUND
- release-notes.md contains `### Fixed` and `**Full changelog:**`: FOUND
- package.json contains `"version": "1.1.1"`: FOUND
- src/angular/package.json contains `"version": "1.1.1"`: FOUND
- src/python/pyproject.toml has 2 occurrences of `version = "1.1.1"`: FOUND
- src/angular/package-lock.json seedsyncarr entry at `"version": "1.1.1"`: FOUND
- Commit c0b0531 exists: FOUND
- Commit 3a81af3 exists: FOUND
