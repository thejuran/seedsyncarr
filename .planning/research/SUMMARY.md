# Project Research Summary

**Project:** SeedSyncarr — v1.0.0 Rebrand Milestone
**Domain:** Open source project rebrand (fork→standalone *arr ecosystem member)
**Researched:** 2026-04-08
**Confidence:** HIGH

## Executive Summary

SeedSyncarr is a repo migration and community launch, not a new application build. The application itself (Angular 21 frontend, Python/Bottle backend, LFTP integration, Sonarr/Radarr webhooks, Docker multi-arch, full E2E test suite) is feature-complete and already ships as `thejuran/seedsync`. The entire v1.0.0 milestone is a controlled identity transition: create a fresh standalone repo, execute an atomic rename across every codebase layer, harden the code against technical scrutiny, and launch into the *arr/self-hosted community in a way that earns sustained organic adoption.

The recommended approach is: infrastructure first (new repo + GitHub Pages config), then a single atomic rename commit covering all 12+ affected layers, then a hardening pass targeting AI-artifact cleanup and dependency hygiene, then presentation work (README, docs site), and finally a staged community launch. The sequencing is load-bearing — partial renames break Docker builds, hardening must precede the launch post to avoid "same problems, new name" reception, and list submissions must be gated by hard external thresholds (50 stars for Awesomarr, 4 months post-tag for awesome-selfhosted).

The primary risks are: (1) a partial rename that creates broken intermediate states in the Docker build system; (2) AI-generated code signals triggering community rejection before the project builds credibility; (3) premature curated list submissions that create a public rejection record. All three are fully preventable with the right phase ordering and explicit pre-close checklists. Zero new runtime dependencies are required — every tool needed for the rebrand is already present in the codebase or available as a GitHub-native feature.

## Key Findings

### Recommended Stack

No new packages are required for this milestone. All rebrand work uses the existing Python/npm ecosystem (MkDocs 1.6.1 + Material 9.7.6 already in `pyproject.toml`) or GitHub-native features (Discussions, YAML issue forms, Actions). The one migration tool needed — `git clone --mirror` + `git push --mirror` — uses standard git, not any new install. The correct repo migration approach is mirror-clone to a fresh `thejuran/seedsyncarr` repo (not GitHub Import, not fork+detach) to ensure all tags and refs transfer reliably.

**Core technologies:**
- `git clone --mirror` + `git push --mirror`: Repo migration — only method that reliably transfers all tags and refs
- `mkdocs` + `mkdocs-material` (existing): Docs site — already configured at `src/python/mkdocs.yml`; needs content and URL updates only
- GitHub YAML issue forms: Community health — replaces existing Markdown templates with validated, structured bug/feature reports
- GitHub Discussions: Community support channel — zero-infrastructure replacement for Discord; appropriate for a solo maintainer
- `gh` CLI (existing): Repo creation, archival, releases — already in CI

### Expected Features

**Must have (table stakes) — required for launch day:**
- New repo `thejuran/seedsyncarr` with fresh v1.0.0 tag and clean standalone identity
- README: one-liner value proposition, CI/license/Docker badges, screenshot, Docker Compose quick-start, env var table, feature list
- Docker image `ghcr.io/thejuran/seedsyncarr:latest` and `:1.0.0` published to GHCR
- GitHub Discussions enabled, YAML issue templates (bug + feature), CONTRIBUTING.md, SECURITY.md
- GitHub topic tags: `seedbox`, `sonarr`, `radarr`, `lftp`, `arr`, `self-hosted`, `file-sync`
- Old repo `thejuran/seedsync` archived with forward notice pointing to new repo

**Should have (competitive differentiators) — within first week post-launch:**
- MkDocs docs site deployed to GitHub Pages — minimum pages: Overview, Installation, Configuration Reference, Sonarr/Radarr Setup
- Sonarr/Radarr webhook integration setup guide as a dedicated docs page (core differentiator vs. rclone/generic sync tools)
- awesome-selfhosted submission PR (no star minimum; submit after docs site is live)
- r/selfhosted launch announcement post (drives initial star count toward Awesomarr threshold)

