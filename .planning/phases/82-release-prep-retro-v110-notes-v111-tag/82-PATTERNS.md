# Phase 82: Release Prep (Retro v1.1.0 Notes + v1.1.1 Tag) - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 6 new/modified files
**Analogs found:** 5 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `CHANGELOG.md` | config (docs) | transform | `CHANGELOG.md` (existing v1.0.0 entry) | exact — same file, extend pattern |
| `src/angular/package.json` | config | transform | `src/angular/package.json` (self) | exact — field edit only |
| `src/python/pyproject.toml` | config | transform | `src/python/pyproject.toml` (self) | exact — two field edits |
| `package.json` (root) | config | transform | `package.json` (self) | exact — field addition (no `version` exists yet) |
| `debian/DEBIAN/control` | config | — | none (new infrastructure) | no analog |
| `.github/workflows/ci.yml` | config (CI) | event-driven | `.github/workflows/ci.yml` `publish-docker-image` job (lines 149–191) | exact — same job shape and trigger |

---

## Pattern Assignments

### `CHANGELOG.md` (config/docs, transform)

**Analog:** `CHANGELOG.md` — existing v1.0.0 entry (lines 1–22)

**Header and preamble pattern** (lines 1–6):
```markdown
# Changelog

All notable changes to SeedSyncarr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).
```

**Version entry pattern** (lines 7–21):
```markdown
## [1.0.0] - 2026-04-08

### Added

- LFTP-based file synchronization from remote seedbox to local server
- Web UI for monitoring and controlling transfers with real-time status via SSE
- Sonarr and Radarr webhook integration for automated media imports with auto-delete
- AutoQueue with pattern-based file selection
- Automatic file extraction after sync completes
- Docker images for amd64 and arm64
- Dark mode UI with Deep Moss and Amber palette
- API token authentication (Bearer tokens)
- Security hardening: HMAC webhooks, CSP, DNS rebinding prevention, credential redaction
```

**Comparison link pattern** (line 22 — placed at bottom of file):
```markdown
[1.0.0]: https://github.com/thejuran/seedsyncarr/releases/tag/v1.0.0
```

