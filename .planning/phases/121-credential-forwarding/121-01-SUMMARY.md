---
phase: 121-credential-forwarding
plan: 01
subsystem: auth
tags: [angular, http-interceptor, karma, jasmine, whatwg-url, security]

# Dependency graph
requires: []
provides:
  - "authInterceptor attaches the app token only when the request resolves to window.location.origin AND a /server/ path, via isOwnApiRequest(url)"
  - "Full D-10 Karma case table in auth.interceptor.spec.ts (own-origin relative/absolute, GitHub URL, external host, protocol-relative, backslash, look-alike host, userinfo, port/scheme mismatch, non-/server/ path, dot-segment escape, unparseable URL, empty-token GitHub case)"
  - "D-05 integration pin in version-check.service.spec.ts: real VersionCheckService -> RestService -> HttpClient -> authInterceptor chain, asserting the GitHub request carries no Authorization header"
  - "RED (test(121-01)) then GREEN (feat(121-01)) commit pair proving the GitHub-URL regression fails before the fix and passes after"
affects: [121-02, 121-03, 126-release]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Destination-gated functional HTTP interceptor: parse req.url with WHATWG URL against window.location.origin, exact origin equality + path-prefix check, fail closed (catch -> no token, generic console.warn with no URL/token in its arguments)"]

key-files:
  created: []
  modified:
    - src/angular/src/app/services/utils/auth.interceptor.ts
    - src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts
    - src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts

key-decisions:
  - "isOwnApiRequest(url) added directly below getApiToken() in the same plain-function, explicit-return-type style; cache state and _resetAuthInterceptorCache left byte-for-byte unchanged"
  - "Condition changed from `if (token)` to `if (token && isOwnApiRequest(req.url))`, using req.url (not urlWithParams) per D-02"
  - "D-13 path moves (caching/rotation specs /api/first -> /server/config/get, /api/second -> /server/autoqueue/get) landed in the RED commit so they stay green both before and after the fix"

patterns-established:
  - "Fail-closed URL-parse gate for any interceptor that attaches credentials: new URL(url, ownOrigin) in try/catch, exact origin equality, no string-prefix checks"

requirements-completed: [SEC-02]

# Metrics
duration: 13min
completed: 2026-10-21
---

# Phase 121 Plan 01: Destination-Gated App Token Summary

**Gated `authInterceptor` to attach `Authorization: Bearer <token>` only to same-origin `/server/*` requests via a fail-closed WHATWG-`URL` check, closing the GitHub update-check token leak (SEC-02); RED commit proves the regression failed on the old interceptor, GREEN commit proves the fix.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-10-21T22:48:00Z (approx.)
- **Completed:** 2026-10-21T23:00:17Z
- **Tasks:** 2 (RED, GREEN)
- **Files modified:** 3

## Accomplishments
- `authInterceptor` no longer sends the app token to any destination except the page's own origin under `/server/`, including the GitHub update check that previously received it on every page load
- Full D-10 Karma case table added (13 new `it` blocks) covering every same-origin-positive, external-host, protocol-relative, backslash, look-alike-host, userinfo, port-mismatch, scheme-mismatch, non-`/server/`-path, dot-segment-escape, unparseable-URL, and empty-token-GitHub case
- A separate integration-pin `describe` in `version-check.service.spec.ts` proves the *real* `VersionCheckService -> RestService -> HttpClient -> authInterceptor` chain sends the GitHub request with no `Authorization` header (D-05)
- RED/GREEN TDD gate satisfied: the GitHub-URL test and the integration pin both fail with "Expected true to be false" against the unmodified interceptor, then pass after the fix

## RED

Commit `eb8ffb3` added the full D-10 case table, moved the D-13 caching/rotation tests off `/api/first`/`/api/second` onto `/server/config/get`/`/server/autoqueue/get`, and added the D-05 version-check integration pin — with **no** change to `auth.interceptor.ts`.

Quick command: `cd src/angular && npx ng test --browsers ChromeHeadless --watch=false --include='**/auth.interceptor.spec.ts' --include='**/version-check.service.spec.ts'`

Result: **12 FAILED, 18 SUCCESS**. Failing test names (all "Expected true to be false", one with an additional spy-count assertion):
```
authInterceptor should NOT send the token to the GitHub update-check URL (SEC-02, D-11) FAILED
  Expected true to be false.
authInterceptor should NOT send the token to another external host FAILED
  Expected true to be false.
authInterceptor should NOT send the token to a protocol-relative //host URL FAILED
  Expected true to be false.
authInterceptor should NOT send the token to a backslash /\host URL FAILED
  Expected true to be false.
authInterceptor should NOT send the token to a look-alike host, without logging a warning FAILED
  Expected true to be false.
authInterceptor should NOT send the token to a userinfo host@evil URL, without logging a warning FAILED
  Expected true to be false.
authInterceptor should NOT send the token when the port does not match FAILED
  Expected true to be false.
authInterceptor should NOT send the token when the scheme does not match FAILED
  Expected true to be false.
authInterceptor should NOT send the token to a same-origin path outside /server/ FAILED
  Expected true to be false.
authInterceptor should NOT send the token to a /server/../ escape FAILED
  Expected true to be false.
authInterceptor should NOT send the token for an unparseable URL, and should log a generic warning FAILED
  Expected true to be false.
  Expected spy warn to have been called once. It was called 0 times.
VersionCheckService through authInterceptor (SEC-02 pin) should send the GitHub update check without the app token FAILED
  Expected true to be false.
```
All 18 pre-existing tests (positive-token, empty-token, missing-meta, header-preservation, caching, rotation, POST, plus the untouched `VersionCheckService` mock-based describe) passed unchanged, confirming the RED commit broke nothing and failed only for the intended reason.

