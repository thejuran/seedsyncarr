# Phase 130: Release 1.8.1 - Context

**Gathered:** 2026-11-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Release 1.8.1 (REL-07, REL-08): ship Phases 127–129 (README accuracy, Arr key whitespace normalization, web-service cleanup isolation) as 1.8.1. Confirm the fail-before/pass-after regressions for ARR and WEB. Triage Dependabot and roll in only justified fixes. Publish from a green release commit, smoke-test the exact published digest on the NAS sandbox, and deploy that same digest to NAS production. Done means a successful scan, a queue check and the owner's confirmation. This is a patch release with no new product capability.

</domain>

<decisions>
## Implementation Decisions

### Sequencing (PR #156)
- **D-01:** Phase 129's PR #156 (open, CI green on 2026-11-19) merges to `main` first as its own phase PR, keeping history, in line with one PR per phase. The 1.8.1 release branch is then cut from `main`. The release PR carries only the version bump, release notes and the dependency fixes.
- **D-02:** Claude merges #156 at the start of execution. This discussion is the owner's go-ahead. Re-confirm CI is green and the PR is mergeable before merging. If it isn't, stop and ask.

### Dependency triage (REL-07)
Snapshot taken 2026-11-19. Re-check at release time. Open alerts: soupsieve #108, #109, #111, #112 (2 high, 2 medium; first patched version 3.0.2) and minimatch #110 (dev, Angular, medium; first patched 11.0.1). Open Dependabot PRs: #154 (npm group, 23 updates incl. Angular 22.2.3→22.2.6), #153 (puppeteer), #151 (soupsieve 2.9.1→4.0), #149 (mkdocs-material), #147 (pytest), #146 (paste 3.10.1→3.11.0), #145 (pytz 2026.5→2026.6).
- **D-03:** **Soupsieve: roll in the fix** to clear all 4 alerts. It reaches the lockfile only through `webtest` → `beautifulsoup4` (dev tooling), but the lock marks it `main`. Research must confirm whether it actually ships in the Docker image or PyPI wheel, and state that in the owner summary. Use the smallest fixed version that passes CI (3.0.2+ satisfies the advisories; #151's 4.0 is acceptable if the minimal pin is impractical).
- **D-04:** **Shipped bumps (#146 paste, #145 pytz) go in only if justified.** Research reads each changelog. Roll a bump in only if it fixes a security issue or a bug that affects SeedSyncarr. Otherwise leave it for a later release and record why.
- **D-05:** **Fix the minimatch alert in the smallest possible way** (e.g. a targeted override or lockfile update). Leave #154 (Angular group), #153, #149 and #147 open. The shipped UI bundle should stay unchanged from 1.8.0 apart from anything the minimatch fix unavoidably touches. Research confirms that minimatch is build-time only.
- **D-06 (carried from 126 D-02):** If a roll-in breaks the build, tests, e2e or ruff, stop and ask the owner. Say which update failed and what the options are (drop it, or fix it, with an estimated size).
- **D-07 (carried from 126 D-04/D-05):** If a new runtime/shipped alert appears before the tag, raise it with the owner. At the pre-tag checkpoint, give the owner the final dependency list in plain terms: what was rolled in, what was left out and why, and the alert count before and after.

### Regression gates (REL-07)
- **D-08:** Confirm that the existing Phase 128 (ARR) and 129 (WEB) fail-before/pass-after regressions are present and green on the release commit. Point to the tests and their evidence rather than writing new ones. Add a test only if verification finds a gap. Also required green: the full Python suite, whole-tree `ruff check src/python/`, Angular tests, e2e and release CI.

### Smoke test (REL-08)
- **D-09:** Smoke on the standing sandbox `seedsyncarr-test`, **upgraded in place** from its existing 1.8.0 config. This mirrors production's 1.8.0→1.8.1 path. Repin it to the exact published `:1.8.1@sha256:…` digest and record the digest it replaces. It may stay on 1.8.1 afterwards. Production is read-only during the smoke.
- **D-10:** Smoke depth is REL-08 plus one real transfer:
  - setup/start on the upgraded config;
  - a queue completion check with a whitespace-padded key, entered through the normal Settings save path (not by hand-editing the config, per the Phase 128 hand-off);
  - stop/restart with **clean shutdown visible in the logs**, the Phase 129 D-08 hand-off (no "did not stop in time" warning, no port-bind failure on restart);
  - one real transfer completing.

  Don't re-run the auto-delete or webhook checks, since 1.8.1 didn't change them.
- **D-11:** Run the padded-key queue check against **both `sonarr-v4` (mirrors production) and `radarr`**. Afterwards, restore the sandbox's arr URLs, keys and wiring to their pre-smoke values, as in 126 D-12.

### Release notes
- **D-12:** The notes cover changes since 1.8.0. A plain **Fixed** line for the Arr key fix ("API keys with stray spaces, e.g. from copy-paste, now work"), plus "no configuration changes needed". No upgrade tip.
- **D-13:** A plain **Fixed** line for the shutdown fix: stopping or restarting no longer hangs or leaves the web server half-stopped. **The README corrections (Phase 127) are not mentioned in the notes.**
- **D-14:** List any dependency roll-ins that touch shipped code briefly and plainly. Omit dev-only ones, or give them one line at most.
- **D-15:** The rollback runbook in release-notes.md targets **1.8.0** (`:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`). Research must check whether Phases 127–129 changed any persisted state or config format in a way that affects rolling back (e.g. normalized keys written back to settings), and document any extra steps. Include the CHANGELOG link line the release-metadata check requires.

### Release route, approvals, deploy, rollback (carried from Phase 126)
- **D-16 (126 D-13):** Two owner checkpoints. The first comes before pushing the `v1.8.1` tag: show the notes, the dependency list (D-07) and CI status. The second comes before the production deploy: show the smoke results.
- **D-17 (126 D-14):** Release branch + PR CI green → merge keeping history → annotated `v1.8.1` tag from main → tag CI publishes GHCR, GitHub release and PyPI → sandbox smoke on that digest → production. Bump the version metadata to 1.8.1 everywhere 1.8.0 set it.
- **D-18 (126 D-15):** Production compose is pinned to `ghcr.io/thejuran/seedsyncarr:1.8.1@sha256:<same digest as smoked>`. Never `:dev`, never a local build. Back up the persist files and compose before the upgrade. Pause wud from the tag push until production is verified, then restore it.
- **D-19 (126 D-16):** If production clearly can't sync after the deploy, roll back immediately to 1.8.0 (digest above) using the backups, then tell the owner. If the situation is ambiguous, stop and ask.
- **D-20 (126 D-17):** Done when there's a successful scan after start (any warm-up scanner error must be followed by a later successful scan), a queue check succeeds, Sonarr/Radarr are reachable with no stuck holds, wud is restored and the owner confirms (recorded). A real production import isn't required.

### Claude's Discretion
- How each dependency fix is applied (Dependabot PR cherry-pick, a targeted pin or override, or lockfile regeneration), provided the result is CI-verified.
- Smoke scripting and evidence layout, reusing the Phase 126 SMOKE/DEPLOY evidence pattern and scripts.
- Exact wording of the release notes within D-12–D-14.
- Plan and wave grouping.

</decisions>

<specifics>
## Specific Ideas

- REL-07 is deliberately stricter than 1.8.0 (126 D-01 rolled in everything). For 1.8.1, the owner chose triage plus justified fixes only. Leaving PRs open is expected and fine.
- The owner's global release rule: review Dependabot before the bump, fix runtime deps, roll in dev-only ones only if they're cheap, and present the list in plain terms.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §"Phase 130: Release 1.8.1" — success criteria 1–4
- `.planning/REQUIREMENTS.md` — REL-07, REL-08

### Prior release pattern (follow it)
- `.planning/phases/126-release-1-8-0/126-CONTEXT.md` — D-11–D-17 carried forward here
- `.planning/phases/126-release-1-8-0/126-REL-EVIDENCE.md`, `126-SMOKE-EVIDENCE.md`, `126-DEPLOY-EVIDENCE.md` — command recipes and evidence format
- `.planning/phases/126-release-1-8-0/126-teardown.sh`, `126-extract_secrets.py` — reusable smoke helpers
- `.planning/phases/119.1-startup-log-secrets-fix-and-1-7-6-release/119.1-CONTEXT.md` — original release-gate, wud and rollback decisions

### What 1.8.1 ships (hand-offs into this phase)
- `.planning/phases/128-arr-key-normalization/128-CONTEXT.md` — line ~44: the padded-key smoke must use the normal settings save path
- `.planning/phases/128-arr-key-normalization/128-VERIFICATION.md` — ARR fail-before/pass-after evidence
- `.planning/phases/129-web-service-cleanup-isolation/129-CONTEXT.md` — D-08: the live restart/clean-shutdown check lives in this phase; the ServiceRestart/port-bind note
- `.planning/phases/129-web-service-cleanup-isolation/129-VERIFICATION.md` — WEB fail-before/pass-after evidence
- `.planning/phases/127-readme-accuracy/127-CONTEXT.md` — README changes (not in the release notes, per D-13)

### Release content
- `CHANGELOG.md` — the latest section is `[1.8.0]`. Add `[1.8.1]`.
- `release-notes.md` — GitHub release body template (CI substitutes `{{VERSION}}`)
- `.github/workflows/ci.yml` — tag pipeline and release-metadata check

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The tag pipeline in `.github/workflows/ci.yml` publishes GHCR (stripping the `v`), the GitHub release from `release-notes.md`, and PyPI.
- The Phase 126 smoke/deploy scripts and evidence files hold the NAS recipes (absolute `sudo /usr/local/bin/docker`, compose at `/volume1/docker/docker-compose.yml`).

### Established Patterns
- Version metadata is bumped in every place the previous release set it. Find every `1.8.0` occurrence, e.g. the `src/python/pyproject.toml` `[tool.poetry] version`.
- CI gates: Python suite, a separate whole-tree ruff job, Angular unit tests with Karma thresholds, e2e, Docker build, CodeQL, packaging check.
- Locally, 5 Python test modules fail or hang on macOS. Ignore them locally; PR CI is the authority.

### Dependency facts (2026-11-19)
- `soupsieve` 2.9.1 enters only via dev `webtest` → `beautifulsoup4`. The lock has `groups = ["main", "dev"]`.
- `paste` and `pytz` are direct runtime dependencies in `[tool.poetry.dependencies]`.

### Integration Points (NAS)
- As of 2026-10-28, prod `seedsyncarr` and sandbox `seedsyncarr-test` both run `:1.8.0@sha256:6e8d453f…`. Re-observe at execution time.
- Arr containers: `sonarr` (prod), `sonarr-v4`, `sonarr-v5`, `radarr`. wud is running.

</code_context>

<deferred>
## Deferred Ideas

- Dependabot PRs #154 (npm/Angular group), #153 (puppeteer), #149 (mkdocs-material) and #147 (pytest) stay open for a later release, as do #146/#145 if research finds no justifying fix.
- The README corrections aren't announced in the release notes (owner choice).

</deferred>

---

*Phase: 130-release-1-8-1*
*Context gathered: 2026-11-19*
