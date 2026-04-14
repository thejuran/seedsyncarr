# Feature Research

**Domain:** *arr ecosystem and self-hosted community project presentation / rebrand
**Researched:** 2026-04-08
**Confidence:** HIGH (awesome-selfhosted/awesome-arr criteria, *arr ecosystem patterns), MEDIUM (r/selfhosted community norms, README patterns), LOW (star threshold timing for awesome-arr admission)

## Context

This is the **SeedSyncarr rebrand milestone**. The project already works — all functional features are built and shipped. The question this document answers is: **what presentation, documentation, and community-signal features must exist for the self-hosted and *arr community to trust and adopt this project?**

The project will be submitted to:
- **awesome-selfhosted** (acceptance criteria: open source, <250 char description, OSI license, actively maintained, free/libre software)
- **awesome-arr** (acceptance criteria: open source, minimum 50 GitHub stars)
- **r/selfhosted** (community culture: working Docker Compose, screenshots, clear problem statement, responsive maintainer)
- **Servarr wiki / TRaSH Guides Discord** (*arr community: webhook integration documentation, Sonarr/Radarr setup walkthrough)

The rebrand is from `thejuran/seedsync` (maintained fork history) to `thejuran/seedsyncarr` (standalone *arr project). The rename signals community membership and purpose clarity.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features and presentation elements users assume exist. Missing these = project looks abandoned, incomplete, or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fresh repo with standalone identity (`thejuran/seedsyncarr`) | Fork history on old repo signals "not original work." The *arr community expects a project at its canonical home. | LOW | Archive `thejuran/seedsync`, create new repo. Transfers stars won't happen — start at zero, which makes the 50-star threshold for awesome-arr a real first milestone to earn. |
| README: one-liner value proposition | First thing any visitor reads. "What does this do and why should I care?" If it's not answered in 1-2 sentences, users close the tab. | LOW | "SeedSyncarr syncs files from your seedbox to local storage and notifies Sonarr/Radarr when downloads are ready." |
| README: screenshot or GIF of the UI | Community consistently values visual proof the app works. Autobrr, Recyclarr, and every well-received self-hosted project shows the UI. Absence implies broken or ugly. | LOW | Screenshots already captured via Playwright in v4.0.0 release. Embed the dashboard screenshot and the Settings page screenshot in the README. |
| README: quick-start Docker Compose block | `docker compose up -d` is the universal self-hosted deployment unit. If there's no compose block, users don't know how to run it. Every successful *arr project leads with Docker. | LOW | Single docker-compose.yml block with `image: ghcr.io/thejuran/seedsyncarr:latest`, the three required env vars, and volume mount. |
| README: environment variable reference table | Users need to know what to configure before they can run the app. No table = users dig through source or give up. | LOW | List LFTP host/user/path, remote/local paths, API token, webhook secret, Sonarr/Radarr URL+key. One row per var: name, default, description. |
| CI status badge | Signals the project builds and tests pass. A broken badge or no badge implies no CI. The *arr community is technically savvy enough to notice. | LOW | `[![CI](badge-url)](workflow-url)` in README header. Already have CI — just add the badge. |
| OSI-approved license clearly stated | awesome-selfhosted requires it. Users need it to deploy at work or contribute. No license = legally ambiguous. | LOW | License badge in README header + `LICENSE` file in repo root. Project already has a license; confirm it's OSI-approved. |
| GitHub Discussions enabled | How users ask questions without polluting the issue tracker. Autobrr and Recyclarr both route general support to Discord/Discussions and reserve Issues for bugs. | LOW | Enable in repo settings. No code changes. |
| Issue templates (bug report + feature request) | Signals the project is maintained and takes contributions seriously. Bare issue box = project may be unmaintained. GitHub shows a community health checklist that many experienced users check. | LOW | Two templates: `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`. Standard boilerplate. |
| CONTRIBUTING.md | Required for GitHub community health score. Tells contributors how to submit PRs. Signals the project welcomes contributions. | LOW | Short file: how to run tests, coding conventions, PR process. |
| CHANGELOG or GitHub Releases with readable entries | Users need to know what changed between versions before upgrading. Missing changelog = users don't upgrade (or upgrade blind). | LOW | GitHub Releases already exist (v4.0.0). Continue the pattern with SeedSyncarr v1.0.0. Categorized changelog entries (Features, Bug Fixes, Security). |
| Docker multi-arch image (amd64 + arm64) | Raspberry Pi is the most common self-hosting hardware. arm64-only users instantly bounce if the image doesn't run. | LOW | Already built and tested in CI. Just republish under new image name `ghcr.io/thejuran/seedsyncarr`. |
| SECURITY.md | GitHub flags repos without this in community health checklist. The *arr community is security-aware. Shows the project has a responsible disclosure process. | LOW | Standard template: how to report vulnerabilities privately (GitHub private security advisories), response time commitment. |

