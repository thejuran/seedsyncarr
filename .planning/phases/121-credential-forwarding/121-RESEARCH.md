# Phase 121: Credential Forwarding - Research

**Researched:** 2026-10-21
**Domain:** Angular functional HTTP interceptor (destination-gated Bearer token), Karma/Jasmine unit tests, Playwright E2E (Docker harness)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Which requests get the token
- **D-01:** Attach the token only when the request resolves to the **same origin as the loaded UI** (`location.origin`) **and** its path is under `/server/`. Everything else, including same-origin non-`/server/` paths, gets no `Authorization` header.
- **D-02:** Determine the destination by **parsing the URL** (resolve relative URLs against `location.origin`, then compare the exact origin and check the pathname). Do not use string-prefix checks. They let `//evil.com/server/x` through and are confused by look-alike hosts such as `https://host.evil.com`.
- **D-03:** Fail closed. If the URL can't be parsed, or the resolved origin or path doesn't match, the request goes out with no token. A missed token shows up as a 401; a leaked token is silent.
- **D-04:** "Own origin" is whatever address the browser loaded SeedSyncarr from. No new setting; this works behind a reverse proxy and under any hostname (`<base href="/">`, and all API calls use relative `/server/...` URLs).

#### Update check hardening
- **D-05:** The rule fix alone protects the GitHub update check. No separate token-free HTTP path or `HttpBackend` bypass for `VersionCheckService`. One mechanism, guarded by a regression test pinned to the real GitHub URL.
- **D-06:** Leave the update request's credentials/cookie mode as is. The app doesn't use cookie auth, and browsers don't send its cookies cross-origin to GitHub.
- **D-07:** Expected side effect, to verify and record: GitHub's API returns 401 to an unrecognized Bearer token, so for users with a token configured the "new version available" notice has likely never worked. After the fix it should start working. Note this in the summary and in the 1.8.0 release notes.

#### Existing users' exposed token (feeds Phase 126 release notes and deploy)
- **D-08:** The 1.8.0 release notes disclose the exposure factually: since v1.0.0, a configured API token was sent in an `Authorization` header to `api.github.com` (HTTPS) on each UI page load; GitHub rejected it; no other destination received it. Present rotation as **optional**, recommended mainly for instances reachable beyond the user's LAN, with steps: edit `api_token` in `settings.cfg`, then restart.
- **D-09:** Phase 126 production deploy adds a step: after 1.8.0 is live on the NAS, rotate the production `api_token`, then confirm the UI loads, authenticated calls succeed and a scan completes. Deploy first, then rotate, so the new token never reaches GitHub. Before rotating, the planner/executor for 126 checks whether anything else on the NAS uses the current token.
- Phase 121 itself does not write the release notes or touch the NAS. D-08 and D-09 are carried forward to Phase 126.

#### How we prove it
- **D-10:** Unit tests (Karma/Jasmine, `auth.interceptor.spec.ts`) cover the full case table:
  - `/server/...` relative URL gets the token
  - absolute same-origin `/server/...` URL gets the token
  - GitHub releases URL gets no token
  - another external host gets no token
  - protocol-relative `//other-host/server/...` gets no token
  - look-alike host prefix gets no token
  - same-origin non-`/server/` path gets no token
  - unparseable URL gets no token
  - existing no-token and missing-meta cases are unchanged
- **D-11:** Red first: the GitHub-URL "no Authorization header" test must fail against the current interceptor before the fix and pass after it (milestone CI gate).
- **D-12:** Add **one E2E (Playwright) run with an API token configured** that proves (a) the UI loads and authenticated `/server/*` flows work with the token, and (b) the browser's request to `api.github.com` carries no `Authorization` header. Intercept and stub the GitHub request so the test never depends on the real network. This closes the gap that the existing E2E suite never configures a token.
- **D-13:** Existing interceptor specs that use non-`/server/` paths (the caching and token-rotation tests use `/api/first` and `/api/second`) move to `/server/...` paths so they still test caching rather than the new path rule.

### Claude's Discretion
- How the E2E token run is wired: a separate Playwright project, a config variant, or a token set in the E2E Docker config, chosen to keep the existing no-token E2E coverage intact.
- Exact helper structure inside `auth.interceptor.ts`, e.g. a small `isOwnApiRequest(url)` function, provided the token caching and `_resetAuthInterceptorCache` behavior are preserved.

### Deferred Ideas (OUT OF SCOPE)
- Token rotation UI (regenerate token from Settings): a new capability, not in this phase or milestone. Rotation stays a `settings.cfg` edit plus restart.
- Release-note text and NAS token rotation are decided here (D-08, D-09) but executed in Phase 126.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEC-02 | The app token is attached only to requests to SeedSyncarr's own API; requests to any other destination (including the GitHub update check) carry no app token, with regression tests for both cases | Interceptor fix pattern (Pattern 1), URL edge-case table verified with WHATWG `URL` (Pitfalls 1-3), Karma spec case table (Code Examples), E2E token project wiring via Playwright project `dependencies` + runtime `config/set` (Pattern 3), header-absence assertion with `allHeaders()` plus a positive control (Pitfall 5) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

