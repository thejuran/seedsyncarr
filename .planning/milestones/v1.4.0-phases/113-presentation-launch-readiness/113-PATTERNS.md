# Phase 113: Presentation & Launch Readiness - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 9 (6 repo artifacts + 1 rename + 2 phase-internal)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `README.md` | README | N/A | `README.md` itself (existing 154 lines) + `docs/GETTING-STARTED.md` for install voice | exact (targeted rewrite) |
| `SECURITY.md` | security policy | N/A | `SECURITY.md` itself (existing 45 lines) | exact (add section) |
| `CONTRIBUTING.md` | contributor doc | N/A | `CONTRIBUTING.md` itself + `docs/DEVELOPMENT.md` for full build command list | exact (freshen) |
| `CODE_OF_CONDUCT.md` | community-health | N/A | `.github/ISSUE_TEMPLATE/bug_report.yml` (community-health tone/register) | role-match (create new) |
| `CHANGELOG.md` | changelog | N/A | `CHANGELOG.md` [1.3.0] entry (lines 7-30) | exact (add section) |
| `LICENSE.txt` → `LICENSE` | license | N/A | `LICENSE.txt` itself (content unchanged) | exact (rename only) |
| `113-TEARDOWN.md` (phase dir) | phase-internal artifact | N/A | `release-notes.md` (accessible plain prose, no front-matter) | tone-match |
| `113-CODEX-PASS.md` (phase dir) | phase-internal artifact | N/A | `.planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md` (structured findings) | role-match |
| `113-REPO-METADATA.md` (phase dir) | phase-internal artifact | N/A | `release-notes.md` (copy-paste-ready plain text, draft for human application) | tone-match |

---

## Pattern Assignments

### `README.md` (README, targeted rewrite)

**Analog:** `README.md` (existing file, all 154 lines in context above)

**Current structure to preserve** (lines 1-18):
```markdown
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="doc/brand/wordmark-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="doc/brand/wordmark-light.png">
    <img alt="SeedSyncarr" src="doc/brand/wordmark-dark.png" width="480">
  </picture>
</p>

<p align="center">
  <img src="doc/images/screenshot-dashboard.png" alt="SeedSyncarr Dashboard" width="800" />
</p>

> Sync files from your seedbox to your local media server — fast, automated, and integrated with Sonarr and Radarr.

[![CI](https://github.com/thejuran/seedsyncarr/actions/workflows/ci.yml/badge.svg)](...)
[![Release](https://img.shields.io/github/v/release/thejuran/seedsyncarr)](...)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](...)
[![License](https://img.shields.io/github/license/thejuran/seedsyncarr)](LICENSE.txt)
```

**Badge link to fix** (line 18): Change `LICENSE.txt` → `LICENSE` in the license badge href:
```markdown
[![License](https://img.shields.io/github/license/thejuran/seedsyncarr)](LICENSE)
```

**One-liner sharpening target** (line 13): Replace the current blockquote with the owned-axis one-liner per D-02:
```markdown
> A Sonarr-driven seedbox sync tool where an HMAC-verified import webhook drives safe auto-delete — so you never delete a file that didn't make it into your library.
```

**Fork-relationship note to insert** (new section after the one-liner / before Quick Start, per D-03/D-04):
```markdown
## About This Fork

SeedSyncarr is a fork of [SeedSync](https://github.com/ipsingh06/seedsync) (ipsingh06). Like other active forks, it modernizes the original; SeedSyncarr's focus is a Sonarr-driven workflow where an HMAC-verified import webhook drives safe auto-delete — so you never delete a file that didn't reach your library.
```

> **HONESTY GUARD (codex-review correction, 2026-06-02):** When framing the fork note, the absence of outbound-push MUST be framed as a *chosen scope* ("SeedSyncarr is Sonarr-driven, so it receives import webhooks rather than pushing them"), NOT as a competitive advantage. Do NOT write any phrasing that implies the missing outbound-push is *better* — forbidden styles: "without cluttering Sonarr with API calls", "cleaner than push", "avoids extra API calls", "lighter-weight than push-based forks", or any "so you don't have to…" framing of the missing feature. This is enforced by negative grep gates in 113-01 Task 2 and 113-04 Task 1 (see §9 of `reports/comparison-nitrobass24-seedsync-2026-06-02.md`).

