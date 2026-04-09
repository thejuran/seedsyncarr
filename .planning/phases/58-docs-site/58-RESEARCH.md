# Phase 58: Docs Site — Research

**Researched:** 2026-04-08
**Domain:** MkDocs Material, GitHub Pages (peaceiris/actions-gh-pages), documentation authoring
**Confidence:** HIGH

---

## Summary

Phase 58 is a documentation authoring phase. The infrastructure is fully pre-built: `mkdocs.yml`
exists at `src/python/mkdocs.yml`, the `publish-docs` CI job exists in `.github/workflows/ci.yml`,
and `mkdocs>=1.6.1` plus `mkdocs-material>=9.7.1` are already in `pyproject.toml` dev dependencies
(verified locally: mkdocs 1.6.1, mkdocs-material 9.7.1 installed). The gap is entirely in content:
the `docs/` directory does not exist under `src/python/`, so `mkdocs build` currently aborts with
"The path '.../src/python/docs' isn't an existing directory."

The only code work is: (1) create `src/python/docs/` with the required page files, (2) add image
assets so the MkDocs logo/favicon references don't break, (3) update the README's docs link from
the placeholder `…/wiki` to `https://thejuran.github.io/seedsyncarr`, and (4) verify the
`publish-docs` CI job runs clean on push to main.

GitHub Pages deployment uses `peaceiris/actions-gh-pages@v4` pushing to the `gh-pages` branch.
The workflow runs on push to `main` or on any version tag. The CI workflow has `contents: write`
permissions (required by peaceiris to push the gh-pages branch). [VERIFIED: direct file inspection
of `.github/workflows/ci.yml`]

**Primary recommendation:** Create five Markdown pages under `src/python/docs/`, copy the favicon
asset, confirm build is clean locally, then push — the existing CI job handles deployment.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRES-04 | MkDocs docs site live at `thejuran.github.io/seedsyncarr` | CI `publish-docs` job already wired; needs docs/ content to build |
| PRES-05 | Docs include installation guide, configuration reference, FAQ/troubleshooting | Requires install.md, config-reference.md (or merged into install.md), faq.md |
| PRES-06 | Docs include Sonarr/Radarr setup guide as flagship page | Requires dedicated arr-setup.md with step-by-step webhook instructions |
</phase_requirements>

---

## Current State Audit

[VERIFIED: direct file inspection, `python3 -m mkdocs build` invocation]

| Item | Current State | Gap |
|------|--------------|-----|
| `src/python/mkdocs.yml` | Exists; fully configured with Material theme, nav, extensions, site_url | No changes needed |
| `src/python/docs/` directory | Does not exist — build aborts | Must create with all nav pages |
| `mkdocs` + `mkdocs-material` installed | 1.6.1 / 9.7.1 — both present locally and in pyproject.toml | No install work needed |
| `publish-docs` CI job | Exists; runs on push to main or tag; uses peaceiris/actions-gh-pages@v4 | Will work once docs/ content exists |
| Logo asset `images/logo.png` | mkdocs.yml references `images/logo.png` — not present in docs/ | Must add; can copy favicon.png as placeholder or omit logo key |
| Favicon asset `images/favicon.png` | mkdocs.yml references `images/favicon.png` — not present in docs/ | Must copy from `src/angular/src/assets/favicon.png` |
| README docs link | Points to `https://github.com/thejuran/seedsyncarr/wiki` (placeholder) | Update to `https://thejuran.github.io/seedsyncarr` |
| GitHub Pages branch | `gh-pages` branch created by peaceiris on first successful run | No manual setup needed; will be created on first push |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs | 1.6.1 | Static site generator from Markdown | Already in pyproject.toml dev deps |
| mkdocs-material | 9.7.1 | Material Design theme with admonitions, tabs, code copy | Already in pyproject.toml; mkdocs.yml already configured |

[VERIFIED: `pip3 show mkdocs-material` returns Version: 9.7.1; `python3 -m mkdocs --version` returns 1.6.1]

### CI Deployment

