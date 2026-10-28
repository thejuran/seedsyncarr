# Phase 126: Release 1.8.0 - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Release 1.8.0 (REL-05, REL-06): review and roll in open Dependabot alerts/PRs before the version bump, then publish 1.8.0 (GHCR, GitHub release, PyPI) from a green release commit, smoke-test the exact published digest on the NAS sandbox, and deploy that same digest to NAS production, confirmed by a successful post-deploy scan and the owner's confirmation. 1.8.0 bundles Phases 121–125 (all complete; PR #140 merged 2026-10-28). No new product capability.

</domain>

<decisions>
## Implementation Decisions

### Dependency roll-ins (REL-05)
Snapshot taken 2026-10-28. Re-check at release time.
- **D-01:** Roll in **every open Dependabot PR**: #136 certifi (runtime: the shipped CA bundle), #135 vite, #138 follow-redirects, #130 @modelcontextprotocol/server + @angular/cli, #131 npm_and_yarn group (23 updates, including Angular framework 22.2.1→22.2.3/4 patch bumps that ship in the UI bundle and a `@types/jasmine` 6→7 major), #141 mkdocs-material, #125 testfixtures and #117 puppeteer. Goal: zero open Dependabot alerts (9 open on 2026-10-28, all dev-scope npm: vite ×5, follow-redirects ×2, MCP SDK ×2) and an empty Dependabot PR queue at tag time.
- **D-02:** If any of these updates breaks the build, the Angular unit tests/Karma thresholds, e2e, or the Python suite, **stop and ask the owner** with the specifics: which update, what failed, and the options (drop it, or fix it with an estimated size). Don't silently drop an update and don't expand into an open-ended fix.
- **D-03:** Backlog 999.4 (braces/karma advisory) gets rechecked as part of this review, with the outcome recorded: current advisory status, affected versions, and whether the D-01 roll-ins resolve it. Its original PR #128 is now CLOSED. #125 and #117 are folded in by D-01.
- **D-04 (carried from 119.1 D-07):** If a NEW runtime/shipped security alert appears between this review and the tag push, raise it to the owner. Don't add it silently.
- **D-05:** The owner gets the final dependency list in plain terms (what was rolled in, what each touches, alert count before and after) at the pre-tag approval checkpoint (D-13).

### Release notes (CHANGELOG + release-notes.md)
- **D-06:** Production and most users upgrade from 1.7.6, so the 1.8.0 notes cover everything since 1.7.6. Finalize the existing `[Unreleased]` CHANGELOG draft (which currently only covers Phase 125) as `[1.8.0]`.
- **D-07:** Order: **Security first** (1.7.6 pattern), then **Changed** (the Test Connection behaviour change, which is why this is a minor version), then **Fixed**, then the rollback runbook in release-notes.md, plus the standard CHANGELOG link line the release-metadata check requires.
- **D-08:** **Security** contains Phase 125's existing entries (keep the owner-approved 125 D-13 wording) plus Phase 121: the app's API token was sent with the GitHub update-check request (to GitHub), and 1.8.0 sends it only to SeedSyncarr's own API. Include a plain suggestion to rotate the API token after upgrading as a cheap precaution, in the same plain tone as the 1.7.6 notice and with no exploit detail. **Check the exact exposure conditions in the Phase 121 artifacts before writing** (e.g. only when an API token is configured, which versions are affected), and state only what's verified.
- **D-09:** **Fixed** gets one plain-English line each for 122 (webhook test events now appear in the log; a dropped hold is no longer logged as "cleared"), 123 (a startup that fails partway shuts down already-started parts cleanly, and one part failing to shut down no longer stops the rest), and 124 (a slow or backgrounded browser tab catches up to current state instead of falling behind, with bounded memory). No internals.
- **D-10:** The Test Connection **Changed** entries from Phase 125 stay as drafted (125 D-10/D-14 wording), edited only for accuracy and flow.

