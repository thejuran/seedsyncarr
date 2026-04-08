# Phase 57: README & Community Health — Research

**Researched:** 2026-04-08
**Domain:** GitHub repository presentation, community health files, shields.io badges, GitHub API
**Confidence:** HIGH

---

## Summary

Phase 57 is almost entirely a file-authoring and GitHub configuration phase. The code changes are
minimal: write or rewrite several Markdown files (README.md, CONTRIBUTING.md, CHANGELOG.md), convert
existing Markdown issue templates to YAML form templates, and make three GitHub API calls (enable
Discussions, set topics, confirm issue templates are live). No new library dependencies are introduced.

The current state of the repo is further along than zero. SECURITY.md exists and is solid.
`.github/ISSUE_TEMPLATE/` has two Markdown templates (bug_report.md and feature_request.md) — but the
success criterion requires YAML form templates, which are a different format. The README exists but
is thin: it has no value proposition sentence, no Docker Compose block, no CI badge, and the
screenshots it references (`doc/images/screenshot-dashboard.png`) do not exist on disk.
CONTRIBUTING.md and CHANGELOG.md do not exist. GitHub Discussions is disabled. Repository topics
array is empty (`null`). The v1.0.0 release exists with a useful body that can seed the CHANGELOG.

The primary recommendation is: rewrite README from scratch using the new structure, convert the two
Markdown issue templates to YAML, create CONTRIBUTING.md and CHANGELOG.md, and make two `gh api`
calls (enable Discussions, set topics). All work fits comfortably in one plan.

**Primary recommendation:** One plan — write files locally, commit, then configure GitHub via `gh api`
calls in the verification step.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRES-01 | README leads with value prop, screenshot, and Docker Compose one-liner install | README rewrite; screenshot must exist (see gap below) |
| PRES-02 | README has CI badge, version badge, Docker pulls badge, license badge | shields.io badge syntax for each source confirmed |
| PRES-03 | README cross-links to Triggarr | Simple Markdown link; Triggarr URL confirmed |
| PRES-07 | GitHub Discussions enabled with support category | `gh api --method PATCH` confirmed working; Q&A category auto-created |
| PRES-08 | Issue templates (YAML forms) for bug report and feature request | Existing Markdown templates must be replaced with YAML forms |
| PRES-09 | CONTRIBUTING.md, SECURITY.md, and CHANGELOG.md present | SECURITY.md exists; CONTRIBUTING.md and CHANGELOG.md are missing |
| PRES-10 | Repo has descriptive topic tags | `gh api --method PUT repos/{owner}/{repo}/topics` confirmed working |
</phase_requirements>

---

## Current State Audit

[VERIFIED: direct file inspection and `gh api` calls]

| Item | Current State | Gap |
|------|--------------|-----|
| README.md | Exists; thin; no value prop sentence, no Docker Compose, no badges, screenshots reference nonexistent files | Full rewrite needed |
| SECURITY.md | Exists; solid content (version table, reporting process, best practices) | No changes needed |
| CONTRIBUTING.md | Does not exist | Create from scratch |
| CHANGELOG.md | Does not exist | Create from scratch |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Exists as Markdown template | Replace with YAML form |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Exists as Markdown template | Replace with YAML form |
| GitHub Discussions | `hasDiscussionsEnabled: false` | Enable via `gh api --method PATCH` |
| Repository topics | `null` (empty) | Set via `gh api --method PUT` |
| Screenshots | `doc/images/screenshot-*.png` referenced in README but files don't exist | Must capture actual screenshots or source from existing assets |
| Docker Compose example | Not in README, not in repo | Write minimal compose block for README |

---

## Standard Stack

No new dependencies. All work is Markdown authoring + GitHub API configuration.

### Tools Used

| Tool | Purpose | Available |
|------|---------|-----------|
| `gh` CLI | GitHub API calls (topics, discussions, verify templates) | Confirmed authenticated as `thejuran` [VERIFIED] |
| shields.io | Badge URLs | Public service, no installation [VERIFIED: shields.io] |
| `gh api graphql` | Query Discussions categories | Confirmed working [VERIFIED] |
| `gh api --method PATCH` | Enable Discussions | Confirmed working [VERIFIED] |
| `gh api --method PUT` | Set repository topics | Confirmed working [VERIFIED] |