### Differentiators (Competitive Advantage)

Features that set SeedSyncarr apart from similar seedbox sync tools and signal it belongs in the *arr ecosystem.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Sonarr/Radarr webhook integration with setup guide | Most seedbox sync tools (rclone, resilio, syncthing) are generic and require manual post-processing steps. SeedSyncarr is the only one with native *arr webhook integration that triggers library imports automatically. This is the core differentiator. | MEDIUM | Docs page: "Sonarr/Radarr Setup" with step-by-step webhook configuration, HMAC secret setup, and what the import flow looks like end-to-end. This turns a feature into a community signal. |
| MkDocs documentation site | Successful *arr projects (Recyclarr, autobrr) have dedicated docs sites, not just a README. A docs site signals the project is serious, long-term, and user-focused. It also enables awesome-selfhosted submission's optional "docs" link. | MEDIUM | Already have mkdocs set up. Deploy to GitHub Pages. Minimum pages: Overview, Installation, Configuration Reference, Sonarr/Radarr Setup, FAQ/Troubleshooting. |
| Security hardening disclosure | The self-hosted community is increasingly security-aware (post-Huntarr controversy). A project that visibly lists its security features — Bearer token auth, HMAC webhooks, path traversal protection, DNS rebinding prevention — differentiates from tools that ignore security. | LOW | "Security" section in README (brief, 4-5 bullets). Full details in docs site. This is already built — surfacing it is the work. |
| Demonstrated test coverage | 1,133 Python tests at 84% coverage, 403 Angular unit tests, full E2E suite. Few self-hosted projects have this rigor. Shows reliability and maintainability. | LOW | "Tests" badge (coverage %) in README header. One sentence in README: "1,100+ tests, 84% Python coverage enforced in CI." |
| GitHub topic tagging (`seedbox`, `sonarr`, `radarr`, `lftp`, `arr`) | GitHub topic tags drive discovery. Projects without relevant tags are invisible to people browsing `github.com/topics/sonarr`. Every well-known *arr ecosystem project tags itself. | LOW | Add 5-8 tags in the repo "About" section. Zero code changes. |
| awesome-arr entry (50 stars prerequisite) | Being listed in awesome-arr is a community signal. It means "the *arr community vouches for this." The 50-star threshold means the project needs a launch strategy, not just a repo. | LOW (apply) / MEDIUM (earn stars) | Submit PR to awesome-arr after hitting 50 stars. The launch announcement drives the initial star count. |
| awesome-selfhosted entry | The most trusted curated list in the self-hosted world. Projects listed there get sustained organic discovery. Requires: OSI license, active maintenance, <250 char description, self-hosted (no required third-party services). | LOW (apply, no star minimum) | SeedSyncarr qualifies on all criteria except it's unknown. Submit after launch. The ⚠ flag for "requires third-party service" does NOT apply — Sonarr/Radarr are optional integrations, not requirements. |

### Anti-Features (Commonly Requested, Often Problematic)