## GREEN

Commit `206729a` added `isOwnApiRequest(url: string): boolean` to `auth.interceptor.ts`: resolves `url` with `new URL(url, window.location.origin)` inside try/catch, returns `parsed.origin === ownOrigin && parsed.pathname.startsWith("/server/")`, and on a catch logs `console.warn("authInterceptor: request URL could not be parsed; sending without app token")` (no URL, no token) and returns `false`. Changed the interceptor condition to `token && isOwnApiRequest(req.url)`. Token caching, `tokenRead`, `getApiToken()` and `_resetAuthInterceptorCache()` are byte-for-byte unchanged.

- Quick command: 30/30 pass (all D-10 rows + D-05 pin + 18 pre-existing tests)
- Full suite with `--code-coverage`: **657/657 pass**; coverage Statements 84.62% / Branches 70.49% / Functions 81.56% / Lines 85.44% — all above the `check.global` floors (83/68/79/83)
- `npm run lint` (`eslint --max-warnings 0`): exit 0
- SC4 static check: `git diff --stat c3d2788 -- src/python src/angular/src/app/app.config.ts src/angular/src/app/services/utils/rest.service.ts src/angular/src/app/services/utils/version-check.service.ts` — empty (no auth redesign, no touched files outside the interceptor and its specs)

## REFACTOR

None needed — the GREEN implementation matched the planned shape with no cleanup required.

## Task Commits

1. **Task 1 (RED): D-10 case table, D-13 path moves, D-05 pin** - `eb8ffb3` (test)
2. **Task 2 (GREEN): isOwnApiRequest fail-closed gate** - `206729a` (feat)

## Files Created/Modified
- `src/angular/src/app/services/utils/auth.interceptor.ts` - Added `isOwnApiRequest(url)`; gated token attachment on `token && isOwnApiRequest(req.url)`; rewrote interceptor JSDoc
- `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` - Added `GITHUB_LATEST_RELEASE_URL`, `expectNoAuth`/`expectBearer` helpers, 13 D-10 case-table tests; moved caching/rotation tests to `/server/...` paths
- `src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts` - Added a second top-level `describe` with a real `RestService` + real `authInterceptor` chain, pinning the GitHub request to carry no `Authorization` header

## Decisions Made
- Followed the plan's interface contract exactly: `isOwnApiRequest(url: string): boolean` placed directly below `getApiToken()`, same plain-function/explicit-return-type style as the existing helper
- Built every look-alike/port/scheme/userinfo test URL at runtime from `location.origin`/`location.protocol`/`location.hostname`/`location.host` rather than hardcoding `localhost:9876`, per RESEARCH Pitfall 1/2
- Used `"http://["` for the unparseable-URL case (verified it throws under Node's WHATWG `URL` and works under `HttpTestingController`, per RESEARCH Pitfall 3)
- Ran `npm ci` in the worktree's `src/angular` first since `node_modules` did not exist there (per project_notes instruction, not a deviation from the plan)

## Deviations from Plan

None — plan executed exactly as written. All D-10 rows, the D-11 anchor, D-13 path moves and the D-05 integration pin match the plan's `<action>`/`<behavior>` text; no architectural changes, no scope changes, no auto-fixes beyond the plan's own instructions were needed.

## Issues Encountered

None. `npm ci` in `src/angular` emitted standard `EBADENGINE` (Node 25.9.0 vs the package's declared `^22`/`^24`/`>=26` range, for a transitive npm-internal dependency, not a direct project dependency) and deprecation warnings; both are pre-existing environment notices unrelated to this change and did not affect test or lint results.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The interceptor fix and its full regression coverage are complete and committed; `src/angular/src/app/services/utils/auth.interceptor.ts`, `rest.service.ts`, `version-check.service.ts` and `app.config.ts` are confirmed unchanged outside the interceptor file itself (SC4)
- D-07 side effect to verify and carry forward: GitHub's API returns 401 to an unrecognized Bearer token, so for instances with a token configured the "new version available" notice has likely never worked since v1.0.0. After this fix, the update-check request to `api.github.com` is sent with no `Authorization` header at all, so it should receive a normal 200 response. This phase does not exercise a live GitHub call or the notification UI — that end-to-end proof belongs to the Plan 02 E2E token run (D-12), with the release-note mention carried to Phase 126 (D-08).
- Plan 02 (E2E Playwright token run) and Plan 03 are unblocked; nothing in this plan's scope blocks them. Plan 02 runs concurrently in a separate worktree and touches only `src/e2e` files, so there is no file overlap with this plan's changes.

---
*Phase: 121-credential-forwarding*
*Completed: 2026-10-21*
