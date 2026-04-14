# Stack Research

**Domain:** Project rebrand — repo migration, docs site, community presence
**Researched:** 2026-04-08
**Milestone:** v1.0.0 SeedSyncarr Rebrand
**Confidence:** HIGH

---

## Scope

This document covers ONLY the new tooling required for the SeedSync → SeedSyncarr rebrand. Core application stack (Angular 21, Python/Bottle, Bootstrap 5.3, LFTP, Sonarr/Radarr webhooks, Docker multi-arch, Playwright E2E, CI/CD, security hardening) is already validated and is NOT re-researched.

Four new areas:

1. **Repo migration** — fresh `thejuran/seedsyncarr` without fork relationship, preserving history
2. **MkDocs docs site** — update existing setup for new branding and GitHub Pages deploy
3. **GitHub community signals** — issue templates (YAML form schema), GitHub Discussions, PR template
4. **awesome-selfhosted submission** — exact format and eligibility criteria

---

## Recommended Stack

### Core Technologies — NO NEW PACKAGES REQUIRED

All rebrand work uses the existing Python/npm ecosystem or GitHub-native features. Zero new runtime dependencies.

| Technology | Version | Purpose | Why No New Package Needed |
|------------|---------|---------|--------------------------|
| `mkdocs` | `^1.6.1` (already in `pyproject.toml`) | Documentation build engine | Already installed; just needs `mkdocs.yml` content updates |
| `mkdocs-material` | `^9.7.1` (already in `pyproject.toml`) | Docs theme | Already configured at `src/python/mkdocs.yml`; latest stable is 9.7.6 (2026-03-19). Theme is in maintenance mode with security updates until Nov 2026. |
| GitHub YAML issue forms | GitHub-native (no install) | Structured bug/feature/question reports | YAML forms in `.github/ISSUE_TEMPLATE/*.yml` — replaces existing Markdown templates |
| GitHub Discussions | GitHub-native (no install) | Community Q&A, announcements, show-and-tell | Enable in repo Settings; optional `.github/DISCUSSION_TEMPLATE/*.yml` for structured categories |
| `gh` CLI | 2.x (already available) | Create repo, archive old repo, create releases | Used in existing CI; also covers repo migration steps |

### What the Rebrand Touches (Configuration Only)

| Area | Current State | Change Needed |
|------|--------------|---------------|
| `mkdocs.yml` | `site_name: SeedSync`, `repo_url: thejuran/seedsync`, `site_url: thejuran.github.io/seedsync` | Update all three to SeedSyncarr; update social links |
| `.github/ISSUE_TEMPLATE/` | Two Markdown templates (`bug_report.md`, `feature_request.md`) | Convert to YAML form schema (`.yml` extension); add `config.yml` for template chooser |
| GitHub Actions workflows | Reference `thejuran/seedsync`, image name `seedsync` | Update all refs to `seedsyncarr` |
| Docker image names | `ghcr.io/thejuran/seedsync` | `ghcr.io/thejuran/seedsyncarr` |
| Python package metadata | `pyproject.toml` `name`, `description` | Rename to `seedsyncarr` |
| Angular `package.json` | `"name": "seedsync"` | Rename to `seedsyncarr` |
| awesome-selfhosted entry | SeedSync listed (if at all) | New entry for SeedSyncarr via PR to `awesome-selfhosted-data` |

---

## Area 1: Repo Migration (Fresh Repo, No Fork Relationship)

### Approach: `git clone --mirror` + `gh repo create` + `git push --mirror`

Do NOT use GitHub Import or fork-and-detach. Those approaches can leave residual upstream links or lose some refs.

The correct three-step pattern:

```bash
# Step 1: Mirror-clone the existing repo (preserves all branches, tags, notes)
git clone --mirror https://github.com/thejuran/seedsync.git seedsync-mirror

# Step 2: Create the new repo via gh CLI (no --template, no fork)
gh repo create thejuran/seedsyncarr --public --description "Sync files from your seedbox. Fast. With Sonarr/Radarr integration."

# Step 3: Push all refs to the new repo
cd seedsync-mirror
git remote set-url origin https://github.com/thejuran/seedsyncarr.git
git push --mirror

# Step 4: Archive the old repo (makes it read-only, keeps it discoverable)
gh repo archive thejuran/seedsync --yes
```