Features or presentation choices that hurt adoption or create ongoing problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| "Fork of SeedSync" in the description | Transparency about project history | Fork framing suppresses adoption. The *arr community looks for original tools, not maintenance forks. The entire point of the rebrand is to establish independent identity. | Mention original project only in a brief "History" section at the bottom of the README or in a migration doc. Lead with what SeedSyncarr is, not where it came from. |
| Detailed feature comparison table vs competitors | Seems like thorough documentation | Comparison tables age badly (competitors ship), invite "why not just use X" comments, and signal you're playing defense. Top *arr projects lead with their own value, not with "we're better than X." | One paragraph positioning statement: "SeedSyncarr is the only seedbox-to-local sync tool with native Sonarr/Radarr webhook integration." Let the features speak. |
| Discord server (for a solo maintainer) | Discord signals community presence | A dead or rarely-checked Discord is worse than no Discord. It signals abandonment faster than any other signal. A solo maintainer cannot sustain a Discord. | GitHub Discussions. Less cool, but asynchronous and persistent. Direct contributors to Discussions for support, Issues for bugs. |
| Changelog in a `CHANGELOG.md` file in the repo | Traditional open source practice | GitHub Releases are how the self-hosted community tracks updates (Watchtower uses them, Renovate reads them). A `CHANGELOG.md` file is a second source that diverges from Releases and creates maintenance burden. | GitHub Releases as canonical changelog. Each release has categorized notes. Optionally a docs site changelog page generated from the release notes. No `CHANGELOG.md` file. |
| Semantic version reuse (starting at v4.1.0 from old history) | Preserves version continuity | The rebrand starts a new project identity. Continuing from v4.x signals "this is still SeedSync." The community expects *arr projects to version independently. v1.0.0 signals "this is the first stable release of a new project." | Tag the new repo as v1.0.0. The old SeedSync repo archives at v4.0.3. The break is clean and intentional. |
| Deb package as primary install method | Shows broad platform support | Self-hosted community defaults to Docker. A deb package as the prominent install option signals "not cloud-native" and adds documentation surface area. The security risk surface of a system package is also harder to communicate. | Docker as primary install method in README. Deb package available as secondary, linked from GitHub Releases. Do not lead with deb in README Quick Start. |
| README > 1000 lines | Thoroughness | Long READMEs bury the value proposition. Users skim the top 100 lines, then click the docs link. Autobrr's README is ~150 lines; Recyclarr's is ~80 lines — both link to comprehensive docs sites. | Keep README to 200-300 lines max: tagline, badges, screenshot, quick start, feature list, links to docs. Everything else belongs in the docs site. |

---

## Feature Dependencies

```
[New GitHub repo (thejuran/seedsyncarr)]
    └──enables──> [Fresh v1.0.0 tag and release]
    └──enables──> [New Docker image (ghcr.io/thejuran/seedsyncarr)]
    └──required by──> [awesome-selfhosted submission] (needs canonical repo URL)
    └──required by──> [awesome-arr submission] (needs 50 stars at this URL)

[README with screenshot + Docker Compose + value prop]
    └──drives──> [Initial star count from r/selfhosted announcement]
    └──required by──> [awesome-selfhosted submission] (reviewers read the README)
    └──gates──> [awesome-arr submission] (50 star threshold; README drives stars)

[MkDocs docs site]
    └──enables──> [awesome-selfhosted optional "docs" link]
    └──enables──> [Sonarr/Radarr setup guide] (docs page vs README section)
    └──requires──> [New repo GitHub Pages enabled]

[GitHub Discussions + Issue Templates + CONTRIBUTING.md + SECURITY.md]
    └──satisfies──> [GitHub community health checklist]
    └──signals──> [Project is maintained and welcomes contributions]
    └──required by──> [awesome-selfhosted "actively maintained" criterion]

[50+ GitHub stars at thejuran/seedsyncarr]
    └──required by──> [awesome-arr submission]
    └──driven by──> [r/selfhosted launch post]
    └──driven by──> [README quality and screenshot]

[v1.0.0 tag + GitHub Release]
    └──triggers──> [CI Docker publish to ghcr.io/thejuran/seedsyncarr:latest]
    └──triggers──> [CI Deb package publish]
    └──enables──> [Watchtower / Renovate auto-update detection]
```

### Dependency Notes

