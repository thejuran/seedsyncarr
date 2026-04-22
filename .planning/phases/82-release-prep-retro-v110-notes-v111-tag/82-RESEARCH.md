# Phase 82: Release Prep (Retro v1.1.0 Notes + v1.1.1 Tag) - Research

**Researched:** 2026-04-22
**Domain:** Release engineering — changelog authoring, version bumping, GitHub Releases, Debian packaging, CI tag-push pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Changelog Style**
- D-01: Use Keep a Changelog standard sections (Added, Changed, Fixed, Security) — no per-phase breakdowns, no phase references.
- D-02: Entries must be user-facing — describe what changed from the user's perspective, not internal implementation details. Avoid jargon like "SCSS consolidation" in favor of descriptions like "Unified color theme across all pages."

**GitHub Release Format**
- D-03: GitHub Release body mirrors the CHANGELOG.md entry for each version. Add a brief intro line summarizing the release, then the categorized list, then a "Full changelog" link.
- D-04: Both v1.1.0 and v1.1.1 get GitHub Releases. v1.1.0 tag already exists — create the Release on the existing tag. v1.1.1 gets a new tag + Release.

**Release Artifacts**
- D-05: Docker images and .deb package publish from the same CI tag-push trigger. Docker already wired via `publish-docker-image` job; add a new CI job for Deb packaging.
- D-06: .deb attached as a GitHub Release asset (no apt repository). Built in CI, uploaded via `gh release upload`.
- D-07: .deb targets amd64. ARM64 Deb is not required (Docker covers arm64).

**Version Bump**
- D-08: Bump straight from 1.0.0 → 1.1.1 in a single commit. No retroactive 1.1.0 version bump — the v1.1.0 tag stays on its existing commit as-is.
- D-09: Files to bump: `package.json` (root), `src/angular/package.json`, `src/python/pyproject.toml`, and `debian/control` (new file created for Deb packaging).

### Claude's Discretion
- Debian control file structure and metadata (package name, description, dependencies, maintainer)
- Exact categorization of each v1.1.0 and v1.1.1 change into Keep a Changelog sections
- CI job structure for Deb build (which runner, build steps, artifact upload)
- Whether to delete the `v1.1.0-dev` pre-release after v1.1.0 proper is published
- Order of operations (changelog first vs version bump first vs tag first)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | v1.1.0 release notes exist in CHANGELOG and as a GitHub Release (tag `v1.1.0`) with a categorized summary of Phases 62-74. Retroactively filed for the 2026-04-19 release that shipped without notes. | Changelog authoring pattern established from v1.0.0 entry; v1.1.0 tag exists with no GitHub Release; `gh release create` available via CI `contents: write` permission. |
</phase_requirements>

---

## Summary

Phase 82 is a release engineering phase with no production code changes. The work falls into four distinct lanes: (1) write retroactive v1.1.0 changelog entry and GitHub Release, (2) write v1.1.1 changelog entry, (3) bump version strings from 1.0.0 to 1.1.1 across four files, and (4) add a Debian packaging CI job and push the v1.1.1 tag to trigger release artifacts.

All upstream phases (75-81) have implementation complete. Phase 81 (SEC-02) has all three plan summaries and a review/fix round committed but no `VERIFICATION.md` — the verifier pass is pending. The CONTEXT.md already treats Phase 81 as a dependency that must be merged before release; planning should note this upstream gate.

The project's CI already gates artifact publishing on `startsWith(github.ref, 'refs/tags/v')`, and `permissions: contents: write` is set globally on the workflow. The `gh` CLI is available in GitHub Actions natively (no action needed). Debian packaging is new infrastructure: no `debian/` directory exists yet. The simplest compliant approach is `dpkg-deb` (built into `ubuntu-latest`) with a handcrafted `debian/DEBIAN/control` file, building a package that installs the Python app source, Angular HTML, and `scanfs` binary. [VERIFIED: codebase inspection]