**Defer (v1.1+):**
- Awesomarr submission — hard gate: 50 GitHub stars required before opening PR
- selfh.st listing submission
- Servarr wiki mention or Discord outreach (requires community history)
- awesome-selfhosted submission — submit no earlier than August 2026 (4 months post-v1.0.0 tag)

**Anti-features to avoid:**
- "Fork of SeedSync" in the project description or README header — harms adoption; use origin story framing instead
- Discord server — dead Discord is worse than no Discord for a solo maintainer
- `CHANGELOG.md` file in repo — GitHub Releases are the canonical changelog; do not maintain two sources
- Semantic version continuity from v4.x — v1.0.0 signals standalone identity; v4.x signals "still SeedSync"
- README longer than 200-300 lines — top *arr projects keep READMEs short and link to docs

### Architecture Approach

The rebrand is an identity-layer operation, not a runtime architecture change. The runtime system (Angular SPA -> Python/Bottle REST API -> LFTP -> filesystem) is unchanged. What changes is every surface where the string "seedsync" appears across 12 distinct layers. The non-negotiable architectural constraint is that all renames must happen in a single atomic commit — Dockerfile stage names and compose file `target:` references are tightly coupled, and a partial rename leaves the Docker build system in a broken state.

**Major components requiring rename:**
1. Python entry point (`seedsync.py` -> `seedsyncarr.py`) and `SERVICE_NAME` constant — visible to contributors and the systemd unit
2. Docker infrastructure (Dockerfile stage names, compose `image:` and `target:` values, CMD, user/group, home directory `~/.seedsync` -> `~/.seedsyncarr`) — broken Docker build is the most visible failure mode
3. Debian package (`control`, `changelog`, `seedsync.service` -> `seedsyncarr.service`) — service name is what users reference at the command line
4. Angular UI (nav brand text, about page, `<title>`, localization strings, GitHub Releases API URL in `version-check.service.ts`) — visible to end users
5. CI workflow and Makefile (hardcoded `seedsync` in `docker-image-release` target, `RELEASE_REGISTRY` publish steps) — controls what gets published to GHCR
6. Docs and community files (mkdocs.yml, all docs pages, CLAUDE.md, README, issue templates, PR template) — visible to all contributors and users

**Critical sequencing constraint:** Create the new repo and enable GitHub Pages *before* pushing any code. The CI pipeline derives the GHCR staging registry from `${GITHUB_REPOSITORY,,}` — the repo must exist for CI to push to the correct namespace.

### Critical Pitfalls

1. **Incremental rename across multiple commits** — Dockerfile stage renames and compose `target:` references are coupled; a partial rename breaks `docker build` with a confusing "target not found" error. Prevention: one atomic rename commit covering all 12 layers, verified with `grep -r "seedsync"` before merge.

2. **AI-generated code signals triggering community rejection** — Triggarr was rejected from Awesomarr despite 60 stars; the *arr community's technical reviewers flag verbose AI comments, over-broad exception handling, duplicate utility functions, and inconsistent style. Prevention: explicit AI-artifact audit before any community submission.

3. **Premature curated list submissions creating a public rejection record** — Awesomarr requires 50 GitHub stars (hard threshold); awesome-selfhosted requires 4+ months from v1.0.0 tag date. Submitting early creates a visible rejected PR. Prevention: star-count gate documented in launch plan; calendar the 4-month eligibility date (August 2026).

4. **"New name, same problems" community reception** — launching with open Dependabot alerts, CI failures, or untested Docker Compose instructions sets a permanent negative first impression. Prevention: hardening phase closes before README is written and before any community post goes out.