- **Star threshold gates awesome-arr**: The 50-star minimum for awesome-arr means the launch announcement must happen before the submission. The r/selfhosted post drives initial traffic; a quality README and screenshot drive conversion from visitor to star.
- **awesome-selfhosted has no star minimum**: The list prioritizes free software and active maintenance over popularity. SeedSyncarr can be submitted immediately after launch with a working demo link or screenshots.
- **Docs site is not blocking**: awesome-selfhosted does not require a docs site. But MkDocs docs significantly increase trust signal quality and allow the README to stay short. Plan as Phase 2 presentation work.
- **Archive of old repo is not required immediately**: awesome-selfhosted and awesome-arr don't check if a predecessor repo exists. But leaving the old repo live with no redirect creates confusion. Add a notice in the old repo README pointing to SeedSyncarr.

---

## MVP Definition (What Must Exist at Launch)

### Launch With (v1.0.0 release day)

Minimum to be taken seriously by the community.

- [ ] New repo `thejuran/seedsyncarr` with all code, CI, and releases transferred
- [ ] README: tagline, badges (CI, license, Docker), screenshot, Docker Compose quick start, env var table, feature list, links to docs
- [ ] Docker image `ghcr.io/thejuran/seedsyncarr:latest` and `:1.0.0` published to GHCR
- [ ] GitHub Discussions enabled
- [ ] Issue templates (bug report + feature request)
- [ ] CONTRIBUTING.md (short, process-focused)
- [ ] SECURITY.md (responsible disclosure instructions)
- [ ] GitHub topic tags: `seedbox`, `sonarr`, `radarr`, `lftp`, `arr`, `self-hosted`, `file-sync`
- [ ] v1.0.0 GitHub Release with categorized changelog
- [ ] Old repo `thejuran/seedsync` archived with README notice pointing to new repo

### Add Before Community Submissions (v1.0.x)

Required to pass list submission review.

- [ ] MkDocs docs site on GitHub Pages — minimum pages: Overview, Installation, Configuration Reference, Sonarr/Radarr Setup
- [ ] awesome-selfhosted submission PR (no star requirement, submit after docs site)
- [ ] r/selfhosted launch post (drives initial star count toward awesome-arr threshold)

### Future Consideration (v1.1+)

Defer until post-launch validation.

- [ ] awesome-arr submission — after 50 GitHub stars
- [ ] selfh.st listing — submit to the newsletter/apps directory for additional discovery
- [ ] Servarr wiki mention or Discord community outreach — after project has some community history

---

## Feature Prioritization Matrix

| Feature | Community Impact | Implementation Cost | Priority |
|---------|-----------------|---------------------|----------|
| New repo + v1.0.0 tag | HIGH — establishes identity | LOW | P1 |
| README with screenshot + Docker Compose | HIGH — first impression, star driver | LOW | P1 |
| Docker image (new name) | HIGH — required to run | LOW | P1 |
| GitHub Discussions + issue templates | MEDIUM — community health signal | LOW | P1 |
| CONTRIBUTING.md + SECURITY.md | MEDIUM — credibility signal | LOW | P1 |
| GitHub topic tags | MEDIUM — discovery signal | LOW (minutes) | P1 |
| MkDocs docs site (basic) | HIGH — removes "no docs" objection | MEDIUM | P2 |
| Sonarr/Radarr setup guide (docs page) | HIGH — *arr differentiator | MEDIUM | P2 |
| awesome-selfhosted submission | HIGH — sustained organic discovery | LOW (apply) | P2 |
| r/selfhosted launch post | HIGH — initial traction | LOW (write post) | P2 |
| awesome-arr submission | MEDIUM — *arr credibility signal | LOW (apply, after 50 stars) | P3 |
| selfh.st listing | MEDIUM — newsletter discovery | LOW (submit form) | P3 |

**Priority key:**
- P1: Must have for launch — without these, the rebrand is incomplete
- P2: Should have — do these in the first week after launch
- P3: Nice to have — do these once the project has traction

---

## Community Platform Acceptance Criteria (Verified)

### awesome-selfhosted

**Source:** Official CONTRIBUTING.md and pull request template (verified via research)

Requirements:
- Software must be self-hostable (no required third-party cloud service)
- Must be Free/Open Source (OSI-approved license)
- Must be actively maintained (no development for 6-12 months = removal risk)
- Description must be under 250 characters, sentence case
- Must list the license and primary programming language
- One submission per PR