There is no project-level `./CLAUDE.md`. The user's global `~/.claude/CLAUDE.md` applies:
- **Security (absolute):** never hardcode secrets, never log sensitive data (tokens, auth headers). The interceptor must never log the token or the `Authorization` header. A fixed E2E test token is a test fixture, not a secret. Name it so that's obvious (e.g. `e2e-api-token-not-a-secret`).
- **Don't swallow exceptions silently; log at minimum.** The fail-closed `catch` around `new URL(...)` should `console.warn` a generic message (no URL, no token). `no-console` in `eslint.config.js` allows `warn`, `error` and `debug`.
- **Guard nullable returns before property access.** This is already done for the meta tag (`meta?.getAttribute`).
- **Follow existing repo conventions.** Functional `HttpInterceptorFn`, module-level cache, double quotes, explicit return types. `npm run lint` uses `--max-warnings 0`, so `explicit-function-return-type` warnings fail lint.
- **Division of labor:** technical choices (E2E wiring, helper shape) are Claude's call. Verification comes from tests and CI, not from the owner reading code.
- Project skills: `.claude/skills/aidesigner-frontend` only (UI design). Not relevant to this phase.
- Memory: CI runs `ruff check src/python/` as a separate gate. This phase touches **no Python**, so ruff and pytest only need to stay green in CI and need no extra local action.

## Summary

The defect is one line. `authInterceptor` (`src/angular/src/app/services/utils/auth.interceptor.ts`) clones every request with `Authorization: Bearer <token>` whenever the meta tag is non-empty. `VersionCheckService` is forced to start at bootstrap through an `APP_INITIALIZER` in `app.config.ts`, and it calls `https://api.github.com/repos/thejuran/seedsyncarr/releases/latest` through the same `HttpClient`. So every UI page load sends the token to GitHub. I confirmed live that GitHub's CORS preflight allows `Authorization` and that a bogus Bearer gets **401**, while the same request without the header gets **200** [VERIFIED: curl against api.github.com this session]. D-07 holds: for token users the update notice has never worked.

The fix: parse `req.url` with `new URL(req.url, window.location.origin)` inside try/catch. Attach the token only if `parsed.origin === window.location.origin && parsed.pathname.startsWith("/server/")`. I checked every D-10 case against WHATWG `URL`, the same parser Chrome uses. Protocol-relative `//evil.com/...`, backslash `/\evil.com/...`, userinfo `host@evil.com`, scheme or port mismatch and `/server/../dashboard` all resolve as non-matching. `http://[` and `//` throw. One trap: under Karma `location.origin` is `http://localhost:9876` (with a port), so a naive look-alike `${location.origin}.evil.com` **throws** (bad port) and tests the unparseable branch instead of the look-alike branch. Build the look-alike from `location.hostname`.

For E2E (D-12), use a second Playwright project, `chromium-token`, that `dependencies: ['chromium']`. Every existing no-token spec runs first, unchanged. The token spec sets `general.api_token` at runtime through `POST /server/config/set`, which takes effect immediately because the server reads the live config for both the Bearer check and the meta tag. It then loads the UI with `page.route('https://api.github.com/**')` stubbed, and asserts with `request.allHeaders()` that GitHub got no `authorization`, while a `/server/*` request in the same page **did** carry it (positive control). This needs no Docker, compose or Python changes. The new spec lives under `src/e2e/tests/`, which the E2E Dockerfile already copies.

**Primary recommendation:** Add a fail-closed `isOwnApiRequest(url)` URL-parse gate to `authInterceptor`. Commit the red Karma case table first, including the GitHub-URL test. Add a `chromium-token` Playwright project that depends on the existing `chromium` project and asserts header absence with `allHeaders()` plus a positive control.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Decide whether a request gets the app token | Browser / Client (Angular `authInterceptor`) | — | Only the browser knows the request's destination. The server never sees requests to GitHub. |
| Supply the token | Frontend Server (Bottle `__index` injects `<meta name="api-token">`) | — | Unchanged (D-04, out-of-scope boundary) |
| Enforce the token | API / Backend (`web_app.py` `before_request` hook) | — | Unchanged. It still only checks `/server/*` minus exemptions. |
| Update check | Browser / Client (`VersionCheckService` → `RestService` → `HttpClient`) | External (api.github.com) | Unchanged code. It's protected by the interceptor rule (D-05). |
| Live model stream | Browser (`EventSource`) | API (`/server/stream`, auth-exempt) | Doesn't go through `HttpClient`, so the interceptor never sees it. Unaffected. |
| E2E token configuration | Test harness (Playwright spec using `POST /server/config/set`) | API (live config) | No Docker or Python change is needed. |

## Standard Stack

No new dependencies. Everything already in the repo:

