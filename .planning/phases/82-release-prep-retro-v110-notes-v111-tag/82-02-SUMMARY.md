---
phase: 82-release-prep-retro-v110-notes-v111-tag
plan: "02"
subsystem: release-engineering
tags: [debian-packaging, ci, github-release, deb]
dependency_graph:
  requires: []
  provides: [debian/DEBIAN/control, publish-deb-package CI job, release-notes.md template]
  affects: [.github/workflows/ci.yml]
tech_stack:
  added: [dpkg-deb, gh CLI release upload, docker cp artifact extraction]
  patterns: [tag-push CI job, debian control file, staging directory layout]
key_files:
  created:
    - debian/DEBIAN/control
    - release-notes.md
  modified:
    - .github/workflows/ci.yml
decisions:
  - "No QEMU setup in publish-deb-package — amd64-only per D-07; docker pull --platform linux/amd64 uses Buildx only"
  - "Control file cp path uses debian/DEBIAN/control (uppercase DEBIAN per dpkg-deb requirement)"
  - "release-notes.md committed as placeholder; Plan 03 will overwrite with actual v1.1.1 content"
  - "publish-deb-package job also creates the GitHub Release via gh release create — only one job does this per Pitfall 3"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-22"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 82 Plan 02: Debian Packaging Infrastructure Summary

Debian packaging infrastructure added: `debian/DEBIAN/control` metadata file and a new `publish-deb-package` CI job that extracts artifacts from the staging Docker image, builds a `.deb` with `dpkg-deb`, creates the GitHub Release, and uploads the `.deb` asset on every tag push.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create debian/DEBIAN/control file | fcfcaf6 | debian/DEBIAN/control (created) |
| 2 | Add publish-deb-package CI job and release-notes.md template | 88cf332 | .github/workflows/ci.yml (modified), release-notes.md (created) |

## What Was Built

### Task 1: debian/DEBIAN/control

- Created `debian/DEBIAN/` directory (new infrastructure — no prior analog in codebase)
- Control file fields: `Package: seedsyncarr`, `Version: 1.1.1`, `Architecture: amd64`, `Maintainer: thejuran`
- `Depends: python3 (>= 3.11), lftp, openssh-client, p7zip-full, unrar, bzip2` — mirrors Dockerfile runtime apt-get installs
- Description continuation line starts with single space per Debian policy
- File ends with trailing newline
- `Version` field is set to `1.1.1` as committed value; CI `sed` overwrites it with the actual tag version at build time

### Task 2: publish-deb-package CI job

The new job is inserted after `publish-docker-image` (line 149) and before `publish-docker-image-dev` in ci.yml.

**Job structure:**
- `if: startsWith(github.ref, 'refs/tags/v')` — same tag-push guard as `publish-docker-image`
- `needs: [ e2etests-docker-image ]` — gates on E2E tests passing
- Pulls staging Docker image for `linux/amd64` platform using Docker Buildx (no QEMU needed)
- Extracts `/app/html`, `/app/scanfs`, `/app/python` from staging container via `docker cp`
- Stages `deb-staging/DEBIAN/control` from `debian/DEBIAN/control`, overwriting Version via `sed`
- Builds `.deb` with `dpkg-deb --build deb-staging seedsyncarr_$RELEASE_VERSION_amd64.deb`
- Creates GitHub Release with title `v$RELEASE_VERSION — SeedSyncarr` using `release-notes.md` as notes body
- Uploads `.deb` as release asset via `gh release upload`

### Task 2: release-notes.md

- Placeholder template committed at repo root
- Contains `{{VERSION}}` token replaced by `sed` in CI at build time
- Plan 03 will overwrite this file with the actual v1.1.1 release body

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `release-notes.md` contains placeholder content (`Release notes for v{{VERSION}}.`). This is intentional — Plan 03 will populate it with the actual v1.1.1 changelog entry and release body per D-03.

## Threat Surface Review

T-82-05 mitigation confirmed: `GITHUB_TOKEN` in the new job follows the identical pattern already used by `publish-docker-image`. The token is scoped to `contents: write` (set globally at workflow level, line 16). No new trust boundary exposure beyond what already exists.

No new threat surface introduced.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| debian/DEBIAN/control exists | FOUND |
| release-notes.md exists | FOUND |
| commit fcfcaf6 exists | FOUND |
| commit 88cf332 exists | FOUND |