**SeedSyncarr status:** Qualifies. LFTP/Python/Angular stack, open source, active development, no required third-party services (Sonarr/Radarr integration is optional). Sonarr/Radarr are user-controlled — the ⚠ "third-party service" flag does NOT apply.

**Rejection risks:**
- Using the ⚠ flag incorrectly
- Description over 250 characters
- Category doesn't exist or has fewer than 3 items (submit to "Miscellaneous" if "File Sync" sub-category is thin)

### awesome-arr

**Source:** CONTRIBUTING.md verified via WebFetch

Requirements:
- Must be open source
- Must have at least **50 GitHub stars** (hard threshold, not soft)
- Must be relevant to the *arr ecosystem
- Follow alphabetical order in the appropriate category

**SeedSyncarr status:** Qualifies on all criteria except the star count. Stars must be earned before submission. The launch announcement is the primary star-count driver.

**Category:** "Complementing Apps" — tools that work alongside core *arr apps. This is where Bazarr, Recyclarr, and autobrr-adjacent tools live.

### r/selfhosted community expectations

**Source:** Community culture research, project announcement patterns

What lands well:
- Clear "what problem does this solve" in first paragraph
- Screenshots of the actual UI (not diagrams)
- Working Docker Compose in the post or linked immediately
- Mention of what makes it different from existing tools
- Responsive maintainer who replies to comments
- Being there for follow-up questions in the first 24-48 hours

What gets ignored or downvoted:
- "I made a thing, here's a link" with no context
- Paywalled or registration-required demos
- Projects with no documentation
- Projects that require the user to clone and build from source
- Cross-posting the same announcement across multiple subreddits simultaneously

---

## Competitor Feature Analysis

| Feature | SeedSync (old) | rclone | Mover.io / similar | SeedSyncarr target |
|---------|---------------|--------|--------------------|-------------------|
| Sonarr/Radarr webhook integration | Yes (built) | No (scripts only) | No | Yes — prominent in README |
| Web UI | Yes | CLI only | Varies | Yes — screenshot in README |
| Auto-extract | Yes | No | Varies | Yes — listed as feature |
| Auto-delete after import | Yes | No | No | Yes — differentiator |
| Docker multi-arch | Yes | Yes | Varies | Yes — amd64 + arm64 |
| *arr ecosystem identity | No | No | No | Yes — name signals membership |
| Docs site | Yes (mkdocs) | Extensive | Varies | Yes — deploy on launch |
| Community presence | No | Active | No | GitHub Discussions (launch) |
| OSS license | Yes | MIT | Varies | Yes |
| Active CI | Yes | Yes | Varies | Yes — badge in README |

The core gap SeedSyncarr fills: no other seedbox-to-local sync tool has native, first-class Sonarr/Radarr webhook integration. rclone is general-purpose and requires scripting. Everything else is either unmaintained or SaaS. This is the positioning that must lead every community interaction.

---

## Sources

- [awesome-selfhosted/awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) — PR template and contributing guidelines
- [Ravencentric/awesome-arr](https://github.com/Ravencentric/awesome-arr) — CONTRIBUTING.md, 50-star threshold, category structure
- [autobrr README](https://github.com/autobrr/autobrr/blob/develop/README.md) — Successful *arr project README structure: badges, screenshot, feature list, install instructions, community links
- [recyclarr README](https://github.com/recyclarr/recyclarr/blob/master/README.md) — Successful *arr project: docs site, Discord in TRaSH Guides, sponsor section, build status badge
- [selfh.st 2025 wrapped new software](https://selfh.st/post/wrapped-new-software-2025/) — Community norms around self-hosted project launches
- [GitHub community health checklist](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories) — Issue templates, CONTRIBUTING.md, CODE_OF_CONDUCT, SECURITY.md
- [DEV Community: GitHub README that gets stars](https://dev.to/belal_zahran/the-github-readme-template-that-gets-stars-used-by-top-repos-4hi7) — README structure patterns for community traction
- [Awesome ecosystem discovery via ecosyste.ms](https://awesome.ecosyste.ms/lists?topic=self-hosted) — List of self-hosted awesome lists

---

*Feature research for: SeedSyncarr rebrand — community presentation and trust signals*
*Researched: 2026-04-08*