**Primary recommendation:** Four sequenced plans — (1) retroactive CHANGELOG + GitHub Release for v1.1.0, (2) v1.1.1 CHANGELOG entry + version bump, (3) Debian control file + CI Deb-publish job, (4) push v1.1.1 tag and verify CI publishes all artifacts and GitHub Release is created.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Changelog authoring (v1.1.0 + v1.1.1) | Repository (docs) | — | CHANGELOG.md is a repo artifact; no runtime tier involved |
| GitHub Release creation (v1.1.0) | CI / GitHub API | — | Existing tag; `gh release create --tag v1.1.0` from CLI or CI |
| Version string bump | Repository (config files) | — | Four files edited; no runtime logic changes |
| Debian package build | CI (ubuntu-latest) | — | `dpkg-deb` available on runner; amd64 only per D-07 |
| GitHub Release creation + asset upload (v1.1.1) | CI tag-push job | — | Triggered by `git push --tags`; `gh release create` + `gh release upload` |
| Docker image publish (v1.1.1) | CI (existing job) | — | `publish-docker-image` job already wired; no changes needed |

---

## Standard Stack

### Core Tools

| Tool | Source | Purpose | Why Standard |
|------|--------|---------|--------------|
| `gh` CLI | Pre-installed on GitHub Actions ubuntu-latest | Create/update GitHub Releases, upload assets | Native to GitHub ecosystem; `contents: write` already granted |
| `dpkg-deb` | Built into ubuntu-latest | Build `.deb` package from staged directory | Zero-dependency; always available on Debian/Ubuntu runners |
| `git tag` + `git push --tags` | Git | Create and push v1.1.1 tag | Standard git tagging; triggers `refs/tags/v` CI condition |

### Supporting

| Tool | Source | Purpose | When to Use |
|------|--------|---------|-------------|
| `actions/checkout@v4` | GitHub Actions | Checkout repo in Deb CI job | Same pattern as all other CI jobs |
| Docker multi-stage build | Existing Dockerfile | Build Angular HTML + scanfs binary for packaging | Reuse existing build stages rather than duplicating build logic |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dpkg-deb` (manual) | `goreleaser/nfpm-action` | nfpm is cleaner declarative YAML but adds external action dependency; `dpkg-deb` is zero-dep and sufficient for a single-arch package |
| `dpkg-deb` (manual) | `fpm` (Ruby gem) | fpm is powerful but requires Ruby; overkill for a single package format |
| Direct `gh release create` in CI | `softprops/action-gh-release` | GitHub Action is an option but `gh` CLI is already available and more explicit |

---

## Architecture Patterns

### System Architecture Diagram

```
Developer workstation
  │
  ├─► Edit CHANGELOG.md (v1.1.0 + v1.1.1 entries)
  ├─► Edit version files (package.json ×2, pyproject.toml ×2 [project+poetry], debian/control)
  ├─► git commit "chore: bump version to 1.1.1 and add changelogs"
  │
  └─► gh release create v1.1.0 (on existing tag, retroactive)
        └─► GitHub Release created with v1.1.0 body

  └─► git tag v1.1.1 && git push --tags
        │
        ▼
  GitHub Actions CI (refs/tags/v1.1.1)
        ├─► unittests-python ──────────────────────────────────────────┐
        ├─► unittests-angular ─────────────────────────────────────────┤
        │                                                               │
        ├─► build-docker-image (needs: unittests-*) ◄──────────────────┘
        │
        ├─► e2etests-docker-image (amd64 + arm64, needs: build-docker-image)
        │
        ├─► publish-docker-image (EXISTING — if: refs/tags/v)
        │     ├─► push ghcr.io/thejuran/seedsyncarr:1.1.1
        │     └─► push ghcr.io/thejuran/seedsyncarr:latest
        │
        └─► publish-deb-package (NEW — if: refs/tags/v)
              ├─► Build Angular HTML (docker buildx)
              ├─► Build scanfs binary (docker buildx pyinstaller stage)
              ├─► Stage debian/ layout
              ├─► dpkg-deb --build staging/ seedsyncarr_1.1.1_amd64.deb
              ├─► gh release create v1.1.1 --title "v1.1.1 — SeedSyncarr" --notes-file body.md
              └─► gh release upload v1.1.1 seedsyncarr_1.1.1_amd64.deb