5. **GHCR image path inconsistency** — if CI is updated but README is not (or vice versa), users get 404s on first install. Prevention: GHCR image path update is part of the atomic rename commit; `docker pull ghcr.io/thejuran/seedsyncarr:latest` tested from a clean machine before any announcement.

## Implications for Roadmap

Based on the combined research, four phases in strict sequence:

### Phase 1: Rebrand and Rename
**Rationale:** Everything downstream depends on the new repo existing and CI running green in the new namespace. This is the critical-path technical work and must come first.
**Delivers:** `thejuran/seedsyncarr` repo live with all code, CI green, Docker image published to new GHCR path, old repo archived with forward notice.
**Addresses:** All table-stakes technical requirements; establishes canonical repo URL required by every downstream submission.
**Avoids:** Pitfall 1 (atomic rename — no partial states), Pitfall 5 (GHCR path consistency).
**Key steps:** Create repo + enable GitHub Pages first; copy codebase; initial commit; atomic rename commit (all 12 layers); CI green validation; `docker pull` smoke test from clean machine; v1.0.0 tag; archive old repo.

### Phase 2: Harden for Scrutiny
**Rationale:** The *arr community is technically sophisticated and skeptical of AI-assisted projects. Hardening must precede any community-facing presentation work — once the launch post goes out, first impressions are permanent.
**Delivers:** Codebase with zero AI-artifact signals, zero open Dependabot alerts, zero lint errors, CI green on all platforms, Docker Compose tested end-to-end from a clean environment.
**Addresses:** AI-code scrutiny (Pitfall 2), "new name, same problems" reception (Pitfall 4).
**Key checklist:** AI-artifact audit (comments explaining "what", over-broad exception handling, duplicate utilities, inconsistent style); Dependabot alerts resolved; Angular and Python lint clean; `docker compose up` tested from a fresh machine.

### Phase 3: Present
**Rationale:** README and docs site are the primary surface for community trust. Writing them after hardening ensures every claim in the README is backed by the code. The docs site must be live before any wiki submission attempt.
**Delivers:** README (200-300 lines max: tagline, badges, screenshot, Docker Compose, env var table, feature list, docs links), MkDocs docs site on GitHub Pages (Overview, Installation, Configuration Reference, Sonarr/Radarr Setup), GitHub community health files (YAML issue templates, CONTRIBUTING.md, SECURITY.md), GitHub topic tags.
**Addresses:** Must-have and should-have presentation features from FEATURES.md; Servarr wiki listing requirements (Pitfall 7).

### Phase 4: Community Launch
**Rationale:** Launch is the last activity, not the second. Community outreach must be staged (r/selfhosted first; wait for organic traction before crossposting) to avoid Reddit spam detection and optimize engagement.
**Delivers:** r/selfhosted announcement post (substantive "I built X to solve Y" framing), awesome-selfhosted submission PR, follow-up posts customized per audience.
**Addresses:** r/selfhosted community expectations; awesome-selfhosted submission (no star minimum — can submit after docs site is live).
**Avoids:** Pitfall 3 (premature list submissions), Pitfall 6 (wrong channel/timing — posts staggered 24-48 hours, customized per audience).
**Deferred to post-launch:** Awesomarr submission (gate: 50 stars); awesome-selfhosted submission (gate: August 2026); selfh.st listing.

### Phase Ordering Rationale

- Phase 1 before Phase 2: CI must be green in the new repo before hardening can be validated. Hardening a broken build is wasted effort.
- Phase 2 before Phase 3: The README claims (test coverage numbers, security features, CI status) must be verified against a hardened codebase. Writing the README first means claiming things that may not yet be true.
- Phase 3 before Phase 4: The docs site must be live before any community post or wiki submission. A launch post with no docs site is the fastest way to get "no docs, why should I trust this" responses.
- List submissions are NOT phase activities — they are conditional follow-up work gated by external thresholds that cannot be controlled on launch day.

### Research Flags