**Why `--mirror` over `--bare`:** `--mirror` also copies remote-tracking refs and all notes. `--bare` is sufficient for just history + tags but `--mirror` is safer for a complete transfer.

**Why NOT GitHub Import:** Import creates a normal clone with full history but doesn't transfer git tags reliably in all cases. `push --mirror` is the authoritative method and is used by GitHub's own infrastructure docs.

**History note:** The v4.0.3 commit history will be present in the new repo. The first SeedSyncarr-branded commit will be the renaming commit on top of that history. This is correct — it shows the lineage without being a fork.

**Confidence:** HIGH — `git push --mirror` is documented in GitHub's official "Duplicating a repository" guide.

---

## Area 2: MkDocs Docs Site

### Existing Setup Is Already Correct

The project already has a fully configured MkDocs + Material setup:
- `src/python/mkdocs.yml` — complete configuration with search plugin, navigation, markdown extensions
- `src/python/docs/` — five doc pages: `index.md`, `install.md`, `usage.md`, `faq.md`, `changelog.md`
- `pyproject.toml` — `mkdocs = "^1.6.1"` and `mkdocs-material = "^9.7.1"` already declared
- CI workflow already runs `mkdocs build`
- Deploy command: `mkdocs gh-deploy --force` (manual step per existing CLAUDE.md)

**No new packages.** Only content updates needed.

### Required mkdocs.yml Changes

```yaml
# Update these fields only:
site_name: SeedSyncarr
site_description: Sync files from your seedbox to local. Fast. With Sonarr/Radarr integration.
site_url: https://thejuran.github.io/seedsyncarr
repo_name: thejuran/seedsyncarr
repo_url: https://github.com/thejuran/seedsyncarr
edit_uri: edit/master/src/python/docs/

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/thejuran/seedsyncarr
    - icon: fontawesome/brands/docker
      link: https://github.com/thejuran/seedsyncarr/pkgs/container/seedsyncarr
```

### Palette Note

The existing `mkdocs.yml` uses `primary: teal` which does not match the app's Deep Moss + Amber palette. This is a documentation site detail — teal Material theme is readable and professional. Aligning docs palette to the app palette is optional (nice-to-have, not required for the rebrand).

### GitHub Pages Deploy

GitHub Pages must be enabled on the new `thejuran/seedsyncarr` repo (Settings → Pages → Source: `gh-pages` branch). The `mkdocs gh-deploy --force` command creates/updates the `gh-pages` branch and pushes. Site URL will be `https://thejuran.github.io/seedsyncarr/`.

**Confidence:** HIGH — existing setup already works; this is a find-and-replace plus repo Settings change.

---

## Area 3: GitHub Community Signals

### Issue Templates: Convert Markdown → YAML Form Schema

The two existing Markdown templates (`bug_report.md`, `feature_request.md`) work but lack validation and structured fields. YAML form templates (`.yml` extension) provide a rendered form UI with required fields, dropdowns, and checkboxes — reducing triage friction.

**File location:** `.github/ISSUE_TEMPLATE/` (same directory, `.yml` extension)

**Required top-level fields for each template:**

```yaml
name: "Template display name"
description: "Template description shown in chooser"
title: "[Prefix] "
labels: ["label1"]
body:
  - type: textarea | input | dropdown | checkboxes | markdown
    id: unique-id
    attributes:
      label: "Field label"
      description: "Help text"
      placeholder: "Placeholder"  # textarea/input only
      options: ["opt1", "opt2"]   # dropdown/checkboxes only
    validations:
      required: true | false
```

**Key schema constraints:**
- `type: markdown` renders static text (use for headers/notes), has no `id` and no `validations`
- `type: checkboxes` options use `{label: "text", required: true}` not plain strings
- `id` must be unique within a form; cannot contain spaces
- At least one body element required

**Required `config.yml` for template chooser (adds "Open a blank issue" link):**