| Component | Version | Purpose |
|-----------|---------|---------|
| peaceiris/actions-gh-pages | v4 | Pushes built `site/` to `gh-pages` branch | 

[VERIFIED: `.github/workflows/ci.yml` lines 256-259]

### No New Dependencies

This phase introduces zero new Python or Node.js dependencies. All tooling is already present.

**Local build command:**
```bash
cd src/python && python3 -m mkdocs build --site-dir ../../site
```

**Local serve command (dev):**
```bash
cd src/python && python3 -m mkdocs serve
```

---

## Architecture Patterns

### Required Directory Structure

```
src/python/
├── mkdocs.yml           # Already exists — no changes needed
└── docs/
    ├── index.md         # Home page (nav: Home)
    ├── install.md       # Installation guide (nav: Installation)
    ├── configuration.md # Config reference (nav: Configuration) — rename from usage.md
    ├── arr-setup.md     # Sonarr/Radarr setup (nav: Sonarr & Radarr)
    ├── faq.md           # FAQ / Troubleshooting (nav: FAQ)
    ├── changelog.md     # Symlink or copy of /CHANGELOG.md
    └── images/
        ├── favicon.png  # Copy of src/angular/src/assets/favicon.png
        └── logo.png     # Same favicon or placeholder — required by mkdocs.yml
```

### Nav Configuration (existing mkdocs.yml)

Current nav in `mkdocs.yml`:
```yaml
nav:
  - Home: index.md
  - Installation: install.md
  - Usage: usage.md
  - FAQ: faq.md
  - Changelog: changelog.md
```

The existing nav uses `usage.md`. Phase 58 introduces a dedicated `arr-setup.md` page, which
means the nav must be updated. Recommended updated nav:

```yaml
nav:
  - Home: index.md
  - Installation: install.md
  - Configuration: configuration.md
  - Sonarr & Radarr: arr-setup.md
  - FAQ: faq.md
  - Changelog: changelog.md
```

This requires renaming the planned `usage.md` to `configuration.md` and adding `arr-setup.md`.

### Page Content Map

**index.md** — Home
- Brief value prop (one sentence)
- Feature bullets (LFTP-based sync, Web UI, Sonarr/Radarr integration, auto-extraction, AutoQueue)
- Screenshot embed (`images/screenshot.png` — use `doc/images/screenshot-dashboard.png` from repo root)
- Quick Start Docker Compose block (same as README)
- Links to Installation, arr-setup

**install.md** — Installation
- Docker Compose (recommended path) — full compose.yml with volume mounts
- `docker run` one-liner
- Post-install: open http://localhost:8800
- Mention default port 8800 (from Config.Web.port)
- Note: no Debian package install path exists in v1.0.0 — Docker is the only supported method

**configuration.md** — Configuration Reference
- All sections from `Config` class (source of truth: `src/python/common/config.py`)
- Table per section: field name, type, default, description
- Sections: General, Lftp, Controller, Web, AutoQueue, Sonarr, Radarr, AutoDelete
- Stored at: `~/.seedsyncarr/settings.cfg` (INI format)

**arr-setup.md** — Sonarr & Radarr Setup (flagship page per PRES-06)
- Step-by-step Sonarr webhook setup
- Step-by-step Radarr webhook setup
- Webhook URL format: `http://<seedsyncarr-host>:8800/server/webhook/sonarr`
- Webhook URL format: `http://<seedsyncarr-host>:8800/server/webhook/radarr`
- Event type: "On Import" (Download event in *arr webhook payload)
- Optional HMAC signing: `webhook_secret` in General config + `X-Webhook-Signature` header
- Test button in *arr sends "Test" event — SeedSyncarr returns 200 "Test OK"

**faq.md** — FAQ & Troubleshooting
- Minimum 3 entries required (PRES-05 success criteria)
- Entry 1: "Connection refused" — check SeedSyncarr is running, port 8800 reachable
- Entry 2: "HMAC mismatch / webhook returns 401" — webhook_secret must match between SeedSyncarr and *arr HMAC secret field
- Entry 3: "arm64 test caveat" — Python unit tests skip `rar` extraction on arm64; Docker image is fully functional

