---
phase: 121-credential-forwarding
plan: 03
subsystem: testing
tags: [ci, github-actions, playwright, karma, e2e, security]

# Dependency graph
requires:
  - phase: 121-credential-forwarding plan 01
    provides: "authInterceptor destination-gated Bearer token fix (isOwnApiRequest, fail-closed)"
  - phase: 121-credential-forwarding plan 02
    provides: "chromium-token Playwright project and auth-token.spec.ts (3 tests)"
provides:
  - "Phase gate evidence: full local Angular suite + coverage + lint green, e2e tsc + --list green, SC4 diff empty, TDD RED/GREEN commit order confirmed"
  - "D-07 curl evidence: GitHub returns 401 to an unrecognized Bearer token, 200 with no Authorization header"
  - "Draft PR #132 to main with PR CI green, including all 3 [chromium-token] auth-token.spec.ts tests passing in a real browser against the CI-built staging image"
  - "D-08/D-09 carried to Phase 126 as a STATE.md pending todo (release-note disclosure, production token rotation)"
affects: [126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Pushed gsd/phase-121-credential-forwarding to origin and opened PR #132 as DRAFT only after the owner's explicit 'push' reply in Task 2 (checkpoint:human-verify, gate=blocking)"
  - "PR body documents that the branch also carries 17 pre-existing planning-doc commits not yet on origin/main (predate this phase, inherited from local main at branch-cut time), per plan instruction"
  - "No code changes made in this plan — Task 1 gates were already green from plans 01/02; this plan only records evidence, pushes, and watches CI"

patterns-established: []

requirements-completed: [SEC-02]

# Metrics
duration: ~17min (Task 3, this session; Task 1 ran in a prior session, see 121-STATE history)
completed: 2026-10-21
---

# Phase 121 Plan 03: Credential-Forwarding Gate Closure and PR CI Verification Summary

**Pushed the destination-gated app-token fix (plan 01) and its token-configured E2E coverage (plan 02) to origin as draft PR #132; PR CI run 39692441447 is green across all 11 required jobs, including the new `chromium-token` Playwright project — all 3 of its tests passed in a real browser against the CI-built staging image, proving SEC-02's real-browser half.**

## Performance

- **Duration:** Task 1 (local gate + D-07 + STATE.md carry-forward) ran in a prior session, committed `9eb02b8` at 2026-10-21T23:05:14Z. Task 2 (owner checkpoint) resolved with "push" at the start of this session. Task 3 (this session): push at ~2026-10-21T23:14Z, PR #132 opened at 2026-10-21T23:17:23Z, CI run completed at 2026-10-21T23:29:49Z — approx 17 min end to end.
- **Tasks:** 3 (Task 1 local gate — prior session; Task 2 checkpoint — resolved "push"; Task 3 push + PR + CI watch — this session)
- **Files modified:** 2 (STATE.md, ROADMAP.md — metadata only; no source files touched in this plan)

## Accomplishments

- Confirmed `git branch --show-current` was `gsd/phase-121-credential-forwarding` (not `main`) before any push, per the plan's refusal condition.
- `git push -u origin gsd/phase-121-credential-forwarding` succeeded (new branch on origin).
- Opened draft PR #132 (`fix(121): attach app token only to SeedSyncarr's own API (SEC-02)`, base `main`) with a body summarizing the leak, the fix, the test matrix, the D-07 side effect, and the Phase 126 carry-forward; body ends with the required Claude Code attribution line.
- Watched PR checks end to end via `gh pr checks 132 --watch --interval 60` (looped across two 600s Bash windows, resumed from background-task notification — no polling beyond the tool's own refresh).
- All 11 active jobs on run `39692441447` (plus the separate CodeQL/code-scanning workflow run `39692439112`) passed. `End-to-end tests on Docker Image (amd64)` passed in 4m5s with "55 passed (1.4m)" and all 3 `[chromium-token]` tests green. `Publish GitHub Release`, `Publish Docker Image`, `Publish Docker Image (:dev)`, `Publish Documentation`, `Publish to PyPI` correctly show `skipping` (this is a draft PR, not a tag push).

## Task 1 Results (local gate, carried into this summary per resume instructions)

- Angular: `npx ng test --browsers ChromeHeadless --watch=false --code-coverage` → **657/657 SUCCESS**. Coverage: Statements 84.62% / Branches 70.49% / Functions 81.56% / Lines 85.44% — all above `check.global` floors (83/68/79/83).
- `npm run lint` → exit 0.
- E2E: `npx tsc --noEmit -p .` → exit 0. `npx playwright test --list` → 55 tests in 10 files, including 3 `[chromium-token]` entries for `auth-token.spec.ts`.
- SC4 no-redesign check: `git diff --stat c3d2788 -- src/python src/angular/src/app/app.config.ts src/angular/src/app/services/utils/rest.service.ts src/angular/src/app/services/utils/version-check.service.ts` → empty output → **SC4-OK**.
- TDD gate: `git log --oneline --grep="^test(121-01)"` → `eb8ffb3`; `git log --oneline --grep="^feat(121-01)"` → `206729a`; RED (`eb8ffb3`) precedes GREEN (`206729a`) in history.

## D-07: GitHub token-rejection evidence

```
curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer not-a-real-token' https://api.github.com/repos/thejuran/seedsyncarr/releases/latest
→ 401

curl -s -o /dev/null -w '%{http_code}\n' https://api.github.com/repos/thejuran/seedsyncarr/releases/latest
→ 200
```

Confirms: any SeedSyncarr instance with `api_token` configured had GitHub reject its update-check request (401) on every page load since v1.0.0 — the "new version available" notice has likely never worked for token users. After the plan 01 fix, the same request is sent with no `Authorization` header and gets GitHub's normal `200`. The `chromium-token` E2E spec's stubbed-release assertion (below) demonstrates this working end to end in a real browser.

## PR CI Verification (Task 3, this plan's primary gate)

- **PR:** https://github.com/thejuran/seedsyncarr/pull/132 — `isDraft: true`, `baseRefName: main` (confirmed via `gh pr view 132 --json isDraft,baseRefName`)
- **CI run:** https://github.com/thejuran/seedsyncarr/actions/runs/39692441447

| Job | Conclusion | Duration |
|---|---|---|
| Analyze (actions) | pass | 39s |
| Analyze (javascript-typescript) | pass | 1m1s |
| Analyze (python) | pass | 50s |
| CodeQL | pass | 4s |
| Angular unit tests | pass | 1m56s |
| Lint (Angular) | pass | 20s |
| Lint (Python) | pass | 12s |
| Python unit tests | pass | 4m54s |
| Release metadata verifier tests | pass | 9s |
| Verify Python package | pass | 25s |
| Verify release metadata | pass | 3s |
| Build Docker Image | pass | 3m14s |
| **End-to-end tests on Docker Image (amd64)** | **pass** | **4m5s** |
| Publish GitHub Release / Docker Image / Docker Image (:dev) / Documentation / PyPI | skipping (expected — draft PR, not a tag push) | — |

No failing checks.

### `[chromium-token]` log lines (job `119544630980`, step "Run e2e test")

```
✓  53 [chromium-token] › tests/auth-token.spec.ts:47:9 › API token configured (SEC-02) › rejects /server/ requests without the token (178ms)
✓  54 [chromium-token] › tests/auth-token.spec.ts:55:9 › API token configured (SEC-02) › sends the token to /server/* but never to api.github.com (571ms)
✓  55 [chromium-token] › tests/auth-token.spec.ts:85:9 › API token configured (SEC-02) › authenticated write flow works with the token (607ms)
```

Overall Playwright result line: `55 passed (1.4m)`. No `[chromium-token]` line marked failed or skipped — all three ran and passed against the real CI-built staging image.

This closes the real-browser half of SEC-02 (D-12): the header-absence assertion against `api.github.com` and the D-07 update-notice demonstration both ran in an actual Chromium instance, not a unit-test mock.

## Carried to Phase 126

Per 121-CONTEXT D-08 and D-09, recorded as a Pending Todo in `.planning/STATE.md` (added in Task 1, commit `9eb02b8`) rather than executed in this phase:

> Phase 126 (carried from 121-CONTEXT D-08/D-09): 1.8.0 release notes disclose factually that since v1.0.0 a configured api_token was sent in an Authorization header to api.github.com (HTTPS) on each UI load, GitHub rejected it, no other destination received it; rotation optional, recommended mainly for instances reachable beyond the LAN (edit api_token in settings.cfg, restart). Release notes also mention the update notice now works for token users (D-07). Prod deploy: after 1.8.0 is live on the NAS, check nothing else on the NAS uses the current token, rotate the production api_token, confirm UI loads, authenticated calls succeed and a scan completes.

No release notes were written and no NAS access occurred in this phase.

## Task Commits

1. **Task 1: Run the full local phase gate, record D-07 evidence, carry D-08/D-09 to Phase 126** - `9eb02b8` (docs) — prior session
2. **Task 2: Owner go-ahead checkpoint** - no commit (owner replied "push" in-session)
3. **Task 3: Push, open draft PR, confirm PR CI** - no code commit (git remote + GitHub operations only, per plan's `<files>` spec: "none (git remote and GitHub only)")

**Plan metadata:** this SUMMARY's commit (docs, created after this file).

## Files Created/Modified

- `.planning/STATE.md` - Task 1: added Phase 126 pending todo (D-08/D-09); this plan's metadata commit refreshes `last_updated`, position, and decisions.
- `.planning/ROADMAP.md` - Updated via `roadmap.update-plan-progress` after this SUMMARY.
- No `src/` files were modified in this plan — all source changes (interceptor fix, E2E spec) landed in plans 01 and 02 and were only verified/pushed here.

## Decisions Made

See `key-decisions` in frontmatter. In short: push and PR-open were gated strictly behind the owner's "push" reply (Task 2); the PR body transparently discloses the 17 inherited planning-doc commits not yet on `origin/main`; no source-level decisions were made in this plan.

## Deviations from Plan

None — plan executed exactly as written. Branch-not-main check passed before pushing; push, draft PR, and CI watch followed the plan's `<action>` text verbatim; no auto-fixes, no architectural questions, no package installs.

## Assumption Drift (advisory)

None material. The plan anticipated "up to ~45 minutes" for the E2E job because it needs the Docker image build first; the actual end-to-end CI run (image build + e2e job) completed in under 13 minutes from PR creation to final check, well inside that envelope — a timing variance, not an assumption drift worth flagging.

## Issues Encountered

None. All gates passed on the first CI run; no retries, no failing jobs, no log excerpts of failures to collect.

## Security Context (from a prior deep-review, not re-run in this plan)

A `/vibe-check:deep-review` of phase 121 (6 agents) reported 0 findings ≥70 (noted in this plan's checkpoint resolution, not independently re-verified here). Two sub-threshold e2e notes were surfaced: the `githubHeaders` length assertion could theoretically race the route handler's push, and the `chromium-token` project is skipped by Playwright if any `chromium` test fails (by design, since `chromium-token` depends on the `chromium` project). Neither affected this run — all 52 `chromium` tests and all 3 `chromium-token` tests passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 121 (SEC-02) is fully gated: local Angular/lint/e2e-compile/SC4/TDD-order checks (Task 1) plus real PR CI, including a real-browser run of the `chromium-token` project (Task 3), are both green.
- D-07, D-08, D-09 are all recorded; D-08/D-09 explicitly deferred to Phase 126 (release notes, production token rotation) with no NAS access or release-note drafting performed here.
- PR #132 remains **draft** — merging, undrafting, or any further CI re-runs are outside this plan's scope (ship flow, e.g. `/bm:ship`, is a separate step).
- No blockers for Phase 122.

---
*Phase: 121-credential-forwarding*
*Completed: 2026-10-21*

## Self-Check: PASSED

- FOUND: .planning/phases/121-credential-forwarding/121-03-SUMMARY.md
- FOUND commit 9eb02b8 (Task 1: docs, local gate + D-07 + Phase 126 carry-forward)
- FOUND commit 0589aed (this SUMMARY + STATE/ROADMAP/REQUIREMENTS metadata)
- FOUND branch gsd/phase-121-credential-forwarding pushed to origin, HEAD 0589aed matches origin
- FOUND PR #132: https://github.com/thejuran/seedsyncarr/pull/132 (draft, base main)
- FOUND CI run 39692441447: all jobs pass, including End-to-end tests on Docker Image (amd64) with 3/3 [chromium-token] tests passing
- NOTE: pushing this SUMMARY/STATE commit (0589aed, docs-only, no src/ changes) triggered a new CI run (39694551605 / 39694547370) on PR #132 per normal GitHub Actions behavior; not re-watched to completion as the plan's gate criteria were already satisfied by the preceding code-bearing commit's green run above
