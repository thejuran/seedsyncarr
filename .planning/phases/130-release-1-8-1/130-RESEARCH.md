# Phase 130: Release 1.8.1 - Research

**Researched:** 2026-11-20
**Domain:** Patch release engineering: Dependabot triage (Poetry and npm lockfiles), release gates, GHCR digest smoke test, NAS production deploy by digest
**Confidence:** HIGH (every dependency claim was checked against the live alert API, the published 1.8.0 image, or a scratch dry run. Only the smoke and deploy recipes are MEDIUM, because they come from Phase 126 artifacts and can't be rerun from here.)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Sequencing (PR #156)
- **D-01:** Phase 129's PR #156 (open, CI green on 2026-11-19) merges to `main` first as its own phase PR, keeping history, in line with one PR per phase. The 1.8.1 release branch is then cut from `main`. The release PR carries only the version bump, release notes and the dependency fixes.
- **D-02:** Claude merges #156 at the start of execution. This discussion is the owner's go-ahead. Re-confirm CI is green and the PR is mergeable before merging. If it isn't, stop and ask.

#### Dependency triage (REL-07)
Snapshot taken 2026-11-19. Re-check at release time. Open alerts: soupsieve #108, #109, #111, #112 (2 high, 2 medium; first patched version 3.0.2) and minimatch #110 (dev, Angular, medium; first patched 11.0.1). Open Dependabot PRs: #154 (npm group, 23 updates incl. Angular 22.2.3→22.2.6), #153 (puppeteer), #151 (soupsieve 2.9.1→4.0), #149 (mkdocs-material), #147 (pytest), #146 (paste 3.10.1→3.11.0), #145 (pytz 2026.5→2026.6).
- **D-03:** **Soupsieve: roll in the fix** to clear all 4 alerts. It reaches the lockfile only through `webtest` → `beautifulsoup4` (dev tooling), but the lock marks it `main`. Research must confirm whether it actually ships in the Docker image or PyPI wheel, and state that in the owner summary. Use the smallest fixed version that passes CI (3.0.2+ satisfies the advisories; #151's 4.0 is acceptable if the minimal pin is impractical).
- **D-04:** **Shipped bumps (#146 paste, #145 pytz) go in only if justified.** Research reads each changelog. Roll a bump in only if it fixes a security issue or a bug that affects SeedSyncarr. Otherwise leave it for a later release and record why.
- **D-05:** **Fix the minimatch alert in the smallest possible way** (e.g. a targeted override or lockfile update). Leave #154 (Angular group), #153, #149 and #147 open. The shipped UI bundle should stay unchanged from 1.8.0 apart from anything the minimatch fix unavoidably touches. Research confirms that minimatch is build-time only.
- **D-06 (carried from 126 D-02):** If a roll-in breaks the build, tests, e2e or ruff, stop and ask the owner. Say which update failed and what the options are (drop it, or fix it, with an estimated size).
- **D-07 (carried from 126 D-04/D-05):** If a new runtime/shipped alert appears before the tag, raise it with the owner. At the pre-tag checkpoint, give the owner the final dependency list in plain terms: what was rolled in, what was left out and why, and the alert count before and after.

#### Regression gates (REL-07)
- **D-08:** Confirm that the existing Phase 128 (ARR) and 129 (WEB) fail-before/pass-after regressions are present and green on the release commit. Point to the tests and their evidence rather than writing new ones. Add a test only if verification finds a gap. Also required green: the full Python suite, whole-tree `ruff check src/python/`, Angular tests, e2e and release CI.

#### Smoke test (REL-08)
- **D-09:** Smoke on the standing sandbox `seedsyncarr-test`, **upgraded in place** from its existing 1.8.0 config. This mirrors production's 1.8.0→1.8.1 path. Repin it to the exact published `:1.8.1@sha256:…` digest and record the digest it replaces. It may stay on 1.8.1 afterwards. Production is read-only during the smoke.
- **D-10:** Smoke depth is REL-08 plus one real transfer:
  - setup/start on the upgraded config;
  - a queue completion check with a whitespace-padded key, entered through the normal Settings save path (not by hand-editing the config, per the Phase 128 hand-off);
  - stop/restart with **clean shutdown visible in the logs**, the Phase 129 D-08 hand-off (no "did not stop in time" warning, no port-bind failure on restart);
  - one real transfer completing.

  Don't re-run the auto-delete or webhook checks, since 1.8.1 didn't change them.
- **D-11:** Run the padded-key queue check against **both `sonarr-v4` (mirrors production) and `radarr`**. Afterwards, restore the sandbox's arr URLs, keys and wiring to their pre-smoke values, as in 126 D-12.

#### Release notes
- **D-12:** The notes cover changes since 1.8.0. A plain **Fixed** line for the Arr key fix ("API keys with stray spaces, e.g. from copy-paste, now work"), plus "no configuration changes needed". No upgrade tip.
- **D-13:** A plain **Fixed** line for the shutdown fix: stopping or restarting no longer hangs or leaves the web server half-stopped. **The README corrections (Phase 127) are not mentioned in the notes.**
- **D-14:** List any dependency roll-ins that touch shipped code briefly and plainly. Omit dev-only ones, or give them one line at most.
- **D-15:** The rollback runbook in release-notes.md targets **1.8.0** (`:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`). Research must check whether Phases 127–129 changed any persisted state or config format in a way that affects rolling back (e.g. normalized keys written back to settings), and document any extra steps. Include the CHANGELOG link line the release-metadata check requires.

#### Release route, approvals, deploy, rollback (carried from Phase 126)
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

### Deferred Ideas (OUT OF SCOPE)
- Dependabot PRs #154 (npm/Angular group), #153 (puppeteer), #149 (mkdocs-material) and #147 (pytest) stay open for a later release, as do #146/#145 if research finds no justifying fix.
- The README corrections aren't announced in the release notes (owner choice).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-07 | Release 1.8.1 passes its gates: ARR and WEB fail-before/pass-after regressions, full test suite, whole-tree `ruff check src/python/`, release CI. Dependency work is limited to triage and justified fixes, with open alerts and PRs surfaced to the owner before the tag. | §Regression gates (exact test node IDs and prior red evidence); §Dependency triage (soupsieve fix recipe, paste/pytz verdicts, minimatch lockfile recipe, verified bundle identity); §Version metadata; §Validation Architecture |
| REL-08 | The 1.8.1 image is smoke-tested by digest (setup, queue completion check with a whitespace-padded key, stop/restart), then deployed to NAS production with that exact digest, followed by a successful scan, a queue check and owner confirmation. | §Smoke recipes (padded key through `POST /server/config/set`, queue-check proof via the `No matching queue entry` hold, clean-shutdown log strings, in-app restart route); §Deploy and rollback (126 runbook reuse, no state-format change); Open Question 1 (production queue-check evidence) |
</phase_requirements>

## Summary

This patch release follows the Phase 126 (1.8.0) playbook almost exactly. The 126 artifacts already contain working recipes for every step: the release branch and PR, the tag CI, the GHCR digest cross-check (two methods), the sandbox repin by inode-preserving compose edit, `teardown.sh`, the count-only secrets extractor, `parse_check.py` loader checks, production backups, the wud pause and the rollback runbook. Plan 130 on the 126 plan shape, with less smoke depth (no webhook, no auto-delete, no token probe) and the new checks added: padded key, clean shutdown and in-app restart.

Research found facts that correct or sharpen CONTEXT's dependency assumptions:

1. **Soupsieve needs version 4.0.0 or later, not 3.0.2.** Alert #109 (high, GHSA-mmhr-3c5m-f64f) covers `< 4.0.0`, so 4.0.0 is the smallest version that clears all four alerts.
2. **Dependabot PR #151 doesn't fix the alerts.** Its title says 4.0, but its lockfile diff resolves to **2.10**, which still leaves #109, #111 and #112 open. It was also generated by Poetry 2.5.1, while the Dockerfile pins 2.3.4.
3. **Why Poetry can't pick 4.x today.** Every soupsieve ≥3.0.2 requires Python `>=3.11.5`, and the project's Poetry constraint is `>=3.11,<3.13`. The fix is to narrow only `[tool.poetry.dependencies] python` to `">=3.11.5,<3.13"` (the `[project] requires-python` that PyPI sees stays unchanged). The scratch dry run gave soupsieve 4.1.2 with `poetry check` warnings unchanged, and 564 web tests passed.
4. **Soupsieve doesn't ship.** It is absent from the published 1.8.0 image (`ModuleNotFoundError`) and from the `scanfs` PyInstaller archive (0 entries). It isn't a dependency of the PyPI wheel either, since it only comes in through the `dev` extra.
5. **minimatch is dev-only.** A lockfile-only `npm update` of the eslint/typescript-eslint packages moves every vulnerable `minimatch@10.2.6` to 11.0.9. Lint stays clean, and the production Angular build stayed **byte-identical to the published 1.8.0 `/app/html`**. Don't use npm `overrides`: the whole `src/angular/package.json`, including devDependencies and overrides, is embedded in `main-*.js`, so any `package.json` edit changes the shipped bundle bytes.
6. **paste 3.11.0 fixes a CRITICAL advisory, but in a module SeedSyncarr doesn't use.** The advisory (GHSA-vf89-fq68-57cx) is a pickle/path-traversal flaw in `paste.session`. SeedSyncarr imports only `paste.httpserver` and `paste.translogger`. 3.11.0 also adds an import-time `DeprecationWarning` (all of paste is now deprecated) and drops paste's `setuptools` dependency. **Recommend leaving #146 out**, but tell the owner plainly because of the "critical" label. **pytz isn't imported by any runtime code**, so leave #145 out.

The rollback check (D-15) found nothing to add. Phases 127–129 changed no persisted format: `common/config.py`, the persist modules and `seedsyncarr.py` have zero diff since `v1.8.0`, and the only `common/` change is the new `arr_api_key.py`. Keys that 1.8.1 saves are trimmed, valid keys that 1.8.0 reads fine. The 1.8.0 runbook carries over with renamed files and target, plus the existing AutoDelete-off step.

**Primary recommendation:** Merge #156, then cut `release/1.8.1` from main. Make one commit for soupsieve (pyproject Poetry Python narrowing + `poetry update soupsieve --lock`), one lockfile-only commit for minimatch (checked by bundle hash identity against 1.8.0), then the version bump, CHANGELOG and release notes. Gate it, take owner checkpoint 1, merge, poll Dependabot after the merge, tag, and then reuse the 126 smoke and deploy recipes with the new padded-key and shutdown checks.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dependency fixes (soupsieve, minimatch) | Build/dependency manifests (`src/python/pyproject.toml`, `poetry.lock`, `src/angular/package-lock.json`) | CI (verification) | Lockfile-level only; no source change |
| Version metadata, CHANGELOG, release notes | Repo root and package manifests | CI `verify-release-metadata` job | Checked on tag by `scripts/verify-release-metadata.mjs` |
| Publishing (GHCR, GitHub release, PyPI) | GitHub Actions tag pipeline (`.github/workflows/ci.yml`) | — | Only a `v*` tag push publishes |
| Padded-key normalization (what's under test) | API/Backend (`web/handler/config.py` save path, `controller/arr_queue.py` read path) | Browser UI `ConfigService` → `POST /server/config/set` | The smoke uses the same HTTP route the UI uses |
| Clean shutdown/restart (what's under test) | Backend process lifecycle (`seedsyncarr.py`, `web/web_app_job.py`) | Docker (SIGTERM, 10 s grace) | Two paths: container stop/restart and in-app `ServiceRestart` |
| Sandbox smoke and production deploy | NAS Docker host (`seedsyncarr-test`, `seedsyncarr`, compose files) | Seedbox (synthetic roots), Sonarr/Radarr (read-only GETs) | Operator steps over `ssh nas` |

## Standard Stack

No new libraries. The tooling below is already in the repo, and every item was checked in this session.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Poetry | 2.3.4 (local and Dockerfile pin) | Python lock regeneration | Dockerfile pins `poetry==2.3.4`; regenerate with the same version so the lock header stays `Poetry 2.3.4` [VERIFIED: `poetry --version`, Dockerfile line 49/105] |
| npm | 11.12.1 local (Node 25); CI uses Node 22 | Angular lockfile update | Same lockfile v3 format; 126 roll-ins were also done locally [VERIFIED: `npm --version`] |
| ruff | 0.15.22 (CI pin) | Whole-tree Python lint gate | CI job `Lint (Python)` pins `ruff==0.15.22` [VERIFIED: ci.yml line 91] |
| gh CLI | present | PR/CI/Dependabot queries, merge | 126 pattern [VERIFIED: `command -v gh`] |
| docker buildx | v0.38.1 local | GHCR digest method A (`imagetools inspect`) | 126 pattern [VERIFIED] |

### Dependency changes recommended in this release
| Package | Ecosystem | From → To | Scope | Ships? |
|---------|-----------|-----------|-------|--------|
| soupsieve | PyPI | 2.9.1 → 4.x (4.1.2 at research time; minimum fixing 4.0.0) | dev (via webtest → beautifulsoup4) | **No.** Verified absent from the 1.8.0 image and scanfs |
| minimatch (top-level instance) | npm | 10.2.6 → 11.0.x (11.0.9 at research time) | dev (eslint, @eslint/config-array, @typescript-eslint/typescript-estree) | **No.** Bundle byte-identical |
| eslint | npm | 10.13.0 → 10.15.0 (lock only, range `^10.13.0` unchanged) | dev | No |
| @typescript-eslint/* and typescript-eslint | npm | 8.72.1 → 8.73.0 (lock only) | dev | No |
| @eslint/config-array | npm | 0.23.5 → 0.23.6 | dev | No |
| @isaacs/nonrecursive-glob-match | npm | new, 1.1.0 | dev (required by every minimatch ≥11.0.1) | No |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Narrowing `[tool.poetry.dependencies] python` to `>=3.11.5` | Cherry-pick Dependabot #151 | **Don't.** #151 resolves to soupsieve 2.10, which leaves 3 of 4 alerts open, and bumps the lock header to Poetry 2.5.1 |
| Narrowing only the Poetry constraint | Also narrowing `[project] requires-python` | Changes PyPI wheel metadata, so `pip` users on Python 3.11.0–3.11.4 (e.g. Debian bookworm's 3.11.2) would be refused. Unnecessary; leave `[project]` alone |
| Lockfile-only `npm update` for minimatch | npm `overrides` (`"minimatch": "^11"`) | A global override would also force karma's `minimatch@3.1.5` to v11, which breaks the API. Any override also edits `package.json`, which is embedded in the shipped bundle, so the bundle bytes would change |
| Lockfile-only `npm update` | Merging #154 | #154 is the Angular group (deferred by D-05), and its typescript-eslint 8.72.2 still depends on minimatch ^10, so it wouldn't fully clear the alert anyway |
| Pinning soupsieve to exactly 4.0 | Taking the resolver's latest 4.x | Pinning 4.0 exactly would mean adding a direct dev dependency (a bigger pyproject change). Recommend the resolver result: dev-only, all 4.x versions are past every advisory, and CI is the arbiter. Tell the owner "4.x" |

**Installation / regeneration commands (executor runs them on the release branch):**
```bash
# soupsieve (one commit: pyproject.toml + poetry.lock)
cd src/python
#   edit [tool.poetry.dependencies]  python = ">=3.11,<3.13"  ->  python = ">=3.11.5,<3.13"
#   ([project] requires-python stays ">=3.11,<3.13")
poetry update soupsieve --lock
grep -A2 '^name = "soupsieve"' poetry.lock          # expect version = "4.x"
head -1 poetry.lock                                   # expect "Poetry 2.3.4"

# minimatch (one commit: src/angular/package-lock.json only)
cd src/angular
npm update --package-lock-only --ignore-scripts eslint @eslint/config-array \
  @typescript-eslint/parser @typescript-eslint/eslint-plugin \
  @typescript-eslint/typescript-estree typescript-eslint
git diff --stat            # expect ONLY src/angular/package-lock.json
npm ci && npm ls minimatch --all   # no minimatch in [7.0.0, 11.0.1); karma's 3.1.5 remain
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| soupsieve | PyPI | years (existing dep) | very high | github.com/facelessuser/soupsieve | [OK] | Approved |
| minimatch | npm | years (existing dep) | very high | github.com/isaacs/minimatch | [OK] | Approved |
| eslint | npm | years (existing dep) | very high | github.com/eslint/eslint | [OK] | Approved |
| typescript-eslint, @typescript-eslint/parser | npm | years (existing deps) | very high | github.com/typescript-eslint/typescript-eslint | [OK] | Approved |
| @isaacs/nonrecursive-glob-match | npm | created 2026-10-26 (~3.5 weeks) | not measured | maintainer `isaacs` (minimatch's author); SLSA provenance attestation present | [SUS] (new package) | Flagged. Planner must add a verification step. It is a hard dependency of **every** patched minimatch (11.0.1–11.0.9 all declare it), so it can't be avoided if the alert is to be fixed. Its install scripts are only `prepare`/test (no `preinstall`/`install`/`postinstall`) [VERIFIED: `npm view … scripts`] |

**Packages removed due to slopcheck [SLOP] verdict:** none. (A first run without `--pkg npm` checked npm names against PyPI and falsely reported SLOP. Rerun per ecosystem, all OK except the one above.)
**Packages flagged as suspicious [SUS]:** `@isaacs/nonrecursive-glob-match`. Before the release PR, the executor should record `npm view @isaacs/nonrecursive-glob-match@<ver> maintainers dist.attestations` and `npm audit signatures` output in evidence. The owner sees it as one line in the D-07 dependency list ("a new small helper package from minimatch's own author, required by the fixed minimatch, dev-only").

`brace-expansion` stays at 5.0.12 (minimatch 11 needs `^5.0.12`). No root `package-lock.json` change.

## Architecture Patterns

### Release flow (data/approval flow)

```
PR #156 (Phase 129, CI green, MERGEABLE/CLEAN)
   │  gh pr merge 156 --merge  (history kept; triggers :dev publish + Dependabot rescan of main)
   ▼
main ──► git checkout -b release/1.8.1
            │ commit A: soupsieve (pyproject Poetry python + poetry.lock)
            │ commit B: minimatch (src/angular/package-lock.json only)  ← bundle-hash check vs 1.8.0 here
            │ commit C: version bump 1.8.1 (7 sites) + CHANGELOG [1.8.1] + release-notes.md
            │ local gate: pytest (macOS ignores), ruff 0.15.22, Karma (docker), ng build, packaging, metadata
            ▼
         push → PR into main → CI (8 gate jobs + CodeQL) green
            ▼
   ◆ OWNER CHECKPOINT 1 (notes, D-07 dependency list, CI)  ── hold/changes → amend
            ▼ "approve"
   pause wud (prod NAS) → gh pr merge --merge → poll Dependabot alerts on main
            │ new runtime alert? → STOP, ask owner (D-07). (In 126 this happened: #106/#107)
            ▼ 0 open (or only owner-accepted)
   git tag -a v1.8.1 <main merge sha> → push tag
            ▼ tag CI: verify-release-metadata, e2e amd64+arm64, Publish GHCR (:1.8.1 + :latest), GitHub Release, PyPI
   RELEASE_DIGEST (method A buildx imagetools == method B anonymous GHCR HEAD)
            ▼
   Sandbox seedsyncarr-test: repin 1.8.0 → 1.8.1@RELEASE_DIGEST (in place)
     start/upgrade → padded key (Sonarr v4, then Radarr) → queue check → real transfer
     → container restart + in-app restart (clean-shutdown log check) → teardown/restore
            ▼
   ◆ OWNER CHECKPOINT 2 (smoke table)  ── "deploy"
            ▼
   Production: precheck → stop → backups (+sha256) → parse_check both images → compose repin (inode-preserving)
     → up -d → .Image == SMOKE_IMAGE_ID → scan OK → Test Connection both → queue check → steady state
     → no-secrets count → wud start → re-fingerprint → owner "confirmed"
     (can't sync → rollback to 1.8.0@6e8d453f… with backups; ambiguous → ask)
```

### Recommended plan shape (mirrors 126's six plans, slimmed)
| Plan | Wave | Content | Autonomous |
|------|------|---------|-----------|
| 01 | 1 | Merge #156 (D-02 rechecks), cut `release/1.8.1`, Dependabot snapshot, soupsieve + minimatch commits with targeted checks, bundle-identity proof | yes (stop rule D-06) |
| 02 | 2 | Version bump, CHANGELOG, release notes + rollback runbook, regression-gate confirmation (D-08), full local gate, push, PR, CI green | yes |
| 03 | 3 | Owner checkpoint 1 → wud pause → merge → post-merge Dependabot poll → tag → tag CI → digest, GH release, PyPI checks | no |
| 04 | 4 | Sandbox smoke on RELEASE_DIGEST (130 copies of the harness with `SSA130.` / `probe130` prefixes) → teardown → owner checkpoint 2 | no |
| 05 | 5 | Production deploy, verification, wud restore, owner confirmation, final Dependabot state | no |

A separate harness plan (126-02) isn't needed. The 126 scripts exist and work, and only prefix renames are needed (see Pitfall 6). Optionally fold harness prep into Plan 04's first task.

### Anti-Patterns to Avoid
- **Cherry-picking #151.** See Alternatives. It fixes 1 of 4 alerts.
- **Using `overrides` for minimatch.** It changes shipped bundle bytes (package.json is embedded) and risks breaking karma's minimatch 3.
- **Hand-editing `poetry.lock`.** Always regenerate with Poetry 2.3.4.
- **Pushing the local Phase 130 docs commits to PR #156 before merging.** Local branch HEAD `47a9d5b6` is 2 commits ahead of PR head `d23f4bdc`. Pushing them restarts CI (~25 min) for planning-only changes. Merge #156 at `d23f4bdc` and carry the `.planning/` commits onto the release branch, as 126 did.
- **Treating the `git push` advisory banner as an alert count.** 126 documented that it disagrees with the alerts API. The API is the source of truth.
- **Printing key values.** Every key move goes through 0600 files and `jq -nR … < file`, with counts and sha256 comparisons only (126 pattern). The 1.8.0 save response echoed the value (`set to <value>`); 1.8.1 returns `<section>.<key> updated`. Still never record response bodies for secret saves.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sandbox restore | New restore script | `.planning/phases/126-release-1-8-0/126-teardown.sh` (sha256 `a7f059da…c225e`, includes the jq-1.5 and empty-restore fixes) copied to `130-teardown.sh` with prefixes changed | Already idempotent; handles jq 1.5 on the NAS, empty-value restores and URL restore edge cases |
| No-secrets log check | grep for key patterns | `126-extract_secrets.py` (sha256 `c35768d7…baef6`, identical to the 119.1 version) run in the release image `--read-only --network none --cap-drop ALL --user 1026:100` | Count-only, handles `%` serialized forms |
| Backup loader check | Ad-hoc parse | `.planning/phases/118-durable-state/118-05-parse_check.py` (sha256 `920363ac…5dd53`, matches 126) run in **both** the 1.8.0 and 1.8.1 images | Proves both versions can load the backups (rollback safety) |
| Release digest | Single source | Method A `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:1.8.1` + method B anonymous token `HEAD /v2/thejuran/seedsyncarr/manifests/1.8.1` (OCI index Accept) | 126 cross-check; `:latest` index digest legitimately differs (attestation manifest), but the per-platform digests match |
| Compose repin | `sed -i` (replaces the inode) | `sed … > tmp && cat tmp > docker-compose.yml`, checking the inode before and after, the wud label count and `grep -c seedsyncarr:dev == 0` | 118/126 established the inode-preserving pattern |
| Alert count | `npm audit`, the push banner | `gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate --jq '[.[]|select(.state=="open")]|length'` | `npm audit` and GitHub alerts aren't 1:1 (126) |

## Runtime State Inventory (rollback / upgrade safety, D-15)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (settings.cfg, controller.persist, autoqueue.persist) | **No format change.** `git diff v1.8.0 origin/gsd/phase-129-web-service-cleanup-isolation -- src/python/common src/python/controller/*persist* src/python/controller/auto_queue.py src/python/seedsyncarr.py src/docker` shows only the new `common/arr_api_key.py` and a `common/__init__.py` export [VERIFIED]. 1.8.1 saves Arr keys trimmed. A trimmed key is valid for 1.8.0. `configparser` also strips surrounding whitespace on read, so unencrypted on-disk values were already trimmed at load time [VERIFIED: Python check]. | None. 1.8.0 reads 1.8.1-written state unchanged. Keep the 1.8.0 runbook's AutoDelete-off step: prod backups recorded `AutoDelete.enabled=True` in 126-1c. |
| Live service config | Production compose `/volume1/docker/docker-compose.yml` (image pin line, 34 `wud.` labels at 1.8.0 time); sandbox compose `/volume1/docker/v5test/docker-compose.yml`; wud container state | Repin by inode-preserving edit; pause and restore wud |
| OS-registered state | None. Docker restart policy and compose only. | None |
| Secrets/env vars | Sandbox `settings.cfg` holds Sonarr/Radarr keys. In 126, production Radarr's key was copied into the sandbox, then **cleared on disk** by an owner-sanctioned addendum (the API can't set empty values). D-11 needs a Radarr key in the sandbox again. | After the smoke, restore Radarr URL/key to empty by the 126-05 addendum procedure (stop sandbox, 0600 backup, inode-preserving awk edit, start, sha256 DIFFERENT check, delete backup). Get owner sanction at the smoke checkpoint, or ahead of time in the plan. |
| Build artifacts | GHCR `:1.8.1` and `:latest` tags, PyPI `seedsyncarr==1.8.1` (can't be re-uploaded), GitHub release `v1.8.1` | Irreversible after the tag. This is why owner checkpoint 1 comes first. |

**Rollback consequence (for release notes):** rolling back to 1.8.0 brings back the two fixed bugs. The shutdown hang can return. A padded key is sent unnormalized again, but only while the padded value is in memory (until restart) or when encryption at rest is on (an encrypted value keeps its padding). Rollback needs no data conversion. The `%`-in-secrets handling is unchanged (`common/config.py` has zero diff), so no step is needed for that.

## Common Pitfalls

### Pitfall 1: New Dependabot alerts appear only after merging to main
**What goes wrong:** In 126, two alerts (#106 qs, #107 setuptools) appeared within a minute of the release PR merging. That forced a follow-up PR #143 before the tag.
**Why:** GitHub rescans the default branch on merge, and new advisories get indexed continuously.
**How to avoid:** After `gh pr merge`, poll the alerts API (2 polls, about 2 minutes apart) **before** tagging. A new runtime/shipped alert means STOP (D-07). Merging #156 also triggers a rescan, so snapshot again before cutting the release branch.
**Warning signs:** Alert count goes up instead of down after a merge.

### Pitfall 2: The soupsieve fix silently resolves to 2.10
**What goes wrong:** `poetry update soupsieve` without the Python narrowing produces 2.10 (verified in scratch), which looks like an upgrade but leaves #109, #111 and #112 open.
**How to avoid:** Assert `version` ≥ 4.0.0 in the lock, and after the merge confirm via the alerts API that #108, #109, #111 and #112 are closed.

### Pitfall 3: The bundle changes even though "only lockfiles changed"
**What goes wrong:** `src/angular/src/app/common/version.ts` does `require("../../../package.json")`, and esbuild embeds the **entire** package.json object (name, scripts, dependencies, devDependencies, overrides) in `main-*.js` [VERIFIED: grep of the 1.8.0 `main-PNOY3NS3.js`].
**Consequence:** (a) any `package.json` edit, including overrides, changes the shipped JS bytes. (b) The version bump itself changes `main-*.js` (so its content-hash filename changes) and therefore `index.html`.
**How to prove "bundle unchanged":** Before the version bump, build and compare file-by-file sha256 against the published 1.8.0 `/app/html` (recipe in Code Examples). Expect **identical**: research reproduced this for both the current tree and the minimatch-fixed lockfile. After the bump, expect exactly two differing files (`main-*.js`, `index.html`). Normalizing `version:"1.8.1"` back to `1.8.0` and the main filename in `index.html` should make them identical again.

### Pitfall 4: Clean shutdown has two different paths
**What goes wrong:** `docker restart` sends SIGTERM and the process exits, so a new process binds port 8800 fresh, and the port-bind risk is never exercised. The Phase 129 port-bind concern is the **in-process** `ServiceRestart` (UI Restart button → `POST /server/command/restart`), where the old web thread must release the port before the next `setup()` binds.
**How to avoid:** The smoke must do **both**: (a) a container restart, checking that `Caught signal SIGTERM` → `Exiting Seedsyncarr` → `Exited successfully` appears within the 10 s grace, ExitCode 0 on a stop; (b) an in-app restart via `curl -X POST http://127.0.0.1:8801/server/command/restart`, expecting `Received a restart action`, then `Restarting (auto=False, reset=False, consecutive=…)`, then a fresh `Starting SeedSyncarr`, with `/server/status` reachable again.
**Check both the container log (`docker logs`, stderr) and the app log file.** Per the Phase 129 D-08 hand-off, a server-thread bind failure goes to stderr only (backlog 999.10).
**Must be absent:** `Error stopping web app during web service cleanup`, `Error stopping web server during web service cleanup`, `Error joining web server thread during web service cleanup`, `Web server did not stop within 5.0 seconds; continuing shutdown`, `Address already in use` / `Errno 98`, and `Exception in thread` (stderr). Also expect 0 `Traceback`.

### Pitfall 5: A queue check only runs when there is an auto-queue candidate
**What goes wrong:** `CompletionGate._run` only calls `start_fetch` `if candidates:` [VERIFIED: completion_gate.py line 216]. With no new remote item, no queue request is ever made, and "queue check works" can't be observed.
**How to avoid (sandbox):** Create a synthetic root on the seedbox (`SSA130.*`, 126 pattern). The hold verdict is the proof. `Completion hold for 'SSA130…': No matching queue entry` is only reachable when **every** enabled arr's queue snapshot is fresh, i.e. each fetch succeeded with the key (completion_gate.py lines 358–366). A key failure would instead show `Sonarr unavailable` / `Radarr unavailable` with a `queue check failed: HTTP 401` or `queue check skipped: API key is missing or invalid` warning.
**Production:** see Open Question 1.

### Pitfall 6: Harness prefix guards
**What goes wrong:** `126-teardown.sh` refuses synthetic roots not starting `SSA126.`, probe containers not starting `seedsyncarr-probe126` and dirs not under `/volume1/docker/probe126-`. Reusing it unchanged with `SSA130.` names makes teardown refuse cleanup.
**How to avoid:** Copy to `130-teardown.sh` and change the three prefixes (and header comments). Re-run `bash -n` and `shellcheck`, then do the 126-style dry run on the live sandbox with an empty capture dir (all `ok (not set this session)`, exit 0) before any change. The probe container and dirs aren't needed in 130 (no token probe).

### Pitfall 7: The API can't restore empty values
**What goes wrong:** `ConfigHandler.__handle_set_config` returns 400 for any empty value (D-06), so teardown can't restore `radarr_url`/`radarr_api_key` to empty. The sandbox currently has Radarr **disabled with empty URL and key** (126 addendum).
**How to avoid:** Restore `radarr.enabled=false` via the API (teardown does this), then clear URL and key on disk with the 126-05 addendum procedure. Record `RADARR_*_L0` in `state.env` before touching anything.

### Pitfall 8: Rate limits on the config API
`/server/config/set` is limited to 60 requests per 60 s and each Test Connection route to 5 per 60 s [VERIFIED: config.py lines 158–169]. Smoke scripts that loop Test Connection must pace themselves, otherwise a 429 looks like a failure.

### Pitfall 9: macOS local test limits
Locally, exclude `tests/unittests/test_controller/test_extract/test_extract_process.py`, `tests/unittests/test_controller/test_scan/test_scanner_process.py`, `tests/unittests/test_ssh/test_sshcp.py`, `tests/unittests/test_system/test_scanner.py` and `tests/integration/test_lftp/`. Linux PR CI (`Python unit tests`, dockerized) is the authority for the full suite and the coverage floor of 88.

### Pitfall 10: The paste Dependabot PR claims a critical fix
#146's body links GHSA-vf89-fq68-57cx ("critical", 9.8). The owner may see "critical" and assume SeedSyncarr is exposed. Explain plainly that the flaw is in paste's *session cookie* feature, which SeedSyncarr never loads: it imports only `paste.httpserver` and `paste.translogger` [VERIFIED: grep]. There's also no Dependabot alert for it (the advisory has no CVE and isn't in the global advisory DB, so `gh api /advisories/GHSA-vf89-fq68-57cx` returns 404).

## Dependency triage details (D-03, D-04, D-05)

### Live snapshot (2026-11-20, `gh api …/dependabot/alerts --paginate`)
| # | Package | Severity | Scope (per GitHub) | Vulnerable | First patched |
|---|---------|----------|--------------------|-----------|---------------|
| 108 | soupsieve | medium | runtime* | ≤ 2.9.2 | 2.10.0 |
| 109 | soupsieve | **high** | runtime* | **< 4.0.0** | **4.0.0** |
| 110 | minimatch | medium | development | ≥ 7.0.0, < 11.0.1 | 11.0.1 |
| 111 | soupsieve | medium | runtime* | ≥ 0.4, ≤ 2.10 | 3.0.2 |
| 112 | soupsieve | **high** | runtime* | ≤ 2.10 | 3.0.2 |

*GitHub labels these "runtime" because the lock lists `groups = ["main","dev"]`. The `main` membership carries `markers = {main = "extra == \"dev\""}`, so it only applies when the `dev` extra is installed [VERIFIED: poetry.lock line 1394].

Open Dependabot PRs: #154, #153, #151, #149, #147, #146, #145 (same as CONTEXT). The CONTEXT note "first patched 3.0.2" applies to #111 and #112 only. **4.0.0 is required for #109.**

### Soupsieve "does it ship?" evidence
- Runtime stage runs `poetry install --only main` with no extras (Dockerfile line 116), so the `extra == "dev"` marker excludes it.
- In the published 1.8.0 image, `pip list` shows no soupsieve, beautifulsoup4 or webtest, and `python3 -c "import soupsieve"` gives `ModuleNotFoundError` [VERIFIED].
- The `scanfs` binary is built in a stage that runs a full `poetry install`, but `pyi-archive_viewer -l -r` on `/app/scanfs` lists 302 entries with 0 matching soupsieve/bs4/webtest [VERIFIED].
- PyPI wheel: `[project].dependencies` doesn't include it. It only arrives with `seedsyncarr[dev]` [VERIFIED: pyproject.toml].
- **Owner wording:** "The 4 soupsieve alerts are in a test-only tool. It isn't inside the Docker image or the PyPI package, so users were never exposed. We're updating it anyway so the alerts close."

### paste #146 (3.10.1 → 3.11.0): recommend LEAVE
- Changes [VERIFIED: PR body + `gh api repos/pasteorg/paste/compare/3.10.1...3.11.0`]: fixes GHSA-vf89-fq68-57cx (critical, `paste.session` unpickles a cookie-chosen file), removes `pkg_resources`, **adds `warnings.warn("Paste is not being actively maintained…", DeprecationWarning)` at `import paste`**, and drops `setuptools` from install_requires.
- SeedSyncarr usage: `web/web_app_job.py` only (`from paste import httpserver`, `from paste.translogger import TransLogger`). No `paste.session`, no `SessionMiddleware` [VERIFIED: grep].
- Risk of rolling in: Phase 129's new shutdown code depends closely on paste's httpserver internals (worker pool, `server_close`, running flag). The release would ship an untested-in-sandbox change to the very component this release fixes. Benefit: none reachable.
- Side effect if it's ever rolled in: setuptools would drop out of the runtime closure (it's only there via paste).
- Follow-up idea for the owner, not this phase: paste is now deprecated upstream, so a backlog item to replace it may be worth capturing.

### pytz #145 (2026.5 → 2026.6): recommend LEAVE
- The change is an IANA tz database 2026f data refresh only [VERIFIED: PR body commits].
- No runtime module imports pytz. Only two test files do (`tests/unittests/test_web/test_serialize/test_serialize_model.py`, `test_serialize_status.py`) [VERIFIED: grep]. A timezone data update can't affect SeedSyncarr behavior.

### minimatch #110: lockfile-only fix, verified
- All six minimatch dependents in `src/angular/package-lock.json` are `dev: true`. The vulnerable instance is the hoisted `node_modules/minimatch@10.2.6` (eslint, @eslint/config-array, @typescript-eslint/typescript-estree). karma, karma-coverage and glob use 3.1.5, which is **outside** the vulnerable range [VERIFIED: lockfile scan].
- Parent versions that depend on ^11: eslint 10.15.0 (`^11.0.5`), @eslint/config-array 0.23.6 (`^11.0.5`), @typescript-eslint/typescript-estree 8.73.0 (`^11.0.1`). Peer ranges are fine: typescript `>=4.8.4 <6.1.0` covers the project's `~6.0.3`, and eslint 10.15 requires Node `^20.19 || ^22.13 || >=24`, which CI's Node 22 satisfies [VERIFIED: npm view].
- Scratch dry run [VERIFIED]: `package.json` was unchanged and every lock change was `dev`. Changes were eslint, typescript-eslint packages, @eslint/config-array and minimatch, a new `@isaacs/nonrecursive-glob-match`, plus a dev-only `@emnapi/*` hoisting reshuffle (wasm32 optional bindings). `npm ci` then `npm run lint` passed (exit 0, eslint v10.15.0). `ng build --configuration=production` was **byte-identical to the 1.8.0 image's `/app/html`** (all files sha256-equal).
- Not touched: Angular framework packages, @angular/build/cli, karma, the root `package-lock.json`.

## Regression gates (D-08)

PR #156: `OPEN`, `MERGEABLE`, `CLEAN`, head `d23f4bdcd86130954939094a06912b3838aabd4b`, base `main`. All 13 non-publish checks were SUCCESS, including CodeQL; the 5 publish jobs were SKIPPED [VERIFIED: `gh pr view 156`, 2026-11-20]. Phase 128 merged via PR #155 (`8fbe8c5b` on origin/main).

### ARR (Phase 128): fail-before evidence in `128-VERIFICATION.md` (truths 2, 10, 12; probe table row "Regression fails before the fix: 18 failed, 3 passed" against pre-phase `2f2b1576`)
| Test (node ID, from `src/python`) | Proves |
|---|---|
| `tests/unittests/test_controller/test_arr_queue.py::TestArrQueueFetch::test_padded_in_memory_key_is_sent_normalized` | ARR-02 core regression: a padded stored key is sent trimmed |
| `tests/unittests/test_controller/test_arr_queue.py::TestArrQueueTargets::test_padded_key_and_trimmed_key_share_identity` | No spurious gate reset |
| `tests/unittests/test_controller/test_arr_queue.py::TestArrQueueFetch::test_invalid_key_*`, `::test_missing_key_skips_request` | ARR-03 fail-safe, no key in logs |
| `tests/integration/test_web/test_handler/test_arr_key_parity.py::TestArrKeyParity` (6 tests, incl. `test_padded_key_saved_then_same_key_on_all_three_paths[_radarr]`, `test_padded_key_in_live_config_agrees_between_test_connection_and_queue`) | ARR-01 save/test/queue parity |
| `tests/unittests/test_web/test_handler/test_config_handler.py::…::test_set_arr_key_sonarr_padded_is_trimmed`, `…radarr_padded_is_trimmed` | Save trims |
| `tests/unittests/test_common/test_arr_api_key.py` | Rule table |

### WEB (Phase 129): fail-before evidence in `129-VERIFICATION.md` (SC1: 11 failed/2 passed at `982e4518`; 129-02 tests: 7 failed/14 passed at `4ad109ec`)
| Test (`tests/unittests/test_web/test_web_app_job.py::…`) | Proves |
|---|---|
| `TestWebAppJobCleanup::test_app_stop_failure_still_stops_server_and_joins` | WEB SC1 core regression |
| `TestWebAppJobCleanup::test_server_stop_failure_still_joins_thread`, `::test_join_failure_is_logged_and_cleanup_returns`, `::test_all_steps_fail_all_attempted_and_logged` | SC2 |
| `TestWebAppJobCleanup::test_cleanup_without_setup_does_not_raise`, `::test_server_not_created_skips_server_and_join`, `::test_thread_not_started_skips_join` | SC3 |
| `TestMyWSGIRefServer::test_cleanup_returns_within_bound_with_stuck_requests`, `::test_process_exits_when_web_server_never_stopped`, `::test_real_server_stop_frees_port` | SC4, port release |

The file has 25 tests in total. No gap was found, so no new tests are needed. On the release commit, run the selectors and include the CI `Python unit tests` job result as authority. Re-proving fail-before isn't required by D-08 ("point to the tests and their evidence"). Cite the two verification files.

## Version metadata (D-17)

The 1.8.0 bump commit `c171598a` changed exactly these sites [VERIFIED: `git show --stat`]. Today's tree has `1.8.0` at:
| File | Location |
|---|---|
| `package.json` | `"version"` (line 2) |
| `package-lock.json` | top-level `"version"` (line 3) and `packages[""].version` (line 8) |
| `src/angular/package.json` | `"version"` (line 3). **This is embedded in the UI bundle and shown on the About page** |
| `src/angular/package-lock.json` | top-level (line 3) and `packages[""].version` (line 9) |
| `src/python/pyproject.toml` | `[project] version` (line 7) and `[tool.poetry] version` (line 47) |
| `CHANGELOG.md` | add `## [1.8.1] - YYYY-MM-DD` above `## [1.8.0] - 2026-10-28` |
| `release-notes.md` | rewrite for 1.8.1; must keep the last line `**Full changelog:** https://github.com/thejuran/seedsyncarr/blob/v{{VERSION}}/CHANGELOG.md` with the literal `{{VERSION}}` placeholder (checker regex `/v\{\{VERSION\}\}\/CHANGELOG\.md\b/`; CI substitutes it with `sed` at release time) |

`scripts/verify-release-metadata.mjs <ver>` checks 6 things: a CHANGELOG heading matching `^##\s+\[?1.8.1\]?(\s+-\s+.+)?$`, the release-notes `v{{VERSION}}/CHANGELOG.md` link, and the 4 JSON version fields. It does **not** check pyproject (the PyPI job stamps the version from the tag with `sed`), but bump pyproject anyway (126 precedent; `poetry check` and the packaging job build `seedsyncarr-<ver>`). CHANGELOG compare-link references at the bottom stop at 1.4.0, so don't add a 1.8.1 link reference (convention since 1.5.0).

**CHANGELOG/notes content constraints:** D-12 (Arr key Fixed line + "no configuration changes needed"), D-13 (shutdown Fixed line; no README mention), D-14 (shipped roll-ins: **none**, if the recommendation holds, because soupsieve and minimatch are both dev-only; at most one dev-tooling line). The rollback section targets `ghcr.io/thejuran/seedsyncarr:1.8.0` (digest `6e8d453f…4879aa7`), with backups named `.pre-1.8.1`, and the AutoDelete-off step kept. Remove 1.8.0-specific text: the container-name Test Connection caveat and the security-regression line no longer apply as written. The 1.8.0 security fixes stay in place on a rollback to 1.8.0; rolling back loses only the two 1.8.1 fixes.

## Smoke recipes (D-09 to D-11), derived from repo artifacts

Sandbox facts (from 126-SMOKE-EVIDENCE, re-observe at execution): container `seedsyncarr-test`, API `http://127.0.0.1:8801` (no api_token at 126 time), compose `/volume1/docker/v5test/docker-compose.yml`, config dir `/volume1/docker/v5test/seedsyncarr`, capture dirs under `/volume1/docker/v5test/results/`, seedbox staging `/home/jules1651/<stage>/` then `mv` into `/home/jules1651/v5test/`. Last known wiring: `sonarr_url=http://sonarr-v5:8989`, `radarr.enabled=false`, Radarr URL and key empty on disk. Image `:1.8.0@sha256:6e8d453f…`, image ID `sha256:12fba785…79309`. NAS `jq` is **1.5** (no `--rawfile`).

### Padded key through the normal Settings save path
The UI's Settings save is `ConfigService` → `POST /server/config/set` with JSON `{"section": …, "key": <option>, "value": <string>}` [VERIFIED: `src/angular/src/app/services/settings/config.service.ts:62`; handler `web/handler/config.py` `__handle_set_config`]. The 126 teardown's `post_arr_key()` already builds this body from a 0600 file without the value in argv. For padding, wrap the file content in the jq program:
```bash
# key file holds the bare arr key (0600, copied from the arr's config.xml, never printed)
jq -nR --arg section sonarr --arg key sonarr_api_key \
  '{section:$section,key:$key,value:("  " + ([inputs]|join("\n")) + " \t")}' < "$D/sonarr_v4.key" > "$D/body.json"
chmod 600 "$D/body.json"
curl -s -o /dev/null -w '%{http_code}\n' -H 'Content-Type: application/json' \
  -d @"$D/body.json" http://127.0.0.1:8801/server/config/set      # expect 200 (body "sonarr.sonarr_api_key updated")
shred -u "$D/body.json" 2>/dev/null || rm -f "$D/body.json"
```
Expected evidence, in order:
1. HTTP 200 on the save.
2. `GET /server/config/sonarr/test-connection` gives `{"success": true, "version": "4.…"}`.
3. A synthetic root on the seedbox produces `Completion hold for 'SSA130…': No matching queue entry` and no `queue check failed`, `queue check skipped` or `unavailable` lines.
4. Optional but strong: after a restart (persist writes `settings.cfg`), a count-only on-disk check that the stored key's sha256 equals the `sonarr-v4` config.xml key's sha256 (SAME). This proves it was stored trimmed.

Repeat for Radarr (`section radarr`, `radarr_api_key`, plus `radarr_url=http://radarr:7878` and `radarr.enabled=true`; the key comes read-only from production Radarr's mounted config.xml, as in 126). The hold must stay `No matching queue entry` with both arrs enabled. That outcome needs both queue fetches to succeed. SeedSyncarr only makes `GET` requests to the arrs (`/api/v3/queue`, `/api/v3/system/status`) [VERIFIED: grep shows no requests.post/put/delete], so production Radarr only receives reads.

Optional extra (cheap, valuable, Claude's discretion): before repinning, while still on 1.8.0, check the sandbox key wiring. Don't save a padded key on 1.8.0: its save response echoes the value, and configparser would strip it at the next load anyway, so this proves little. Skip it.

### Real transfer
Same as 126: release the held synthetic root with `POST /server/command/queue/<name>?release_unverified=true`. The log shows `Manual release of unverified …` then `Completion hold dropped …`. Compare local and remote sha256, and check the model state reaches `downloaded`. Teardown removes `SSA130.*` roots locally and remotely.

### Stop/restart with clean shutdown
See Pitfall 4 for the two paths and the forbidden strings. Record the restart marker time and pull `docker logs seedsyncarr-test --since <marker>` (stderr included) plus the app log file. Note the app-log clock is NAS host time + 1h. After each restart, require a successful scan with `scan_time` ≥ restart epoch, `/server/status` up, a new `Starting SeedSyncarr` line, and 0 `Traceback`. Docker's stop grace is 10 s: a clean stop takes about 2 s (126 prod CLEAN_STOP 1.9 s), and the Phase 129 web join bound is 5 s.

### Restore (D-11)
`130-teardown.sh` restores `sonarr_url`, `sonarr_api_key` (from `sonarr_key.l0`) and `radarr.enabled`. Radarr URL and key go back to empty via the on-disk addendum (Pitfall 7). Run an independent fresh-session read-back, and check the production fingerprint (Id, Image, StartedAt) at P0 through P3, which must be unchanged.

## Deploy and rollback

Reuse `126-DEPLOY-EVIDENCE.md` steps 1a–1i verbatim, replacing versions, digests and the TS suffix:
- ROLLBACK_IMAGE `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7`; prod image ID at 1.8.0 `sha256:12fba7858e2b84e5578753e340d5ebe8fd4703f62873ecb84f35ba5b35e79309`.
- Backups: `settings.cfg`, `controller.persist`, `autoqueue.persist` in `/volume1/docker/seedsync/`, plus `/volume1/docker/docker-compose.yml`, suffix `.pre-1.8.1-<TS>`, sha256 recorded, `parse_check.py` PASS in **both** the 1.8.0 and 1.8.1 images.
- The stop should now be fully clean on 1.8.0. The `ScannerProcessDiedError` traceback seen in 126-1b came from stopping **1.7.6**; Phase 123 closed GAP-1. Any traceback on stopping 1.8.0 is worth recording but isn't a NO-GO by itself.
- Prod Test Connection routes are **GET** (126 deviation 1).
- Rollback steps: as 126-1i with 1.8.0 targets; AutoDelete forced off if the backup has `enabled = True`.

## Code Examples

### Bundle identity proof against the published 1.8.0 image (verified in this session)
```bash
# Source: run during research 2026-11-20; produced BUNDLE_IDENTICAL for current tree and for minimatch-fixed lock
S=<scratchpad>/bundle; mkdir -p "$S/img"
cid=$(docker create ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f15865d7d9f68f8d8d42e8daccbe49f6fe888f3b1e3c1fe4fe4879aa7)
docker cp "$cid":/app/html "$S/img/" && docker rm "$cid"
(cd src/angular && npm ci && npx ng build --configuration=production --output-path "$S/local")
(cd "$S/img/html" && find . -type f | sort | xargs shasum -a 256) > "$S/img.sha"
(cd "$S/local/browser" && find . -type f | sort | xargs shasum -a 256) > "$S/local.sha"
diff "$S/img.sha" "$S/local.sha" && echo BUNDLE_IDENTICAL
```
Run this after the minimatch commit and **before** the version-bump commit. After the bump, the expected diff is `main-*.js` (renamed) and `index.html` only.

### Dependabot snapshot (authoritative)
```bash
gh api repos/thejuran/seedsyncarr/dependabot/alerts --paginate \
  --jq '[.[]|select(.state=="open")]|sort_by(.number)|.[]|{number,package:.dependency.package.name,scope:.dependency.scope,severity:.security_advisory.severity,fixed:.security_vulnerability.first_patched_version.identifier}'
gh pr list --author app/dependabot --json number,title,createdAt
```

### Soupsieve shipped-or-not check (reusable on the 1.8.1 image)
```bash
docker run --rm --entrypoint sh ghcr.io/thejuran/seedsyncarr:1.8.1@<RELEASE_DIGEST> -c \
  'pip list 2>/dev/null | grep -iE "soupsieve|beautifulsoup|webtest|paste|pytz"; python3 -c "import soupsieve" 2>&1 | tail -1'
# expect: Paste 3.10.1, pytz 2026.5, and ModuleNotFoundError for soupsieve
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Roll in every Dependabot PR (126 D-01) | Triage plus justified fixes only (130 D-03 to D-05) | This milestone | Several PRs deliberately stay open; the owner list must say why |
| minimatch 10 recursive matcher | minimatch 11 + `@isaacs/nonrecursive-glob-match` | 2026-10-27 (11.0.0/11.0.1) | New transitive package in the dev tree |
| soupsieve 2.x (Python ≥3.10) | soupsieve ≥3.0.2 requires Python ≥3.11.5 | 2026-10-12 | Projects with a `>=3.11` Poetry constraint can't resolve the fix without narrowing |
| paste maintained | paste 3.11.0 deprecates the whole library (import-time DeprecationWarning) | 3.11.0 | SeedSyncarr's web server stack is on a deprecated library. Backlog consideration, not this phase |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Sandbox wiring, ports and paths are as recorded in 126 (8801, v5test paths, Radarr disabled/empty, no api_token) | Smoke recipes | Smoke commands need adjusting; the Step 0 read-only precondition capture catches this |
| A2 | Production's remote watch dir and auto-queue settings allow a synthetic hold probe if the owner chooses that option (Open Question 1) | Open Questions | The prod queue-check evidence path changes |
| A3 | Narrowing only the `[tool.poetry.dependencies] python` constraint doesn't upset Dependabot's future Python PRs or CI | Standard Stack | Low. CI builds every Python path; scratch `poetry check` was unchanged |
| A4 | Resolver results at execution time (soupsieve 4.x, minimatch 11.0.x) may be newer than at research time | Dependency triage | Low. Re-run the bundle-identity and lint checks on whatever resolves |

## Open Questions (RESOLVED)

All three questions are resolved by the Phase 130 plans (revision 1, 2026-11-20). Each item keeps its original analysis and ends with a RESOLVED line naming the plan task that settles it.

1. **What counts as "a queue check succeeds" in production (REL-08, D-20)?**
   - What we know: a queue fetch only happens when an auto-queue candidate exists (Pitfall 5). 126 accepted Test Connection success plus zero `unavailable` lines over a 309 s window. That proves reachability with the key, but not the queue endpoint.
   - What's unclear: whether the owner accepts passive evidence or wants an active probe.
   - Recommendation: the plan should take the active path if no real candidate appears within the steady-state window. Drop a tiny synthetic file named like `SSA130.ProdProbe` into production's seedbox watch dir. It will be **held** (`No matching queue entry`, which proves both queues answered with the stored keys) and can never transfer, because a synthetic name can't match a completed queue record. Then delete it from the seedbox and confirm the hold drops. This writes a file to the production seedbox area, so put the choice to the owner at checkpoint 2 in plain terms ("a harmless placeholder file that SeedSyncarr will look up in Sonarr/Radarr and refuse to download"). If declined, fall back to the 126 passive evidence and say that clearly in the evidence.
   - **RESOLVED (130-05 Task 3, 130-06 Task 1 step 7):** the real production probe is the default and recommended path (orchestrator ruling after the Codex review). 130-06 Task 1 step 7 runs it with verified safety preconditions (an Arr integration enabled, auto-queue on and not patterns-only, no matching queue record), a session-unique name, guaranteed cleanup, and one accepted proof: `Completion hold for '<probe>': No matching queue entry` with zero queue-failure lines. Connection tests only are no longer a fallback. They exist solely as an explicitly labelled, owner-approved deviation offered at the 130-05 Task 3 checkpoint ("this would not prove the queue check works in production"), recorded verbatim against REL-08 SC4, never selected automatically. A probe that cannot run or is inconclusive stops for the owner.

2. **Should the CHANGELOG mention that saving a secret no longer echoes its value (Phase 128 D-07)?**
   - What we know: D-12 to D-14 fix the release-notes lines and don't mention it. It's an API response change (`… updated` instead of `… set to <value>`) for every secret field.
   - Recommendation: leave it out of the GitHub release notes (owner-locked content). A one-line CHANGELOG `Changed`/`Security` mention is reasonable, but it's the owner's call. Ask at checkpoint 1 rather than adding it silently.
   - **RESOLVED (130-03 Task 1, 130-04 Task 1 item 4, 130-04 Task 2 step 1):** the drafted CHANGELOG and release notes leave it out; the owner is asked at the pre-tag checkpoint; if the owner wants it, one `### Changed` CHANGELOG line is added on the release branch before the merge; if the owner does not answer the question, the drafted text stands and that is recorded.

3. **Radarr credential copy into the sandbox (D-11)**
   - What we know: the padded-key Radarr check needs production Radarr's key in the sandbox again, and in 126 the owner sanctioned the on-disk clearing afterwards.
   - Recommendation: state the copy-then-clear plan in the Plan 04 objective so the owner sees it before the smoke. Treat it as covered by D-11's "restore … to their pre-smoke values".
   - **RESOLVED (130-04 Task 1 item 5, 130-05 Task 1 step 2 and Task 2 step 5):** the owner is told about the copy before the tag; 130-05 captures a fingerprint of all six sandbox Arr fields before the first change, restores them (clearing originally empty fields on disk) and proves exact restoration with `130-l0-fingerprint.sh verify` (`L0_VERIFY ok`), so no copy of the production Radarr key remains unless the sandbox already held it before the smoke, which is then reported to the owner.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| gh CLI (authenticated) | PR merge, CI, Dependabot API | ✓ | present | — |
| Poetry | soupsieve lock regen | ✓ | 2.3.4 (matches Dockerfile) | — |
| Node / npm | minimatch lock update, lint, ng build | ✓ | Node 25.9.0 / npm 11.12.1 (CI: Node 22) | — |
| Docker Desktop + buildx | Karma (`make run-tests-angular`), image inspection, digest method A, bundle comparison | ✓ | 29.9.3 / buildx 0.38.1 | — |
| ruff 0.15.22 | Whole-tree lint | ✓ (local ruff is the Python 3.9 user install; version not checked) | — | Scratch venv `pip install ruff==0.15.22` (126 pattern) |
| python3.12 | PyPI install check (package needs <3.13) | ✓ (126 used `/opt/homebrew/bin/python3.12`) | — | — |
| jq (local) | Evidence filtering | ✓ | /usr/bin/jq | — |
| codex CLI | Plan review per CLAUDE.local.md | ✓ | /opt/homebrew/bin/codex | — |
| slopcheck | Package audit | ✓ | — | — |
| `ssh nas`, NAS docker | Smoke and deploy | not probed (research rule: no NAS access) | — | Execution-time Step 0 preconditions |
| NAS `jq` | Teardown/padded-key body | 1.5 per 126 (no `--rawfile`) | — | Use `-nR` + `[inputs]` (already in teardown) |

**Missing dependencies with no fallback:** none known. NAS access was intentionally not probed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x via Poetry (Python); Karma + Jasmine (Angular, dockerized ChromeHeadlessCI); Playwright e2e (CI on the Docker image, amd64 on PRs, amd64+arm64 on tags); `node --test` (release-metadata verifier) |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (timeout 60, coverage `fail_under = 88`); Karma config in `src/angular`; `.github/workflows/ci.yml` |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_web/test_web_app_job.py tests/unittests/test_controller/test_arr_queue.py tests/integration/test_web/test_handler/test_arr_key_parity.py tests/unittests/test_common/test_arr_api_key.py -q -p no:cacheprovider` |
| Full suite command | Local: `cd src/python && poetry run pytest tests/unittests tests/integration -q -p no:cacheprovider --ignore=tests/unittests/test_ssh/test_sshcp.py --ignore=tests/unittests/test_controller/test_scan/test_scanner_process.py --ignore=tests/unittests/test_system/test_scanner.py --ignore=tests/unittests/test_controller/test_extract/test_extract_process.py --ignore=tests/integration/test_lftp`; authority: PR CI `Python unit tests` |

### Phase Requirements → Verification Map
| Req / SC | Behavior | Type | Automated Command / Evidence | Exists? |
|----------|----------|------|------------------------------|---------|
| REL-07 SC1 (ARR) | Padded key regression present and green | unit + integration | `poetry run pytest "tests/unittests/test_controller/test_arr_queue.py::TestArrQueueFetch::test_padded_in_memory_key_is_sent_normalized" tests/integration/test_web/test_handler/test_arr_key_parity.py -q -p no:cacheprovider`; fail-before cited from 128-VERIFICATION.md | ✅ |
| REL-07 SC1 (WEB) | Cleanup isolation regression present and green | unit | `poetry run pytest "tests/unittests/test_web/test_web_app_job.py::TestWebAppJobCleanup::test_app_stop_failure_still_stops_server_and_joins" tests/unittests/test_web/test_web_app_job.py -q -p no:cacheprovider`; fail-before cited from 129-VERIFICATION.md | ✅ |
| REL-07 SC1 | Full suite, ruff, Angular, e2e, release CI | CI | `ruff check src/python/` (0.15.22); `make run-tests-angular`; `gh pr checks <release PR>` all pass; tag run `gh run view <id> --json jobs` all success, incl. `Verify release metadata`, e2e amd64+arm64, publish jobs | ✅ |
| REL-07 SC1 | Release metadata | unit/script | `npm run test:release-metadata` and `node scripts/verify-release-metadata.mjs 1.8.1` (6 checks pass) | ✅ |
| REL-07 SC2 | soupsieve ≥4.0.0 in lock; not shipped | script | `grep -A1 '^name = "soupsieve"' src/python/poetry.lock`; `head -1 poetry.lock` shows Poetry 2.3.4; image check (Code Examples) on the PR staging image `ghcr.io/thejuran/seedsyncarr:<run_number>` and the release digest | ✅ |
| REL-07 SC2 | minimatch has no instance in [7.0.0, 11.0.1); bundle unchanged | script | `cd src/angular && npm ls minimatch --all`; bundle sha256 identity vs the 1.8.0 image (Code Examples); `git diff --stat` shows only `package-lock.json` | ✅ |
| REL-07 SC2 | Alerts closed, no new runtime alert, triage surfaced | API + owner | alerts API count before (5) → after merge (expect 0), 2 polls; D-07 plain-terms list recorded verbatim with the owner's reply | evidence-based |
| REL-08 SC3 | Smoke by exact digest | manual-live (NAS) | Evidence file: `.Config.Image` and `RepoDigests` == RELEASE_DIGEST; padded-key save 200 → Test Connection success (Sonarr 4.x, Radarr) → `No matching queue entry` hold with 0 `unavailable`/`queue check failed`/`skipped`; container restart + in-app restart with forbidden-string counts all 0 (Pitfall 4); real transfer sha256 local==remote | manual-only (needs live NAS/seedbox/arrs) |
| REL-08 SC4 | Prod by the same digest; scan, queue check, owner | manual-live | `.Image` == SMOKE_IMAGE_ID; `/server/status` `latest_remote_scan_failed=false` with `scan_time` after UP_TIME; Test Connection both; queue-check evidence per Open Question 1; no-secrets count 0; wud running; owner reply recorded verbatim | manual-only |

### Sampling Rate
- **Per task commit:** the quick run command (ARR + WEB selectors), plus ruff whole-tree for any Python-touching commit. For the Angular lock commit: `npm ci && npm run lint && bundle identity`.
- **Per wave merge:** local full suite (with macOS ignores) + `make run-tests-angular` + packaging (`python -m build`, `twine check`, `scripts/verify-python-package.py`) + metadata verifier.
- **Phase gate:** release PR CI all green; tag CI all green; smoke verdict table all PASS; deploy verdict PASS; owner confirmations recorded.

### Wave 0 Gaps
None. Existing test infrastructure covers every automated requirement, and the live checks are evidence-based by nature. Harness prep (deriving `130-teardown.sh` from `126-teardown.sh`, plus `130-padded-key-post.sh` and `130-l0-fingerprint.sh`, with `bash -n` + `shellcheck -S error`) is done in Plan 130-03 Task 2, before the release PR, so the scripts are reviewed and committed with the release branch. The live sandbox dry run is the first step of the smoke plan (130-05 Task 1 step 3).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no auth code change) | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (what's under test) | Shared `normalize_arr_api_key`/`is_valid_arr_api_key` rule (Phase 128); the smoke exercises it through the real save route |
| V6 Cryptography | no | — |
| V7 Error Handling and Logging | yes | Count-only no-secrets check (`extract_secrets.py`) on the sandbox and prod logs; evidence files record no key values; secret saves return `… updated` |
| V14 Configuration / Dependencies | yes | Dependabot triage; lockfile regeneration with pinned tools; digest-pinned deployment; `@isaacs/nonrecursive-glob-match` provenance recorded |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain substitution of the deployed image | Tampering | Deploy only `:1.8.1@sha256:<RELEASE_DIGEST>`; digest cross-checked two ways; prod `.Image` must equal the sandbox SMOKE_IMAGE_ID |
| Malicious or new transitive package | Tampering | slopcheck; install-script inspection; npm provenance check for the new package; dev-only scope proven by bundle identity |
| Key leakage into evidence or logs during the padded-key smoke | Information disclosure | Keys only in 0600 files, `jq -nR` from stdin, never in argv or output; sha256/count-only comparisons; delete temp bodies |
| Production Radarr key lingering in the sandbox | Information disclosure | On-disk clear after the smoke (126-05 addendum) with sha256 DIFFERENT confirmation and backup deletion |
| Prod disruption during the smoke | Denial of service | Prod fingerprint P0..Pn unchanged; scripts never name the prod container or compose; wud paused |
| Unauthorized publish | Elevation/Repudiation | Owner checkpoint 1 before the irreversible tag; verbatim owner replies recorded |

## Sources

### Primary (HIGH confidence)
- Live GitHub API: `gh api repos/thejuran/seedsyncarr/dependabot/alerts` (5 open), `gh pr list --author app/dependabot`, `gh pr view 156/151/146/145`, `gh pr diff 151`, `gh api repos/pasteorg/paste/security-advisories/GHSA-vf89-fq68-57cx`, `gh api repos/pasteorg/paste/compare/3.10.1...3.11.0`
- PyPI JSON API for soupsieve (versions and `requires_python`)
- npm registry `npm view` (minimatch, eslint, @eslint/config-array, @typescript-eslint/*, typescript-eslint, @isaacs/nonrecursive-glob-match)
- Published image `ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f…`: pip list, import test, `/app/scanfs` archive listing, `/app/html` hashes
- Scratch dry runs: Poetry lock (A/B), npm lock update, `npm ci` + lint, `ng build` bundle identity, pytest web suites with soupsieve 4.1.2
- Repo: `src/docker/build/docker-image/Dockerfile`, `src/python/pyproject.toml`, `poetry.lock`, `src/angular/package*.json`, `.github/workflows/ci.yml`, `scripts/verify-release-metadata.mjs`, `web/handler/config.py`, `web/handler/server.py`, `web/web_app_job.py`, `seedsyncarr.py`, `controller/completion_gate.py`, `controller/arr_queue.py`, `CHANGELOG.md`, `release-notes.md`
- Planning: 126 CONTEXT/PLANs/REL/SMOKE/DEPLOY evidence, 128-VERIFICATION, 129-VERIFICATION/VALIDATION/CONTEXT, STATE.md hand-off (Phase 129 D-08)

### Secondary (MEDIUM confidence)
- NAS paths, ports and jq version as recorded in 126 evidence (not re-observed; NAS access excluded from research)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack / dependency triage: HIGH. Every claim was checked against the live API, the published image or a scratch run.
- Architecture / release flow: HIGH. It's a proven 126 pattern, read from evidence.
- Smoke/deploy recipes: MEDIUM. They come from 126 artifacts, and NAS state may have drifted (re-observe at Step 0).
- Pitfalls: HIGH. Each is backed by code reads or by things that happened in 126.

**Research date:** 2026-11-20
**Valid until:** about 7 days for the dependency snapshot (advisories and Dependabot move daily); 30 days for the release mechanics.