**changelog.md** — Changelog
- Can be a simple include/copy of root `CHANGELOG.md` content, or a symlink (MkDocs follows symlinks)
- Simplest: copy the CHANGELOG.md content verbatim

---

## Configuration Reference Source of Truth

[VERIFIED: `src/python/common/config.py` direct inspection]

All configuration fields come from the `Config` class. Complete field inventory:

### [General]
| Field | Type | Description |
|-------|------|-------------|
| debug | bool | Enable debug logging |
| verbose | bool | Enable verbose logging |
| webhook_secret | str | HMAC secret for webhook verification (empty = no verification) |
| api_token | str | Bearer token for API auth (empty = no auth, backward compat) |
| allowed_hostname | str | Restrict Host header (empty = allow any, for Docker compat) |

### [Lftp]
| Field | Type | Description |
|-------|------|-------------|
| remote_address | str | SSH hostname of seedbox |
| remote_username | str | SSH username |
| remote_password | str | SSH password |
| remote_port | int | SSH port (positive integer) |
| remote_path | str | Path on remote to sync from |
| local_path | str | Local path to sync to |
| remote_path_to_scan_script | str | Path to scan script on remote |
| use_ssh_key | bool | Use SSH key auth instead of password |
| num_max_parallel_downloads | int | Max concurrent downloads |
| num_max_parallel_files_per_download | int | Max parallel files per download |
| num_max_connections_per_root_file | int | Connections per root file |
| num_max_connections_per_dir_file | int | Connections per directory file |
| num_max_total_connections | int | Total max connections (0 = unlimited) |
| use_temp_file | bool | Use .lftp temp files during download |

### [Controller]
| Field | Type | Description |
|-------|------|-------------|
| interval_ms_remote_scan | int | Remote scan interval in ms |
| interval_ms_local_scan | int | Local scan interval in ms |
| interval_ms_downloading_scan | int | Downloading scan interval in ms |
| extract_path | str | Path for extracted archives |
| use_local_path_as_extract_path | bool | Use local_path as extract destination |
| max_tracked_files | int | Max files tracked in memory |

### [Web]
| Field | Type | Description |
|-------|------|-------------|
| port | int | HTTP port (default: 8800) |

### [AutoQueue]
| Field | Type | Description |
|-------|------|-------------|
| enabled | bool | Enable AutoQueue |
| patterns_only | bool | Only queue files matching patterns |
| auto_extract | bool | Auto-extract on queue |