### Sandbox smoke (REL-06)
- **D-11:** Smoke on the standing sandbox **`seedsyncarr-test`**, repinned to the exact published `:1.8.0@sha256:…` digest (record the digest it replaces). It may stay on 1.8.0 afterwards because that's a release tag. Production is read-only during the smoke.
- **D-12:** Run the integration, import, webhook and cleanup checks against **`sonarr-v4`** (4.0.20) to mirror production's v4 Sonarr, plus Radarr. Add a quick Test Connection against `sonarr-v5`. Restore the sandbox's arr URLs/wiring after the smoke, as in Phase 120 D-03 and Phase 125 D-09.
- **D-12a:** Must pass: restart; a real transfer; Sonarr (v4) and Radarr integration; auto-delete/cleanup. **Plus 1.8.0 spot checks:** Test Connection succeeds with a container name (e.g. `http://sonarr-v4:8989`) and still refuses `http://169.254.169.254` with the new message; a fresh start's container log contains no configured secret values (count-only check, values never printed); the GitHub update-check request carries no app token; a webhook test event appears in the app log.

### Approvals, production deploy and rollback (REL-06)
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

</decisions>

<specifics>
## Specific Ideas

- The owner's release rule (global CLAUDE.md "Releases"): review Dependabot before the bump, fix runtime deps, roll in dev-only ones if cheap, and present the list in plain terms. The owner chose to go beyond that and roll in everything open (D-01), with "ask me" if something breaks (D-02).
- The 1.7.6 security notice tone is the model for the token-rotation note: plain English, what happened, what to do, no exploit detail.
- STATE.md says PR #140 is "draft, not merged". That's stale: it was merged 2026-10-28 (merge commit 123b26f). Correct it during the state update.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §"Phase 126: Release 1.8.0" — success criteria 1–4; §"999.4" — braces/karma recheck scope
- `.planning/REQUIREMENTS.md` — REL-05, REL-06

### Prior release pattern (follow it)
- `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-CONTEXT.md` — D-07–D-11: release gates, prod deploy by digest, wud, rollback, notes structure
- `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-REL04-EVIDENCE.md` — 1.7.6 release/deploy evidence format and command recipes
- `.planning/phases/119-safety-follow-ups-and-1-7-5-release/119-REL03-EVIDENCE.md` — 8-check smoke procedure on an exact digest
- `.planning/phases/118-durable-state/118-CONTEXT.md` — original release-order and rollback-runbook decisions

### Release content sources
- `CHANGELOG.md` `[Unreleased]` — existing 1.8.0 draft (Phase 125)
- `release-notes.md` — GitHub release body template (CI substitutes `{{VERSION}}`, `.github/workflows/ci.yml` ~L332)
- `.planning/phases/125-lan-connection-tests/125-CONTEXT.md` — D-10, D-13, D-14: owner-approved notes wording
- Phase 121–124 directories under `.planning/phases/` — VERIFICATION/SUMMARY for user-facing changes and exposure conditions (D-08)

### Sandbox procedure
- `.planning/phases/122-*/122-SAFE01-EVIDENCE.md` — sandbox runbook, digest repin/restore and teardown pattern
- `.planning/phases/125-lan-connection-tests/125-CONTEXT.md` D-09 — sandbox Test Connection check and restore

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/ci.yml`: the tag pipeline publishes GHCR (strips the `v`), the GitHub release from `release-notes.md`, and PyPI. There's also a release-metadata check that requires the CHANGELOG link line.
- Prior evidence files (119 REL03, 119.1 REL04, 122 SAFE01) hold the NAS command recipes (absolute `sudo /usr/local/bin/docker` path, compose at `/volume1/docker/docker-compose.yml`).

### Established Patterns
- CI gate: full Python suite + whole-tree `ruff check src/python/` (a separate CI job) + Angular unit tests/Karma thresholds + e2e.
- Version metadata is bumped in every place the previous release set it (find all `1.7.6` occurrences).
- A push to `main` publishes `:dev`. That's acceptable but noted; production never uses it.

### Integration Points (NAS, observed 2026-10-28)
- Prod `seedsyncarr`: `:1.7.6@sha256:da6196e0…`. Sandbox `seedsyncarr-test`: `:1.7.6`, currently wired to `sonarr-v5`.
- Arr containers: `sonarr` (linuxserver :latest, prod), `sonarr-v4` (4.0.20), `sonarr-v5` (develop), `radarr`. wud 8.2.2 is running and healthy.

</code_context>

<deferred>
## Deferred Ideas

None. The discussion stayed within phase scope. (Backlog items such as scanner buffering, extract-staging hardening, 999.5 Sonarr API v5 and 999.6/999.7 stay in the backlog and are not part of 1.8.0.)

</deferred>

---

*Phase: 126-release-1-8-0*
*Context gathered: 2026-10-28*
