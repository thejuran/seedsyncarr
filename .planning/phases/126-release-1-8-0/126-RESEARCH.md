# Phase 126: Release 1.8.0 - Research

**Researched:** 2026-10-28
**Domain:** Release engineering (Dependabot roll-in, CI-gated tag/publish pipeline, digest-pinned NAS deploy/rollback) — no new product code
**Confidence:** HIGH (every claim below is either read directly from this repo's files/CI history, confirmed live against `gh api`/NAS, or checked with `slopcheck`/registry lookups; nothing in this phase depends on unfamiliar third-party library behavior)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dependency roll-ins (REL-05)** — Snapshot taken 2026-10-28. Re-check at release time.
- **D-01:** Roll in **every open Dependabot PR**: #136 certifi (runtime: the shipped CA bundle), #135 vite, #138 follow-redirects, #130 @modelcontextprotocol/server + @angular/cli, #131 npm_and_yarn group (23 updates, including Angular framework 22.2.1→22.2.3/4 patch bumps that ship in the UI bundle and a `@types/jasmine` 6→7 major), #141 mkdocs-material, #125 testfixtures and #117 puppeteer. Goal: zero open Dependabot alerts (9 open on 2026-10-28, all dev-scope npm: vite ×5, follow-redirects ×2, MCP SDK ×2) and an empty Dependabot PR queue at tag time.
- **D-02:** If any of these updates breaks the build, the Angular unit tests/Karma thresholds, e2e, or the Python suite, **stop and ask the owner** with the specifics: which update, what failed, and the options (drop it, or fix it with an estimated size). Don't silently drop an update and don't expand into an open-ended fix.
- **D-03:** Backlog 999.4 (braces/karma advisory) gets rechecked as part of this review, with the outcome recorded: current advisory status, affected versions, and whether the D-01 roll-ins resolve it. Its original PR #128 is now CLOSED. #125 and #117 are folded in by D-01.
- **D-04 (carried from 119.1 D-07):** If a NEW runtime/shipped security alert appears between this review and the tag push, raise it to the owner. Don't add it silently.
- **D-05:** The owner gets the final dependency list in plain terms (what was rolled in, what each touches, alert count before and after) at the pre-tag approval checkpoint (D-13).

**Release notes (CHANGELOG + release-notes.md)**
- **D-06:** Production and most users upgrade from 1.7.6, so the 1.8.0 notes cover everything since 1.7.6. Finalize the existing `[Unreleased]` CHANGELOG draft (which currently only covers Phase 125) as `[1.8.0]`.
- **D-07:** Order: **Security first** (1.7.6 pattern), then **Changed** (the Test Connection behaviour change, which is why this is a minor version), then **Fixed**, then the rollback runbook in release-notes.md, plus the standard CHANGELOG link line the release-metadata check requires.
- **D-08:** **Security** contains Phase 125's existing entries (keep the owner-approved 125 D-13 wording) plus Phase 121: the app's API token was sent with the GitHub update-check request (to GitHub), and 1.8.0 sends it only to SeedSyncarr's own API. Include a plain suggestion to rotate the API token after upgrading as a cheap precaution, in the same plain tone as the 1.7.6 notice and with no exploit detail. **Check the exact exposure conditions in the Phase 121 artifacts before writing** (e.g. only when an API token is configured, which versions are affected), and state only what's verified.
- **D-09:** **Fixed** gets one plain-English line each for 122 (webhook test events now appear in the log; a dropped hold is no longer logged as "cleared"), 123 (a startup that fails partway shuts down already-started parts cleanly, and one part failing to shut down no longer stops the rest), and 124 (a slow or backgrounded browser tab catches up to current state instead of falling behind, with bounded memory). No internals.
- **D-10:** The Test Connection **Changed** entries from Phase 125 stay as drafted (125 D-10/D-14 wording), edited only for accuracy and flow.

**Sandbox smoke (REL-06)**
- **D-11:** Smoke on the standing sandbox **`seedsyncarr-test`**, repinned to the exact published `:1.8.0@sha256:…` digest (record the digest it replaces). It may stay on 1.8.0 afterwards because that's a release tag. Production is read-only during the smoke.
- **D-12:** Run the integration, import, webhook and cleanup checks against **`sonarr-v4`** (4.0.20) to mirror production's v4 Sonarr, plus Radarr. Add a quick Test Connection against `sonarr-v5`. Restore the sandbox's arr URLs/wiring after the smoke, as in Phase 120 D-03 and Phase 125 D-09.
- **D-12a:** Must pass: restart; a real transfer; Sonarr (v4) and Radarr integration; auto-delete/cleanup. **Plus 1.8.0 spot checks:** Test Connection succeeds with a container name (e.g. `http://sonarr-v4:8989`) and still refuses `http://169.254.169.254` with the new message; a fresh start's container log contains no configured secret values (count-only check, values never printed); the GitHub update-check request carries no app token; a webhook test event appears in the app log.

**Approvals, production deploy and rollback (REL-06)**
- **D-13:** **Two owner checkpoints.** (1) **Before pushing the `v1.8.0` tag**, because publishing can't be undone. Show the final notes, the dependency list (D-05) and CI status. (2) **Before the production deploy**, with the smoke results.
- **D-14 (carried from 119.1 D-08/D-09):** Release route: release branch + PR CI green (Python suite, whole-tree ruff, Angular tests, e2e, Docker build, CodeQL, packaging check) → merge keeping history → annotated `v1.8.0` tag from main → tag CI publishes GHCR/GitHub/PyPI → sandbox smoke on that digest → production. Bump version metadata to 1.8.0 everywhere 1.7.6 set it. One PR for the phase (the Dependabot roll-ins land on the release branch/PR, not as separate merges, unless the planner has a stated reason).
- **D-15:** Production compose pinned to `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:<same digest as smoked>`. Never `:dev`, never a local build (NAS QEMU blocks it). Back up persist files and compose before the upgrade. Handle wud as in 1.7.6 (pause around the deploy, restore last).
- **D-16:** **Rollback policy:** if production clearly can't sync after deploy (container won't start or stay up, scans keep failing with no later success, Sonarr/Radarr unreachable), immediately roll back to `:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` using the backups, then tell the owner. For anything ambiguous, stop and ask. The release-notes rollback runbook targets 1.7.6. Research must confirm whether 121–125 changed any persisted state or config in a way that makes rollback unsafe or needs extra steps, and document those steps.
- **D-17:** **Done when:** a successful scan after start (any warm-up scanner error must be followed by a later successful scan), Sonarr/Radarr reachable with no stuck holds, wud restored, then the owner confirms (recorded). Waiting for a real production import is NOT required.