### [Sonarr]
| Field | Type | Description |
|-------|------|-------------|
| enabled | bool | Enable Sonarr integration |
| sonarr_url | str | Sonarr base URL (e.g. http://sonarr:8989) |
| sonarr_api_key | str | Sonarr API key |

### [Radarr]
| Field | Type | Description |
|-------|------|-------------|
| enabled | bool | Enable Radarr integration |
| radarr_url | str | Radarr base URL (e.g. http://radarr:7878) |
| radarr_api_key | str | Radarr API key |

### [AutoDelete]
| Field | Type | Description |
|-------|------|-------------|
| enabled | bool | Enable auto-delete after import |
| dry_run | bool | Log deletions without executing |
| delay_seconds | int | Seconds to wait before deleting |

---

## Webhook Integration Details

[VERIFIED: `src/python/web/handler/webhook.py` direct inspection]

Critical facts for the arr-setup.md page:

- **Sonarr endpoint:** `POST /server/webhook/sonarr`
- **Radarr endpoint:** `POST /server/webhook/radarr`
- **Event filtering:** Only `Download` events are processed; `Test` events return 200 OK; all other event types are silently ignored
- **Title extraction (Sonarr):** `episodeFile.sourcePath` (basename) → `release.releaseTitle` → `series.title`
- **Title extraction (Radarr):** `movieFile.sourcePath` (basename) → `release.releaseTitle` → `movie.title`
- **HMAC auth:** `X-Webhook-Signature` header with HMAC-SHA256 hex digest; disabled when `webhook_secret` is empty
- **Payload size limit:** 1 MB maximum
- **Webhook paths are exempt from Bearer token auth** — HMAC is the webhook auth mechanism

---

## Debian Package Note

[VERIFIED: Makefile inspection, Dockerfile inspection, no `.deb` packaging artifacts found]

The phase success criteria mentions "Docker Compose and Debian package install paths." However,
no Debian packaging exists in the repository — there is no `.deb` build target, no DEBIAN/
control files, and no install scripts for apt-based installation. The requirements text in
REQUIREMENTS.md (PRES-05) says "installation guide covering Docker Compose and Debian package
install paths" but the project does not ship a Debian package in v1.0.0.

**Decision required:** The install.md page should document Docker (the only supported install
method). The PRES-05 success criteria text includes "Debian package install paths" — the planner
should note this as a gap and document Docker only, or interpret "Debian package" as the
pip-install path (since pyproject.toml exists with `pip install` support).

**Recommendation:** Document Docker Compose as primary, `pip install` as secondary (for bare-metal
users), and omit a Debian .deb section since none exists. This satisfies the intent of PRES-05
without fabricating packaging that doesn't exist.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Docs site generator | Custom static HTML | MkDocs (already configured) |
| Docs deployment | Manual `git push` to gh-pages | peaceiris/actions-gh-pages (already wired in CI) |
| Theme/styling | Custom CSS | MkDocs Material (already in mkdocs.yml) |
| Code copy buttons | JavaScript snippet | `content.code.copy` feature flag (already in mkdocs.yml) |
| Search | Client-side search script | `search` plugin (already in mkdocs.yml) |

---

## Common Pitfalls

### Pitfall 1: Missing Logo/Favicon Causes Build Warning or Error
**What goes wrong:** `mkdocs.yml` references `images/logo.png` and `images/favicon.png`. If
`docs/images/` does not exist or lacks these files, MkDocs 1.6 will emit warnings and the
favicon will be missing on the live site.
**How to avoid:** Copy `src/angular/src/assets/favicon.png` to `src/python/docs/images/favicon.png`
and also to `src/python/docs/images/logo.png` (MkDocs resizes logos automatically).

### Pitfall 2: Nav References Nonexistent Files
**What goes wrong:** If `nav:` in mkdocs.yml lists a file that doesn't exist in docs/, the build
aborts. The current nav lists `usage.md` — if the phase creates `configuration.md` and `arr-setup.md`
instead, mkdocs.yml must be updated.
**How to avoid:** Update mkdocs.yml nav in the same commit as creating the docs/ files.

### Pitfall 3: GitHub Pages Not Enabled on New Repo
**What goes wrong:** `peaceiris/actions-gh-pages` can push the `gh-pages` branch but GitHub Pages
may not be enabled in repository Settings > Pages. If the setting is "None" (disabled), the branch
push succeeds but `thejuran.github.io/seedsyncarr` returns 404.
**How to avoid:** After first CI run, verify `Settings > Pages > Branch = gh-pages`. Can be set
via `gh api` if needed.

### Pitfall 4: `edit_uri` Branch Mismatch
**What goes wrong:** `mkdocs.yml` has `edit_uri: edit/master/src/python/docs/` — the repo uses
`main`, not `master`. Edit links in Material theme will 404.
**How to avoid:** Change `edit_uri` to `edit/main/src/python/docs/` or set `edit_uri: ""` to
disable edit links.

### Pitfall 5: Changelog File Path
**What goes wrong:** `CHANGELOG.md` is at the repo root; `docs/changelog.md` is inside docs/.
MkDocs does not follow symlinks from outside the docs_dir by default.
**How to avoid:** Copy CHANGELOG.md content into `docs/changelog.md` directly (not a symlink).
This is simple and keeps the build self-contained.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| mkdocs | Local build test | ✓ | 1.6.1 | — |
| mkdocs-material | Local build test | ✓ | 9.7.1 | — |
| Python 3.x | mkdocs invocation | ✓ | 3.9 (local) / 3.11 (CI) | — |
| GitHub Pages (gh-pages branch) | Live site | Created on first CI push | — | Enable in repo Settings |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual / local mkdocs build |
| Config file | `src/python/mkdocs.yml` |
| Quick run command | `cd src/python && python3 -m mkdocs build --strict --site-dir /tmp/mkdocs-site` |
| Full suite command | Same (build is the only test; CI deploys) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRES-04 | MkDocs build completes without error | smoke | `cd src/python && python3 -m mkdocs build --strict` | ❌ Wave 0: create docs/ |
| PRES-04 | Site is live at thejuran.github.io/seedsyncarr | manual | push to main, check URL | N/A |
| PRES-05 | install.md, configuration.md, faq.md exist and build | smoke | included in build --strict | ❌ Wave 0: create pages |
| PRES-06 | arr-setup.md exists with Sonarr + Radarr steps | smoke | included in build --strict | ❌ Wave 0: create page |

### Sampling Rate
- **Per task commit:** `cd src/python && python3 -m mkdocs build --strict --site-dir /tmp/mkdocs-test`
- **Per wave merge:** same
- **Phase gate:** Build passes `--strict` and site loads at thejuran.github.io/seedsyncarr before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/python/docs/` directory — does not exist; create with all nav pages
- [ ] `src/python/docs/images/` — does not exist; copy favicon asset

---

## Security Domain

This phase is documentation-only. No new code, no new endpoints, no auth changes.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | — |
| V6 Cryptography | no | — |

No threat patterns applicable to a static documentation site served by GitHub Pages.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GitHub Pages is not yet enabled for thejuran/seedsyncarr (new repo) | Current State Audit | If already enabled, no action needed — no risk |
| A2 | `doc/images/screenshot-dashboard.png` exists and is suitable for embedding in docs | Page Content Map | If it was deleted or is low quality, need a different screenshot path |

---

## Open Questions

1. **Debian package install path in PRES-05 success criteria**
   - What we know: PRES-05 says "Docker Compose and Debian package install paths"; no Debian packaging exists
   - What's unclear: Is this a requirements error (should say pip install) or a feature not yet built?
   - Recommendation: Document Docker Compose + pip install as the two paths; note in plan that `.deb` packaging is not in scope for v1.0.0

2. **Screenshot on index.md**
   - What we know: `doc/images/screenshot-dashboard.png` exists at repo root; MkDocs serves files from `docs/`
   - What's unclear: Should the screenshot be copied into `docs/images/` or referenced with a relative path to the root?
   - Recommendation: Copy `doc/images/screenshot-dashboard.png` into `docs/images/screenshot-dashboard.png` so MkDocs can serve it

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection of `src/python/mkdocs.yml` — theme, nav, extensions, site_url, edit_uri
- Direct file inspection of `.github/workflows/ci.yml` — publish-docs job, peaceiris/actions-gh-pages@v4
- Direct file inspection of `src/python/common/config.py` — all config sections and fields
- Direct file inspection of `src/python/web/handler/webhook.py` — webhook endpoints, HMAC logic, event filtering
- `python3 -m mkdocs build` invocation — confirmed docs/ is missing and build fails
- `pip3 show mkdocs-material` — confirmed 9.7.1 installed

### Secondary (MEDIUM confidence)
- MkDocs Material 9.7.1 feature set (`--strict` flag behavior, symlink handling, logo resize) [ASSUMED: from training data on mkdocs-material 9.x; behavior is stable across 9.x]

---

## Metadata

**Confidence breakdown:**
- Current state audit: HIGH — all gaps verified by direct file inspection and build invocation
- Standard stack: HIGH — both tools installed and confirmed by version check
- Content requirements: HIGH — all config fields and webhook details read directly from source
- CI deployment: HIGH — workflow file inspected directly
- GitHub Pages live status: LOW — cannot verify a URL that doesn't exist yet

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable domain — MkDocs Material 9.x is stable; CI workflow is project-owned)