```yaml
# .github/ISSUE_TEMPLATE/config.yml
blank_issues_enabled: false
contact_links:
  - name: GitHub Discussions (Q&A)
    url: https://github.com/thejuran/seedsyncarr/discussions
    about: Ask questions and get help from the community
```

Setting `blank_issues_enabled: false` forces contributors through templates, which improves report quality.

### GitHub Discussions Setup

Enable via: Repository Settings → Features → Discussions (checkbox). No file needed to enable.

**Default categories created automatically:** General, Ideas, Polls, Q&A, Show and Tell, Announcements.

**Recommended category use for an *arr project:**
- **Q&A** — "how do I configure X" support questions (keeps Issues for bugs only)
- **Ideas** — feature requests that aren't ready to file as Issues
- **Show and Tell** — users sharing their setups
- **Announcements** — release notes, roadmap updates (maintainer-only posting)

**Discussion category forms** (`.github/DISCUSSION_TEMPLATE/q-a.yml` etc.) are optional — the standard free-text categories work well for a small community starting out. Add structured forms only if Q&A volume grows and triage becomes difficult.

**Confidence:** HIGH — GitHub Discussions is a toggle in repo Settings; YAML form schema is official GitHub docs.

### PR Template

The existing `.github/pull_request_template.md` should be updated to reference SeedSyncarr. No structural changes needed.

---

## Area 4: awesome-selfhosted Submission

### Eligibility Assessment

| Criterion | SeedSyncarr Status | Pass? |
|-----------|-------------------|-------|
| First release older than 4 months | SeedSync v1.0 was Feb 2026; SeedSyncarr v1.0.0 will be tagged in April 2026. SeedSync history predates 4 months, but **the new v1.0.0 tag on the new repo** starts the clock fresh. | BORDERLINE — submit after Aug 2026 to be safe, or argue lineage |
| Free and Open-Source license | BSD-3-Clause or MIT (verify current `pyproject.toml` `license` field) | Likely YES |
| Active maintenance | Active CI, recent commits | YES |
| Working installation instructions | Docker + Deb, documented in `install.md` | YES |
| No cloud provider dependency | Self-hosted only, no external services required | YES |
| Not a desktop/CLI app relying on a separate server | Web UI with backend — this IS a server application | YES |
| Not just Dockerization of another app | Standalone application with own codebase | YES |

**The 4-month rule is the critical path.** awesome-selfhosted maintainers apply it strictly to the tagged release date, not the project's git history. The rebrand creates a new repo with a new `v1.0.0` tag. To be safe: submit to awesome-selfhosted no earlier than August 2026 (4 months after April 2026 tagging). Alternatively, submit while noting the project is a rebrand of SeedSync with history dating to 2026-02.

### Submission Format

Submissions go to `awesome-selfhosted/awesome-selfhosted-data` (NOT the main `awesome-selfhosted` repo). Create `software/seedsyncarr.yml`:

```yaml
name: "SeedSyncarr"
website_url: "https://thejuran.github.io/seedsyncarr"
source_code_url: "https://github.com/thejuran/seedsyncarr"
description: "Sync files from a remote Linux server or seedbox to local storage with a web UI, powered by LFTP. Integrates with Sonarr and Radarr for automated post-download workflows."
licenses:
  - MIT   # or BSD-3-Clause — verify pyproject.toml
platforms:
  - Python
  - Docker
  - deb
tags:
  - File Transfer & Synchronization
  - Automation
```

**Description rules:**
- No "open-source", "free", "self-hosted" (implied by presence on list)
- No leading "A " or project name repetition
- Under 250 characters
- Because it is a rebrand of SeedSync: add `(fork of SeedSync)` at end per CONTRIBUTING guidelines

**Category:** The existing "File Transfer & Synchronization" tag covers this use case. No new tag needed.

**Process:** Open an Issue (not PR) in `awesome-selfhosted-data` using the Addition template, or submit a PR creating `software/seedsyncarr.yml`. PRs are faster when the submission is clean.

**Confidence:** HIGH for format and process (fetched directly from `awesome-selfhosted-data` CONTRIBUTING.md and addition template). MEDIUM for 4-month eligibility interpretation for rebrands — consult maintainers if uncertain.

---