**Security selling-point insertion** (near top, after features list, per D-01): Add a brief "Security" selling point in the Features list or as a short standalone block before "How It Works":
```markdown
- **Security by default** — Fernet-encrypted secrets at rest, HMAC-verified import webhooks, opt-in Bearer auth, an IP-resolution guard on Sonarr/Radarr connection URLs, CSP headers, and rate-limited webhook/config/test-connection/bulk/status endpoints. See [SECURITY.md](SECURITY.md) for the full posture.
```

> **ACCURACY GUARD (codex-review correction, 2026-06-02):** Earlier wording of this bullet said "SSRF guards, ... rate-limited mutable endpoints" — both are overclaims. The guard is an IP-resolution check on the user-supplied *arr connection URLs (not generic outbound-webhook SSRF), and rate-limiting covers the SPECIFIC endpoints enumerated below, not "all mutable endpoints." Keep the README bullet brief but accurate; SECURITY.md holds the detail.

**License line to update** (line 118): Change `LICENSE.txt` to `LICENSE`:
```markdown
Apache License 2.0 — see [LICENSE](LICENSE).
```

**Sections to keep verbatim:** Quick Start (lines 20-33), Installation (lines 53-85), Configuration (lines 88-97), Usage Examples (lines 120-155). Do not restructure these.

**Screenshots section** (lines 98-102): Keep the section heading and `<p align="center">` img tag structure. Planner should note that screenshot src paths are updated at walkthrough time (D-05/D-06) — leave a placeholder comment in the plan action, not a stub img tag.

---

### `SECURITY.md` (security policy, add section)

**Analog:** `SECURITY.md` (existing file, all 45 lines in context above)

**Existing structure to preserve** (lines 1-45):
- `# Security Policy`
- `## Supported Versions` table (lines 3-10)
- `## Reporting a Vulnerability` with sub-sections How to Report, What to Expect, Disclosure Policy (lines 12-37)
- `## Security Best Practices for Users` bulleted list (lines 39-45)

**New section to add** — insert between `## Reporting a Vulnerability` and `## Security Best Practices for Users`:
```markdown
## Security Posture

SeedSyncarr is designed to be self-hosted on a private network, and several protections are active by default:

- **Encrypted secrets at rest** — API tokens, webhook secrets, and *arr API keys are Fernet-encrypted in the config file (AES-128-CBC + HMAC-SHA256); the keyfile is generated with restrictive (0600) permissions on first enable.
- **HMAC-verified import webhooks** — Sonarr/Radarr webhook payloads are HMAC-SHA256 verified when a secret is configured. Use `webhook_require_secret = true` (opt-in) to fail-closed: unauthenticated calls are rejected with 503 when the requirement is on and no secret is set.
- **Bearer auth** — The API requires a Bearer token when `api_token` is set; this is opt-in and especially important for non-loopback binds.
- **IP-resolution guard on *arr connection URLs** — When you test or connect a Sonarr/Radarr server, the user-supplied URL is resolved and rejected if it points to a private, loopback, reserved, or link-local IP. This is an IP-resolution SSRF guard on the outbound *arr request (not a full SSRF library, and DNS-rebinding/TOCTOU is a documented out-of-scope limitation for a homelab tool). SeedSyncarr *receives* import webhooks; it does not send outbound webhooks.
- **CSP headers** — A Content Security Policy header is sent on all responses (layered with Angular's hash-based meta CSP).
- **Rate limiting** — The webhook endpoints (60/60s), the POST config-set endpoint (60/60s), the Sonarr/Radarr test-connection endpoints (5/60s), the bulk-command endpoint (10/60s), and the status endpoint (60/60s) are rate-limited. (Single-file command and autoqueue endpoints are not rate-limited — do not claim blanket "all mutable endpoints.")
- **Log-injection protection** — File names are sanitized for CR/LF and control characters before reaching log lines (CWE-117).

**This is not a substitute for network isolation.** Place SeedSyncarr behind a reverse proxy with authentication if you expose it beyond localhost.
```

