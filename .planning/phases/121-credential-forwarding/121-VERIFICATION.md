---
phase: 121-credential-forwarding
verified: 2026-10-21T23:41:08Z
status: passed
score: 8/8 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
---

# Phase 121: Credential Forwarding Verification Report

**Phase Goal:** The app token is attached only to SeedSyncarr's own API requests, never to external destinations such as the GitHub update check.
**Verified:** 2026-10-21T23:41:08Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All truths below were checked against the actual codebase on branch `gsd/phase-121-credential-forwarding` (worktree `/Users/julianamacbook/seedsyncarr`), not inferred from SUMMARY.md prose. Where feasible, claims were independently reproduced rather than trusted.

| # | Truth (ROADMAP SC / PLAN must-have) | Status | Evidence |
|---|---|---|---|
| 1 | SC1: A request from the UI to `/server/*` still carries the Bearer token and succeeds (no regression in authenticated UI flows) | VERIFIED | `auth.interceptor.ts` gates on `token && isOwnApiRequest(req.url)`, preserving the `req.clone({setHeaders:{Authorization}})` path for same-origin `/server/` URLs. Independently re-ran the Karma suite locally: 657/657 SUCCESS, coverage 84.62%/70.49%/81.56%/85.44% (all above 83/68/79/83 floors). PR CI job "End-to-end tests on Docker Image (amd64)" (run 39692441447) passed with "55 passed", including `auth-token.spec.ts:85` "authenticated write flow works with the token" (add/remove AutoQueue pattern, 200 + Bearer header confirmed) — verified directly from the CI job log, not just the SUMMARY. |
| 2 | SC2: GitHub update-check request, and any other non-app-origin request, carries no Authorization header or app token | VERIFIED | `isOwnApiRequest` requires exact origin match + `/server/` path prefix, fail-closed. Karma test `"should NOT send the token to the GitHub update-check URL (SEC-02, D-11)"` and the separate `VersionCheckService through authInterceptor (SEC-02 pin)` describe (real `RestService`→`HttpClient`→`authInterceptor` chain) both read and pass in the repo today. PR CI log (job 119544630980) directly greps three `[chromium-token]` passing lines, including `"sends the token to /server/* but never to api.github.com"`, which asserts every captured `api.github.com` header map has no `authorization` key. |
| 3 | SC3 / D-11: A regression test asserting token absence on an external request fails against the original interceptor and passes after the fix | VERIFIED | Independently reproduced, not just trusted from SUMMARY: checked out RED commit `eb8ffb3` in a throwaway worktree and ran the quick Karma command — reproduced **12 FAILED, 18 SUCCESS** (exact match to SUMMARY's claim), including `"should NOT send the token to the GitHub update-check URL (SEC-02, D-11)"` and `"should send the GitHub update check without the app token"` both failing with `"Expected true to be false"`. Confirmed `eb8ffb3` touches only the two spec files (`git show --name-only`), and `git show eb8ffb3:...auth.interceptor.ts` shows the original `if (token)` "attaches Bearer token to all outgoing requests" version. Re-ran the same quick command at current HEAD (GREEN): 30/30 SUCCESS. |
| 4 | SC4: No authentication redesign — token source, interceptor mechanism, server-side Bearer check unchanged | VERIFIED | `git diff --stat c3d2788 -- src/python src/angular/src/app/app.config.ts src/angular/src/app/services/utils/rest.service.ts src/angular/src/app/services/utils/version-check.service.ts` prints nothing (confirmed directly, not from SUMMARY). The GREEN commit `206729a` touches only `auth.interceptor.ts` (`git show --name-only`). |
| 5 | D-04: "Own origin" is `window.location.origin`; no new setting | VERIFIED | `isOwnApiRequest` reads `window.location.origin` directly; no new config/settings surface added (`grep` over phase-modified files shows no new setting keys). |
| 6 | D-13: Caching/rotation specs moved to `/server/...` paths; cache/`_resetAuthInterceptorCache`/empty-token/missing-meta behavior unchanged | VERIFIED | `auth.interceptor.spec.ts` caching test uses `/server/config/get` → `/server/autoqueue/get`; rotation test uses the same paths with the "Production coupling note" comment intact; `/api/first`/`/api/second` do not appear in the file (`grep -c` = 0). `getApiToken()`, `cachedToken`, `tokenRead`, `_resetAuthInterceptorCache()` are byte-identical to the pre-fix version (diff against RED commit's version shows no change to those lines). |
| 7 | D-12: E2E run with a configured token proves (a) `/server/*` works with the token and (b) `api.github.com` carries no Authorization, via a real browser against the CI-built staging image | VERIFIED | `chromium-token` Playwright project (`dependencies: ['chromium']`, `testMatch: TOKEN_SPEC`) exists in `playwright.config.ts`; `auth-token.spec.ts` has exactly 3 tests, confirmed via local `npx playwright test --list` (Total: 55 tests in 10 files, 3 under `[chromium-token]`). PR CI log shows all 3 passing in a real Chromium instance against the CI-built image: `rejects /server/ requests without the token`, `sends the token to /server/* but never to api.github.com`, `authenticated write flow works with the token`. |
| 8 | D-07: GitHub rejects an unrecognized Bearer token (401) and accepts no-Authorization (200); update-notice should now work for token users | VERIFIED | Independently re-ran both curls: `-H 'Authorization: Bearer not-a-real-token'` → `401`; no header → `200` (exact match to SUMMARY's recorded evidence). The `chromium-token` E2E test additionally demonstrates the notice rendering (`'.bell-notif-text'` with "A new version of SeedSyncarr is available") against a stubbed `v99.0.0` release, and that assertion passed in CI. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/angular/src/app/services/utils/auth.interceptor.ts` | Fail-closed `isOwnApiRequest(url)` gating token attachment | VERIFIED | Contains `function isOwnApiRequest(url: string): boolean`, `new URL(url, ownOrigin)` in try/catch, `console.warn` with fixed message on catch, condition `token && isOwnApiRequest(req.url)`. Cache helpers unchanged. |
| `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` | Full D-10 case table incl. D-11 GitHub anchor | VERIFIED | Contains `GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/thejuran/seedsyncarr/releases/latest"` and 13 new `it` blocks covering every D-10 row (external host, protocol-relative, backslash, look-alike host w/ no-warn assertion, userinfo w/ no-warn assertion, port mismatch, scheme mismatch, non-`/server/` path, dot-segment escape, unparseable URL w/ warn-content assertion, empty-token GitHub case). |
| `src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts` | D-05 integration pin through the real interceptor chain | VERIFIED | New top-level `describe("VersionCheckService through authInterceptor (SEC-02 pin)")` provides real `RestService` + `provideHttpClient(withInterceptors([authInterceptor]))`; asserts no `Authorization` header on the GitHub request. Original mock-based describe untouched. |
| `src/e2e/playwright.config.ts` | `chromium` (testIgnore token spec) + `chromium-token` (testMatch, `dependencies: ['chromium']`) | VERIFIED | `TOKEN_SPEC` regex, `chromium` project has `testIgnore: TOKEN_SPEC`, `chromium-token` project has `testMatch: TOKEN_SPEC` and `dependencies: ['chromium']`; no `extraHTTPHeaders` anywhere outside a comment explaining why not to set it. |
| `src/e2e/tests/auth-token.spec.ts` | Token-configured E2E run | VERIFIED | Exists; 3 tests; uses `allHeaders()` (3 occurrences), never `.headers()`; stubs `api.github.com` via `page.route`; imports from `./fixtures/csp-listener`; synthetic token literal `e2e-api-token-not-a-secret`; no `console.log`. |
| `src/e2e/README.md` | Note that `chromium-token` runs last and leaves `api_token` set on `myapp` | VERIFIED | "Notes" list item 3 documents run-order, `/server/config/set` mechanism, and the `DEV=1` re-run / `--no-deps` caveats. |
| `.planning/STATE.md` | Pending todo carrying D-08/D-09 to Phase 126 | VERIFIED | "### Pending Todos" contains the full D-08/D-09 bullet (release-note disclosure text + NAS rotation steps), matching 121-CONTEXT.md's D-08/D-09 wording. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `authInterceptor` | `isOwnApiRequest` | token attach condition | WIRED | `if (token && isOwnApiRequest(req.url))` present verbatim in `auth.interceptor.ts`. |
| `isOwnApiRequest` | `window.location.origin` | `new URL(url, ownOrigin)` + exact origin compare | WIRED | `const ownOrigin = window.location.origin; ... parsed.origin === ownOrigin && parsed.pathname.startsWith(OWN_API_PATH_PREFIX)`. |
| `src/e2e/playwright.config.ts` `chromium-token` project | `src/e2e/tests/auth-token.spec.ts` | `testMatch: TOKEN_SPEC` | WIRED | Confirmed via `npx playwright test --list`: exactly 3 tests list under `[chromium-token]` and none of them under `[chromium]`. |
| `src/e2e/tests/auth-token.spec.ts` `beforeEach` | `POST /server/config/set` | `request` fixture w/ `Authorization` header | WIRED | Code present and, per CI log, executed successfully (test 1 "rejects /server/ requests without the token" passed, which depends on this call succeeding first). |
| PR CI `e2etests-docker-image` | `auth-token.spec.ts` | `run_tests.sh` → `npx playwright test` running `chromium-token` after `chromium` | WIRED | Confirmed directly from `gh run view 39692441447 --job 119544630980 --log`: all 3 `[chromium-token]` lines present and marked `✓`, overall `55 passed (1.4m)`. |

### Data-Flow Trace (Level 4)

Not applicable in the Level-4 sense (no dashboard/component rendering fetched data) — the "data flow" here is the token itself flowing through the interceptor to the request, which is covered end-to-end by the key-link table above (unit test → integration pin → real-browser E2E → CI execution), each level independently re-confirmed rather than inferred.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| RED state reproduces (test(121-01) commit, before the fix) | `git worktree add <tmp> eb8ffb3` then `npx ng test --include=auth.interceptor.spec.ts --include=version-check.service.spec.ts` | `TOTAL: 12 FAILED, 18 SUCCESS` (exact match to SUMMARY) | PASS |
| GREEN state passes (current HEAD) | same quick command at current HEAD | `TOTAL: 30 SUCCESS` | PASS |
| Full Angular suite + coverage (milestone CI gate) | `npx ng test --code-coverage` | `657/657 SUCCESS`; 84.62%/70.49%/81.56%/85.44% (≥ 83/68/79/83) | PASS |
| Angular lint | `npm run lint` | exit 0, no output | PASS |
| E2E compiles and lists correctly | `cd src/e2e && npx tsc --noEmit -p . && npx playwright test --list` | exit 0; "Total: 55 tests in 10 files"; 3 under `[chromium-token]` | PASS |
| SC4 no-redesign diff | `git diff --stat c3d2788 -- src/python ... version-check.service.ts` | empty | PASS |
| D-07 GitHub rejection evidence | `curl ... -H 'Authorization: Bearer not-a-real-token' ...` vs. no-header | `401` then `200` | PASS |
| PR CI E2E job contains 3 passing `[chromium-token]` lines | `gh run view 39692441447 --job 119544630980 --log \| grep -F chromium-token` | 3 lines, all `✓` | PASS |

### Probe Execution

Not applicable — Phase 121 is not a migration/tooling phase with `scripts/*/tests/probe-*.sh` scripts; no probes declared in PLAN/SUMMARY. `find scripts -path '*/tests/probe-*.sh'` was checked implicitly via the file listing in Step 1 and no such convention exists in this repo layout for this phase. Skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SEC-02 | 121-01, 121-02, 121-03 | The app token is attached only to requests to SeedSyncarr's own API; requests to any other destination carry no app token, with regression tests for both cases | SATISFIED | All 8 observable truths above VERIFIED; `.planning/REQUIREMENTS.md` line 13 already shows `[x] SEC-02` and line 72 maps SEC-02 → Phase 121 → Complete, consistent with codebase evidence (not merely re-stating the checkbox). No other requirement IDs map to Phase 121 in REQUIREMENTS.md — no orphaned requirements. |

### Anti-Patterns Found

None. Scanned all phase-modified files (`auth.interceptor.ts`, `auth.interceptor.spec.ts`, `version-check.service.spec.ts`, `playwright.config.ts`, `auth-token.spec.ts`, `README.md`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and placeholder-language patterns — zero matches. No `console.log` in the E2E spec (`grep -c console.log` = 0, confirmed). No empty-implementation or hardcoded-empty-data patterns found in the interceptor (every branch returns a real computed boolean or forwards the real request).

### Human Verification Required

None. The one item flagged in `121-VALIDATION.md`'s "Manual-Only Verifications" table — "E2E token run executes against a real container" — was not left to a human: it was proven by the PR CI job `e2etests-docker-image`, and this verification independently re-confirmed the three `[chromium-token]` passing lines and the `55 passed` summary directly from the CI log (not from SUMMARY.md's quoted excerpt). The D-07 bell-notification UI demonstration also ran and passed as part of that same automated E2E test (`.bell-notif-text` visibility assertion), so no separate human visual check is outstanding.

### Gaps Summary

No gaps. All four ROADMAP Phase 121 success criteria, all PLAN frontmatter must-haves (truths, artifacts, key links) across 121-01/02/03, and the phase's own `<verification>`/`<success_criteria>` blocks are independently confirmed against the live codebase and a live CI run — not inferred from SUMMARY.md prose. Where a claim was reproducible locally (RED/GREEN Karma states, full-suite coverage, lint, e2e compile/list, SC4 diff, D-07 curl codes), this verification re-ran it directly rather than trusting the SUMMARY. Where a claim required infrastructure only available in CI (the real-browser `chromium-token` run), this verification queried the GitHub Actions run and job log directly via `gh run view ... --log` rather than citing the SUMMARY's transcription of it.

D-08 (release-note disclosure) and D-09 (production token rotation) are intentionally not executed in this phase — `.planning/STATE.md` carries them to Phase 126 per the phase's own context document, and this is correctly reflected as a forward carry, not a gap.

---

*Verified: 2026-10-21T23:41:08Z*
*Verifier: Claude (bm-verifier)*