## Installation

No new packages to install. Existing setup is used as-is.

```bash
# Verify existing mkdocs setup works in new repo
cd src/python
poetry install
poetry run mkdocs build --site-dir ../../site

# Deploy docs after new repo is live
poetry run mkdocs gh-deploy --force
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `git clone --mirror` + `push --mirror` | GitHub Import tool | Import doesn't reliably transfer all tags; `push --mirror` is authoritative |
| `git clone --mirror` + `push --mirror` | Fork + detach | GitHub doesn't officially support detaching forks; some UI indicators remain; not supported programmatically |
| YAML form issue templates | Keep existing Markdown templates | YAML forms provide required-field validation, structured data, better contributor UX — worth the one-time conversion effort |
| GitHub Discussions | External Discord/Matrix | GitHub Discussions is zero-infrastructure, discoverable, searchable, and keeps community co-located with the code |
| mkdocs-material 9.7.x | Upgrade to 10.x when available | 9.7.x is the current stable branch; project is in maintenance mode with no v10 roadmap — no reason to change |
| awesome-selfhosted submission at 4+ months | Submit immediately at launch | Strict 4-month rule enforced by maintainers; early submissions are closed and must be resubmitted |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| GitHub "Import repository" for migration | Unreliable tag transfer; creates an import watermark in the repo's API metadata | `git clone --mirror` + `git push --mirror` |
| Forking + requesting fork detachment | GitHub doesn't support fork detachment via API or settings; requires contacting GitHub support; outcome unpredictable | Mirror clone to a brand-new repo |
| ReadTheDocs for docs hosting | Adds an external dependency and account to manage; the existing `mkdocs gh-deploy` workflow to GitHub Pages is already set up and working | GitHub Pages via `mkdocs gh-deploy` |
| Markdown-style issue templates for new repo | No form validation, no required fields, higher noise in issues | YAML form schema (`.yml` extension) |
| Submitting to main `awesome-selfhosted` repo | Submissions now go to `awesome-selfhosted-data` (machine-readable YAML); the main repo is auto-generated | `awesome-selfhosted/awesome-selfhosted-data` |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| `mkdocs` | `^1.6.1` | No change from existing `pyproject.toml` constraint |
| `mkdocs-material` | `^9.7.1` (latest stable: 9.7.6) | In maintenance mode; critical fixes + security patches until Nov 2026; no breaking changes expected within `^9.7.x` |
| Python | 3.8+ | mkdocs-material requirement; project uses 3.12+ so no constraint |

---

## Sources

**HIGH CONFIDENCE — Official / Primary Sources:**
- [awesome-selfhosted-data CONTRIBUTING.md](https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted-data/master/CONTRIBUTING.md) — Fetched directly; full submission requirements, 4-month rule, description guidelines
- [awesome-selfhosted-data Addition template](https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted-data/master/.github/ISSUE_TEMPLATE/addition.md) — Fetched directly; exact YAML field schema for software entries
- [GitHub Docs: Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms) — Official YAML form schema reference
- [GitHub Docs: Syntax for GitHub's form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema) — Field types and validation
- [GitHub Docs: Enabling GitHub Discussions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-community/enabling-or-disabling-github-discussions-for-a-repository) — Official enable/disable docs
- [mkdocs-material PyPI](https://pypi.org/project/mkdocs-material/) — Version 9.7.6, released 2026-03-19, Python >=3.8
- [mkdocs-material GitHub releases](https://github.com/squidfunk/mkdocs-material/releases) — Confirmed 9.7.6 latest; maintenance mode until Nov 2026
- Existing `src/python/mkdocs.yml` — Verified working configuration in the current repo

**MEDIUM CONFIDENCE — WebSearch verified:**
- GitHub community discussions on repo migration without fork relationship — `git clone --mirror` + `push --mirror` consistently recommended; aligns with GitHub's official "Duplicating a repository" approach

---

*Stack research for: v1.0.0 SeedSyncarr Rebrand — repo migration, docs site, GitHub community, awesome-selfhosted*
*Researched: 2026-04-08*
*Confidence: HIGH (all core findings verified against official docs or fetched source files)*