### Core
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@angular/common/http` | ^22.2.1 | `HttpInterceptorFn`, `withInterceptors` | Existing mechanism (out-of-scope to change) [VERIFIED: src/angular/package.json] |
| WHATWG `URL` (browser built-in) | — | Resolve and parse destination | The platform's own parser, the same one the browser uses to send the request, so there's no parsing mismatch [VERIFIED: node URL probe this session; same WHATWG spec as Chrome] |
| Karma 6.4.4 + Jasmine (jasmine-core ^6.3.0) + `@angular/build:karma` | — | Unit tests and coverage thresholds | Existing [VERIFIED: karma.conf.js, angular.json; ran locally, 7/7 pass] |
| `@angular/common/http/testing` `HttpTestingController` | ^22.2.1 | Assert request headers | Existing spec pattern |
| `@playwright/test` (src/e2e) | 1.59.1 (lockfile) | E2E, `page.route`, `request.allHeaders()`, project `dependencies` | Existing [VERIFIED: `npx playwright --version` → 1.59.1] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| URL parse gate | `req.url.startsWith("/server/")` | Rejected by D-02. It fails on absolute same-origin URLs and invites prefix bugs. |
| Runtime `config/set` in a dependent project | Second full E2E compose stack with token preset in `settings.cfg` | Doubles CI E2E time (~10+ min), needs compose and configure-script changes (every configure curl would need Bearer) |
| Runtime `config/set` | Set token in configure container for the whole suite | Destroys existing no-token coverage. Every `page.request` helper in seed-state/settings fixtures would need Bearer. Violates "keep no-token coverage intact". |
| `HttpBackend` bypass for version check | — | Rejected by D-05 |

**Installation:** none.

## Package Legitimacy Audit

This phase installs no external packages, so there is nothing to audit. No slopcheck run was needed.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 Browser loads http(s)://<host>[:port]/  (Bottle __index injects <meta name="api-token" content=TOKEN>)
                │
                ▼
   Angular bootstrap ── APP_INITIALIZER ──► VersionCheckService ──► RestService.sendRequest(GITHUB_URL)
                │                                                         │
   App services (config, autoqueue, commands, bulk) ── HttpClient(url) ───┤
                                                                          ▼
                                                  authInterceptor(req, next)
                                                          │
                                       token = getApiToken()  (meta tag, cached once)
                                                          │
                                   ┌──── token empty? ────┴──── yes ──► next(req)  (unchanged)
                                   │ no
                                   ▼
                     isOwnApiRequest(req.url):
                       try parsed = new URL(req.url, location.origin)
                       catch ──────────────────────────────► false (fail closed, console.warn)
                       parsed.origin === location.origin
                         && parsed.pathname startsWith "/server/"
                                   │
                    true ──────────┴────────── false
                     │                           │
   next(req.clone(Authorization: Bearer))     next(req)  (no header)
                     │                           │
                     ▼                           ▼
   Bottle before_request Bearer check     api.github.com (gets 200 now, was 401)
```

### Recommended Project Structure (files touched)
```
src/angular/src/app/services/utils/auth.interceptor.ts            # add isOwnApiRequest gate
src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts  # case table + D-13 path moves
src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts  # OPTIONAL integration pin (see Pattern 2)
src/e2e/playwright.config.ts                                      # add chromium-token project; testIgnore it in chromium
src/e2e/tests/auth-token.spec.ts                                  # new token-configured E2E spec (name: Claude's choice)
```
No changes to `app.config.ts`, `rest.service.ts`, `version-check.service.ts`, `web_app.py`, Docker or compose files, the Makefile or CI.