> **ACCURACY GUARD (codex-review correction, 2026-06-02):** Two bullets above were corrected from earlier factually-wrong wording.
> - **SSRF (CRITICAL #2):** earlier said "Outbound webhook calls validate destination URLs to prevent server-side request forgery." WRONG — SeedSyncarr does not send webhooks. The guard is an IP-resolution check on the user-supplied Sonarr/Radarr *connection* URLs at test/connect time: `config.py:54-84` `_validate_url` (resolves via `socket.getaddrinfo`, rejects private/loopback/reserved/link-local), applied at `config.py:147` inside `_test_arr_connection`. The code itself documents it is NOT a full SSRF library and that DNS-rebinding/TOCTOU is out of scope. Frame it honestly as an IP-resolution guard.
> - **Rate limiting (CRITICAL #1):** earlier said "mutable HTTP endpoints are rate-limited" as a blanket. WRONG — only five decorator sites carry `@rate_limit`. Ground-truth decorator map (enumerate these before writing the claim):
>   - `webhook.py:40-41` — sonarr/radarr webhook → `rate_limit(max_requests=60, window_seconds=60)` (applied INSIDE the require-secret guard)
>   - `config.py:27` — POST config-set → `rate_limit(60, 60)`
>   - `config.py:31,35` — sonarr/radarr test-connection → `rate_limit(5, 60)`
>   - `controller.py:73` — bulk command → `rate_limit(10, 60)`
>   - `status.py:16` — get-status → `rate_limit(60, 60)`
>   - NOT rate-limited: single-file command endpoints (`controller.py:66-70` queue/stop/extract/delete_local/delete_remote), autoqueue add/remove/get (`auto_queue.py` — no `rate_limit` import at all), config-get (`config.py:24`).
> Any draft asserting rate-limiting MUST enumerate the actual decorators in `src/python/web/handler/` first — no claim from pattern memory.

**Honesty pass on contact** (line 18): The email `thejuran@users.noreply.github.com` is a GitHub noreply address. Planner should update to use GitHub's private security advisory feature (`https://github.com/thejuran/seedsyncarr/security/advisories/new`) instead of or alongside the noreply email, as it's the standard maintained path.

---

### `CONTRIBUTING.md` (contributor doc, freshen)

**Analog:** `CONTRIBUTING.md` (existing ~44 lines, all in context above) + `docs/DEVELOPMENT.md` (lines 1-80 in context) for the full build command table

**Current structure to keep:**
- `## Reporting Bugs` — keep as-is (links to issue templates)
- `## Requesting Features` — keep as-is
- `## Development Setup > Prerequisites` — update to match `docs/DEVELOPMENT.md` (add Poetry prerequisite, currently missing)
- `## Development Setup > Getting Started` — expand steps 4/5 to show `ruff check` and `karma` invocations explicitly

**Getting Started expansion pattern** (from `docs/DEVELOPMENT.md` lines 14-34 and `docs/DEVELOPMENT.md` Makefile table):
```markdown
### Getting Started

1. Fork and clone the repository
2. Install Python dependencies: `cd src/python && poetry install`
3. Install Angular dependencies: `cd src/angular && npm install`
4. Run Python unit tests: `make run-tests-python`
5. Run Angular unit tests: `make run-tests-angular`

### Code Quality Checks

- **Python lint/format**: `ruff check src/python && ruff format --check src/python`
- **Angular lint**: `cd src/angular && npm run lint`
- **E2E tests** (requires Docker): `make run-tests-e2e`
```

**PR flow section** — keep the four-item list (lines 36-39), add explicit mention of ruff + lint as a pre-submit check matching the PR template checklist (`.github/pull_request_template.md` lines 21-24).

**Tone register:** Terse, imperative, no emojis. Match existing CONTRIBUTING.md register, not the longer docs/ prose style.

---

### `CODE_OF_CONDUCT.md` (community-health, create)

**Analog:** `.github/ISSUE_TEMPLATE/bug_report.yml` (tone: plain, welcoming, GitHub-native community-health conventions)

**Pattern:** Standard Contributor Covenant 2.1. No customization needed beyond the project name and contact method. Use the canonical template verbatim:

```markdown
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone...

## Our Standards
...

## Enforcement Responsibilities
...

## Scope
...

## Enforcement
...

## Enforcement Guidelines
...

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.1, available at
[https://www.contributor-covenant.org/version/2/1/code_of_conduct.html][v2.1].
```

**Contact field:** Use the same contact as SECURITY.md (GitHub security advisory link or maintainer email). File lives at repo root — same level as `CONTRIBUTING.md` and `SECURITY.md`.

---

### `CHANGELOG.md` (changelog, add [1.4.0] entry)

**Analog:** `CHANGELOG.md` [1.3.0] entry (lines 7-30) — this is the exact structural and tonal model.

**[1.3.0] entry shape to replicate** (lines 7-30):
```markdown
## [1.3.0] - 2026-06-02

A reliability and quality release delivered across four work streams (...). No configuration
changes or migrations are required; existing config files (including encrypted ones) load unchanged.

### Security

- bullet
- bullet

### Fixed

- bullet

### Changed

- bullet
```

**[1.4.0] entry to prepend above [1.3.0]:**
- Lead paragraph: one sentence capturing the release theme (presentation + launch hardening: hardened public surface, community-health files, v1.4.0 documentation).
- `### Security` subsection: HMAC opt-in fail-closed shipped (folded from Phase 111/112 — already in [1.3.0] under security; D-11 says summarize launch-hardening work, so the [1.4.0] entry covers the Phase 113 presentation track specifically — security-posture documentation is the security item here).
- `### Changed` subsection: README rewrite, SECURITY.md posture section, CONTRIBUTING.md freshen, CODE_OF_CONDUCT.md added, LICENSE.txt renamed to LICENSE.
- No `### Fixed` or `### Added` unless planner identifies distinct items from the phase.

**Footer link pattern** (lines 168-175): Add a `[1.4.0]` compare link at the bottom following the existing pattern:
```markdown
[1.4.0]: https://github.com/thejuran/seedsyncarr/compare/v1.3.0...v1.4.0
```

**Do not** add a `[1.3.0]` compare link (it's already missing from the footer — the [1.3.0] entry is the most recent and has no compare link yet; [1.4.0] will need one referencing v1.3.0...v1.4.0).

---

### `LICENSE.txt` → `LICENSE` (rename)

**Analog:** `LICENSE.txt` itself — content is Apache 2.0, correct and complete. This is a filename-only change.

**Pattern:** No content edits. The associated changes are the README badge link (line 18), the README license prose (line 118), AND the `ACKNOWLEDGMENTS.md` license link (line 34 — `[LICENSE](LICENSE.txt)`). All three break on the rename.

> **AUDIT-SCOPE GUARD (codex-review correction, 2026-06-02):** The LICENSE-rename audit MUST be repo-wide over user-facing tracked markdown, not README-only. At minimum `README.md` AND `ACKNOWLEDGMENTS.md` link to `LICENSE.txt` and both break. The acceptance gate is `grep -rn 'LICENSE\.txt' README.md ACKNOWLEDGMENTS.md` (and any other published root `.md`) returns zero hits after the rename. Historical `.planning/` artifacts (FILE_INVENTORY.md, ROADMAP.md, prior-phase docs) are NOT user-facing links and are out of scope for the fix — do not rewrite planning history.

**Executor note:** `git mv LICENSE.txt LICENSE` — one command, no content diff.

---

### `113-TEARDOWN.md` (phase-internal artifact, cynical-reader teardown)

**Analog:** `release-notes.md` (plain prose, no front-matter, no generated-by comment, accessible register)

**Structure pattern:**
```markdown
# Cynical-Reader Teardown — SeedSyncarr README v[draft]

**Framing:** r/selfhosted commenter, first impression in 30 seconds.

## First Impressions

[bullet-style honest critique of above-the-fold claims]

## Credibility Gaps

[any claims that a skeptic would challenge: "prove it", missing screenshots, badge
 states, fork positioning bravado]

## Install Path Issues

[broken steps, missing prereqs, version drift, anything that would cause a first-run failure]

## Security Claims

[any unsupported assertions, anything that reads as oversell]

## What Actually Lands

[the positives a fair reader would note]

## Priority Fixes Before Rewrite Finalization

1. ...
2. ...
```

**Tone:** Direct, adversarial but fair, first-person "I would immediately ask...". Not a bullet dump — complete sentences that a real commenter would write.

---

### `113-CODEX-PASS.md` (phase-internal artifact, codex adversarial pass)

**Analog:** `.planning/milestones/v1.4.0-phases/110-hostile-reader-discovery-pass/110-FINDINGS.md` (structured findings with severity tiers and disposition tracking)

**Structure pattern** (derived from 110-FINDINGS conventions):
```markdown
# Codex Adversarial Content Pass — Phase 113

**Target:** README.md (draft) + SECURITY.md (draft)
**Pass type:** Technical-claims accuracy + credibility

## Methodology

Brief description of what the pass checks (install steps reproducibility, version claims,
security assertions vs actual code, broken links, doc/code drift).

## Findings

### CONTENT-01 — [short title]
**Severity:** high / medium / low
**File:** README.md, line X
**Issue:** [exact claim vs reality]
**Disposition:** fix / accept / defer

...

## Summary

| Severity | Count | Disposition |
|---|---|---|
| high | N | ... |
| medium | N | ... |
| low | N | ... |
```

**Scope note:** This pass targets *content credibility* (install steps work, security claims accurate to shipped code), not engineering approach — distinct from the orchestrator's per-phase plan review.

---

### `113-REPO-METADATA.md` (phase-internal artifact, GitHub About draft)

**Analog:** `release-notes.md` (copy-paste-ready plain text; no markdown structure, just content for a human to paste into a web UI)

**Structure pattern:**
```markdown
# GitHub Repo Metadata — Draft for Manual Application

> Apply via: GitHub repo → Settings (gear icon top-right of repo page) → About

## Description (max 350 chars)

[one sentence: owned-axis value prop, fits GitHub About field]

## Topics / Tags (max 20, lowercase, hyphens)

[comma-separated list, e.g.: self-hosted, arr, sonarr, radarr, seedbox, lftp, media-server,
 docker, python, angular, webhook, automation, file-sync, homelab]

## Homepage URL

https://thejuran.github.io/seedsyncarr

---

> Note: This file is a draft for manual maintainer application. The GitHub web UI cannot be
> edited from the CLI session. Apply after walkthrough sign-off.
```

**Topic domain** (from CONTEXT.md discretion block): draw from `self-hosted / *arr / seedbox / sync` domain. Include `sonarr`, `radarr`, `seedbox`, `lftp`, `homelab`, `docker`, `python`, `angular`, `media-server`, `file-sync`, `webhook`.

---

## Shared Patterns

### Voice and register
**Source:** `README.md` (existing) and `release-notes.md`
**Apply to:** All modified repo-facing docs (README, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md)

- Terse, declarative, no em-dash overuse except in established places (the existing README uses em-dash in feature bullets — match that).
- No first-person ("we" is fine in CoC and CONTRIBUTING; avoid in README/SECURITY/CHANGELOG).
- No emojis in Markdown prose. The existing SECURITY.md uses `:white_check_mark:` / `:x:` in a table — that is acceptable in that specific table context only.
- Sentence case for headings (existing pattern throughout).

### Badge syntax
**Source:** `README.md` lines 15-18
**Apply to:** README.md badge block only
```markdown
[![CI](https://github.com/thejuran/seedsyncarr/actions/workflows/ci.yml/badge.svg)](https://github.com/thejuran/seedsyncarr/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/thejuran/seedsyncarr)](https://github.com/thejuran/seedsyncarr/releases)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/thejuran/seedsyncarr/pkgs/container/seedsyncarr)
[![License](https://img.shields.io/github/license/thejuran/seedsyncarr)](LICENSE)
```
The license badge uses `https://img.shields.io/github/license/...` which calls the GitHub license API — it only resolves correctly when the file is named `LICENSE` (not `LICENSE.txt`).

### Keep a Changelog format
**Source:** `CHANGELOG.md` lines 1-30
**Apply to:** CHANGELOG.md [1.4.0] entry
- `## [version] - YYYY-MM-DD` heading
- One-paragraph release summary before subsections
- Subsections: `### Security`, `### Fixed`, `### Changed`, `### Added` (only include subsections that have entries)
- Footer compare links at bottom of file

### Community-health file placement
**Source:** `CONTRIBUTING.md`, `SECURITY.md` (both at repo root)
**Apply to:** `CODE_OF_CONDUCT.md`
- Repo root, not `.github/` — the existing community-health files live at root; follow that convention.

### Phase artifact front-matter
**Source:** None present in existing phase dirs (110-FINDINGS.md has no YAML front-matter; release-notes.md has no front-matter)
**Apply to:** `113-TEARDOWN.md`, `113-CODEX-PASS.md`, `113-REPO-METADATA.md`
- No YAML front-matter. Start with `# Title`.
- First non-heading line: a brief `**Framing:**` or `**Target:**` context line.

---

## No Analog Found

All artifacts have close analogs. No entries in this table.

---

## Metadata

**Analog search scope:** repo root, `.github/`, `docs/`, `release-notes.md`, `CHANGELOG.md`
**Files read:** README.md, CHANGELOG.md, SECURITY.md, CONTRIBUTING.md, LICENSE.txt (first 5 lines), docs/GETTING-STARTED.md, docs/DEVELOPMENT.md, docs/CONFIGURATION.md, release-notes.md, .github/pull_request_template.md, .github/ISSUE_TEMPLATE/bug_report.yml
**Pattern extraction date:** 2026-06-02
**Revised:** 2026-06-02 (codex adversarial-review corrections: SECURITY.md SSRF wording fixed to IP-resolution guard on *arr connection URLs; rate-limiting wording fixed to enumerate the five actual decorator sites; LICENSE-rename audit broadened repo-wide incl. ACKNOWLEDGMENTS.md; outbound-push honesty guard added to the fork note)