Phases with standard patterns (no additional phase-level research needed):
- **Phase 1:** Architecture file provides complete file-by-file rename inventory from direct codebase inspection. Stack file provides exact `git push --mirror` migration steps from official GitHub docs.
- **Phase 2:** PITFALLS.md specifies the AI-artifact audit checklist explicitly. No new research needed.
- **Phase 3:** FEATURES.md specifies exact README structure and docs site page requirements. STACK.md specifies exact `mkdocs.yml` configuration changes.
- **Phase 4:** PITFALLS.md specifies launch sequencing and per-community post framing. FEATURES.md specifies submission requirements for all target lists.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings verified against official docs (GitHub docs, mkdocs-material PyPI, awesome-selfhosted-data CONTRIBUTING.md fetched directly). Zero new packages — no version compatibility risk. |
| Features | HIGH | awesome-selfhosted and Awesomarr criteria verified from official CONTRIBUTING.md files. Competitor analysis from live README inspection. r/selfhosted norms from multiple corroborating sources. |
| Architecture | HIGH | Derived from direct codebase inspection — every file listed was read and verified. No inference required. |
| Pitfalls | MEDIUM-HIGH | List submission criteria from official sources (HIGH). AI-code scrutiny from academic research + practitioner reports + direct Triggarr precedent. Community launch timing from multiple corroborating sources. |

**Overall confidence:** HIGH

### Gaps to Address

- **awesome-selfhosted 4-month rule for rebrands:** Rule applies to the tagged release date, not git history. For SeedSyncarr v1.0.0 (April 2026), safe submission date is August 2026. There is a possible argument that SeedSync history from February 2026 satisfies the rule, but CONTRIBUTING.md is ambiguous on rebrands. Recommendation: submit in August 2026 without relying on the lineage argument.
- **License field in `pyproject.toml`:** STACK.md notes the license should be verified (MIT or BSD-3-Clause) before the awesome-selfhosted submission YAML is written. Verify during Phase 3.
- **Awesomarr rejection of Triggarr:** PITFALLS.md notes Triggarr was rejected despite 60 stars. The specific rejection reason was not verified — AI-code signal is the most likely cause based on community dynamics research, but if the reason was scope or category fit, the hardening strategy may need adjustment. Verify if Triggarr rejection reasoning is publicly documented before closing Phase 2.

## Sources

### Primary (HIGH confidence)
- `awesome-selfhosted-data` CONTRIBUTING.md (fetched directly) — submission requirements, 4-month rule, description guidelines
- `awesome-selfhosted-data` addition template (fetched directly) — exact YAML field schema for software entries
- `Ravencentric/awesome-arr` CONTRIBUTING.md (fetched directly) — 50-star threshold, category structure
- GitHub Docs: Syntax for issue forms — YAML form schema reference
- GitHub Docs: Enabling GitHub Discussions — official enable/disable docs
- mkdocs-material PyPI + GitHub releases — version 9.7.6 latest stable, maintenance mode until Nov 2026
- Direct codebase inspection (`/Users/julianamacbook/seedsync/`) — all Architecture findings from reading source files
- GitHub Docs: Duplicating a repository — `git clone --mirror` + `git push --mirror` method

### Secondary (MEDIUM confidence)
- autobrr README (live) — successful *arr project README structure: badges, screenshot, feature list, install
- Recyclarr README (live) — successful *arr project: docs site, build status badge, short README
- selfh.st 2025 wrapped new software — community norms around self-hosted project launches
- CodeRabbit "AI vs human code gen report" — 1.7x more major issues in AI-generated code
- InfoQ "AI Vibe Coding Threatens Open Source" — maintainer rejection patterns, AI slop backlash
- Hacker News fork ethics thread — attribution community expectations
- Open Source Guides — community launch timing and engagement

### Tertiary (LOW confidence)
- Awesomarr rejection of Triggarr despite 60 stars — hypothesis that AI-code signals caused rejection; specific reason not verified

---
*Research completed: 2026-04-08*
*Ready for roadmap: yes*