### Pattern 1: Destination-gated functional interceptor (fail closed)
**What:** Parse the request URL against the page origin. Attach the token only when the origin matches exactly and the path is under `/server/`.
**When to use:** Any interceptor that attaches credentials [CITED: https://timdeschryver.dev/blog/watch-out-what-you-expose-with-angular-interceptors; https://ngtips.com/http/access-control].
```typescript
// Source: pattern per CONTEXT D-01..D-04; URL semantics verified via WHATWG URL probe (this session)
const OWN_API_PATH_PREFIX = "/server/";

/**
 * True only when `url` resolves to the origin the UI was loaded from AND its
 * path is under /server/. Fails closed: unparseable URLs return false.
 */
function isOwnApiRequest(url: string): boolean {
    const ownOrigin = window.location.origin;
    let parsed: URL;
    try {
        parsed = new URL(url, ownOrigin);
    } catch {
        // Fail closed (D-03): never attach the token to a URL we cannot parse.
        console.warn("authInterceptor: request URL could not be parsed; sending without app token");
        return false;
    }
    return parsed.origin === ownOrigin && parsed.pathname.startsWith(OWN_API_PATH_PREFIX);
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const token = getApiToken();
    if (token && isOwnApiRequest(req.url)) {
        return next(req.clone({setHeaders: {Authorization: `Bearer ${token}`}}));
    }
    return next(req);
};
```
Notes:
- Use `req.url`, not `urlWithParams`. Query params can't change origin or path.
- Keep `getApiToken()`, `cachedToken`, `tokenRead` and `_resetAuthInterceptorCache()` exactly as they are, so the caching and rotation specs keep their meaning.
- Update the JSDoc on `authInterceptor` ("attaches Bearer token to all outgoing requests" is now false).
- `parsed.origin` lowercases the host and drops default ports. `window.location.origin` is already normalized the same way, so `http://LOCALHOST:9876/server/x` matches and `http://localhost:80/...` (default port dropped) doesn't match `:9876`. Verified.

### Pattern 2 (optional, cheap): Pin the real update-check call end to end
`version-check.service.spec.ts` uses `MockRestService`, so it never goes through the interceptor. D-05 asks for a test "pinned to the real GitHub URL". The interceptor spec should use the literal URL `https://api.github.com/repos/thejuran/seedsyncarr/releases/latest`. For a stronger pin, add one spec that wires the real `RestService` + `provideHttpClient(withInterceptors([authInterceptor]))` + `provideHttpClientTesting()` + `VersionCheckService` (plus `LoggerService`, `NotificationService` or mocks). Then `httpMock.expectOne(req => req.url.startsWith("https://api.github.com/"))` and assert `!req.request.headers.has("Authorization")`. If anyone ever changes the service URL or adds a second external call, that test still guards it. Recommended, but planner's call on scope.

### Pattern 3: E2E token run as a dependent Playwright project
**What:** A second project runs only the token spec and starts after all no-token specs finish.
```typescript
// src/e2e/playwright.config.ts — Source: https://playwright.dev/docs/test-projects (dependencies, testMatch/testIgnore)
const TOKEN_SPEC = /auth-token\.spec\.ts/;
projects: [
  {
    name: 'chromium',
    testIgnore: TOKEN_SPEC,                 // existing no-token suite, unchanged otherwise
    use: { ...devices['Desktop Chrome'], launchOptions: { args: ['--no-sandbox', '--disable-dev-shm-usage'] } },
  },
  {
    name: 'chromium-token',
    testMatch: TOKEN_SPEC,
    dependencies: ['chromium'],             // runs strictly after; token stays set for the rest of the container's life
    use: { ...devices['Desktop Chrome'], launchOptions: { args: ['--no-sandbox', '--disable-dev-shm-usage'] } },
    // DO NOT set use.extraHTTPHeaders here — it would add Authorization to the GitHub request and mask the bug.
  },
],
```
Why this works:
- `general.api_token` is settable through `POST /server/config/set` (`ConfigHandler.__handle_set_config` → `inner_config.set_property`). `web_app.py` reads `self._config.general.api_token` live for both the Bearer check (line ~123) and `_inject_meta_tag` (line ~221), so it takes effect on the next request and page load with no restart [VERIFIED: code read].
- Send the setup call **with** `Authorization: Bearer <E2E_TOKEN>`. When no token is configured the server ignores the header, and when the same token is already set it passes. That makes setup idempotent across Playwright CI retries (`retries: 2`).
- `run_tests.sh` runs plain `npx playwright test`, which runs all projects. The E2E `Dockerfile` copies `src/e2e/tests` wholesale. Nothing else changes.
- Per the docs, if the `chromium` project has a hard failure, `chromium-token` is **skipped**. CI is already red in that case. A test that passes on retry counts as flaky, not failed, so the dependent project still runs [CITED: playwright.dev/docs/test-projects].

### Anti-Patterns to Avoid
- **String-prefix destination checks** (`url.startsWith("/server")`, `url.startsWith(location.origin)`): `location.origin + ".evil.com"` or `+ "@evil.com"` pass a prefix check. Rejected by D-02.
- **`HttpContext` opt-out token for the GitHub call:** allow-by-default with a per-call opt-out repeats the original bug for the next external call. Rejected by D-05.
- **`use.extraHTTPHeaders` in Playwright for the token project:** this injects headers at the browser network layer onto *every* request, including api.github.com, so the absence test passes or fails for the wrong reason.
- **Asserting absence with `request.headers()`:** Playwright documents that `headers()` omits "security-related headers". Use `await request.allHeaders()` [CITED: playwright.dev/docs/api/class-request].
- **Resetting the token in an `afterAll`:** impossible through the API. `config/set` rejects an empty value with 400 (`value is None or str(value) == ""`). Don't try. Rely on project ordering plus container teardown.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL origin/path parsing | Regex or `split("/")` host extraction | `new URL(url, location.origin)` | Backslash normalization, userinfo, IPv6, default ports, dot-segments: the browser's own parser decides where the request really goes |
| Same-origin comparison | Host-string compare | `parsed.origin === location.origin` | Origin includes scheme and port. Both sides are normalized the same way. |
| CORS preflight in E2E stub | Manually handling OPTIONS in `page.route` | Playwright's automatic preflight handling for routed requests + `Access-Control-Allow-Origin: *` on the fulfilled response | Route handlers don't see OPTIONS. Playwright answers them itself [CITED: github.com/microsoft/playwright/issues/2641, #3331, #37245] |
| Mock HTTP in unit tests | Spying on `HttpClient` | `HttpTestingController` (existing pattern) | Already used in this spec |

**Key insight:** A credential gate has to agree with the browser on where a request goes. Only the browser's own URL parser guarantees that.

## Runtime State Inventory

Not a rename or refactor phase. One related runtime fact for Phase 126: the **production NAS `api_token`** has been sent to api.github.com on every UI load since v1.0.0. Rotation happens in Phase 126 (D-09), after the 1.8.0 deploy. Phase 121 touches no runtime state. The E2E token is set only inside the throwaway `seedsyncarr_test_e2e_myapp` container, which is recreated every run (`up --force-recreate`, `rm -f myapp`, no volumes on `myapp` in `src/docker/stage/docker-image/compose.yml`) [VERIFIED: compose files read].

## Common Pitfalls

### Pitfall 1: Look-alike test that actually tests the "unparseable" branch
**What goes wrong:** `` `${location.origin}.evil.com/server/x` `` under Karma becomes `http://localhost:9876.evil.com/...`, which **throws** (invalid port), so the test passes via the catch, not the origin compare.
**How to avoid:** Build the look-alike from the hostname: `` `${location.protocol}//${location.hostname}.evil.example/server/x` `` → origin `http://localhost.evil.example`. Add a separate userinfo case: `` `${location.protocol}//${location.host}@evil.example/server/x` `` → origin `http://evil.example`. [VERIFIED: node WHATWG URL probe]
**Warning signs:** The `console.warn` from the catch fires during the look-alike test. Optionally `spyOn(console, "warn")` and assert it was *not* called for look-alike cases and *was* called for the unparseable case.

### Pitfall 2: Hardcoding the Karma origin
**What goes wrong:** Specs that hardcode `http://localhost:9876` break if the Karma port or host changes (CI Docker vs local).
**How to avoid:** Build every absolute same-origin URL from `location.origin` at runtime. Karma currently serves on `http://localhost:9876` (`port: 9876` in `karma.conf.js`; confirmed in local run log) [VERIFIED].

### Pitfall 3: Unparseable-URL test with HttpClient
`new URL(x, base)` rarely throws. Inputs that **do** throw: `"http://["` (bad IPv6) and `"//"` (empty host). I confirmed `httpClient.get("http://[")` + `httpMock.expectOne("http://[")` works under `HttpTestingController` without Angular throwing first [VERIFIED: throwaway probe spec run locally this session, then deleted]. Use `"http://["`.

### Pitfall 4: D-13 path moves done in the wrong commit
The caching and rotation specs use `/api/first` and `/api/second`. After the fix those get **no** token, so the specs would fail for the wrong reason. Move them to `/server/...` (e.g. `/server/config/get`, `/server/autoqueue/get`) in the **red** commit. They pass both before and after the fix, so the red commit's only failures are the new "no token" cases.

### Pitfall 5: False-pass header-absence E2E assertion
**What goes wrong:** The absence assertion passes because the capture missed the header, the request never happened, or the route didn't match.
**How to avoid:**
1. Register `page.route('https://api.github.com/**', ...)` **before** `page.goto`. The update check fires in an `APP_INITIALIZER` at bootstrap.
2. Await the GitHub request (store a promise or `page.waitForRequest`) so the test fails if it never fires.
3. Read headers with `await route.request().allHeaders()` and assert `authorization` (lower-cased) is `undefined`.
4. **Positive control:** in the same page, capture a `/server/config/get` (or `/server/autoqueue/get`) request with `page.waitForRequest` and assert `allHeaders()['authorization'] === 'Bearer <E2E_TOKEN>'`, and that its response is 200. This proves the capture mechanism sees the header and that the token is really configured.
5. Prove enforcement: `page.request.get('/server/config/get')` **without** a header returns 401. "Authenticated flows work" then means something.

### Pitfall 6: Token project leaking into the no-token suite
**What goes wrong:** With `api_token` set, every existing spec's raw `page.request.post('/server/config/set'...)` (seed-state, settings helpers, dashboard throttle restore) and the UI would hit 401.
**How to avoid:** `dependencies: ['chromium']` plus `testIgnore` on `chromium`, so the token spec runs strictly last. In `DEV=1` local runs `myapp` stays up after the run. Re-running the suite against it then needs a fresh container (re-run `make run-tests-e2e ... DEV=1`, which force-recreates). Document this in `src/e2e/README.md` or a spec header comment.

### Pitfall 7: Stubbed GitHub response blocked by CORS
The fulfilled response must include `Access-Control-Allow-Origin: *`, or the browser hides it from `HttpClient` and RestService logs a warning. The header assertion still works, but if the spec also asserts the "new version available" notification (an optional D-07 demonstration), the response must be readable. The request is not credentialed (`withCredentials` defaults to false), so `*` is valid. Body: `{"tag_name":"v99.0.0","html_url":"https://github.com/thejuran/seedsyncarr/releases/tag/v99.0.0"}`. `html_url` must match `^https://github\.com/` per `VersionCheckService` validation.

### Pitfall 8: Coverage and lint gates
- Karma `check.global` (statements 83, branches 68, functions 79, lines 83) is only enforced when run with `--code-coverage`. That's how CI runs it (`src/docker/test/angular/Dockerfile` CMD). The new branches (catch, origin mismatch, path mismatch) are all covered by the case table, so the risk is nil, but run the coverage command once before finishing.
- `npm run lint` uses `--max-warnings 0`. `explicit-function-return-type` is a warning, so it effectively fails lint. Give `isOwnApiRequest` an explicit `: boolean`. Use double quotes in Angular code. E2E code in `src/e2e` is not linted (it's single-quote style), but check it with `npx tsc --noEmit -p .`.

## Code Examples

### Karma case table (extend existing `auth.interceptor.spec.ts`; reuse `setupWithMeta`)
```typescript
// Source: existing spec pattern + URL semantics verified this session
const GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/thejuran/seedsyncarr/releases/latest";

function expectNoAuth(url: string): void {
    httpClient.get(url, {responseType: "text"}).subscribe();
    const req = httpMock.expectOne(url);
    expect(req.request.headers.has("Authorization")).toBeFalse();
    req.flush("ok");
}

// D-11 red-first anchor: FAILS on current interceptor ("Expected true to be false"), passes after fix
it("should NOT send the token to the GitHub update-check URL", () => {
    setupWithMeta("secret");
    expectNoAuth(GITHUB_LATEST_RELEASE_URL);
});
it("should send the token to an absolute same-origin /server/ URL", () => {
    setupWithMeta("secret");
    const url = `${location.origin}/server/config/get`;
    httpClient.get(url, {responseType: "text"}).subscribe();
    const req = httpMock.expectOne(url);
    expect(req.request.headers.get("Authorization")).toBe("Bearer secret");
    req.flush("ok");
});
it("other external host → no token",            () => { setupWithMeta("secret"); expectNoAuth("https://example.com/server/x"); });
it("protocol-relative //other-host → no token", () => { setupWithMeta("secret"); expectNoAuth("//evil.example/server/config/get"); });
it("backslash /\\other-host → no token",        () => { setupWithMeta("secret"); expectNoAuth("/\\evil.example/server/config/get"); });
it("look-alike host → no token", () => {
    setupWithMeta("secret");
    expectNoAuth(`${location.protocol}//${location.hostname}.evil.example/server/config/get`);
});
it("userinfo trick → no token", () => {
    setupWithMeta("secret");
    expectNoAuth(`${location.protocol}//${location.host}@evil.example/server/config/get`);
});
it("same-origin non-/server/ path → no token", () => { setupWithMeta("secret"); expectNoAuth("/dashboard"); });
it("dot-segment escape /server/../x → no token", () => { setupWithMeta("secret"); expectNoAuth("/server/../dashboard"); });
it("unparseable URL → no token (fail closed)", () => { setupWithMeta("secret"); expectNoAuth("http://["); });
```
(Exact `it` titles are the planner's choice. Keep them descriptive like the existing ones. Note `/server/../dashboard` passes today too because `HttpTestingController` keeps the raw string. That's fine, it pins the normalization behavior.)

Red-first expectation on the **current** interceptor: every "no token" case except the existing empty/missing-meta ones fails. The GitHub case is the named D-11 anchor.

### E2E token spec skeleton (`src/e2e/tests/auth-token.spec.ts`)
```typescript
// Source: Playwright docs — page.route / route.fulfill / request.allHeaders (playwright.dev/docs/api/class-route, class-request)
import { test, expect } from './fixtures/csp-listener';

const E2E_TOKEN = 'e2e-api-token-not-a-secret';
const AUTH = { Authorization: `Bearer ${E2E_TOKEN}` };

test.describe('API token configured (SEC-02)', () => {
  test.beforeEach(async ({ request }) => {
    // Idempotent: server ignores the header when no token is set; passes when already set (CI retries).
    const res = await request.post('/server/config/set', {
      headers: AUTH, data: { section: 'general', key: 'api_token', value: E2E_TOKEN },
    });
    expect(res.ok()).toBe(true);
  });

  test('token reaches /server/* but never api.github.com', async ({ page, request }) => {
    // Enforcement is real: no header → 401
    expect((await request.get('/server/config/get')).status()).toBe(401);

    let githubHeaders: Record<string, string> | undefined;
    await page.route('https://api.github.com/**', async (route) => {
      githubHeaders = await route.request().allHeaders();
      await route.fulfill({
        status: 200, contentType: 'application/json',
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ tag_name: 'v0.0.1', html_url: 'https://github.com/thejuran/seedsyncarr/releases/tag/v0.0.1' }),
      });
    });
    const githubReq = page.waitForRequest((r) => r.url().startsWith('https://api.github.com/'));
    const ownReq = page.waitForRequest((r) => new URL(r.url()).pathname.startsWith('/server/config/get'));

    await page.goto('/settings');   // settings page issues an authenticated /server/config/get

    const own = await ownReq;
    expect((await own.allHeaders())['authorization']).toBe(`Bearer ${E2E_TOKEN}`);   // positive control
    expect((await own.response())?.status()).toBe(200);

    await githubReq;
    expect(githubHeaders).toBeDefined();
    expect(githubHeaders?.['authorization']).toBeUndefined();                         // SEC-02
    await expect(page.locator('meta[name="api-token"]')).toHaveAttribute('content', E2E_TOKEN);
  });
});
```
`ConfigService.onConnected()` issues `GET /server/config/get` once the SSE stream connects. That happens on app load from any route, so waiting for that request after `page.goto('/settings')` (or `/`) is reliable [VERIFIED: config.service.ts lines 94-110]. Optionally add one authenticated UI action, such as adding and removing an autoqueue pattern, to show a write path works with the token.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Class-based `HttpInterceptor` + `HTTP_INTERCEPTORS` | Functional `HttpInterceptorFn` + `withInterceptors` | Angular 15+ | Already adopted here, no change |
| Attach token to all requests | Allow-list by destination (origin + path) | Community guidance (Deschryver; ngtips) | This phase |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Playwright auto-answers the CORS preflight for routed cross-origin requests, so a pre-fix (red) E2E run would still reach the route handler with `authorization` present | Pattern 3 / Pitfall 5 | Low. After the fix there is no `Authorization`, so no preflight at all (GET with a safelisted header). Only affects demonstrating red in E2E, which isn't required (D-11 red-first is the Karma test). Sourced from GitHub issues #2641/#3331/#37245, not the official docs page. |
| A3 | `window.location.origin` is the right "own origin" behind reverse proxies that rewrite paths to a sub-path | Pattern 1 | Low. D-04 locks this. The app already only works with `/server/` at the root of the origin (absolute paths, `<base href="/">`). |

## Open Questions (RESOLVED)

1. RESOLVED (adopted in 121-02: v99.0.0 stub + notice assertion; curl evidence in 121-03): **Should the token E2E also assert the "new version available" notification appears (D-07 demonstration)?**
   - What we know: with a readable stubbed response (`tag_name` newer than APP_VERSION and `Access-Control-Allow-Origin: *`), the notice should render after the fix.
   - Recommendation: optional. Valuable as visible proof of D-07 if cheap (a stub with `v99.0.0` plus a notification locator). Otherwise record D-07 from the curl evidence: GitHub returns 401 with a bogus Bearer and 200 without one.
2. RESOLVED (adopted in 121-02/121-03: PR CI is the E2E gate; local tsc + --list only): **Local E2E execution.** Docker is available locally (29.4.3), but `make run-tests-e2e` pulls `${STAGING_REGISTRY}:${STAGING_VERSION}` built by `make docker-image` (multi-arch buildx `--push`), which is heavy locally. Recommendation: the PR CI job `e2etests-docker-image` (amd64 on PRs) is the E2E gate. Locally, verify wiring with `npx playwright test --list` and `npx tsc --noEmit -p .` in `src/e2e`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | Angular tests, lint | ✓ | v25.9.0 (CI uses 22) | — |
| Google Chrome (local) | `ng test --browsers ChromeHeadless` | ✓ | 155 headless | `make run-tests-angular` (Docker) |
| Angular deps (`src/angular/node_modules`) | unit tests and lint | ✓ | — | `npm ci` |
| E2E deps (`src/e2e/node_modules`) | `--list`, tsc check | ✓ | Playwright 1.59.1 | — |
| Docker | `make run-tests-angular`, local E2E | ✓ | 29.4.3 | CI |
| GitHub Actions CI | Full E2E on built image | ✓ (gh 2.86.0) | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Karma 6.4.4 + Jasmine (Angular `@angular/build:karma`); Playwright 1.59.1 for E2E |
| Config file | `src/angular/karma.conf.js`, `src/angular/angular.json` (test target); `src/e2e/playwright.config.ts` |
| Quick run command | `cd src/angular && npx ng test --browsers ChromeHeadless --watch=false --include='**/auth.interceptor.spec.ts'` (~15 s locally, verified) |
| Full suite command | `cd src/angular && npx ng test --browsers ChromeHeadless --watch=false --code-coverage` (enforces `check.global`) **and** `cd src/angular && npm run lint`; CI-parity: `make run-tests-angular` |
| E2E local wiring check | `cd src/e2e && npx tsc --noEmit -p . && npx playwright test --list` (list shows the token spec under `[chromium-token]` only; verified both commands run today, 52 tests in 9 files) |
| E2E execution | CI job `e2etests-docker-image` on the PR (amd64), or `make run-tests-e2e STAGING_REGISTRY=… STAGING_VERSION=… SEEDSYNCARR_ARCH=…` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-02 (SC1) | `/server/*` relative and absolute same-origin get Bearer | unit | quick command above | ✅ extend `auth.interceptor.spec.ts` |
| SEC-02 (SC2) | GitHub URL, external host, protocol-relative, backslash, look-alike, userinfo, non-/server/, unparseable → no header | unit | quick command above | ✅ extend |
| SEC-02 (SC3) | GitHub-URL test red before fix, green after | unit (TDD red commit) | quick command; record failing output in the red commit/SUMMARY | ✅ extend |
| SEC-02 (SC1/SC2 real browser) | Token-configured UI works; api.github.com request has no `authorization` | E2E | CI `e2etests-docker-image`; local `npx playwright test --list` | ❌ Wave 0: `src/e2e/tests/auth-token.spec.ts` + config project |
| SEC-02 (SC4) | No auth redesign | static | `git diff --stat main -- src/python src/angular/src/app/app.config.ts src/angular/src/app/services/utils/rest.service.ts src/angular/src/app/services/utils/version-check.service.ts` is empty | n/a |
| (optional) D-05 pin | Real VersionCheckService → interceptor → no header | unit integration | quick command with `--include='**/version-check.service.spec.ts'` | ✅ extend (optional) |