```

### Recommended Project Structure (new files this phase)

```
repo root
├── CHANGELOG.md             # Add v1.1.0 and v1.1.1 entries
├── package.json             # Bump version to 1.1.1
├── src/
│   ├── angular/
│   │   └── package.json     # Bump version to 1.1.1
│   └── python/
│       └── pyproject.toml   # Bump [project].version and [tool.poetry].version to 1.1.1
└── debian/
    └── DEBIAN/
        └── control          # New file — Deb package metadata
```

### Pattern 1: Keep a Changelog Entry

**What:** Standard CHANGELOG.md format with semantic version header, date, and categorized subsections
**When to use:** Every release
**Example:**

```markdown
## [1.1.0] - 2026-04-20

### Added

- Per-file selection and bulk actions: select individual files or ranges, apply Queue, Stop, Extract, Delete Local, or Delete Remote to multiple files at once.
- Dashboard filter with URL persistence: filter transfers by status (Active, Done, Pending) with state preserved across page reloads via URL query parameters.
- Storage capacity tiles on the dashboard showing local disk and remote seedbox usage with warning/danger color thresholds.
- New nav bar with connection status indicator and page breadcrumbs.

### Changed

- Transfer table redesigned with sortable columns, search, pagination, and color-coded status badges.
- Settings page reorganized into card sections with toggle switches and inline AutoQueue management.
- Logs page updated with full-viewport terminal view, level filter, and regex search.
- About page redesigned with version badge and system info table.
- Unified color theme applied consistently across all pages.

[1.1.0]: https://github.com/thejuran/seedsyncarr/compare/v1.0.0...v1.1.0
```

Source: [VERIFIED: CHANGELOG.md existing v1.0.0 entry, keepachangelog.com format]

### Pattern 2: GitHub Release body (D-03 format)

**What:** Intro line + CHANGELOG categories + Full changelog link
**When to use:** Both v1.1.0 and v1.1.1 releases
**Example:**

```markdown
UI redesign with Triggarr-style visual identity — new nav bar, redesigned dashboard and settings, per-file selection with bulk actions, and storage capacity tiles.

### Added
- [user-facing items]

### Changed
- [user-facing items]

**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/main/CHANGELOG.md
```

Source: [VERIFIED: v1.0.0 GitHub Release body reviewed; D-03 decision]

### Pattern 3: CI tag-push job (model from `publish-docker-image`)

**What:** Job that runs only on version tag pushes, mirrors the existing publish-docker-image pattern
**When to use:** New `publish-deb-package` job

```yaml
publish-deb-package:
  name: Publish Deb Package
  if: startsWith(github.ref, 'refs/tags/v')
  runs-on: ubuntu-latest
  needs: [ e2etests-docker-image ]
  steps:
    - name: Set release version
      run: echo "RELEASE_VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_ENV
    - name: Checkout
      uses: actions/checkout@v4
    # Build artifacts (Angular HTML + scanfs)
    # ... docker buildx steps (see Pattern 4)
    # Stage deb layout and build
    # gh release create + upload
```

Source: [VERIFIED: ci.yml lines 149-191 reviewed]

### Pattern 4: Debian package layout

**What:** Minimal `debian/DEBIAN/control` file and staged directory for `dpkg-deb`
**When to use:** Deb CI job build step

```
staging/
└── DEBIAN/
    └── control          ← package metadata
/usr/lib/seedsyncarr/
    ├── python/          ← Python app source (seedsyncarr.py, common/, etc.)
    ├── html/            ← Built Angular dist/browser/
    └── scanfs           ← PyInstaller binary (amd64)
/etc/seedsyncarr/        ← Empty dir (config written here at runtime)
/usr/bin/
    └── seedsyncarr      ← Shell wrapper: python /usr/lib/seedsyncarr/python/seedsyncarr.py ...