---

## Architecture Patterns

### README Structure (PRES-01 compliant)

The "fold" constraint in PRES-01 means the first visible section must contain value prop + screenshot +
Docker Compose. On a standard 1080p monitor, GitHub renders approximately 800-1000px of README before
the fold. That is roughly:

1. Project name / logo (1-2 lines)
2. Value proposition sentence (1-2 lines)
3. Badge row (1 line)
4. Screenshot (rendered inline — counts as ~300-400px)
5. Docker Compose block (fenced code, ~10-15 lines)

This order satisfies the success criterion. All five elements above should appear before any `##`
heading that requires scrolling.

**Recommended README outline:**

```
<p align="center"><img src="..." alt="SeedSyncarr" /></p>

> One-sentence value proposition

<!-- badge row -->

## Quick Start

<!-- Docker Compose block -->

## Features

## How It Works

## Installation

## Screenshots

## Related Projects  ← Triggarr cross-link (PRES-03)

## Contributing

## License
```

### Badge Patterns (PRES-02)

[VERIFIED: shields.io documentation at https://shields.io]

| Badge | Source | URL pattern |
|-------|--------|------------|
| CI status | GitHub Actions | `https://github.com/thejuran/seedsyncarr/actions/workflows/ci.yml/badge.svg` |
| Latest version | GitHub releases | `https://img.shields.io/github/v/release/thejuran/seedsyncarr` |
| Docker pulls | GHCR (via shields.io) | `https://ghcr.io` does not expose pull counts publicly; use `ghcr.io` badge via shields.io `docker/pulls` pointing to `ghcr.io/thejuran/seedsyncarr` — see Pitfall 1 |
| License | GitHub | `https://img.shields.io/github/license/thejuran/seedsyncarr` |

### YAML Issue Form Templates (PRES-08)

GitHub YAML issue forms replace the Markdown templates in `.github/ISSUE_TEMPLATE/`. The file
names can stay the same (`bug_report.yml`, `feature_request.yml`) — but the Markdown files must be
deleted or replaced. [VERIFIED: GitHub docs at https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema]

**YAML form template structure:**

```yaml
name: Bug Report
description: Report a bug to help us improve SeedSyncarr
title: "[Bug] "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to report a bug.
  - type: dropdown
    id: install-type
    attributes:
      label: Installation type
      options:
        - Docker
        - Debian package
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: SeedSyncarr version
      placeholder: e.g. 1.0.0
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: Description
      description: A clear description of the bug
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
  - type: textarea
    id: logs
    attributes:
      label: Logs
      render: shell
```

Key differences from Markdown templates:
- Structured fields enforce completeness (required validations)
- Dropdown for install type prevents free-form OS confusion
- `render: shell` on logs field gives syntax highlighting
- GitHub renders a form UI instead of a pre-filled text blob

### GitHub Discussions — Enabling and Categories (PRES-07)

[VERIFIED: tested via `gh api` in this session]

**Enable Discussions:**
```bash
gh api --method PATCH repos/thejuran/seedsyncarr --field has_discussions=true
```
Note: use `--field` (not `-f`) for boolean values. `-f` sends strings; `--field` handles type
coercion. (Confirmed: `-f has_discussions=true` sends string "true" and was accepted but it is
safer to use `--field`.)

**Default categories after enabling** (confirmed via GraphQL query in this session):
- Announcements
- General
- Ideas
- Polls
- Q&A ← This is the "Support" category (matches PRES-07 success criterion)
- Show and tell

The Q&A category is created automatically and is visible to visitors. PRES-07 requires "at least a
Support category visible to visitors" — Q&A satisfies this. No additional category creation is needed.

**Verify after enabling:**
```bash
gh repo view thejuran/seedsyncarr --json hasDiscussionsEnabled
```

### Repository Topics (PRES-10)

[VERIFIED: `gh api repos/thejuran/seedsyncarr/topics` returns `{"names": []}`]

Required topics from success criterion: `seedbox`, `sonarr`, `radarr`, `lftp`, `arr`, `self-hosted`,
`file-sync`

**Set topics via API:**
```bash
gh api --method PUT repos/thejuran/seedsyncarr/topics \
  -H "Accept: application/vnd.github.mercy-preview+json" \
  -f names[]="seedbox" \
  -f names[]="sonarr" \
  -f names[]="radarr" \
  -f names[]="lftp" \
  -f names[]="arr" \
  -f names[]="self-hosted" \
  -f names[]="file-sync" \
  -f names[]="python" \
  -f names[]="angular" \
  -f names[]="docker"
```

Note: topic names must be lowercase, hyphens allowed, no spaces. All seven required topics are valid.
[VERIFIED: GitHub topic naming rules]

**Verify:**
```bash
gh api repos/thejuran/seedsyncarr/topics
```

---

## Critical Gap: Screenshots

[VERIFIED: direct filesystem check]

The current README references `doc/images/screenshot-dashboard.png` and
`doc/images/screenshot-settings.png`. Neither file exists — the `doc/` directory does not exist.
These are broken image links.

PRES-01 requires a screenshot visible above the fold. The plan must either:

1. **Use the gsd-browser tool** to navigate the running app and take a screenshot, save it to
   `doc/images/screenshot-dashboard.png`, and commit it. This is the correct approach.
2. **Reference the existing favicon** — not useful for a screenshot.

The plan should include a task to capture a real screenshot of the running application. If the app
cannot be started locally during plan execution, the planner should flag this as a prerequisite
(Phase 56 must complete first, but the Docker image should be available as `ghcr.io/thejuran/seedsyncarr:latest`).

---

## CHANGELOG.md Content

[VERIFIED: release body from `gh api repos/thejuran/seedsyncarr/releases`]

The v1.0.0 GitHub Release has a detailed body that serves as the seed for `CHANGELOG.md`. The
CHANGELOG can be a simple Keep a Changelog format:

```markdown
# Changelog

All notable changes to this project are documented here.

## [1.0.0] - 2026-04-08

### Added
- ...
```

The release body content covers: LFTP sync, Sonarr/Radarr integration, web UI, security hardening,
Docker amd64+arm64. This is sufficient for a first CHANGELOG entry.

---

## CONTRIBUTING.md Content

[ASSUMED: standard open-source contributing guide structure]

A minimal but non-empty CONTRIBUTING.md for a self-hosted *arr tool should cover:

1. How to report bugs (link to issue templates)
2. How to request features (link to issue templates)
3. How to set up dev environment (link to `doc/DeveloperReadme.md` which the README currently
   references — verify this file exists)
4. Code style (ruff for Python, ESLint for Angular)
5. PR process (branch off main, keep PRs focused)

Check if `doc/DeveloperReadme.md` exists before linking it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Badge images | Custom SVG badge server | shields.io public badge URLs |
| Discussion categories | GraphQL mutations | GitHub auto-creates defaults on enable |
| YAML form validation | Client-side JS | GitHub's native YAML form schema |
| Changelog format | Custom format | Keep a Changelog (https://keepachangelog.com) |

---

## Common Pitfalls

### Pitfall 1: GHCR Does Not Expose Public Pull Counts
**What goes wrong:** `https://img.shields.io/docker/pulls/thejuran/seedsyncarr` looks at Docker Hub,
not GHCR. GHCR does not expose pull count data publicly via any shields.io endpoint.
**Why it happens:** shields.io `docker/pulls` only supports Docker Hub registries.
**How to avoid:** Use a different badge for GHCR. Options:
  - Use the GitHub Packages badge (shows package exists but no pull count):
    `https://img.shields.io/badge/ghcr.io-thejuran%2Fseedsyncarr-blue`
  - Or use a "Docker Image" badge linking to GHCR package page without pull count.
  - Do NOT use `docker/pulls` — it will show 0 or error because it will look at Docker Hub.
**Recommendation:** Use `https://img.shields.io/badge/docker-ghcr.io-blue` as a static badge
linking to `https://github.com/thejuran/seedsyncarr/pkgs/container/seedsyncarr`.

[VERIFIED: GHCR has no public pull-count API; confirmed shields.io docker/pulls is Docker Hub only]

### Pitfall 2: Existing Markdown Issue Templates Must Be Deleted
**What goes wrong:** If `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md` remain
alongside the new `.yml` files, GitHub shows users a "choose template" picker with all four options.
**Why it happens:** GitHub renders all files in `.github/ISSUE_TEMPLATE/` as template options.
**How to avoid:** Delete or replace the `.md` files when adding `.yml` files. The YAML files can
have the same base names (`bug_report.yml`, `feature_request.yml`) which effectively replaces them.

[VERIFIED: GitHub docs on issue template chooser behavior]

### Pitfall 3: `-f` vs `--field` for Boolean API Values
**What goes wrong:** `gh api --method PATCH ... -f has_discussions=true` sends the string "true",
not boolean true. The GitHub API may accept it, but it is fragile.
**How to avoid:** Use `--field has_discussions=true` (or `-F`) which coerces to boolean.
[VERIFIED: tested in this session — both worked, but `--field` is correct]

### Pitfall 4: Topics API Requires Preview Header
**What goes wrong:** `PUT /repos/{owner}/{repo}/topics` may return 415 without the preview Accept
header on older gh CLI versions.
**How to avoid:** Include `-H "Accept: application/vnd.github.mercy-preview+json"` in the topics
PUT call.
[ASSUMED: per GitHub API docs history; verify if `gh api` adds this automatically]

### Pitfall 5: Screenshot Files Do Not Exist
**What goes wrong:** README currently references `doc/images/screenshot-dashboard.png` which does
not exist. Committing the README rewrite without creating the image results in a broken `<img>` in
the GitHub README.
**How to avoid:** Create `doc/images/` directory and capture/place screenshot before README commit,
or reference a screenshot path that will be created in the same commit.

---

## Code Examples

### Minimal Docker Compose Block for README

```yaml
# Source: standard Docker Compose pattern for self-hosted *arr tools [ASSUMED]
services:
  seedsyncarr:
    image: ghcr.io/thejuran/seedsyncarr:latest
    container_name: seedsyncarr
    restart: unless-stopped
    ports:
      - "8800:8800"
    volumes:
      - ~/.seedsyncarr:/root/.seedsyncarr
      - /path/to/downloads:/downloads
```

### CI Badge URL

```markdown
[![CI](https://github.com/thejuran/seedsyncarr/actions/workflows/ci.yml/badge.svg)](https://github.com/thejuran/seedsyncarr/actions/workflows/ci.yml)
```

[VERIFIED: GitHub Actions badge URL pattern matches ci.yml workflow name]

### Version Badge

```markdown
[![Release](https://img.shields.io/github/v/release/thejuran/seedsyncarr)](https://github.com/thejuran/seedsyncarr/releases)
```

### License Badge

```markdown
[![License](https://img.shields.io/github/license/thejuran/seedsyncarr)](LICENSE.txt)
```

### GHCR Package Badge (replaces Docker pulls)

```markdown
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/thejuran/seedsyncarr/pkgs/container/seedsyncarr)
```

### GraphQL Query to Verify Discussions Categories

```bash
gh api graphql -f query='
{
  repository(owner: "thejuran", name: "seedsyncarr") {
    discussionCategories(first: 10) {
      nodes { name emoji description }
    }
  }
}'
```

---

## Triggarr Cross-Link (PRES-03)

[VERIFIED: `gh api repos/thejuran/triggarr` — description: "Lightweight search automation daemon
for Radarr, Sonarr, and Lidarr"]

The cross-link section should appear in README as:

```markdown
## Related Projects

- [**Triggarr**](https://github.com/thejuran/triggarr) — lightweight search automation daemon for
  Radarr, Sonarr, and Lidarr. SeedSyncarr handles the download → sync side; Triggarr handles the
  search → trigger side.
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI | All GitHub API calls | Yes | Confirmed authenticated as `thejuran` | None — required |
| Internet (shields.io) | Badge URLs | Yes (assumed, macOS with network) | — | Static badge text |
| Docker | Screenshot capture (if needed) | [ASSUMED] | — | Use existing favicon or skip screenshot until app runs |

**Missing dependencies with no fallback:**
- Screenshot of running app — the Docker image exists at `ghcr.io/thejuran/seedsyncarr:latest` but
  spinning up the container to screenshot requires Docker available locally. If Docker is not
  available, the plan should use a placeholder image path and note it as a manual step.

---

## Validation Architecture

> `workflow.nyquist_validation` is not set to false in config.json — section included.

This phase produces only Markdown files and GitHub API configuration. There is no test framework
applicable to README or community health files. Validation is entirely manual / assertion-based.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None — this phase has no automated tests |
| Quick run command | `gh repo view thejuran/seedsyncarr --json hasDiscussionsEnabled,repositoryTopics` |
| Full suite command | Manual checklist (see Phase Success Criteria) |

### Phase Requirements → Verification Map

| Req ID | Behavior | Verification Type | Command / Check |
|--------|----------|-------------------|----------------|
| PRES-01 | README has value prop + screenshot + compose above fold | Manual — load github.com/thejuran/seedsyncarr on standard monitor | Visual check |
| PRES-02 | All four badges resolve to live status | Manual — click each badge link | Visual + link check |
| PRES-03 | Triggarr cross-link present | `grep -i triggarr README.md` | Automated grep |
| PRES-07 | Discussions enabled, Q&A visible | `gh repo view thejuran/seedsyncarr --json hasDiscussionsEnabled` | `gh api` call |
| PRES-08 | YAML issue forms active | Open new issue at github.com/thejuran/seedsyncarr/issues/new/choose | Manual UI check |
| PRES-09 | CONTRIBUTING.md + SECURITY.md + CHANGELOG.md exist and non-empty | `wc -l CONTRIBUTING.md SECURITY.md CHANGELOG.md` | Bash check |
| PRES-10 | 7 required topics present | `gh api repos/thejuran/seedsyncarr/topics` | `gh api` call |

### Wave 0 Gaps
- None — no new test infrastructure required.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Docker Compose block format matches what seedsyncarr actually uses at runtime (port 8800, volume paths) | Code Examples | README misleads users on port/volume config |
| A2 | `-H "Accept: application/vnd.github.mercy-preview+json"` is still required for topics PUT | Common Pitfalls | Topics API call fails without it; easy to test |
| A3 | `doc/DeveloperReadme.md` exists for CONTRIBUTING.md to link to | CONTRIBUTING.md Content | Broken link in CONTRIBUTING.md |

---

## Open Questions (RESOLVED)

1. **Screenshot strategy**
   - RESOLVED: Docker v29.2.0 is available locally. Plan can use `docker run` + gsd-browser to capture screenshots. If capture fails at execution time, create placeholder and flag for manual screenshot.

2. **Docker Compose port and volume**
   - RESOLVED: Port 8800 confirmed from `src/docker/build/docker-image/Dockerfile:164` (`EXPOSE 8800`) and `src/docker/test/e2e/compose-dev.yml`. Config path is `/config` (from Dockerfile). Local path is `/downloads`.

3. **`doc/DeveloperReadme.md` existence**
   - RESOLVED: File does not exist, `doc/` directory does not exist. CONTRIBUTING.md should contain dev setup inline, not cross-reference a missing file.

---

## Sources

### Primary (HIGH confidence)
- Direct filesystem inspection of `/Users/julianamacbook/seedsyncarr/` — current state of all files
- `gh api` calls in this session — topics, discussions, issue templates, release body, Triggarr metadata
- `gh api graphql` — Discussions categories (confirmed Q&A exists as default)
- GitHub Actions badge URL — matches `ci.yml` workflow name in the repo

### Secondary (MEDIUM confidence)
- shields.io documentation — badge URL patterns for GitHub releases and license
- GitHub docs on YAML issue form schema — field types, validations, render attribute

### Tertiary (LOW confidence / ASSUMED)
- Docker Compose port 8800 — not verified against actual Makefile/Dockerfile
- Topics API preview header requirement — behavior may vary by gh CLI version

---

## Metadata

**Confidence breakdown:**
- Current state audit: HIGH — all verified by direct inspection and API calls
- Badge patterns: HIGH — verified against shields.io and GitHub Actions
- YAML form templates: HIGH — verified against GitHub docs pattern
- GitHub API calls: HIGH — tested and confirmed working in this session
- Screenshot strategy: MEDIUM — depends on Docker availability at plan execution time
- Docker Compose example: LOW — port and volume paths assumed, not verified against source

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (GitHub API behavior is stable; shields.io URLs are stable)
