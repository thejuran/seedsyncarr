---
phase: 126-release-1-8-0
verified: 2026-10-28T23:59:00Z
status: passed
score: 8/8 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
re_verification:
  previous_status: none (initial verification)
---

# Phase 126: Release 1.8.0 Verification Report

**Phase Goal:** 1.8.0 is published, smoke-tested by exact digest, and running on NAS production with a confirmed successful scan
**Requirements:** REL-05, REL-06
**Verified:** 2026-10-28T23:59:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Method

This verification does not trust SUMMARY.md or evidence-file claims on their own. Every truth
below was independently re-checked against: the local git history and tags, the GitHub API (`gh`,
read-only), the live GHCR registry (`docker buildx imagetools inspect`), the live PyPI JSON API,
and the NAS over `ssh nas` using only read-only `sudo /usr/local/bin/docker inspect`/`logs`/`ps`
and plain reads of mounted config files (no secret values printed; count/length/hash comparisons
only, never raw credential text). No NAS state was changed by this verification.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1–4)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Open Dependabot alerts/PRs reviewed before the bump; runtime fixes rolled in, dev-only if cheap; 999.4 rechecked and recorded | ✓ VERIFIED | `gh api .../dependabot/alerts?state=open` → 0 open today. All 8 pre-release PRs (#136,#141,#125,#117,#131,#130,#135,#138) closed; a 9th/10th post-merge alert pair (#106 qs, #107 setuptools) was caught by the D-04 re-scan and fixed via PR #143 (merged, CI+CodeQL green) per owner's verbatim "1". `126-REL-EVIDENCE.md` §"Dependency list for the owner (draft, D-05)" shows before/after counts and the owner packet. 999.4: `braces@3.0.3` confirmed unchanged in `src/angular/package-lock.json`, recorded "no fix needed". |
| 2 | Full suite/ruff/Angular/release CI green on the release commit; tag `v1.8.0` publishes GHCR+GitHub+PyPI with CHANGELOG and release notes (LAN behavior change + rollback runbook) | ✓ VERIFIED | Tag CI run `40775673056` (triggered by `v1.8.0` on merge commit `098ed81b`): all 14 non-skip jobs `success`, `:dev` publish correctly `skipped`. e2e log greps confirm all 3 `[chromium-token]` SEC-02 tests pass on both amd64 and arm64. `gh release view v1.8.0`: live, not draft/prerelease, body resolves `{{VERSION}}`→`blob/v1.8.0/CHANGELOG.md`, includes a full rollback-to-1.7.6 runbook. `CHANGELOG.md` has `## [1.8.0] - 2026-10-28` (Security/Changed/Fixed order, includes the LAN-02 behavior-change line). PyPI `https://pypi.org/pypi/seedsyncarr/1.8.0/json` returns the published release; independently reinstalled `seedsyncarr==1.8.0` into a clean Python-3.12 venv here (`pip show` → `Version: 1.8.0`). |
| 3 | Published image smoke-tested on NAS sandbox by exact digest: restart, real transfer, Sonarr/Radarr integration, cleanup checks pass | ✓ VERIFIED | `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:1.8.0` → index digest `sha256:6e8d453f...4879aa7`, matches `RELEASE_DIGEST` recorded in evidence exactly. Live `ssh nas 'docker inspect seedsyncarr-test'` → `Config.Image` is that exact digest, container `running`. `126-SMOKE-EVIDENCE.md` records 11/11 D-12a checks PASS (restart, real transfer, Sonarr v4 integration, Radarr integration, webhook import, cleanup/auto-delete, webhook test event, container-name Test Connection, metadata refusal, no-secrets, no-token-to-GitHub); teardown re-run twice (incl. a fresh SSH session) confirmed idempotent restore. |
| 4 | NAS production compose pinned to the same `:1.8.0@sha256:…`; never `:dev`/local build; successful post-deploy scan confirms recovery; owner confirmation recorded | ✓ VERIFIED | `/volume1/docker/docker-compose.yml` on the NAS: `image: ghcr.io/thejuran/seedsyncarr:1.8.0@sha256:6e8d453f...4879aa7` (exact match). Live `docker inspect seedsyncarr` → `running`, `Config.Image` same digest, started `2026-10-28T23:10:24Z`. Live `GET http://127.0.0.1:8800/server/status` on the NAS right now returns `"latest_remote_scan_failed": false` with a scan timestamp well after the deploy start — an independently observed, currently-successful scan, not just a historical evidence-file claim. `126-DEPLOY-EVIDENCE.md` records CLEAN_STOP, 4 sha256-recorded backups (confirmed present on disk, non-empty, matching sizes), dual-image loader PASS, image-ID match to the smoked sandbox image, a 309 s zero-error steady-state window, 0 secret matches, wud restored last (confirmed live: `wud Up 25 minutes (healthy)`) and re-fingerprinted unchanged, and the owner's verbatim `"confirmed"` reply. |

**Score:** 4/4 ROADMAP success criteria verified (expanded to 8/8 granular must-haves across the 6 plans; see below).

### Supplementary Must-Haves (PLAN frontmatter, D-01..D-17 / D-12a)

| # | Must-have | Status | Evidence |
|---|-----------|--------|----------|
| 5 | D-12a spot checks: no secrets in a fresh container log; GitHub update-check carries no app token; webhook Test event logged | ✓ VERIFIED | Smoke evidence records `WITH_TOKEN=0`/`WITH_AUTH=0` on 1.8.0 vs. a proven-non-vacuous positive control (`WITH_TOKEN=1`) on 1.7.6 (`126-token-probe.mjs`, sha256-verified byte-identical extractor to 119.1's). Production's own log independently reviewed here (`docker logs seedsyncarr --since 2h`) shows no `Authorization`/token text, no Traceback, and the three security `WARNING` lines are the documented unauthenticated-by-config state, not a leak. |
| 6 | Owner-approved deviations honored: wud paused at tag, post-merge setuptools/qs fixed via PR #143 (owner decision "1"), sandbox prod-Radarr-key cleanup | ✓ VERIFIED | wud: evidence + live `docker inspect wud` both show it was stopped before the tag and is now `Up ... (healthy)` again post-deploy. PR #143: confirmed merged via `gh pr view 143` (`MERGED`), CI+CodeQL green via `gh pr checks 143`, Dependabot alerts now 0. Sandbox Radarr cleanup: independently confirmed live on the NAS — `settings.cfg` `[Radarr]` section has `enabled = False`, `radarr_url` length 0, and `radarr_api_key` length 0 (sha256 of the empty field is the well-known empty-string hash), vs. production Radarr's `config.xml` `<ApiKey>` which hashes to a different, non-empty value — the sandbox no longer holds a copy of production's key. |
| 7 | Requirements coverage: REL-05 and REL-06 are the only two requirement IDs scoped to Phase 126 and both are accounted for | ✓ VERIFIED | `REQUIREMENTS.md` lists exactly REL-05 and REL-06 under "Release", both `[x]` and both rows in the Traceability table say "Phase 126 / Complete". Every 126-0N-PLAN.md frontmatter `requirements:` field maps to one or both of these two IDs; no orphaned Phase-126 requirement exists. |
| 8 | Code review (126-REVIEW.md) found no blocking issues | ✓ VERIFIED | `126-REVIEW.md` frontmatter: `critical: 0, warning: 1, info: 4, status: issues_found`. WR-01 (`@types/jasmine` 7 vs. `jasmine-core` 4.6 runtime mismatch) is a test-tooling type/runtime gap, not a shipped-code defect; CI's Angular unit tests (657/657) and all e2e suites pass regardless, so it does not affect the phase goal. The 4 info items are documentation-accuracy follow-ups (release-notes wording, a `playwright` range, a backup-runbook omission, a SECURITY.md heading nuance) — none block publication, smoke, or deploy. Treated as non-blocking per task instruction; recommend parking WR-01 and the 4 info items to the backlog for a documentation/dependency-hygiene follow-up. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `v1.8.0` git tag (annotated, on main) | Points at the release merge commit | ✓ VERIFIED | `git cat-file -p v1.8.0` → `object 098ed81b...` = PR #143's merge commit SHA; tag exists on `origin` (`git ls-remote --tags origin v1.8.0`). |
| GHCR `ghcr.io/thejuran/seedsyncarr:1.8.0` | Multi-arch image at `RELEASE_DIGEST` | ✓ VERIFIED | `docker buildx imagetools inspect` → index digest matches evidence exactly; amd64+arm64 manifests present. |
| PyPI `seedsyncarr==1.8.0` | Installable | ✓ VERIFIED | Live JSON API + independent clean-venv install both confirm. |
| GitHub Release `v1.8.0` | Live, not draft | ✓ VERIFIED | `gh release view` → `isDraft: false`, `isPrerelease: false`, body = rendered `release-notes.md`. |
| `CHANGELOG.md` `[1.8.0]` entry | Security→Changed→Fixed, covers 121–125 | ✓ VERIFIED | Present, correctly ordered, LAN-02 line present. |
| `release-notes.md` | Rollback runbook to 1.7.6 | ✓ VERIFIED | Full runbook present (stop, restore 3 files, AutoDelete-off check, re-pin, verify). |
| `SECURITY.md` IP-resolution guard bullet | Describes Phase 125 behavior | ✓ VERIFIED | Matches `_validate_url`/`_classify_resolved_address` per code review's line-by-line check. |
| `.planning/phases/126-release-1-8-0/126-{REL,SMOKE,DEPLOY}-EVIDENCE.md`, harness scripts | Present, substantive | ✓ VERIFIED | All present; harness scripts (`126-teardown.sh`, `126-webhook-post.sh`, `126-token-probe.mjs`, `126-extract_secrets.py`) contain the literal D-11/D-12a hooks claimed (RADARR_URL_L0, `--revert-image`, `^SSA126`, `eventType`, `sourcePath`); `126-extract_secrets.py` sha256-identical to the 119.1 original. |
| NAS production `docker-compose.yml` | Pinned to exact `RELEASE_DIGEST` | ✓ VERIFIED | Live read confirms exact digest string. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `v1.8.0` tag push | GHCR/GitHub/PyPI publish jobs | Tag CI run 40775673056 | ✓ WIRED | All 5 publish jobs `success`, `:dev` publish `skipped` as expected on a tag. |
| `release/1.8.0-deps` PR #143 | `origin/main` | Merge commit `098ed81b`, CI+CodeQL green | ✓ WIRED | Confirmed via `gh pr view 143` and `gh pr checks 143`. |
| RELEASE_DIGEST (126-04) | Sandbox smoke (126-05) | `seedsyncarr-test` image pin | ✓ WIRED | Live sandbox image digest == RELEASE_DIGEST. |
| Smoked sandbox image ID | Production deploy (126-06) | Compose digest pin + image-ID equality check | ✓ WIRED | Live production `.Image` = `sha256:12fba785...` = evidence's `SMOKE_IMAGE_ID`. |
| 126-token-probe.mjs | `auth.interceptor.ts` destination-gating (Phase 121) | Positive control (1.7.6, WITH_TOKEN=1) vs. target (1.8.0, WITH_TOKEN=0) | ✓ WIRED | Probe proven non-vacuous before trusting its zero result. |

### Behavioral Spot-Checks (run independently in this verification)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| GHCR index digest matches RELEASE_DIGEST | `docker buildx imagetools inspect ghcr.io/thejuran/seedsyncarr:1.8.0` | `sha256:6e8d453f...4879aa7` | ✓ PASS |
| PyPI package installs | `pip install seedsyncarr==1.8.0` in a clean Python 3.12 venv | `Version: 1.8.0` | ✓ PASS |
| Production container runs the exact digest | `ssh nas docker inspect seedsyncarr` | `Config.Image` = RELEASE_DIGEST, `running` | ✓ PASS |
| Current scan is succeeding right now | `ssh nas curl 127.0.0.1:8800/server/status` | `latest_remote_scan_failed: false` | ✓ PASS |
| Sandbox no longer holds prod Radarr's key | sha256 of blank field vs. sha256 of prod `config.xml` key | empty-string hash vs. distinct non-empty hash | ✓ PASS |
| Tag CI e2e proves SEC-02 | `gh run view 40775673056 --log \| grep chromium-token` | 3/3 passing on amd64 + arm64 | ✓ PASS |
| Dependabot alerts fully cleared | `gh api .../dependabot/alerts?state=open` | 0 | ✓ PASS |
| Pre-upgrade backups exist on NAS | `ssh nas ls -la *.pre-1.8.0-*` | 4 files present, non-empty, matching evidence sizes | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|--------------|--------|----------|
| REL-05 | 126-01, 126-03, 126-04 | Dependabot review before bump; runtime/shipped rolled in; 999.4 rechecked | ✓ SATISFIED | REQUIREMENTS.md `[x]`, 0 open alerts live, 999.4 outcome recorded |
| REL-06 | 126-02 through 126-06 | Published, smoke-tested by digest, deployed to production with confirmed scan | ✓ SATISFIED | REQUIREMENTS.md `[x]`, GHCR/GitHub/PyPI live, sandbox+production digest-matched and confirmed live |

No orphaned Phase-126 requirements found in REQUIREMENTS.md.

### Anti-Patterns Found

None blocking. `grep -nE "TBD|FIXME|XXX"` across every file this phase modified returned no real debt markers (one incidental substring match inside a base64 integrity hash in `package-lock.json`, not a marker). No placeholder/stub patterns found in the four harness scripts or the release-content files.

### Human Verification Required

None. All owner checkpoints this phase required (D-13 pre-tag approval, D-04 follow-up decision, D-13 pre-prod go-ahead, D-17 post-deploy confirmation) already occurred and are recorded verbatim in the evidence files, and this verification independently confirmed the downstream state those approvals authorized (merge, tag, publish, smoke, deploy) actually exists in GitHub/GHCR/PyPI/NAS — not just that the evidence file claims it does.

### Gaps Summary

No blocking gaps. The code review's single warning (WR-01, `@types/jasmine` 7 vs. `jasmine-core` 4.6 type/runtime mismatch) and its 4 info findings are real but non-blocking — they affect test-tooling accuracy and documentation wording, not the shipped product or the phase's publish/smoke/deploy goal. Recommend parking them to the backlog as a documentation/dependency-hygiene follow-up item rather than reopening Phase 126.

---

_Verified: 2026-10-28T23:59:00Z_
_Verifier: Claude (bm-verifier)_