**Copy rules for new entries:**
- v1.1.0 entry goes above v1.0.0 entry (newest first)
- v1.1.1 entry goes above v1.1.0 entry
- Sections used: `### Added`, `### Changed`, `### Fixed`, `### Security` — only include sections that have entries
- Comparison links go at the very bottom of the file, after all entries, as reference-style link definitions
- v1.1.0 link format: `[1.1.0]: https://github.com/thejuran/seedsyncarr/compare/v1.0.0...v1.1.0`
- v1.1.1 link format: `[1.1.1]: https://github.com/thejuran/seedsyncarr/compare/v1.1.0...v1.1.1`
- Existing `[1.0.0]` link stays; update its format to comparison-style if desired: `[1.0.0]: https://github.com/thejuran/seedsyncarr/releases/tag/v1.0.0` (keep as-is, it's the initial release)

---

### `src/angular/package.json` (config, transform)

**Analog:** `src/angular/package.json` (self) — line 3

**Current version field** (line 3):
```json
"version": "1.0.0",
```

**Target state:**
```json
"version": "1.1.1",
```

**Warning:** After editing `src/angular/package.json`, the `src/angular/package-lock.json` must also be updated. Run `cd src/angular && npm install` (or `npm ci` to verify only) after the version bump to regenerate `package-lock.json` with the new version string.

---

### `src/python/pyproject.toml` (config, transform)

**Analog:** `src/python/pyproject.toml` (self) — lines 7 and 45

**Two version fields — BOTH must be bumped:**

Field 1 — `[project]` section (line 7):
```toml
[project]
name = "seedsyncarr"
version = "1.0.0"
```

Field 2 — `[tool.poetry]` section (line 44–45):
```toml
[tool.poetry]
name = "seedsyncarr"
version = "1.0.0"
```

**Target state for both:**
```toml
version = "1.1.1"
```

**Verification command:** `grep "1.0.0" src/python/pyproject.toml` must return zero matches after the bump.

---

### `package.json` (root) (config, transform)

**Analog:** `package.json` (self) — lines 1–8

**Current state — NO `version` field:**
```json
{
  "devDependencies": {
    "puppeteer": "^24.40.0"
  },
  "overrides": {
    "basic-ftp": "^5.3.0"
  }
}
```

**Decision required (planner must resolve explicitly):** D-09 lists root `package.json` as a version file, but the field does not currently exist. Two options:
1. Add `"version": "1.1.1"` as the first key — harmless since `version.ts` reads from `src/angular/package.json`, not root.
2. Omit — treat root `package.json` as not a version carrier and note it in the commit message.

**Recommended pattern (option 1):**
```json
{
  "version": "1.1.1",
  "devDependencies": {
    "puppeteer": "^24.40.0"
  },
  "overrides": {
    "basic-ftp": "^5.3.0"
  }
}
```

---

### `debian/DEBIAN/control` (config, no analog)

**No analog in codebase** — `debian/` directory does not exist yet.

**Standard Debian control file format** (from RESEARCH.md Pattern 4 + Debian policy):
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

**Control file rules (Debian policy):**
- `Description:` — first line is short description; continuation lines start with a single space
- `Depends:` — comma-separated list of package names with optional version constraints
- `Version:` field will be overwritten by `sed` in the CI job so it stays in sync with `$RELEASE_VERSION`
- File must be placed at `debian/DEBIAN/control` (note: `DEBIAN` directory is uppercase — dpkg-deb requirement)
- No trailing newline issues: file must end with a newline character

**Dependency rationale** (mirrors `src/docker/build/docker-image/Dockerfile` apt-get installs):
- `lftp` — core sync tool
- `openssh-client` — SSH tunnel / SFTP support
- `p7zip-full` — archive extraction
- `unrar` — RAR extraction
- `bzip2` — compression support
- `python3 (>= 3.11)` — runtime; app also needs pip-installed packages (see postinst consideration in RESEARCH.md Pitfall 6)

---

### `.github/workflows/ci.yml` — new `publish-deb-package` job (config/CI, event-driven)

**Analog:** `.github/workflows/ci.yml` `publish-docker-image` job — lines 149–191

**Trigger + job-level pattern** (lines 149–153 — copy exactly, change job name):
```yaml
publish-deb-package:
  name: Publish Deb Package
  if: startsWith(github.ref, 'refs/tags/v')
  runs-on: ubuntu-latest
  needs: [ e2etests-docker-image ]
```

**Release version env variable step** (lines 155–156 — identical pattern):
```yaml
    - name: Set release version
      run: echo "RELEASE_VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_ENV
```

**Checkout step** (lines 157–158 — identical):
```yaml
    - name: Checkout
      uses: actions/checkout@v4
```

**Docker Buildx setup** (lines 162–169 — same actions, but no QEMU needed for amd64-only deb):
```yaml
    - name: Set up Docker Buildx
      id: buildx
      uses: docker/setup-buildx-action@v3
```

**GHCR login step** (lines 170–172 — identical):
```yaml
    - name: Log into GitHub Container Registry
      run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login https://ghcr.io -u ${{ github.actor }} --password-stdin
```

**Staging registry env step** (lines 173–175 — identical):
```yaml
    - name: Set staging registry env variable
      run: echo "staging_registry=ghcr.io/${GITHUB_REPOSITORY,,}" >> $GITHUB_ENV
```

**Deb-specific steps** (new — no analog; from RESEARCH.md Pattern 3 / Code Examples):
```yaml
    - name: Extract artifacts from staging image
      run: |
        docker pull ${{ env.staging_registry }}:${{ github.run_number }} --platform linux/amd64
        CID=$(docker create ${{ env.staging_registry }}:${{ github.run_number }})
        mkdir -p deb-staging/usr/lib/seedsyncarr
        docker cp $CID:/app/html ./deb-staging/usr/lib/seedsyncarr/html
        docker cp $CID:/app/scanfs ./deb-staging/usr/lib/seedsyncarr/scanfs
        docker cp $CID:/app/python ./deb-staging/usr/lib/seedsyncarr/python
        docker rm $CID

    - name: Stage Debian layout
      run: |
        mkdir -p deb-staging/DEBIAN
        cp debian/DEBIAN/control deb-staging/DEBIAN/control
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

**Placement in ci.yml:** Insert the new job block immediately after `publish-docker-image` (after line 191), before `publish-docker-image-dev` (line 192). Keep the same indentation level as sibling jobs.

**Note on release-notes.md:** The CI job references `release-notes.md` as a `--notes-file`. The planner must decide whether this file is committed to the repo (containing the v1.1.1 GitHub Release body from D-03) or generated inline in the CI step. Committed file is simpler and avoids heredoc quoting issues.

---

## Shared Patterns

### CI Tag-Push Guard
**Source:** `.github/workflows/ci.yml` line 151
**Apply to:** `publish-deb-package` job (same as `publish-docker-image`)
```yaml
if: startsWith(github.ref, 'refs/tags/v')
```

### CI Release Version Extraction
**Source:** `.github/workflows/ci.yml` line 156
**Apply to:** `publish-deb-package` job
```yaml
run: echo "RELEASE_VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_ENV
```

### CI GHCR Login
**Source:** `.github/workflows/ci.yml` lines 101, 137, 171
**Apply to:** `publish-deb-package` job (amd64 docker pull to extract artifacts)
```yaml
run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login https://ghcr.io -u ${{ github.actor }} --password-stdin
```

### Keep a Changelog Entry Format
**Source:** `CHANGELOG.md` lines 7–21
**Apply to:** Both v1.1.0 and v1.1.1 CHANGELOG entries
- Blank line after version header
- Section headers: `### Added`, `### Changed`, `### Fixed`, `### Security`
- Blank line after each section header, before list items
- List items are user-facing sentences, not developer/implementation detail
- Newest release at top of file

### GitHub Release Title Format
**Source:** `gh release list` output (v1.0.0 title: `v1.0.0 — SeedSyncarr`)
**Apply to:** v1.1.0 GitHub Release + v1.1.1 GitHub Release
```
v1.1.0 — SeedSyncarr
v1.1.1 — SeedSyncarr
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `debian/DEBIAN/control` | config | — | No Debian packaging infrastructure exists in the codebase; `debian/` directory absent |

---

## Key Pitfall Reminders (for planner)

1. **Root `package.json` has no `version` field** — planner must explicitly decide to add it or skip it; do not write "bump existing field."
2. **`pyproject.toml` has two `version` fields** — both `[project].version` (line 7) and `[tool.poetry].version` (line 45) must be updated.
3. **`publish-deb-package` job creates the v1.1.1 GitHub Release** — the `publish-docker-image` job must NOT also create the release (it currently doesn't, so no conflict). Only one job runs `gh release create`.
4. **v1.1.0 GitHub Release is retroactive** — creating it does NOT re-trigger CI (CI is tag-push triggered, not release-creation triggered). Create it via local `gh release create --tag v1.1.0`.
5. **`gh release upload` requires the release to exist first** — combine `gh release create` + `gh release upload` in a single CI step, in that order.
6. **Changelog comparison links** — placed at EOF as reference-style link definitions, not inline in headers.
7. **`src/angular/package-lock.json` update** — required after bumping `src/angular/package.json`; run `cd src/angular && npm install`.

---

## Metadata

**Analog search scope:** `CHANGELOG.md`, `.github/workflows/ci.yml`, `package.json`, `src/angular/package.json`, `src/python/pyproject.toml`, `Makefile`
**Files scanned:** 7
**Pattern extraction date:** 2026-04-22