/lib/systemd/system/
    └── seedsyncarr.service  ← Optional: systemd unit (Claude's discretion)
```

**Control file:**

```
Package: seedsyncarr
Version: 1.1.1
Architecture: amd64
Maintainer: thejuran
Description: Fast file syncing from remote seedbox with Sonarr/Radarr integration
 LFTP-based file sync with a web UI, automated media imports, and auto-delete.
Depends: python3 (>= 3.11), python3-pip, lftp, openssh-client, p7zip-full, unrar, bzip2
```

Source: [ASSUMED: Debian packaging conventions. Control file format is standard. Exact runtime dependencies and install layout are Claude's discretion per CONTEXT.md.]

### Pattern 5: Version bump across files

**What:** Edit four files in a single commit to bump 1.0.0 → 1.1.1
**Files:**
1. `package.json` (root) — `"version"` field absent (root package.json has no version field — only `devDependencies` and `overrides`) [VERIFIED: file read]
2. `src/angular/package.json` — `"version": "1.0.0"` → `"version": "1.1.1"` [VERIFIED: file read]
3. `src/python/pyproject.toml` — `[project].version = "1.0.0"` AND `[tool.poetry].version = "1.0.0"` (both sections) → `1.1.1` [VERIFIED: file read]
4. `debian/control` (new file) — created with `Version: 1.1.1` [ASSUMED: new file]

**Important discovery:** The root `package.json` does NOT have a `version` field — it only has `devDependencies` and `overrides`. [VERIFIED: file read] The CONTEXT.md D-09 says to bump `package.json` (root), but there is no version field there. The Angular app version flows from `src/angular/package.json` via `version.ts`. The planner should clarify: either add a `version` field to root `package.json`, or acknowledge only `src/angular/package.json` + `pyproject.toml` + `debian/control` carry the version.

### Anti-Patterns to Avoid

- **Retroactively moving the v1.1.0 tag:** D-08 explicitly forbids this. The tag stays on its existing commit.
- **Per-phase changelog breakdown:** D-01 forbids this. No "Phase 72:" references in changelog.
- **Developer-facing changelog language:** D-02 forbids "SCSS consolidation," "BehaviorSubject," "service class." Use "Unified color theme," "File selection and bulk actions."
- **Creating a GitHub Release for v1.1.1 before the tag is pushed:** Tag must exist before `gh release create`.
- **Bumping `src/angular/package.json` version without a `package-lock.json` update:** Angular package-lock.json is at `src/angular/package-lock.json`; regenerate after edit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deb package metadata validation | Custom control file validator | `dpkg-deb --build` (validates on build) | dpkg-deb catches malformed control files automatically |
| GitHub Release body formatting | Custom template engine | `gh release create --notes-file body.md` | gh CLI handles markdown rendering |
| Version consistency check | Custom grep script | Planner writes explicit verification task per file | Four files, simple grep suffices |
| ARM64 deb cross-compilation | QEMU + cross-compile setup | Skip — D-07 says amd64 only | Docker covers arm64; deb is amd64-only by decision |

**Key insight:** This phase is docs + CI plumbing. The complexity is editorial (writing correct user-facing changelog) and sequencing (tag before release, test before publish). Avoid over-engineering the packaging step.

---

## Common Pitfalls

### Pitfall 1: Root `package.json` has no `version` field

**What goes wrong:** Planner adds "bump root package.json" as a task, executor adds a `version` field, which may or may not affect anything (version.ts reads from `src/angular/package.json`).
**Why it happens:** D-09 lists `package.json (root)` as a version file, but the actual root `package.json` does not contain a version field — only `devDependencies` and `overrides`. [VERIFIED: file read]
**How to avoid:** Planner should explicitly decide: either add `"version": "1.1.1"` to root `package.json` as a new field for consistency (harmless), or note that the root package.json is not a version carrier and omit it. Either way, make the decision explicit in the plan task.
**Warning signs:** If a task says "update version in root package.json" without noting the field doesn't currently exist.

### Pitfall 2: `pyproject.toml` has version in TWO sections

**What goes wrong:** Only `[project].version` is bumped; `[tool.poetry].version` remains at 1.0.0.
**Why it happens:** pyproject.toml has both `[project]` (PEP 517/hatchling) and `[tool.poetry]` sections, each with a separate `version = "1.0.0"` field. [VERIFIED: file read]
**How to avoid:** Plan must bump both occurrences. Verification step should grep for `1.0.0` in pyproject.toml and confirm zero matches.
**Warning signs:** `grep "1.0.0" src/python/pyproject.toml` returns any results after the bump commit.

### Pitfall 3: `gh release create` on v1.1.1 may conflict with existing tag

**What goes wrong:** If CI runs the release creation step and the tag doesn't exist yet, or the step is run twice.
**Why it happens:** `gh release create` fails if called with a tag that already has a release.
**How to avoid:** Use `gh release create --tag v1.1.1` only once in CI (the new `publish-deb-package` job). The planner must decide which CI job creates the release vs which only uploads assets — avoid double-creation.
**Warning signs:** CI job failing with "release already exists."

### Pitfall 4: v1.1.0 GitHub Release creation may trigger CI

**What goes wrong:** `gh release create v1.1.0` or editing the v1.1.0 release does NOT push a tag (tag already exists), so CI is not triggered. But creating a release via the web UI sometimes surprises people who think it will re-trigger CI.
**Why it happens:** CI is triggered by `git push --tags`, not by GitHub Release creation.
**How to avoid:** Create v1.1.0 GitHub Release independently from local shell or CI — it's a one-time docs step. Tag was pushed 2026-04-20; release creation today is retroactive and safe.
**Warning signs:** Expecting Docker publish to run when the v1.1.0 release is created — it won't.

### Pitfall 5: `gh release upload` requires the release to already exist

**What goes wrong:** The Deb CI job tries to upload `.deb` to a release that doesn't exist yet.
**Why it happens:** `gh release upload v1.1.1 file.deb` fails if `gh release create v1.1.1` hasn't run first.
**How to avoid:** Create the release (with `--draft` if needed) before uploading. Or combine release creation + asset upload in a single job where the release is created before the upload step.
**Warning signs:** `gh release upload` exit code 1 with "release not found."

### Pitfall 6: Deb Python dependency declaration vs runtime reality

**What goes wrong:** `debian/control` declares `Depends: python3 (>= 3.11), ...` but apt-installed python3 may be 3.10 on older Ubuntu targets, or Poetry-managed venv deps are not available system-wide.
**Why it happens:** The app uses Poetry for dependency management; a Deb package can't easily ship a venv.
**How to avoid:** The simplest first-version approach: declare system package deps for runtime tools (lftp, openssh-client, unrar, p7zip-full) and install Python deps via a `postinst` script that runs `pip install -r` or `poetry install`. [ASSUMED: packaging approach — Claude's discretion per CONTEXT.md]
**Warning signs:** App fails at startup because `bottle`, `pexpect`, or `cryptography` not importable.

### Pitfall 7: Changelog comparison links

**What goes wrong:** Comparison link format `[1.1.0]: https://github.com/thejuran/seedsyncarr/compare/v1.0.0...v1.1.0` must be added at the BOTTOM of CHANGELOG.md (after all entries), not inline.
**Why it happens:** Keep a Changelog convention puts the reference-style links at the bottom.
**How to avoid:** Add all comparison links at the bottom of the file in a consistent block.
**Warning signs:** Links appear inline in the version header rather than as reference definitions at EOF.

---

## Code Examples

### v1.1.0 CHANGELOG entry (draft — user-facing, no phase refs)

```markdown
## [1.1.0] - 2026-04-20

### Added

- Per-file selection and shift-range select with a bulk-actions bar for Queue, Stop, Extract, Delete Local, and Delete Remote operations on multiple files.
- Dashboard filter with URL persistence: filter transfers by status (Active, Done, Pending) with filter state preserved in the browser URL for sharing and reload.
- Storage capacity tiles on the dashboard showing local disk and seedbox usage with 80%/95% warning and danger thresholds.
- New navigation bar with live connection status indicator and notification panel.

### Changed

- Transfer table redesigned with search, pagination, status badges, and progress bars.
- Settings page reorganized into card sections with toggle switches and inline AutoQueue pattern management.
- Logs page updated with full-viewport terminal view, log-level filter buttons, and regex search.
- About page updated with version badge and system information table.
- Color theme unified consistently across all pages.
```

Source: [ASSUMED: Changelog content based on v1.1.0 phase scope from CONTEXT.md and commit history review. Exact wording at Claude's discretion per D-02. Review against commit history before committing.]

### v1.1.1 CHANGELOG entry (draft — user-facing, no phase refs)

```markdown
## [1.1.1] - 2026-04-22

### Added

- Optional Fernet encryption at rest for all five secret config fields (`webhook_secret`, `api_token`, `remote_password`, `sonarr_api_key`, `radarr_api_key`). Enable via `enabled = True` in `[Encryption]` section; a keyfile is generated at `<config_dir>/secrets.key` on first enable.

### Fixed

- Bulk-actions bar now shows "Re-Queue from Remote" when the selection includes deleted files, matching the behavior for single-file selections.
- Auto-delete for pack directories waits until all child files are individually confirmed as imported by Sonarr before deleting — prevents premature deletion when Sonarr silently rejects a pack episode.

### Security

- Updated `basic-ftp` transitive dependency to 5.3.0+ to address GHSA-rp42-5vxx-qpwr (DoS, low severity).
```

Source: [ASSUMED: Changelog wording based on FIX-01, FIX-02, SEC-01, SEC-02 requirement descriptions from REQUIREMENTS.md. UAT/TEST/TECH items are internal and do not appear in user-facing changelog per D-02. DOCS-01 is this phase itself and need not be called out.]

### Deb control file

```
Package: seedsyncarr
Version: 1.1.1
Architecture: amd64
Maintainer: thejuran <rnmnqv7fr4@privaterelay.appleid.com>
Description: Fast file syncing from remote seedbox with media library integration
 LFTP-based file synchronization from a remote seedbox to local storage,
 with a web UI, Sonarr/Radarr webhook integration, and auto-delete.
Depends: python3 (>= 3.11), lftp, openssh-client, p7zip-full, unrar, bzip2
Homepage: https://github.com/thejuran/seedsyncarr
```

Source: [ASSUMED: Deb control file format is standard. Exact dependency list and maintainer email are Claude's discretion per CONTEXT.md. Dependency list mirrors Dockerfile apt-get install lines.]

### CI: publish-deb-package job skeleton

```yaml
publish-deb-package:
  name: Publish Deb Package
  if: startsWith(github.ref, 'refs/tags/v')
  runs-on: ubuntu-latest
  needs: [ e2etests-docker-image ]
  steps:
    - name: Set release version
      run: echo "RELEASE_VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_ENV
    - name: Checkout
      uses: actions/checkout@v4
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Log into GHCR
      run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login https://ghcr.io -u ${{ github.actor }} --password-stdin
    - name: Set staging registry
      run: echo "staging_registry=ghcr.io/${GITHUB_REPOSITORY,,}" >> $GITHUB_ENV
    - name: Extract Angular HTML from staging image
      run: |
        docker pull ${{ env.staging_registry }}:${{ github.run_number }} --platform linux/amd64
        CID=$(docker create ${{ env.staging_registry }}:${{ github.run_number }})
        docker cp $CID:/app/html ./deb-staging/usr/lib/seedsyncarr/html
        docker cp $CID:/app/scanfs ./deb-staging/usr/lib/seedsyncarr/scanfs
        docker cp $CID:/app/python ./deb-staging/usr/lib/seedsyncarr/python
        docker rm $CID
    - name: Stage Debian layout
      run: |
        mkdir -p deb-staging/DEBIAN
        cp debian/control deb-staging/DEBIAN/control
        sed -i "s/^Version:.*/Version: ${{ env.RELEASE_VERSION }}/" deb-staging/DEBIAN/control
    - name: Build deb package
      run: dpkg-deb --build deb-staging seedsyncarr_${{ env.RELEASE_VERSION }}_amd64.deb
    - name: Create GitHub Release and upload deb
      run: |
        gh release create v${{ env.RELEASE_VERSION }} \
          --title "v${{ env.RELEASE_VERSION }} — SeedSyncarr" \
          --notes-file release-notes.md
        gh release upload v${{ env.RELEASE_VERSION }} \
          seedsyncarr_${{ env.RELEASE_VERSION }}_amd64.deb
      env:
        GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Source: [ASSUMED: CI job structure based on existing `publish-docker-image` job pattern (ci.yml lines 149-191) and `gh` CLI conventions. Exact steps are Claude's discretion per CONTEXT.md. Docker copy approach for extracting build artifacts is one valid option.]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual release notes | Keep a Changelog format | v1.0.0 | Consistent, parseable format |
| No deb packaging | `.deb` released as GitHub asset | v1.1.1 (this phase) | Users can install without Docker |
| v1.1.0-dev pre-release only | Proper v1.1.0 GitHub Release | This phase | v1.1.0 visible as non-pre-release |

**Existing GitHub Releases:**
- `v1.0.0 — SeedSyncarr` — Live, not pre-release, Latest = true [VERIFIED: gh release list]
- `v1.1.0-dev — UI Redesign (Triggarr Style)` — Pre-release, will no longer be "Latest" after v1.1.0 release is created [VERIFIED: gh release list]
- `v1.1.0` — Tag exists (2026-04-20 commit), no GitHub Release yet [VERIFIED: gh release view v1.1.0 → "release not found"]

---

## Runtime State Inventory

> Not a rename/refactor/migration phase. No runtime state inventory required.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Changelog wording for v1.1.0 (Added/Changed items) | Code Examples | Wrong if phase scope misidentified; verify against commit history v1.0.0..v1.1.0 |
| A2 | Deb control file dependency list matches runtime needs | Code Examples | App startup failure if deps missing on target system |
| A3 | CI Deb job approach (docker cp to extract artifacts from staging image) | Code Examples | May need alternative if staging image architecture doesn't match amd64 extraction |
| A4 | `postinst` script needed for Python pip deps | Common Pitfalls | Deb install may succeed but app fails to start without pip deps |
| A5 | Root `package.json` intentionally has no `version` field (D-09 lists it but field is absent) | Standard Stack / Pitfalls | If planner adds version field, that's a new addition — acceptable but not pre-existing |
| A6 | Phase 81 (SEC-02) is complete for release purposes despite no VERIFICATION.md | Summary | If Phase 81 CI fails, v1.1.1 release cannot proceed |

---

## Open Questions

1. **Root package.json version field**
   - What we know: Root `package.json` has no `version` field — only `devDependencies` and `overrides`.
   - What's unclear: D-09 says to bump it, but there's nothing to bump. Should we add the field, or acknowledge it's not a version carrier?
   - Recommendation: Add `"version": "1.1.1"` as a new field for consistency; it has no runtime impact since `version.ts` reads from `src/angular/package.json`.

2. **Phase 81 verification gate**
   - What we know: Phase 81 has implementation + review/fix committed. No `VERIFICATION.md` exists.
   - What's unclear: Is Phase 81 "done enough" to release, or should the verifier pass happen first?
   - Recommendation: The planner should include Phase 81 verification as a prerequisite in Wave 0 or treat it as a pre-condition to document. The user context implies 81 is done (context was gathered for 82 immediately after 81 review/fix).

3. **Deb Python dependency management**
   - What we know: The app uses Poetry/pip; Deb doesn't ship a venv natively.
   - What's unclear: Should the deb include a `postinst` that pip-installs, or bundle a virtualenv, or declare system packages as deps?
   - Recommendation: For v1.1.1 simplicity, declare system packages (lftp, python3) and add a `postinst` that runs `pip3 install bottle paste patool pexpect pytz requests tblib timeout-decorator cryptography` into a fixed venv path. This matches the Docker approach pattern.

4. **v1.1.0-dev pre-release: delete or keep?**
   - What we know: Claude's discretion per CONTEXT.md.
   - What's unclear: Does the v1.1.0-dev pre-release confuse users once v1.1.0 proper exists?
   - Recommendation: Delete the `v1.1.0-dev` pre-release after creating the `v1.1.0` proper Release. It served its purpose as a dev preview; the proper release supersedes it. Use `gh release delete v1.1.0-dev --cleanup-tag=false` (preserve the tag itself if desired, but the dev tag can also be deleted since v1.1.0 supersedes it).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI | GitHub Release creation | ✓ (CI) | 2.86.0 (local) | — (native in Actions) |
| `dpkg-deb` | Deb build | ✓ (ubuntu-latest) | built-in | — |
| `docker` | Extract build artifacts | ✓ (CI) | Actions runner | — |
| `git tag` | v1.1.1 tag creation | ✓ | 2.x | — |

All required tools are available in the CI environment. [VERIFIED: gh --version locally; dpkg-deb is standard ubuntu-latest]

---

## Validation Architecture

> nyquist_validation not set in config.json — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual verification + CI artifact checks |
| Config file | `.github/workflows/ci.yml` |
| Quick run command | `gh release view v1.1.0 --repo thejuran/seedsyncarr` |
| Full suite command | CI green after `git push --tags v1.1.1` |

This phase has no automated unit tests — DOCS-01 is verified by observable system state (release exists, changelog has entries, CI green).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 (part 1) | CHANGELOG.md has v1.1.0 entry | Smoke | `grep "## \[1.1.0\]" CHANGELOG.md` | ❌ Wave 0 (entry written this phase) |
| DOCS-01 (part 2) | GitHub Release v1.1.0 exists | Manual/API | `gh release view v1.1.0 --repo thejuran/seedsyncarr` | ❌ Wave 0 |
| SC-3 | CHANGELOG.md has v1.1.1 entry | Smoke | `grep "## \[1.1.1\]" CHANGELOG.md` | ❌ Wave 0 |
| SC-4 | Version strings all at 1.1.1 | Smoke | `grep -r "version" package.json src/angular/package.json src/python/pyproject.toml \| grep "1.1.1"` | ❌ Wave 0 |
| SC-5 | v1.1.1 tag + GitHub Release + .deb asset exist | Manual | `gh release view v1.1.1` + `gh release download v1.1.1` | ❌ Wave 0 (CI run creates) |

### Sampling Rate
- **Per task commit:** `grep "## \[1.1" CHANGELOG.md && grep "1.1.1" src/angular/package.json src/python/pyproject.toml`
- **Per wave merge:** `gh release view v1.1.0` (after wave 1); CI green (after v1.1.1 tag push)
- **Phase gate:** All 5 success criteria TRUE before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] No test infrastructure gaps — this phase has no code; verification is state-based (release exists, file contents)
- [ ] Pre-condition: Phase 81 `VERIFICATION.md` should exist before Phase 82 begins (or explicitly waived)

---

## Security Domain

> security_enforcement not set in config.json — treated as enabled.

This phase makes no changes to application security controls. The security-relevant observation is:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth changes |
| V5 Input Validation | No | No input handling changed |
| V6 Cryptography | No | No new crypto (SEC-02 shipped in Phase 81) |

The `.deb` package is a distribution artifact. Security considerations for the deb:
- `debian/control` permissions: `dpkg-deb` enforces correct DEBIAN/ permissions automatically
- `secrets.key` is generated at runtime by the app, not shipped in the package — no secrets in the artifact [VERIFIED: Phase 81 implementation reviewed]
- GitHub Release asset (`.deb`) is signed by GitHub's infrastructure; no additional signing required for v1.1.1

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] — `CHANGELOG.md`, `package.json`, `src/angular/package.json`, `src/python/pyproject.toml` read directly
- [VERIFIED: codebase] — `.github/workflows/ci.yml` read directly (lines 1-254)
- [VERIFIED: codebase] — `src/docker/build/docker-image/Dockerfile` read (all stages)
- [VERIFIED: codebase] — `Makefile` read directly
- [VERIFIED: gh CLI] — `gh release list` confirms v1.0.0 (Latest), v1.1.0-dev (Pre-release), v1.1.0 tag exists with no Release
- [VERIFIED: git] — `git tag --list` confirms tags: v1.0.0, v1.1.0, v1.1.0-dev
- [VERIFIED: git] — commit history v1.0.0..v1.1.0 reviewed for changelog content

### Secondary (MEDIUM confidence)
- [CITED: keepachangelog.com] — Keep a Changelog format (established by existing v1.0.0 entry)
- [CITED: GitHub Actions documentation] — `gh` CLI is pre-installed on ubuntu-latest runners; `dpkg-deb` available on ubuntu-latest

### Tertiary (LOW confidence / ASSUMED)
- Changelog wording (user-facing descriptions) — derived from commit history + requirement descriptions, editorial
- Deb package content and `postinst` approach — standard Debian packaging patterns, not verified against a working build

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools confirmed in CI and/or local environment
- Architecture: HIGH — CI workflow fully read; tag/release flow confirmed from existing jobs
- Pitfalls: HIGH — discovered from direct file inspection (root package.json missing version, pyproject.toml dual version fields)
- Changelog content: MEDIUM — derived from commit history + REQUIREMENTS.md; exact wording is editorial

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (stable domain; Keep a Changelog format and gh CLI are stable)
