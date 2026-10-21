---
phase: 121-credential-forwarding
plan: 02
subsystem: testing
tags: [playwright, e2e, auth, bearer-token, github-api]

# Dependency graph
requires:
  - phase: 121-credential-forwarding plan 01
    provides: "authInterceptor destination-gated Bearer token fix (not yet merged in this worktree)"
provides:
  - "chromium-token Playwright project, dependent on chromium, running strictly after the 52 no-token specs"
  - "auth-token.spec.ts: 401-without-token enforcement, Bearer+200 positive control, api.github.com header-absence assertion, D-07 update-notice demonstration, authenticated AutoQueue add/remove write flow"
affects: [121-credential-forwarding plan 03, 126-release-1.8.0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dependent Playwright project (testIgnore/testMatch + dependencies: ['chromium']) to add a token-configured E2E run without disturbing existing no-token coverage"
    - "Header-absence assertion via request.allHeaders() with a positive control on a same-origin request, never request.headers() (which omits security headers)"

key-files:
  created:
    - src/e2e/tests/auth-token.spec.ts
  modified:
    - src/e2e/playwright.config.ts
    - src/e2e/README.md

key-decisions:
  - "Wired the token-configured run as a second Playwright project (chromium-token) with dependencies: ['chromium'] rather than a second compose stack or a token baked into the E2E Docker config (Claude's discretion per CONTEXT D-12-adjacent note); keeps the existing 52 no-token tests completely unaffected and needs no Docker/compose/Makefile/CI changes"
  - "E2E_TOKEN is a named synthetic fixture ('e2e-api-token-not-a-secret'), set via an idempotent POST /server/config/set in beforeEach (sent with Authorization so retries pass whether or not the token is already set); never reset in afterEach because config/set rejects an empty value"
  - "D-07 (GitHub update notice) demonstrated with a stubbed v99.0.0 release and a visible '.bell-notif-text' assertion, in addition to the SEC-02 header-absence assertion"

patterns-established:
  - "Pattern 3 from RESEARCH.md: runtime-settable token via /server/config/set + Playwright project dependencies, instead of a parallel compose stack, to add a token-configured E2E lane cheaply"

requirements-completed: [SEC-02]

# Metrics
duration: ~20min
completed: 2026-10-21
---

# Phase 121 Plan 02: Token-configured E2E coverage for credential forwarding (SEC-02) Summary

**Added a dependent `chromium-token` Playwright project and a 3-test spec that proves, with `general.api_token` set at runtime, `/server/*` requests carry the Bearer token and work while the browser's request to `api.github.com` carries no `authorization` header.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-10-21T22:52:42Z (worktree base commit)
- **Completed:** 2026-10-21T22:59:40Z
- **Tasks:** 2 of 2 completed
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments

- `playwright.config.ts` now declares `TOKEN_SPEC`, ignores it on the existing `chromium` project (`testIgnore`), and adds a `chromium-token` project (`testMatch`, `dependencies: ['chromium']`) that runs strictly after all other E2E tests, with no `use.extraHTTPHeaders` (which would have masked the bug).
- `src/e2e/tests/auth-token.spec.ts` (new): one `describe` block, exactly 3 tests —
  1. **Enforcement**: `/server/config/get` returns 401 with no header, 200 with `Authorization: Bearer <token>`.
  2. **SEC-02 core assertion**: with the token configured, a same-origin `/server/config/get` request carries `Authorization: Bearer <token>` and returns 200 (positive control), while every captured `api.github.com` request header map has no `authorization` key; also asserts the `<meta name="api-token">` tag content and, as a D-07 demonstration, that the stubbed newer-release response renders the "A new version of SeedSyncarr is available" notice in the bell dropdown.
  3. **Authenticated write flow**: add and remove an AutoQueue pattern through the UI, with the `/server/autoqueue/add/*` response confirmed to carry the Bearer token.
- `README.md` documents that `chromium-token` runs last, that the API cannot clear `api_token` once set, and the `DEV=1` re-run / `--project chromium-token` caveats.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the dependent chromium-token project and document its ordering** - `d2f125f` (test)
2. **Task 2: Write the token-configured E2E spec** - `4992afc` (test)

**Plan metadata:** (this summary's commit, created after this file)

## Files Created/Modified

- `src/e2e/playwright.config.ts` - Adds `TOKEN_SPEC`, `chromium` `testIgnore`, and the `chromium-token` project with `dependencies: ['chromium']`
- `src/e2e/README.md` - Documents the `chromium-token` run-order and `DEV=1` re-run caveat
- `src/e2e/tests/auth-token.spec.ts` - New spec: enforcement, SEC-02 header-absence + positive control, D-07 notice, authenticated AutoQueue write flow

## Decisions Made

See `key-decisions` in frontmatter. In short: a dependent Playwright project (not a second compose stack), a named synthetic token fixture, and no token-reset in `afterEach` (the API cannot clear it, so correctness relies on project ordering + container recreation between runs).

## Deviations from Plan

None - plan executed exactly as written. `npm ci` was run in `src/e2e` to populate this worktree's own `node_modules` from the existing, already-committed `package-lock.json` (no new or different package introduced — this worktree simply had no dependencies installed yet); this is routine environment setup, not a plan deviation.

## Issues Encountered

None.

## Verification Performed (actually run, not inferred)

```
cd src/e2e && npx tsc --noEmit -p .          # exit 0
cd src/e2e && npx playwright test --list
```

Observed `--list` output (tail):

```
  [chromium-token] › auth-token.spec.ts:47:9 › API token configured (SEC-02) › rejects /server/ requests without the token
  [chromium-token] › auth-token.spec.ts:55:9 › API token configured (SEC-02) › sends the token to /server/* but never to api.github.com
  [chromium-token] › auth-token.spec.ts:85:9 › API token configured (SEC-02) › authenticated write flow works with the token
Total: 55 tests in 10 files
```

Acceptance-criteria greps (Task 1 + Task 2), all observed passing:
- `[chromium] ›` count: 52 (unchanged from before this plan)
- `[chromium-token]` count for auth-token.spec.ts: 3; `[chromium] ` count for auth-token.spec.ts: 0
- `dependencies: ['chromium']` count: 1; `testIgnore: TOKEN_SPEC` count: 1; `testMatch: TOKEN_SPEC` count: 1
- `extraHTTPHeaders` outside comments: 0
- `chromium-token` mentions in README.md: 2 (>= 1 required)
- `allHeaders()` count: 3 (>= 2 required); `.headers()` count: 0
- `page.route('https://api.github.com/**'` literal count: 1
- `from './fixtures/csp-listener'` count: 1; `console.log` count: 0; `e2e-api-token-not-a-secret` literal count: 1
- `git diff --stat c3d2788 -- src/docker Makefile .github src/python` — empty (no harness/infra/Python changes)

**What has NOT been executed, and is explicitly out of scope for this plan:** the spec has never run against a live container. Local E2E execution needs the pushed staging image (per RESEARCH "Open Questions" resolution), which this worktree does not build. Real execution is gated on the PR CI job `e2etests-docker-image` in plan 121-03, and — per the plan's own objective — the new spec only passes in CI once plan 121-01's interceptor fix lands on the same branch (this worktree does not yet have 121-01's `auth.interceptor.ts` change, so the token spec's header-absence assertion is expected to fail against current `main` if it were run today — that is the intended red state, not a defect in this plan's wiring).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wiring and spec are complete and locally verified for compilation and listing (`tsc`, `--list`).
- Plan 121-03 must confirm the PR CI `e2etests-docker-image` job passes with plan 121-01 merged onto the same branch, including the 3 `[chromium-token]` tests, before this plan's SEC-02 contribution can be considered proven end to end.
- No blockers for plan 121-03.

---
*Phase: 121-credential-forwarding*
*Completed: 2026-10-21*

## Self-Check: PASSED

- FOUND: src/e2e/playwright.config.ts
- FOUND: src/e2e/README.md
- FOUND: src/e2e/tests/auth-token.spec.ts
- FOUND: .planning/phases/121-credential-forwarding/121-02-SUMMARY.md
- FOUND commit d2f125f (Task 1)
- FOUND commit 4992afc (Task 2)
- FOUND commit 300c95d (this SUMMARY)