### Sampling Rate
- **Per task commit:** quick command (interceptor spec) plus `npm run lint`
- **Per wave merge:** full Angular suite with `--code-coverage` and lint; E2E `--list` + `tsc`
- **Phase gate:** full Angular suite green with thresholds, lint clean, and the PR CI E2E job green (including `chromium-token`) before `/bm:verify-work`

### Wave 0 Gaps
- [ ] `src/e2e/tests/auth-token.spec.ts`: token-configured E2E (D-12)
- [ ] `src/e2e/playwright.config.ts`: `chromium-token` project with `dependencies: ['chromium']`, plus `testIgnore` on `chromium`
- No framework install needed.

### TDD Sequence (tdd_mode: true)
1. **RED commit:** add the D-10 case table plus D-13 path moves to `auth.interceptor.spec.ts`. Run the quick command. Expect failures on the GitHub-URL test (D-11 anchor) and the other no-token cases. Capture the output.
2. **GREEN commit:** add `isOwnApiRequest` to `auth.interceptor.ts` and update the JSDoc. Quick command all green, then full suite with coverage and lint.
3. **E2E commit:** add the config project and spec. Run the `tsc` + `--list` checks locally. CI runs it.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | Existing Bearer check in `web_app.py` |
| V3 Session Management | no | No sessions or cookies |
| V4 Access Control | no (unchanged) | — |
| V5 Input Validation | yes (URL handling) | WHATWG `URL` parse, fail closed |
| V6 Cryptography | no | — |
| V8 Data Protection / V14 Config (credential leakage to third parties) | **yes** | Destination allow-list in the interceptor; no logging of token or header |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential sent to third-party origin (CWE-201/CWE-522) | Information disclosure | Origin + path allow-list (this phase) |
| Origin confusion via `//host`, `\`, userinfo, look-alike subdomain | Spoofing / Info disclosure | Exact `URL.origin` equality, not prefix matching |
| Unparseable or odd URL bypass | Info disclosure | Fail closed (catch → no token) |
| Token in logs | Info disclosure | `console.warn` message must not include URL or token |

## Sources

### Primary (HIGH confidence)
- Codebase read: `auth.interceptor.ts`, `auth.interceptor.spec.ts`, `version-check.service.ts`, `rest.service.ts`, `app.config.ts`, `web_app.py`, `web/handler/config.py`, `serialize_config.py`, `karma.conf.js`, `angular.json`, `eslint.config.js`, `src/e2e/*`, `src/docker/test/{e2e,angular}/*`, `Makefile`, `.github/workflows/ci.yml`
- Local runs: interceptor spec (7/7 pass, Karma at localhost:9876); throwaway probe spec (unparseable URL through HttpTestingController); `npx playwright --version`/`--list`; `tsc --noEmit`
- Node WHATWG `URL` probe of all edge cases
- curl to api.github.com: bogus Bearer → 401, no header → 200; preflight allows `Authorization`
- https://playwright.dev/docs/test-projects: dependencies, testMatch/testIgnore, skipped-on-failure
- https://playwright.dev/docs/api/class-request: `headers()` omits security headers; `allHeaders()` complete

### Secondary (MEDIUM confidence)
- https://playwright.dev/docs/api/class-route: `fulfill` headers
- https://timdeschryver.dev/blog/watch-out-what-you-expose-with-angular-interceptors and https://ngtips.com/http/access-control (from CONTEXT canonical refs)

### Tertiary (LOW confidence)
- [microsoft/playwright #2641](https://github.com/microsoft/playwright/issues/2641), [#3331](https://github.com/microsoft/playwright/issues/3331), [#37245](https://github.com/microsoft/playwright/issues/37245), [#12929](https://github.com/microsoft/playwright/issues/12929): automatic preflight handling for routed requests, CORS headers on fulfilled responses

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new dependencies; versions read from lockfiles and local runs.
- Architecture: HIGH. Single-file interceptor change, URL semantics verified by execution.
- E2E wiring: HIGH for config, runtime token setting and project dependencies (code read + official docs). MEDIUM only for the red-state preflight behavior (A1), which isn't on the critical path.
- Pitfalls: HIGH. Look-alike/port trap and unparseable-URL handling verified by execution.

**Research date:** 2026-10-21
**Valid until:** 2026-11-20 (stable domain)