### Claude's Discretion
- How the Dependabot changes are merged into the release branch (cherry-pick, rebase, or regenerating lockfiles), provided the result is equivalent and CI-verified.
- Smoke scripting and evidence-file layout (reuse the 119 REL03 / 122 SAFE01 evidence pattern).
- Exact wording of the release-note lines within D-07–D-10.
- Order and grouping of plans/waves.

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within phase scope. (Backlog items such as scanner buffering, extract-staging hardening, 999.5 Sonarr API v5 and 999.6/999.7 stay in the backlog and are not part of 1.8.0.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-05 | Open Dependabot alerts and PRs are reviewed before the version bump/tag; runtime/shipped fixes are rolled in, dev-only ones only if cheap (includes the 999.4 braces/karma recheck) | §Dependabot roll-in mechanics, §999.4 recheck, §Package Legitimacy Audit — concrete PR list, overlap analysis, exact alert→fix mapping, and a tested roll-in strategy (regenerate-lockfile, not cherry-pick) |
| REL-06 | 1.8.0 is published (Docker/GitHub/PyPI), smoke-tested on the NAS by exact digest (restart, transfer, integration, cleanup), and deployed to NAS production by that digest, with a successful post-deploy scan confirming recovery | §Release pipeline mechanics, §Version bump sites, §Rollback safety, §Sandbox smoke procedure, §Prod deploy + wud + backups — exact commands and file list reused/adapted from 119.1-REL04 and 122-SAFE01 evidence |
</phase_requirements>

## Summary

Phase 126 is pure release engineering: no new product behavior, so there is nothing to "design." The two open questions that actually drive planning are (1) how to land eight open Dependabot PRs — four of which touch the same `src/angular/package-lock.json` — onto one release branch without a manual merge-conflict mess, and (2) whether 121–125 changed anything that makes the committed rollback target (1.7.6) unsafe. Both are now answered with evidence, not assumption.

On rollback: **`git diff v1.7.6..main` shows zero changes to `src/python/common/persist.py`, `src/python/common/config.py`, `src/python/controller/controller_persist.py`, or `src/python/controller/auto_queue.py`.** No persist file format, no new/removed/renamed `settings.cfg` key, no new secret field. Rollback to 1.7.6 is a plain redeploy of the old digest with the existing three-file backup/restore procedure — materially *simpler* than the 1.7.6-era rollback runbook, because the target (1.7.6) already has the SEC-01 startup-log fix, so the "rotate again, your credentials get reprinted" caution from that runbook does **not** apply to a 1.8.0→1.7.6 rollback. The one real rollback caveat is behavioral, not data-format: if an operator saves a Sonarr/Radarr URL on 1.8.0 that only validates under Phase 125's broadened rules (a Docker container name, or an IPv6 ULA/CGNAT edge case), rolling back to 1.7.6 makes the **Test Connection button** refuse that URL again — but this does not break live sync, because `_validate_url` is only called by the Test Connection endpoint, never by the actual Sonarr/Radarr queue-polling path. Production's current Sonarr/Radarr URLs are LAN IPs (`192.168.7.233`), which pass both the old and new guard, so today's production config carries zero rollback risk from this change.

On the Dependabot roll-in: all 9 currently-open alerts are **dev-scope npm** (5× vite, 2× follow-redirects, 2× `@modelcontextprotocol/server`), confirmed by `gh api .../dependabot/alerts` and cross-checked with `npm audit`. Three of the eight open PRs (#136 certifi, #125 testfixtures, #141 mkdocs-material) are independent single-package `poetry.lock`-only diffs with no interaction. One (#117 puppeteer) touches the root `package.json`/`package-lock.json`, also independent. The remaining four (#130, #131, #135, #138) all touch `src/angular/package-lock.json`, and two of them (#130, #131) both bump `@angular/cli` — #131's target (22.2.4) supersedes #130's (22.2.3), but #130 *also* carries the only fix for the `@modelcontextprotocol/server` alerts, which #131 does not touch. The two PRs cannot both be cherry-picked cleanly (same lines, different target versions). **Recommended approach: regenerate, not cherry-pick** — update `package.json` version ranges for the one major bump (`@types/jasmine` 6→7) and run `npm install`/`poetry update` naming every target package at once, the same pattern already proven in 119-REL03 (`poetry update cryptography pytz`, `npm update source-map-js`). This produces one clean, CI-verified lockfile diff per manifest instead of three conflicting ones.

The single biggest non-obvious risk found: **`@types/jasmine` 6→7 is a major bump that the project's own `.github/dependabot.yml` did not block**, even though it explicitly blocks the matching `jasmine-core` major bump with the comment "karma-jasmine 5 cannot patch jasmine 7 globals." Jasmine 7's own release notes confirm Zone.js cannot monkey-patch jasmine-core 7, and karma-jasmine is unmaintained against it — but this PR only bumps the *type declarations*, not the runtime (`jasmine-core` stays pinned at 6.3.0), so the practical risk is a `tsc`/Karma type-mismatch, not a Zone.js crash. This must be verified (`ng test` + a TS compile) in isolation per D-02 before folding it into the group commit.

A second non-obvious finding: **`SECURITY.md`'s "IP-resolution guard on *arr connection URLs" bullet is now factually wrong.** It still says the guard "rejects" private/loopback/reserved/link-local IPs — but Phase 125 flipped that: the guard now *allows* private-range IPs and Docker container names (that is the entire LAN-01 point) and only blocks link-local/reserved/metadata addresses. `git diff v1.7.6..main -- SECURITY.md` confirms zero changes to this file since 1.7.6. The 119.1 release already had an owner catch exactly this class of drift (SECURITY.md's encryption claim) at the pre-tag checkpoint — fixing it proactively here avoids a repeat.

A third finding worth flagging to the planner: there is **no dedicated Radarr test instance on the NAS** (there is a `sonarr-v4` and a `sonarr-v5` for Sonarr, but only one `radarr` container, which is the live production library). The sandbox's `/server/webhook/radarr` endpoint exists and works identically to the Sonarr one (receiving a synthetic signed webhook does not touch any real Radarr instance), so the import/cleanup half of D-12a's "Radarr integration" check is fully achievable without touching production Radarr. A live Radarr *queue-polling* integration check (the ArrQueueClient actually calling a reachable Radarr) would need to point at the real `radarr` container — reachable from `seedsyncarr-test` on the shared `docker_default` network — which is read-only/non-destructive (GET `/api/v3/queue` only) but will never show a matching entry for a synthetic test file, so it can prove reachability but not a completion-gate release. This is flagged as an Open Question with a recommended default (reachability + webhook, not a full completion-gate replay — that was already exhaustively proven for Sonarr in Phase 122 and does not need re-proving per-arr for a release smoke).

**Primary recommendation:** Treat this phase as five sequential waves — (1) Dependabot roll-in on the release branch via lockfile regeneration with isolated verification of the `@types/jasmine` bump, plus the SECURITY.md fix and the 999.4 recheck record; (2) version bump + CHANGELOG/release-notes finalization + owner checkpoint 1 (pre-tag); (3) tag, publish, verify GHCR/PyPI/GitHub release; (4) sandbox smoke on the exact digest reusing the 122/125 teardown-script pattern extended with a `radarr_url` restore key; (5) owner checkpoint 2 (pre-prod) → prod deploy by digest with the exact backup/verify/wud sequence from 119.1-REL04 → owner confirmation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dependabot alert/PR triage | Build tooling (CI config + lockfiles) | — | Pure dependency-metadata work; no application tier touched |
| Version bump / CHANGELOG / release-notes | Build tooling (repo metadata files) | — | Text and JSON/TOML files consumed by `scripts/verify-release-metadata.mjs`, not runtime code |
| Tag → build → publish pipeline | CI/CD (`.github/workflows/ci.yml`) | GHCR / PyPI / GitHub Releases (external services) | GitHub Actions owns build, test-gating and publish; external registries are passive storage |
| Sandbox smoke test | Ops/Deployment (NAS Docker, `seedsyncarr-test`) | API/Backend (SeedSyncarr's own `/server/*` endpoints, invoked over HTTP from the smoke script) | Verifies the published artifact's backend behavior from outside the process, not by reading source |
| Production deploy + rollback | Ops/Deployment (NAS Docker Compose, digest pin) | Database/Storage (three persist files: `settings.cfg`, `controller.persist`, `autoqueue.persist`) | Compose/image-pin changes are infra; persist-file backup/restore is the data-safety half of the same operation |
| wud (Watchtower-like updater) pause/restore | Ops/Deployment (NAS Docker) | — | A third-party automation tool that must be quiesced around the deploy window to avoid racing the manual pin |

## Standard Stack

This phase installs/upgrades existing dependencies only — it does not introduce any new library. "Standard Stack" here means the release-engineering tooling already established by Phases 118/119/119.1/122/125, all of which is reused unchanged.

### Core (release tooling, already in the repo)
| Tool | Version (pinned where relevant) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scripts/verify-release-metadata.mjs` | repo script, no version | CI gate: CHANGELOG `[X.Y.Z]` heading, release-notes `{{VERSION}}` link, `package.json`/`src/angular/package.json`/`src/angular/package-lock.json` version fields all match the pushed tag | [VERIFIED: repo file] — already the authority for "did I bump every version site" |
| `ruff` | `0.15.22` (hard-pinned in `ci.yml`, separately from `poetry.lock`'s `ruff>=0.15,<0.16`) | Whole-tree Python lint gate | [VERIFIED: `.github/workflows/ci.yml:91`] — comment explicitly warns "bump together with the poetry.lock ruff version"; no Dependabot PR touches ruff this round, so no action needed, but any `poetry update` must stay scoped to the named packages to avoid silently drifting `poetry.lock`'s ruff pin out of sync with CI's hardcoded one |
| `slopcheck` | `0.6.1` (installed this session) | Package-legitimacy scan before recommending any dependency bump | [VERIFIED: ran locally, see Package Legitimacy Audit] |
| `gh` CLI | n/a | Dependabot alert/PR triage, CI run/job log inspection, release view | [VERIFIED: used throughout this research] |

### Supporting (NAS/deploy tooling, already in the repo)
| Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `teardown.sh` pattern (`125-teardown.sh` is the most recent) | repo script per phase dir | Idempotent sandbox restore: image pin, `sonarr_url`, wait-for-status, final verification | Copy and extend for 126 — add a `RADARR_URL_L0`/`RADARR_URL_SET` restore pair (Phase 125's script only tracks `SONARR_URL_*`) |
| `extract_secrets.py` (119.1-04, sha256 `c35768d7…baef6`) | repo script, committed in phase evidence dirs | Count-only secret-in-log check: reads `Config.secret_fields()`, never prints a value | Reuse verbatim for the 1.8.0 "no secrets in startup log" D-12a spot check |
| `118-05-parse_check.py` (sha256 `920363ac…dd53`) | repo script | Read-only loader check of `settings.cfg`/`controller.persist`/`autoqueue.persist` against both the old and new image, before/after a prod deploy | Reuse verbatim — `common/config.py`/`controller_persist.py`/`auto_queue.py` are byte-for-byte unchanged since 1.7.6, so this script's PASS result is guaranteed in both directions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Regenerating lockfiles via `npm install`/`poetry update <pkg>...` | Cherry-picking each Dependabot PR's single commit | Cherry-pick is faithful to Dependabot's own tested diff, but #130 and #131 touch overlapping lines in `src/angular/package-lock.json` with different target versions for `@angular/cli` — a clean cherry-pick of both is not possible; regeneration lets npm's resolver produce one consistent lockfile reflecting every target version at once (precedent: 119-REL03 already used `poetry update <names>` / `npm update <name>` rather than cherry-picks) |
| A dedicated throwaway Radarr container for the sandbox smoke's Radarr check | Pointing `radarr_url` at the real production `radarr` container (read-only `/api/v3/queue` polling only) | The real-container approach is zero-setup and genuinely read-only (no write call exists on that path), but can only prove reachability, not a completion-gate release, since a synthetic test file will never appear in the real queue; a throwaway container (mirroring the disposable-ssh-remote pattern from 119.1-04) would let a full release-on-completion proof run, at the cost of extra setup/teardown the phase may not need (Sonarr's full completion-gate matrix was already exhaustively proven in Phase 122) |

**Installation:** No new packages. Dependency version bumps only:
```bash
# Python (src/python), on the release branch:
cd src/python && poetry update certifi mkdocs-material testfixtures

# Root (puppeteer):
npm update puppeteer

# Angular (src/angular) — bump the one major range in package.json first,
# then let npm resolve everything else in one pass:
#   "@types/jasmine": "^6.0.0" -> "^7.0.0"
cd src/angular && npm install
```

**Version verification (ran this session):**
| Package | Target (from open PR) | Registry check | Result |
|---|---|---|---|
| certifi | 2026.10.19 | `pip index versions certifi` | [VERIFIED: PyPI] latest listed is 2026.10.23, 2026.10.19 present |
| testfixtures | 12.4.0 | `curl pypi.org/pypi/testfixtures/json` → `info.version` | [VERIFIED: PyPI] `"version": "12.4.0"` |
| mkdocs-material | 9.8.0 | `pip index versions mkdocs-material` | [VERIFIED: PyPI] latest listed 9.7.7 at research time, 9.8.0 is PR's target (one patch ahead of what PyPI's index endpoint shows — same index-lag behavior 119.1-04 observed for PyPI, non-blocking) |
| vite | 7.3.7 | `npm view vite@7 version` | [VERIFIED: npm] 7.3.7 exists in the 7.x line |
| follow-redirects | 1.16.2 | `npm view follow-redirects version` | [VERIFIED: npm] current npm latest is 1.16.2 |
| @modelcontextprotocol/server | 2.3.1 | `npm view @modelcontextprotocol/server version` | [VERIFIED: npm] current npm latest is 2.4.0; 2.3.1 is further back in the same major, confirmed to exist via the PR's own lockfile diff |
| @angular/cli (and the other 21 `npm_and_yarn` group packages) | 22.2.4 (cli), per-package per PR #131's table | `npm view @angular/cli version` | [VERIFIED: npm] current npm latest is 22.2.5; 22.2.4 confirmed to exist |
| @types/jasmine | 7.0.0 | `npm view @types/jasmine version` | [VERIFIED: npm] 7.0.0 exists, published 2026-09-29 |
| puppeteer | 25.16.0 | `npm view puppeteer version` | [VERIFIED: npm] current npm latest is 25.16.0, matches PR target exactly |

## Package Legitimacy Audit

All nine packages under version bump are long-established, already-vendored dependencies (no net-new package is being introduced). `slopcheck` (v0.6.1, installed this session) was run with `scan --pkg` on every package (not `install`, to avoid mutating the working tree during read-only research):

| Package | Registry | Downloads/Maturity | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| vite | npm | Extremely high; multi-year | github.com/vitejs/vite | [OK] | Approved |
| follow-redirects | npm | Extremely high; multi-year | github.com/follow-redirects/follow-redirects | [OK] | Approved |
| @modelcontextprotocol/server | npm | Official Anthropic/MCP SDK package | github.com/modelcontextprotocol/typescript-sdk | [OK] | Approved |
| @angular/cli (+ 21 sibling `npm_and_yarn` packages) | npm | Official Angular/Google tooling | github.com/angular/angular-cli (and angular/angular, microsoft/playwright, eslint/eslint, etc., per-package) | [OK] | Approved |
| @playwright/test | npm | Official Microsoft Playwright | github.com/microsoft/playwright | [OK] | Approved |
| @types/jasmine | npm | DefinitelyTyped official types | github.com/DefinitelyTyped/DefinitelyTyped | [OK] | Approved — see Common Pitfalls for the compatibility risk (not a legitimacy risk) |
| puppeteer | npm | Official Google/Puppeteer team | github.com/puppeteer/puppeteer | [OK] | Approved — has a `postinstall: node install.mjs` script (downloads a Chromium binary); this is the existing, already-reviewed behavior of the package already in use, not new risk introduced by the version bump |
| certifi | PyPI | Extremely high; multi-year; CA-bundle reference implementation | github.com/certifi/python-certifi | [OK] | Approved |
| testfixtures | PyPI | Long-established, widely used Python test helper | github.com/Simplistix/testfixtures | [OK] | Approved |
| mkdocs-material | PyPI | Long-established, widely used MkDocs theme | github.com/squidfunk/mkdocs-material | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

Postinstall-script check (Step 4 of the protocol, npm only): `npm view <pkg> scripts.postinstall` returned empty for vite, follow-redirects, `@modelcontextprotocol/server` and `@angular/cli`. `puppeteer` has `node install.mjs` (downloads the Chromium binary it bundles) — this is pre-existing, documented, expected behavior for this package (it is already a root devDependency today at 25.11.0) and not a new risk introduced by bumping to 25.16.0.

## Architecture Patterns

### System Architecture Diagram

```
 Dependabot PRs (GitHub)          Release branch (local/CI)
 ┌───────────────────┐    land    ┌─────────────────────────┐
 │ #130 #131 #135     │──────────▶│ lockfile regeneration     │
 │ #138 #136 #141     │  (D-01)   │ + version bump + CHANGELOG│
 │ #125 #117          │            │ + release-notes.md        │
 └───────────────────┘            └──────────┬───────────────┘
                                              │ push, PR CI green
                                              ▼
                                   ┌─────────────────────────┐
                                   │ Owner checkpoint 1 (D-13) │  <-- show notes, dep list, CI status
                                   │ "approve tag push"        │
                                   └──────────┬───────────────┘
                                              │ merge (keep history) -> tag v1.8.0
                                              ▼
                                   ┌─────────────────────────┐
                                   │ Tag CI (.github/ci.yml)   │
                                   │ publish-docker-image      │──▶ GHCR :1.8.0@sha256:…
                                   │ publish-github-release    │──▶ GitHub Release (release-notes.md, {{VERSION}} subbed)
                                   │ publish-pypi               │──▶ PyPI seedsyncarr==1.8.0
                                   └──────────┬───────────────┘
                                              │ exact digest
                                              ▼
                                   ┌─────────────────────────┐
                                   │ NAS sandbox smoke          │  <-- seedsyncarr-test repinned to :1.8.0@sha256:…
                                   │ (D-11/D-12/D-12a)          │      sonarr-v4 + radarr + sonarr-v5 spot check
                                   └──────────┬───────────────┘
                                              │ Owner checkpoint 2 (D-13)
                                              ▼
                                   ┌─────────────────────────┐
                                   │ NAS production deploy      │  <-- compose pin by digest, backups, wud pause/restore
                                   │ (D-15/D-16/D-17)           │      successful-scan confirmation, owner confirms
                                   └─────────────────────────┘
                                              │ only if sync clearly fails
                                              ▼
                                   ┌─────────────────────────┐
                                   │ Rollback to :1.7.6@sha256: │  (D-16 — see Rollback Safety below; data-format-safe)
                                   │ da6196e0…101e               │
                                   └─────────────────────────┘
```

### Recommended Wave Structure
```
Wave 1  — Dependency roll-in:         lockfile regeneration, isolated @types/jasmine verification,
                                       999.4 recheck record, SECURITY.md fix, full CI gate
Wave 2  — Release content:            version bump everywhere, CHANGELOG [1.8.0], release-notes.md,
                                       Owner checkpoint 1 (pre-tag)
Wave 3  — Publish:                    merge, tag, tag-CI verification (GHCR/GitHub/PyPI), digest capture
Wave 4  — Sandbox smoke:              repin seedsyncarr-test, run D-12/D-12a checks, restore wiring
Wave 5  — Production deploy:          Owner checkpoint 2, backup, deploy by digest, verify, wud, confirm
```

### Pattern 1: Lockfile regeneration instead of cherry-pick, for overlapping Dependabot PRs
**What:** When two+ open Dependabot PRs touch the same lockfile with overlapping/different target versions for the same package (here: #130 and #131 both bump `@angular/cli`), do not attempt to cherry-pick both PR commits onto the release branch. Instead, bump the one `package.json` range that needs a major-version change (`@types/jasmine` `^6.0.0`→`^7.0.0`), then run the package manager's own resolver naming every target package (or simply `npm install`/`poetry update <names>`), and let it produce one consistent lockfile.
**When to use:** Whenever 2+ open dependency PRs touch the same manifest/lockfile with any version overlap.
**Example (precedent, already used in this repo at 119-REL03):**
```bash
# Source: .planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md §"Dependabot roll-ins (D-21)"
cd src/python && poetry update cryptography pytz   # produced a lockfile diff limited to those two packages
cd src/angular && npm update source-map-js          # produced a lockfile diff limited to that one package
```

### Pattern 2: Idempotent NAS sandbox teardown/restore script
**What:** A bash script (`125-teardown.sh` is the current reference) that reads a small `state.env` key=value file, restores the sandbox's image pin and any config fields it changed this session, waits for `/server/status` to return 200, and verifies the restore with a read-back rather than trusting the write. Safe to run multiple times (every step checks current value before acting).
**When to use:** Any phase that repins `seedsyncarr-test` to a staging/release digest and changes its `sonarr_url`/`radarr_url` for a live check.
**Example:**
```bash
# Source: .planning/phases/125-lan-connection-tests/125-teardown.sh (committed in repo)
# Extend for 126: add a RADARR_URL_L0 / RADARR_URL_SET pair mirroring the existing
# SONARR_URL_L0 / SONARR_URL_SET pair (lines 64-65, 126-141), with a
# get_radarr_url()/set_radarr_url() pair hitting {section:"radarr",key:"radarr_url",...}
# the same way get_sonarr_url()/set_sonarr_url() do today.
```

### Pattern 3: Count-only secret verification, never print-and-check
**What:** A script that reads the application's own `Config.secret_fields()` list, decodes each configured secret's value, writes the values to a 0600 scratch file, then `grep -cFf` that file against the captured log — printing only match counts, field names and HTTP codes, never a value.
**When to use:** Any live check of "does this log contain a secret" — this is the project's established hygiene bar (per `extract_secrets.py`, used identically in 119.1-04 and the 119.1 production deploy).
**Example:**
```bash
# Source: .planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-REL04-EVIDENCE.md §"Step 9"/"1g"
sudo /usr/local/bin/docker run --rm -i --read-only --network none --cap-drop ALL \
  --user 1026:100 -v /volume1/docker/seedsync:/c:ro --entrypoint python3 -w /app/python \
  ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:<digest> - < extract_secrets.py > "$T/values" 2> "$T/fields"
sudo /usr/local/bin/docker logs seedsyncarr > "$T/log" 2>&1
grep -cFf "$T/values" "$T/log"   # must be 0; rc=1 confirms no match
```

### Anti-Patterns to Avoid
- **Cherry-picking overlapping Dependabot commits:** will conflict or silently under-apply (#130 vs #131's `@angular/cli` target). Regenerate instead.
- **Trusting `npm audit`'s package list as the alert source of truth:** `npm audit --json` surfaced `zod`, `qs`, `body-parser` and `fast-uri` as vulnerable transitive packages that have **no corresponding open GitHub Dependabot alert** (only 9 alerts are open, covering vite/follow-redirects/mcp-server). These are almost certainly resolved transitively once `@angular/cli`/`@modelcontextprotocol/server` are bumped; re-run `npm audit` after the bump to confirm, but don't treat its raw package list as a 1:1 match to GitHub's alert count.
- **Printing a secret value "just to confirm it saved":** every established pattern in this codebase (`extract_secrets.py`, the smoke scripts) counts matches, never echoes a value. This research itself inadvertently captured one live Sonarr API key value via an unauthenticated `curl` to the sandbox's `/server/config/get` during environment probing (see Open Questions) — do not repeat that in evidence files; redact or avoid reading that endpoint's response body when a key might be present.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Did I bump every version-metadata site?" | A manual checklist re-grep | `node scripts/verify-release-metadata.mjs 1.8.0` | Already exists, already CI-gated (`unittests-release-metadata` + `verify-release-metadata` jobs), covers CHANGELOG heading, release-notes link line, and 4 of the ~7 version sites automatically |
| "Which Dependabot alerts exist / are fixed by this bump?" | Reading PR titles and guessing | `gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '...'` (this session's exact queries are reproduced above) | GitHub's alert API is the ground truth for `state`, `vulnerable_version_range` and `first_patched_version`; PR titles can be stale relative to current `main` |
| "Is this new/bumped package safe?" | Manually eyeballing npm page / download counts | `slopcheck scan --pkg <ecosystem> <name>` | Already installed and run this session; gives a structured OK/SUS/SLOP verdict instead of ad hoc judgment |
| Secret-in-log verification | `grep` for literal known strings, or eyeballing logs | The existing `extract_secrets.py` (sha256-pinned, reused three times already) | Derives its field list from `Config.secret_fields()` — catches a *new* secret field automatically, not just the ones a human remembers to check |

**Key insight:** every tool this phase needs already exists in the repo from the three prior releases (1.7.4, 1.7.5, 1.7.6). The work is sequencing and re-running them against the current state, not building anything new.

## Rollback Safety (D-16 — detailed finding)

**Question:** Did Phases 121–125 change any persisted state, persist-file formats, config keys/`settings.cfg` schema, or on-disk layout such that running 1.7.6 against 1.8.0-written state is unsafe or needs extra steps?

**Answer: No.** Evidence:

```bash
$ git diff v1.7.6..main --stat -- src/python/common/persist.py src/python/common/config.py \
    src/python/controller/controller_persist.py src/python/controller/auto_queue.py
# (no output — zero changes to any of these four files)
```

`src/python/common/persist.py` (the sole writer of all three persist files, `Persist.to_file`) and `src/python/common/config.py` (the `Config` class and every `PROP(secret=True)` declaration, i.e. the entire `settings.cfg` schema including which fields are secret) are **byte-for-byte unchanged since 1.7.6**. `ControllerPersist` and `AutoQueuePersist` (the two other persisted-data classes) are also unchanged. The 229-line diff in `controller.py` and the 277-line diff in `web/handler/config.py` are runtime logic (import-credit bookkeeping, SSRF guard rules) — neither touches what gets written to disk or what key names `settings.cfg` understands.

**Practical consequences for the rollback runbook:**
1. **No data migration needed.** The existing three-file backup/restore procedure from 119.1-REL04 (`settings.cfg`, `controller.persist`, `autoqueue.persist`, each copied with a `.pre-1.8.0-<timestamp>` suffix, verified non-empty and checksummed before the deploy) is sufficient and needs no changes beyond the suffix/version string.
2. **The 119.1-era rollback runbook's "secrets get reprinted to the container log" caution does NOT apply** for a 1.8.0→1.7.6 rollback, because 1.7.6 already carries the SEC-01 fix (it's the version 1.7.6 itself that stopped printing `settings.cfg`). That caution only mattered for rollbacks to pre-1.7.6 targets.
3. **The `%`-in-secrets caution still applies identically**, because `common/config.py`'s interpolation-escaping behavior (the `%%`-encoding introduced in 119.1) is unchanged in 1.8.0. Before any rollback, remove `%` from any secret saved under 1.8.0, exactly as documented in the current `release-notes.md`.
4. **New behavioral-only rollback consideration (not a data-safety issue):** if an operator saves a Sonarr/Radarr URL on 1.8.0 that only validates under Phase 125's broadened `_validate_url` rules (a Docker container name like `http://sonarr:8989`, or specific IPv6 ULA/CGNAT ranges), rolling back to 1.7.6 makes the **Test Connection button** refuse that URL again with the old "private/reserved IP address" message. This does **not** break the actual sync path: `_validate_url`'s only caller is `_test_arr_connection` (the Settings-page Test button), confirmed in `src/python/web/handler/config.py` — the real `ArrQueueClient` queue-polling path never calls it. **Production's current configuration carries zero risk here**: both `sonarr_url` and `radarr_url` are set to the LAN IP `192.168.7.233` (confirmed via a live, read-only `curl` to `/server/config/get` this session), which passes both the pre-125 and post-125 guard identically.
5. **AutoDelete re-arm caution (carried from the 1.7.6 runbook, still applicable):** the 118-05 loader check on both images confirmed `AutoDelete.enabled=True` in the production backup at the 1.7.6 deploy; if that is still true at 1.8.0 deploy time, step (iii) of the rollback runbook (force `enabled = False` in the restored `settings.cfg` before starting 1.7.6) is still the correct precaution, for the same reason as before (the restored version doesn't know about any newer import-credit bookkeeping 1.8.0 may have recorded for an in-flight transfer).

**Recommended rollback runbook structure for `release-notes.md`:** reuse the exact 7-step structure from the 1.7.6 runbook (stop wud → stop seedsyncarr → restore 3 files with checksum verification → force `AutoDelete.enabled = False` → verify → re-pin compose to `:1.7.6@sha256:da6196e0e89a4d986381b3f3d14ff7c1c63e9ec02c807f6e8efde00fc4db101e` → `docker compose up -d` → verify → restore wud last), dropping only the "rotate again" caution (item 2 above) and keeping the `%`-in-secrets caution (item 3 above) and the AutoDelete caution (item 4 above).

## Dependabot Roll-In Mechanics (D-01 — detailed finding)

### Open alerts (ground truth, `gh api .../dependabot/alerts`, state=open, 2026-10-28)

| # | Package | Severity | Vulnerable range | First patched | Fixed by |
|---|---|---|---|---|---|
| 99,100,101,103,104 | vite | high/medium/low ×5 | `>=7.0.0, <=7.3.6` | 7.3.7 | PR #135 |
| 97, 98 | follow-redirects | high ×2 | `>=1.16.0, <1.16.1` | 1.16.1 | PR #138 (bumps to 1.16.2, satisfies) |
| 94, 96 | `@modelcontextprotocol/server` | medium, high | `>=2.0.0, <2.3.0` | 2.3.0 | PR #130 (bumps to 2.3.1, satisfies) |

All 9 are `scope: development` (dev-only npm packages in `src/angular`). Landing #135, #138 and #130 (or equivalent target versions via regeneration) closes all 9. `npm audit --audit-level=low --json` in `src/angular` additionally lists `@angular/cli`, `zod`, `qs`, `body-parser`, `fast-uri` as vulnerable (via the `@modelcontextprotocol/server`/`@angular/cli` dependency chain) — these have no separate GitHub alert number and should resolve transitively; **re-run `npm audit` after the bump to confirm zero remaining findings**, don't assume.

### PR overlap analysis (`gh pr view <n> --json files,additions,deletions`, 2026-10-28)

| PR | Manifest(s) touched | Independent? |
|---|---|---|
| #136 certifi 2026.1.4→2026.10.19 | `src/python/poetry.lock` only | Yes |
| #125 testfixtures 12.3.0→12.4.0 | `src/python/poetry.lock` only | Yes |
| #141 mkdocs-material 9.7.7→9.8.0 | `src/python/poetry.lock` only | Yes |
| #117 puppeteer 25.11.0→25.16.0 | root `package.json` + `package-lock.json` | Yes |
| #138 follow-redirects 1.16.0→1.16.2 | `src/angular/package-lock.json` | **Overlaps** #130/#131/#135 (same file) but a different package — no version conflict |
| #135 vite 7.3.5→7.3.7 | `src/angular/package.json` (`overrides.vite`) + `package-lock.json` | **Overlaps** same file; independent package, no conflict |
| #130 `@modelcontextprotocol/server` 2.0.0→2.3.1 **and** `@angular/cli` 22.2.1→22.2.3 | `src/angular/package.json` + `package-lock.json` | **Conflicts with #131 on `@angular/cli`** (different target version) |
| #131 npm_and_yarn group, 23 packages incl. `@angular/cli` 22.2.1→**22.2.4**, `@types/jasmine` 6.0.0→**7.0.0** (major) | `src/angular/package.json` + `package-lock.json` | **Conflicts with #130 on `@angular/cli`**; #131's target is newer and supersedes #130's for that one package, but does not cover `@modelcontextprotocol/server` |

**Why #130 and #131 exist as separate PRs despite the repo's `dependabot.yml` defining one `npm_and_yarn` group with pattern `"*"`:** that group config applies to *scheduled* version-update PRs (#131). Security-alert-triggered PRs (#130 for the two `@modelcontextprotocol/server` CVEs, #135 for vite, #138 for follow-redirects) are opened immediately on alert discovery, outside the group's schedule, and Dependabot bundles `@angular/cli` into #130 only because it is an "ancestor dependency that needs updating together" with `@modelcontextprotocol/server` — not because of the group config.

**Recommendation:** land #131 (the broader, newer `@angular/cli` target plus 22 other packages) and, separately, bump `@modelcontextprotocol/server` to at least 2.3.0 (the fix version; #130's target 2.3.1 or newer is fine) — do this by naming both in one `npm install`/update invocation on the release branch rather than attempting to cherry-pick either PR, per Pattern 1 above. Do the same for #135 (vdite) and #138 (follow-redirects) in the same pass since they all touch the same lockfile.

### @types/jasmine 6→7 — isolated risk, not a legitimacy risk
`.github/dependabot.yml` contains:
```yaml
ignore:
  - dependency-name: "typescript"
    update-types: ["version-update:semver-major"]
  - dependency-name: "jasmine-core"
    update-types: ["version-update:semver-major"]
```
with the comment "karma-jasmine 5 cannot patch jasmine 7 globals" — i.e. the maintainer already knows jasmine-core 7 is unsafe with the current Karma/Zone.js setup and blocked it. **This ignore rule does not cover `@types/jasmine`** (a different package name), so Dependabot bumped the type-declarations package to 7.0.0 in PR #131 while `jasmine-core` stays pinned at 6.3.0 (`jasmine-core: ^6.3.0` in `src/angular/package.json`, untouched by #131). [CONFIRMED via web search] Jasmine 7's own release notes state Zone.js's monkey-patch of jasmine-core no longer works under 7.0, and karma-jasmine (unmaintained since 2022) does not support it — but since `jasmine-core` itself is **not** being bumped here, that specific crash mode does not apply. The actual risk is narrower: `@types/jasmine` 7's type declarations may describe APIs (e.g., the new `notApplicable` spec status) that don't exist in the still-6.3.0 runtime, or may remove/change types for deprecated APIs still used in this repo's spec files, causing `tsc`/Karma compile errors.

**Recommendation:** apply this one package's bump first, in isolation, and run `ng test --code-coverage` (or at minimum `npx tsc --noEmit` over the Angular project) before combining it with the other 22 `npm_and_yarn` updates — so that if something fails, D-02's "name which update, what failed" requirement is trivially satisfiable.

## 999.4 Recheck: braces/karma dev-test advisory (D-03)

**Current status: resolved, no action needed.**
```bash
$ cd src/angular && npm ls braces
seedsyncarr@1.7.6 /Users/julianamacbook/seedsyncarr/src/angular
└─┬ karma@6.4.4
  ├── braces@3.0.3
  └─┬ chokidar@3.6.0
    └── braces@3.0.3 deduped
```
`braces@3.0.3` is already the patched version for CVE-2024-4068 (memory-exhaustion via unbounded brace-expansion parsing, fixed upstream by capping `MAX_LENGTH` at 10,000; see [Jonschlinkert/braces commit 415d660](https://github.com/micromatch/braces/commit/415d660c3002d1ab7e63dbf490c9851da80596ff)). `gh api .../dependabot/alerts` (all states, not just open) returns **zero** alerts naming `braces`, `karma` or `chokidar` — there is currently no tracked advisory for this dependency chain at all. [VERIFIED: `npm ls` + GitHub alerts API, both queried this session]

**Record for the CHANGELOG/owner summary:** "999.4 rechecked 2026-10-28: `braces` is already at 3.0.3 (the patched version for the historical CVE-2024-4068 memory-exhaustion advisory, dev-only via karma→chokidar); no open Dependabot alert exists for it or for karma/chokidar. No fix needed; the original PR #128 is closed, and #125/#117 are addressed by this phase's broader D-01 roll-in."

## SECURITY.md correction required (new finding, not in CONTEXT.md)

`SECURITY.md`'s "Security posture" section (unchanged since 1.7.6, confirmed via `git diff v1.7.6..main -- SECURITY.md` = empty) contains:

> **IP-resolution guard on *arr connection URLs** — When you test or connect a Sonarr/Radarr server, the user-supplied URL is resolved via `socket.getaddrinfo` and rejected if it points to a private, loopback, reserved, or link-local IP.

This is now **factually wrong**. Phase 125 (LAN-01/LAN-02) inverted the private-IP behavior: private-range IPs and Docker container/host names resolving to private addresses are now the **primary allowed case** (that is the whole point of the phase); only link-local/cloud-metadata, unspecified, reserved, multicast and loopback-outside-8989/7878 are refused. This should be corrected in the same release that ships the behavior change, both because it is simply inaccurate and because the 119.1 release already had the owner catch an analogous SECURITY.md drift (the encryption-at-rest bullet) at the pre-tag checkpoint — fixing it proactively avoids a repeat of that same review cycle.

**Suggested corrected wording (discretion: exact phrasing is the planner's/owner's call):**
> **IP-resolution guard on *arr connection URLs** — When you test or connect a Sonarr/Radarr server, the user-supplied URL is resolved via `socket.getaddrinfo`. Private-network addresses (LAN ranges, Tailscale/CGNAT, Docker container and host names resolving to them) and public addresses are allowed; cloud-metadata and other link-local addresses, unspecified/reserved/multicast addresses, and loopback outside Sonarr's/Radarr's default ports (8989/7878) are rejected with a specific reason. This is an SSRF guard scoped to the *arr connection URL (not a full SSRF library; DNS-rebinding/TOCTOU is a documented out-of-scope limitation for a homelab tool).

## Version Bump Sites (exact file list)

Confirmed by `grep -rl "1\.7\.6"` across the repo (excluding `.planning/`, `node_modules/`):

| File | Field(s) | Checked by `verify-release-metadata.mjs`? |
|---|---|---|
| `package.json` (root) | `.version` | Yes |
| `package-lock.json` (root) | `.version`, `.packages[""].version` | **No** — not covered by the automated script; bump and verify by eye (precedent: 119.1-REL04 did this manually via `grep -n "version"`) |
| `src/angular/package.json` | `.version` | Yes |
| `src/angular/package-lock.json` | `.version`, `.packages[""].version` | Yes |
| `src/python/pyproject.toml` | **two** separate lines: `[project] version = "..."` and `[tool.poetry] version = "..."` | **No** — not covered by the script (PyPI publish re-stamps this at build time via `sed` in `ci.yml`'s `publish-pypi` job, but the committed release-tree value should still be bumped for consistency and for anyone reading the tree directly) |
| `CHANGELOG.md` | `## [1.8.0] - <date>` heading | Yes (heading-presence check only, not content) |
| `release-notes.md` | `v{{VERSION}}/CHANGELOG.md` link line (template substituted by CI) | Yes (link-pattern check only) |

No Dockerfile contains a version label (`grep -rn "1.7.6" Dockerfile src/docker` returns nothing). No `docs/` file or Python source file hardcodes the version.

## Release Pipeline Mechanics

`.github/workflows/ci.yml` (443 lines, unchanged structure since 1.7.6 — confirmed no diff to this file across v1.7.6..main would be needed for this phase's release, since it already supports everything needed):

- **On every push/PR:** `unittests-release-metadata`, `unittests-python` (full Python suite, Dockerized), `unittests-angular`, `lint-python` (ruff 0.15.22, whole-tree `ruff check src/python/`), `verify-python-package` (build wheel+sdist, `twine check`, `scripts/verify-python-package.py`, install-and-run in a clean venv), `lint-angular`, `build-docker-image` (staging tag = `github.run_number`), `e2etests-docker-image` (amd64 only on PRs; amd64+arm64 on `main` push or a `v*` tag push).
- **`verify-release-metadata` job:** only runs its checks when `startsWith(github.ref, 'refs/tags/v')` — on a PR it just echoes "guard only runs for v* tags." This means the metadata check is NOT enforced on the release PR itself, only after the tag is pushed — the planner should still run `node scripts/verify-release-metadata.mjs 1.8.0` manually before tagging (as 119.1-REL04 did).
- **On a `v*` tag push only:** `publish-docker-image` (pushes `ghcr.io/thejuran/seedsyncarr:1.8.0` and `:latest`, both multi-arch via `make docker-image-release`), `publish-github-release` (needs `e2etests-docker-image` + `verify-release-metadata` + `publish-docker-image`; runs `sed "s|{{VERSION}}|1.8.0|g" release-notes.md > release-body.md` then `gh release create`), `publish-pypi` (needs the same three; re-stamps `pyproject.toml`'s version via `sed`, builds, publishes with `pypa/gh-action-pypi-publish`).
- **On `main` push only (not tags):** `publish-docker-image-dev` (pushes `:dev`), `publish-docs` (mkdocs → GitHub Pages; also runs on tag push).

**Exact command precedent for cutting the release** (from 119.1-REL04, same shape applies to 1.8.0 with version strings updated):
```bash
git tag -a v1.8.0 -m "SeedSyncarr 1.8.0 — <summary>" <merge-commit-sha>
git push origin v1.8.0
# then poll: gh run list --workflow=ci.yml --branch v1.8.0 OR gh run view <id>
# digest resolution (two independent methods, cross-checked):
docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:1.8.0
# or anonymous GHCR token lookup:
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:thejuran/seedsyncarr:pull&service=ghcr.io" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -I -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.oci.image.index.v1+json" \
  "https://ghcr.io/v2/thejuran/seedsyncarr/manifests/1.8.0" | grep -i docker-content-digest
```

## Release Notes Content (D-06–D-10 — verified facts for drafting)

### Security section — Phase 121 exact exposure (D-08)
From `121-VERIFICATION.md` (independently re-confirmed facts, not inferred) and `STATE.md`'s "Pending Todos" carry-forward:
- **Exact condition:** the pre-fix `auth.interceptor.ts` attached the Bearer `api_token` header to **every** outgoing HTTP request made by the Angular app whenever `api_token` was configured (non-empty) in `settings.cfg` — including the GitHub update-check request to `https://api.github.com/repos/thejuran/seedsyncarr/releases/latest`, which fires on every UI page load.
- **Affected versions:** since v1.0.0 (the interceptor's unconditional `if (token)` attach logic predates this milestone; no earlier phase touched it).
- **What GitHub did with it:** GitHub's API rejected the unrecognized Bearer token with 401 (confirmed live by curl in 121-VERIFICATION: `-H 'Authorization: Bearer not-a-real-token'` → `401`; no header → `200`) — so the practical effect was that the update-availability notice silently failed to render for any user who had `api_token` set, not that GitHub accepted/used the token. The token value itself was still transmitted over HTTPS to GitHub on every page load.
- **No other external destination received it** — Phase 121's fix scope and its regression tests confirm the interceptor had no other non-app-origin call site.
- **Current production exposure:** verified live this session (read-only `curl` to `/server/config/get`) — **production currently has no `api_token` set at all**, so production itself was never exposed by this; the notice is for any user who did configure one.
- **Draft fact for CHANGELOG (not final prose):** "Versions 1.0.0 through 1.7.6 sent the configured API token to GitHub's update-check endpoint on every page load (GitHub rejected it; no other destination ever received it). 1.8.0 only ever attaches the token to SeedSyncarr's own `/server/*` requests. If you have an API token configured, rotating it after upgrading is a cheap precaution — not required."

### Fixed section — exact facts (D-09)
- **122 (LOG-01/LOG-02):** a webhook Test event now produces a `<source> webhook test event received` INFO line in the app log (confirmed live, `122-SAFE01-EVIDENCE.md` §"LOG-01 live", logger `seedsyncarr.WebhookHandler`); a pruned completion hold (no release) is now logged as "dropped (reason)", distinct from "Completion hold cleared" which is reserved for an actual proof-based release.
- **123 (LIFE-01/LIFE-02):** confirmed live across 17 restart cycles (123-LIFE-EVIDENCE.md) — a failure partway through startup now cleans up already-started children before the failure surfaces; a cleanup failure in one component no longer prevents cleanup of the remaining components. One narrow, owner-approved exception exists: `Lftp.exit()` has a bounded (≤2.0s) reap wait, only on the path where pexpect's own force-close fails to reap an lftp child stuck in uninterruptible I/O — this is a genuine live-confirmed fix (122-13's lftp fallback was observed reaping a real `state=D` child in 0.35s during an actual active-transfer restart), not a cosmetic change; no new sleep exists on the clean-shutdown path.
- **124 (STRM-01/STRM-02):** a slow/backgrounded browser tab's model stream now resyncs to current state after an overflow instead of replaying stale backlog, with bounded buffering (one pending snapshot, not unbounded). Verification found two minor, non-blocking gaps (a narrow unlocked-read race between the drop-count check and the dequeue, and a pending-snapshot invariant not fully test-proven) — both are "converges within one more cycle, not within the current call" nuances, already backlogged by the owner, not worth release-note detail (D-09 asks for "no internals").

### Changed section (D-10) — verbatim reuse of the existing CHANGELOG `[Unreleased]` draft
The current `CHANGELOG.md` `[Unreleased]` section already contains the owner-approved Phase 125 wording (Test Connection behavior change + the three Security bullets for the SSRF parser-differential fix, multicast/deprecated-site-local blocking, and the `fd00:ec2::254`/`100.100.100.200` cloud-metadata carve-outs). D-10 says keep this as drafted, editing only for accuracy/flow when folded under the `[1.8.0]` heading.

## Sandbox Smoke Procedure (D-11/D-12/D-12a)

### Reusable harness
Copy `.planning/phases/125-lan-connection-tests/125-teardown.sh` as the starting point (most recent, already handles `sonarr_url` restore + image-pin restore + status-wait + verify-and-report). Required extension: add a `RADARR_URL_L0`/`RADARR_URL_SET` key pair and `get_radarr_url()`/`set_radarr_url()` functions mirroring the existing `sonarr_url` ones (same `config/get`/`config/set` JSON shape, `section:"radarr"`).

### Rewiring sonarr-v5 → sonarr-v4 and back
- `seedsyncarr-test`'s current `sonarr_url` is `http://sonarr-v5:8989` (confirmed live this session, read-only query). Both `sonarr-v4` (image `linuxserver/sonarr:4.0.20`) and `sonarr-v5` (image `linuxserver/sonarr:develop`) are on the same `docker_default` Docker network as `seedsyncarr-test`, confirmed reachable by container name.
- Record `SONARR_URL_L0=http://sonarr-v5:8989` before changing anything (this session's state).
- Set `sonarr_url=http://sonarr-v4:8989` for the main D-12 integration/import/webhook/cleanup checks (with the real Sonarr-v4 API key — present in `/volume1/docker/v5test/sonarr`'s own `config.xml`, never log it).
- For the D-12a "Test Connection succeeds with a container name" spot check, point at `sonarr-v5` (`http://sonarr-v5:8989`) — this is explicitly what D-12's second sentence calls for ("Add a quick Test Connection against sonarr-v5"), separate from the main sonarr-v4 integration check.
- Restore to `SONARR_URL_L0` at teardown, same idempotent-restore pattern as `125-teardown.sh`.

### Radarr: no dedicated test instance exists — recommendation
There is exactly one `radarr` container on the NAS (production's live media-library instance; confirmed via `docker ps`). There is no `radarr-v4`/`radarr-test` equivalent to Sonarr's dual-instance setup.
- The `/server/webhook/radarr` endpoint exists (`src/python/web/handler/webhook.py:39`) and behaves identically to the Sonarr one: it is SeedSyncarr *receiving* a signed, synthetic webhook POST, which never touches any real Radarr instance. **The import/webhook/cleanup half of D-12's Radarr check is fully achievable this way**, exactly mirroring the Sonarr-style webhook pattern already proven three times (119-REL03, 119.1-REL04, 122-SAFE01).
- A genuine Radarr *reachability* check (`radarr/enabled=True` against a real URL, confirming `http=200` the same way 119.1-04 §1f checked Sonarr/Radarr reachability) can safely point at the real `radarr` container (`http://radarr:7878`, confirmed on the same shared `docker_default` network as `seedsyncarr-test`) — this is read-only (`GET /api/v3/system/status`) and non-destructive.
- **What this cannot prove:** a full completion-gate release (ArrQueueClient confirming a synthetic test file as "complete" via Radarr's real queue) — the real Radarr's queue will never contain a matching entry for a sandbox-synthetic filename, so that path can only ever produce a "no matching queue entry" Waiting state, not a release.
- **Recommendation (flagged for planner judgment, not locked by CONTEXT.md):** for a release smoke (as opposed to the exhaustive Phase 122 SAFE-01 acceptance matrix, which already proved the completion-gate logic generically via Sonarr and does not need re-proving per-arr), reachability + webhook/import/cleanup via the synthetic-webhook path is sufficient to satisfy D-12a's "Radarr integration" bullet at the same depth the 119.1-04 release smoke used for Sonarr (which also did not do a live completion-gate replay — it used `sonarr/enabled=False` and a direct synthetic webhook). If the owner wants a true live Radarr completion-gate proof, the only clean path is a throwaway Radarr container (mirroring 119.1-04's disposable-SSH-remote pattern) seeded with one synthetic queue entry — flagged as an Open Question below for the owner/planner to decide, not assumed.

### "No app token on the GitHub update-check request" — cannot be curl/log-verified alone
This is a **browser-origin** behavior: the request is made by the Angular SPA's `VersionCheckService` via `HttpClient`, gated by `authInterceptor` running in the browser — not by the Python backend. None of the established server-side smoke tooling (docker logs, curl, extract_secrets.py) can observe it, because the request never touches the SeedSyncarr container's own HTTP server or log. Two options:
1. **Cite the already-passing Phase 121 CI evidence** (unit tests + the real-browser `chromium-token` Playwright project, both already re-confirmed in `121-VERIFICATION.md` against the exact code that ships in 1.8.0, unchanged since 121-03) as sufficient proof, since this behavior is purely a function of `auth.interceptor.ts`, which carries zero diff between 121-03 and `main` (confirmed: `git log` shows no touches to that file after 121-03's merge).
2. **A manual browser DevTools Network-tab check** against the sandbox UI with `api_token` configured, during the live smoke session — consistent with this project's existing precedent of leaving browser-only checks to a human UAT step (e.g. `119-HUMAN-UAT.md`'s Waiting-badge check) rather than scripting them.
Recommendation: option 1 (cite CI evidence) is sufficient and avoids adding a new browser-automation dependency to the smoke harness for a behavior that cannot regress without a code change this phase doesn't make.

## Prod Deploy + wud + Backups (D-15/D-16/D-17 — exact recipe, adapted from 119.1-REL04)

```bash
# 1. Preconditions: confirm wud exited, confirm current prod image/digest, back up compose
ssh nas 'sudo /usr/local/bin/docker inspect wud --format "{{.State.Status}}"'
ssh nas 'sudo /usr/local/bin/docker inspect seedsyncarr --format "{{.Config.Image}} {{.Image}} {{.State.Status}} {{.Id}}"'
ssh nas 'cd /volume1/docker && cp -p docker-compose.yml docker-compose.yml.pre-1.8.0-<TS> && echo COMPOSE_BACKUP_OK'

# 2. Pull by exact digest (never :dev, never latest)
ssh nas 'sudo /usr/local/bin/docker pull -q ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:<digest>'

# 3. Graceful stop + classify (CLEAN_STOP requires ExitCode 0, OOMKilled false, <10s)
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose stop seedsyncarr'
ssh nas 'sudo /usr/local/bin/docker inspect seedsyncarr --format "{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.FinishedAt}}"'

# 4. Back up the three persist files with a timestamp suffix, checksum, non-empty check
ssh nas 'cd /volume1/docker/seedsync && cp -p settings.cfg settings.cfg.pre-1.8.0-<TS> && cp -p controller.persist controller.persist.pre-1.8.0-<TS> && cp -p autoqueue.persist autoqueue.persist.pre-1.8.0-<TS> && sha256sum *.pre-1.8.0-<TS>'

# 5. Read-only loader check of the backups against BOTH images (118-05-parse_check.py, unchanged since 1.7.6)
#    — guaranteed PASS in both directions since common/config.py and the two Persist subclasses are unchanged

# 6. Inode-preserving compose pin rewrite (sed to a temp file, cat back, never redirect directly)
ssh nas 'cd /volume1/docker && sed "s|seedsyncarr:1.7.6@sha256:da6196e0…|seedsyncarr:1.8.0@sha256:<digest>|" docker-compose.yml > /tmp/dc.new && cat /tmp/dc.new > docker-compose.yml && rm /tmp/dc.new'

# 7. Recreate, verify image ID matches the smoked digest, poll /server/status for a successful scan
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose up -d seedsyncarr'

# 8. Arr reachability + steady-state window (no holds, no Backing-up/Traceback/ERROR lines over ~5 min)

# 9. Count-only no-secrets check on the fresh container log (extract_secrets.py pattern)

# 10. seedsyncarr-test: already on 1.8.0 from the Wave 4 smoke — re-verify its fingerprint is still correct
#     (it does not need a second deploy; D-11 explicitly allows it to stay on the release tag)

# 11. wud restored LAST, only after every check above passes
ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose start wud'
```

**Backup file list (unchanged from 1.7.6):** `docker-compose.yml`, `settings.cfg`, `controller.persist`, `autoqueue.persist` — all four, each with a `.pre-1.8.0-<timestamp>` suffix, each checksummed before the deploy and compared against a post-rollback restore if one is ever needed.

**Confirming a successful scan (D-17):** poll `curl http://localhost:8800/server/status` for `latest_remote_scan_failed: false` with a `latest_remote_scan_time` newer than `UP_TIME`; a scanner-died warm-up `ERROR` line immediately after `Exiting Seedsyncarr` (the known 118-05 shutdown race) is acceptable **only if** followed by a later successful scan — never dismiss it without that confirmation (owner's standing rule, carried in every prior release's deploy gate).

**Clock note:** the app-log clock is the NAS host clock **+1 hour** (confirmed again this session's context; some earlier evidence files used +4h/+5h offsets at different times of year — always re-derive the offset for the current session by matching a command's own host-clock timestamp against its own resulting log line, don't assume a fixed offset).

## Common Pitfalls

### Pitfall 1: Cherry-picking overlapping Dependabot PR commits
**What goes wrong:** #130 and #131 both touch `src/angular/package-lock.json`, bumping `@angular/cli` to different target versions (22.2.3 vs 22.2.4). A cherry-pick of both produces either a conflict or a lockfile where one PR's intended version silently loses to the other's commit order.
**Why it happens:** Dependabot PRs are generated independently against `main` at PR-creation time; by the time multiple PRs are rolled in together, `main` has moved and their diffs no longer compose cleanly.
**How to avoid:** Regenerate lockfiles by naming every target package in one `npm install`/`poetry update` invocation (Pattern 1), not cherry-picking.
**Warning signs:** `git cherry-pick` reports a conflict in `package-lock.json`, or a seemingly-clean cherry-pick leaves `@angular/cli` at an unexpected version.

### Pitfall 2: Assuming `verify-release-metadata.mjs` catches every version site
**What goes wrong:** The script does not check the root `package-lock.json` or `src/python/pyproject.toml` — both were manually verified by eye in every prior release (119.1-REL04's evidence shows an explicit manual `grep`/inspection step for exactly these two).
**Why it happens:** The script was written to check the sites that actually block a broken release (Angular version drift, CHANGELOG/release-notes presence); it was never extended to cover the two sites that PyPI's own CI job re-stamps or that have no functional consequence if stale.
**How to avoid:** After running the automated check, also manually `grep -n "version" package-lock.json src/python/pyproject.toml` and compare to the target version.
**Warning signs:** `verify-release-metadata.mjs` reports all green but `pyproject.toml` still says `1.7.6`.

### Pitfall 3: Treating `jasmine-core` and `@types/jasmine` as interchangeable
**What goes wrong:** The project's own Dependabot config blocks `jasmine-core` major bumps (documented reason: Zone.js/karma-jasmine incompatibility with jasmine 7) but does not block the matching `@types/jasmine` major bump, which Dependabot proposes anyway in PR #131.
**Why it happens:** They are two different npm package names; a per-package `ignore` rule in `dependabot.yml` does not cascade to a related-but-separately-named package.
**How to avoid:** Apply the `@types/jasmine` bump in isolation first and run the full Angular test suite (not just a lint) before folding it into the group update, per D-02.
**Warning signs:** TypeScript compile errors in `*.spec.ts` files referencing Jasmine matcher/spy types after the bump; this would NOT show up as a Zone.js runtime crash (that specific crash only happens if `jasmine-core` itself is also bumped, which it is not here).

### Pitfall 4: Stale SECURITY.md describing the pre-Phase-125 SSRF guard behavior
**What goes wrong:** Shipping 1.8.0 with SECURITY.md still saying the *arr-connection guard "rejects" private IPs, when Phase 125 made private IPs the primary allowed case, creates a public-facing document that contradicts the shipped CHANGELOG entry for the same release.
**Why it happens:** SECURITY.md is not touched by the code-change phases (121-125); nothing in the normal PR flow prompts an update to it.
**How to avoid:** Fix it as part of this phase's release-content wave, before the pre-tag owner checkpoint (precedent: 119.1 had the owner catch and fix an analogous SECURITY.md drift at exactly that checkpoint — doing it proactively here saves a review round-trip).
**Warning signs:** Owner (or a reviewer) notices the contradiction between SECURITY.md and the 1.8.0 CHANGELOG's Changed section during the D-13 pre-tag review.

### Pitfall 5: Reading `/server/config/get` unauthenticated and capturing a live secret
**What goes wrong:** When no `api_token`/`webhook_secret` is configured (true of both production and the sandbox today), `/server/config/get` returns HTTP 200 with the full config **including `sonarr_api_key`/`radarr_api_key` values** to any caller — there is no separate "redact secrets in this read-only endpoint" behavior. A naive `curl` during environment probing (as happened once in this research session) captures a live key in the response body.
**Why it happens:** `api_token` gates the API only when it is set; with no token configured (the current state on both the sandbox and production), every endpoint is open, including the one that echoes back the full config.
**How to avoid:** When probing config state for research/evidence purposes, always post-filter the response to strip `*_api_key`/`*_password`/`*_secret`/`*_token` fields before it reaches a log, a terminal scrollback that will be reproduced, or this kind of document — treat it exactly like a `settings.cfg` read, not like a harmless status check.
**Warning signs:** A tool-call transcript or evidence file contains what looks like a 32-character hex string next to a `sonarr_api_key`/`radarr_api_key` field name.

## Code Examples

### Dependabot alert query (exact command used this session)
```bash
# Source: gh CLI against GitHub's REST API
gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate \
  --jq '.[] | select(.state=="open") | {number, package: .security_vulnerability.package.name, severity: .security_vulnerability.severity, first_patched: .security_vulnerability.first_patched_version.identifier}'
```

### Isolated @types/jasmine verification before the group bump
```bash
cd src/angular
# bump only this one line in package.json: "@types/jasmine": "^6.0.0" -> "^7.0.0"
npm install
npx tsc --noEmit -p .      # catches any type-mismatch compile error in isolation
npm run test:ci 2>&1 | tail -30   # or the repo's actual Karma invocation (`make run-tests-angular`)
```

### Full dependency roll-in verification gate (combining all three ecosystems)
```bash
cd src/python && poetry update certifi mkdocs-material testfixtures && poetry run pytest tests/unittests -q
npm update puppeteer   # root
cd src/angular && npm install && npm run lint && make -C ../.. run-tests-angular
cd src/angular && npm audit --audit-level=low   # confirm 0 remaining findings
gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'   # expect 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Cherry-picking Dependabot PR commits one at a time (implied by earlier small rounds with 0-1 open PR) | Regenerating lockfiles with `poetry update <names>`/`npm update <name>` for multiple packages at once | Established at 119-REL03 (2026-10-15), reused here at a larger scale (8 PRs vs 2-3) | Avoids merge conflicts when PRs overlap on the same lockfile |
| Treating every open Dependabot PR as deferrable "dev-only, defer to next milestone" | Owner directive D-01: roll in literally everything open, ask if something breaks | This phase (2026-10-28), a deliberate expansion beyond the standing CLAUDE.md release rule | Larger single roll-in, more surface area for D-02's "stop and ask" gate to actually trigger |

**Deprecated/outdated:**
- The SECURITY.md "IP-resolution guard...rejected if private/loopback/reserved/link-local" bullet — superseded by Phase 125's LAN-01/LAN-02 allow-by-default-for-private-ranges behavior; needs correction in this release (see dedicated section above).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reachability-only + synthetic-webhook testing is sufficient for the sandbox smoke's "Radarr integration" bullet, rather than a full live completion-gate proof against a throwaway Radarr instance | Sandbox Smoke Procedure, Radarr sub-section | If the owner actually wants a full completion-gate proof for Radarr (not just Sonarr), the planner needs to budget time to stand up a throwaway Radarr container; flagged explicitly as an Open Question below so this is a decision, not a silent default |
| A2 | Citing Phase 121's existing CI evidence is sufficient proof for the "no app token on GitHub update-check request" D-12a spot check, rather than a fresh manual browser check during the live smoke | Sandbox Smoke Procedure, GitHub-update-check sub-section | If the planner/owner wants fresh, this-exact-digest proof (not just "the code hasn't changed"), a manual DevTools check needs to be added as an explicit task |
| A3 | `poetry update <names>`/`npm install` after a manifest-range bump will reproduce the same target versions the open Dependabot PRs already specify, without pulling in unplanned additional transitive bumps | Dependabot Roll-In Mechanics | Low risk (this is exactly how 119-REL03 behaved — diff "limited to those two packages"), but worth a `git diff --stat` sanity check after running, to catch any unexpected extra lockfile churn before committing |

**If this table is empty:** N/A — three assumptions logged above, none blocking, all carry a concrete verification step.

## Open Questions

1. **Does the owner want a full live Radarr completion-gate proof, or is reachability + synthetic webhook sufficient for the release smoke?**
   - What we know: there is no dedicated Radarr test instance on the NAS (unlike Sonarr's `sonarr-v4`/`sonarr-v5` pair); the real production `radarr` container is reachable read-only from the sandbox for a connectivity check, and the `/server/webhook/radarr` endpoint fully exercises the import/cleanup path without touching any real Radarr instance.
   - What's unclear: D-12a's "Sonarr (v4) and Radarr integration" phrasing doesn't specify whether "integration" here means the same depth as the Sonarr-v4 check (which does use a real, reachable, dedicated Sonarr instance) or can be satisfied at the lighter depth described above.
   - Recommendation: default to reachability (against the real `radarr` container, read-only) + synthetic webhook/import/cleanup, matching the depth used in the 119.1-04 release smoke (which also didn't do a live completion-gate replay for Sonarr, just reachability + synthetic webhook); surface this choice explicitly to the owner at the D-13 pre-tag checkpoint rather than assuming silently.

2. **Should the `%40` rollback runbook change the TARGET version string anywhere else besides `release-notes.md`?**
   - What we know: the current `release-notes.md` is entirely 1.7.6-era content (security notice, 1.7.5 carry-forward section, rollback-to-1.7.4 runbook) that gets **fully replaced** for 1.8.0, per the established pattern of each release writing a self-contained `release-notes.md`.
   - What's unclear: nothing, really — this is confirmed by inspecting the 1.7.4/1.7.5/1.7.6 git history pattern (each release's `release-notes.md` commit is a full rewrite, not an append). Listed here only so the planner doesn't accidentally try to "add a section" instead of rewriting the file.
   - Recommendation: treat `release-notes.md` as a full rewrite for 1.8.0, using the structure in the Release Notes Content section above.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI (authenticated) | Dependabot alert/PR queries, PR view, CI run/job logs, release view | ✓ | confirmed working this session | — |
| `slopcheck` | Package Legitimacy Audit | ✓ | 0.6.1 (installed this session via `pip install --break-system-packages`) | If unavailable in the planner's environment, mark all packages `[ASSUMED]` and gate behind `checkpoint:human-verify` per the Package Legitimacy Protocol — not needed here since it installed cleanly |
| `npm` / `npm view` / `npm audit` | Version verification, audit re-check | ✓ | npm 11.12.1 (update to 11.21.1 available, non-blocking) | — |
| `pip index versions` | PyPI version verification | ✓ | — | — |
| `ssh nas` (Tailscale, key auth) | All NAS read-only probes (container status, network inspection, live config reads) | ✓ | — | — |
| `sudo /usr/local/bin/docker` over `ssh nas` | All NAS docker operations | ✓ | Docker engine on NAS confirmed responsive | Must always use the absolute path per the owner's global CLAUDE.md rule — bare `sudo docker` over non-interactive SSH fails (no TTY for a password prompt) |
| `docker buildx imagetools` (local) | Digest resolution for a published tag, as an independent cross-check alongside the GHCR anonymous-token method | Not explicitly tested this session, but used successfully in 119.1-REL04/122-SAFE01 on the same machine | — | GHCR anonymous-token curl method (shown above) is a fully independent fallback already proven to work |

**Missing dependencies with no fallback:** none identified.
**Missing dependencies with fallback:** none identified — everything needed for this phase is already present and working in this environment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Python framework | pytest (poetry-managed), full suite run inside the Dockerized `unittests-python` CI job; see `Makefile`'s `run-tests-python` target |
| Angular framework | Karma + Jasmine (`karma.conf.js`), run via `make run-tests-angular` / `unittests-angular` CI job |
| E2E framework | Playwright (`src/e2e/playwright.config.ts`), run via `e2etests-docker-image` CI job against the actual built Docker image |
| Release-metadata framework | Node's built-in `node --test` runner, over `scripts/verify-release-metadata.test.mjs` |
| Quick run command (Python) | `cd src/python && poetry run pytest tests/unittests -q -p no:cacheprovider` (with the four documented host-only exclusions: `test_sshcp.py`, `test_scanner_process.py`, `test_scanner.py`, `test_extract_process.py`) |
| Full suite command | CI's Dockerized `unittests-python` job is the authority (runs the four host-excluded files too) |
| Lint command | `ruff check src/python/` (0.15.22, pinned) + `cd src/angular && npm run lint` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-05 | Every open Dependabot PR is rolled in or explicitly deferred with owner sign-off; 999.4 recheck recorded | Scripted verification (not a unit test) | `gh api repos/thejuran/seedsyncarr/dependabot/alerts --jq '[.[]|select(.state=="open")]|length'` must print `0`; `npm audit --audit-level=low` in `src/angular` must show 0 findings | ✅ (both are `gh`/`npm` built-ins, no new script needed) |
| REL-05 | None of the rolled-in dependency bumps breaks the build/tests | Automated (existing suites) | `poetry run pytest tests/unittests -q` (Python) + `make run-tests-angular` (Angular) + whole-tree `ruff check src/python/` + `npm run lint` (Angular) | ✅ existing CI jobs |
| REL-05 | Version-metadata consistency across every bump site | Automated (existing script) | `node scripts/verify-release-metadata.mjs 1.8.0` | ✅ `scripts/verify-release-metadata.mjs` |
| REL-06 | Release commit passes full CI (Python suite, ruff, Angular tests, e2e, Docker build, CodeQL, packaging) | Automated (CI) | PR CI run on the release branch, all jobs green | ✅ `.github/workflows/ci.yml` |
| REL-06 | Tag CI successfully publishes GHCR/GitHub Release/PyPI | Automated (CI) + manual verification | `gh run view <tag-ci-run-id>`; `gh release view v1.8.0`; `pip install --no-cache-dir seedsyncarr==1.8.0` in a scratch venv | ✅ precedent in 119.1-REL04 |
| REL-06 | Published image smoke-tested by exact digest (restart, real transfer, Sonarr/Radarr integration, cleanup) | Manual/scripted live check (no automated test file — this is infra behavior, not application code) | Reuse/extend `125-teardown.sh` + the step sequence documented in Sandbox Smoke Procedure above | ⚠️ script needs the `RADARR_URL_*` extension noted above; everything else exists |
| REL-06 | Production deploy by exact digest, backups verified, successful post-deploy scan, wud restored, owner confirms | Manual/scripted live check | Reuse the exact command sequence from 119.1-REL04 §"Deploy :1.7.6 to the NAS" with version strings updated | ✅ fully precedented, no new script needed |

### Sampling Rate
- **Per dependency-bump sub-task:** targeted pytest/Karma subset for the touched ecosystem, immediately after each `poetry update`/`npm install` invocation (so a failure is attributable to one specific bump, per D-02).
- **Per wave merge (release branch push):** full Python suite + whole-tree ruff + full Angular suite + e2e, via PR CI.
- **Phase gate:** `node scripts/verify-release-metadata.mjs 1.8.0` green, PR CI fully green, `gh api .../dependabot/alerts` returns 0 open, before the D-13 pre-tag owner checkpoint.

### Wave 0 Gaps
None — every test framework, CI job and release-verification script this phase needs already exists and is already exercised by the prior three releases. The only artifact that needs a small extension (not a new framework) is `125-teardown.sh` → `126-teardown.sh`, adding the `RADARR_URL_L0`/`RADARR_URL_SET` restore pair described in Pattern 2 above.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (no auth mechanism changes in this phase) | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | No (Phase 125 already shipped the `_validate_url` changes; this phase only publishes them) | — |
| V6 Cryptography | No | — |
| V14 Configuration / Dependency Management | Yes | This phase's entire scope: Dependabot alert triage (`gh api .../dependabot/alerts`), `slopcheck` package-legitimacy verification before any version bump, registry existence/version checks via `npm view`/`pip index versions` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain: a malicious/typosquatted package slips in during a dependency bump | Tampering | `slopcheck scan --pkg` run on every bumped package before applying (done this session — all 10 packages `[OK]`); cross-check target version exists on the correct ecosystem registry (`npm view`/`pip index versions`, done this session) |
| Stale security documentation misleading an operator about actual guard behavior | Information Disclosure (indirectly — a false sense of safety) | Correct `SECURITY.md` in the same release that changes the described behavior (flagged above as a required fix, not previously in CONTEXT.md) |
| Rollback to an older image reintroducing a previously-fixed vulnerability | Tampering / Repudiation | D-16's rollback target (1.7.6) already has every security fix through this milestone except the ones *this* release ships (SEC-02 token-scoping, the LAN-01/LAN-02 SSRF hardening); the release-notes rollback runbook must state plainly that rolling back reverts to the pre-1.8.0 SSRF/token-forwarding posture, not silently omit it |

## Sources

### Primary (HIGH confidence — read directly from this repo or queried live this session)
- `.planning/phases/126-release-1-8-0/126-CONTEXT.md` — locked decisions D-01 through D-17
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` §"Phase 126" and §"999.4" — scope and success criteria
- `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-CONTEXT.md` and `119.1-REL04-EVIDENCE.md` — release/deploy/rollback command recipes and evidence format
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md` — Dependabot roll-in precedent (`poetry update`/`npm update`), 8-check smoke format
- `.planning/phases/118-durable-state/118-CONTEXT.md` — original release-order/rollback-runbook decisions
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md` — sandbox deploy/teardown pattern, LOG-01 live-check format
- `.planning/phases/125-lan-connection-tests/125-CONTEXT.md` and `125-teardown.sh` — LAN-01/LAN-02 exact behavior, sandbox sonarr_url restore pattern
- `.planning/phases/121-credential-forwarding/121-VERIFICATION.md` — exact SEC-02 exposure facts
- `CHANGELOG.md`, `release-notes.md`, `SECURITY.md`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `src/python/pyproject.toml`, `package.json`, `src/angular/package.json`, `src/angular/package-lock.json` — read directly this session
- `git diff v1.7.6..main` (multiple scoped invocations) — rollback-safety evidence
- `gh api repos/thejuran/seedsyncarr/dependabot/alerts` and `gh pr view <n> --json ...` (all 8 open PRs) — live alert/PR state, 2026-10-28
- `ssh nas` read-only probes (`docker ps`, `docker inspect`, `docker network inspect`, read-only `curl` to `/server/config/get` and `/server/status`) — live NAS topology, 2026-10-28
- `slopcheck scan --pkg` (v0.6.1, installed this session) — package legitimacy verdicts for all 10 bumped packages
- `npm view`, `npm audit --json`, `pip index versions`, `curl pypi.org/pypi/.../json` — registry/version verification, 2026-10-28

### Secondary (MEDIUM confidence)
- WebSearch: jasmine-core 7.0.0 / @types/jasmine 7.0.0 compatibility (Zone.js/karma-jasmine incompatibility), cross-checked against this repo's own `.github/dependabot.yml` ignore-rule comment, which independently corroborates the same root cause
- WebSearch: braces CVE-2024-4068 fix version (3.0.3), cross-checked against the locally-installed `npm ls braces` output and GitHub's empty alert-history result for that package

### Tertiary (LOW confidence)
None — every finding in this document was either read from a committed file, confirmed via a live tool call, or cross-verified against at least one independent source.

## Metadata

**Confidence breakdown:**
- Dependabot roll-in mechanics: HIGH — every PR's files/overlap confirmed via `gh pr view --json files`, every alert confirmed via `gh api`, every target version confirmed on the correct registry
- Rollback safety: HIGH — based on a direct `git diff` showing zero changes to the four files that define persist/config format, not inference
- Release pipeline mechanics: HIGH — read directly from `.github/workflows/ci.yml`, cross-checked against three prior releases' actual CI run evidence
- Sandbox smoke procedure: HIGH for the Sonarr/webhook/secrets portions (fully precedented three times); MEDIUM for the Radarr-depth recommendation (no dedicated test instance exists, so the "sufficient depth" judgment is a reasoned recommendation, not a precedent — flagged as Open Question A1)
- @types/jasmine risk: MEDIUM — the Zone.js/jasmine-core incompatibility is well-documented and independently corroborated by this repo's own dependabot.yml comment, but the exact failure mode (if any) of @types/jasmine 7 alone against jasmine-core 6.3.0 was not reproduced locally in this research pass (no `npm install` was run against the real lockfile, to keep this research read-only)

**Research date:** 2026-10-28
**Valid until:** Re-check Dependabot alert/PR state immediately before the pre-tag checkpoint (D-04 requires it) — dependency state is fast-moving; everything else (rollback safety, pipeline mechanics, prior evidence) is stable for the life of this phase.
