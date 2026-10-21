# Phase 121: Credential Forwarding - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The configured app token (`api_token`) is attached only to SeedSyncarr's own API requests (`/server/*` on the origin the UI was loaded from) and never to any other destination, including the GitHub update check. Requirement: SEC-02.

Out of scope (roadmap planning boundary): no authentication redesign. The token source (`<meta name="api-token">`), the interceptor mechanism (`authInterceptor` registered via `withInterceptors`) and the server-side Bearer check in `web_app.py` stay unchanged. No new token-rotation UI.

</domain>

<decisions>
## Implementation Decisions

### Which requests get the token
- **D-01:** Attach the token only when the request resolves to the **same origin as the loaded UI** (`location.origin`) **and** its path is under `/server/`. Everything else, including same-origin non-`/server/` paths, gets no `Authorization` header.
- **D-02:** Determine the destination by **parsing the URL** (resolve relative URLs against `location.origin`, then compare the exact origin and check the pathname). Do not use string-prefix checks. They let `//evil.com/server/x` through and are confused by look-alike hosts such as `https://host.evil.com`.
- **D-03:** Fail closed. If the URL can't be parsed, or the resolved origin or path doesn't match, the request goes out with no token. A missed token shows up as a 401; a leaked token is silent.
- **D-04:** "Own origin" is whatever address the browser loaded SeedSyncarr from. No new setting; this works behind a reverse proxy and under any hostname (`<base href="/">`, and all API calls use relative `/server/...` URLs).

### Update check hardening
- **D-05:** The rule fix alone protects the GitHub update check. No separate token-free HTTP path or `HttpBackend` bypass for `VersionCheckService`. One mechanism, guarded by a regression test pinned to the real GitHub URL.
- **D-06:** Leave the update request's credentials/cookie mode as is. The app doesn't use cookie auth, and browsers don't send its cookies cross-origin to GitHub.
- **D-07:** Expected side effect, to verify and record: GitHub's API returns 401 to an unrecognized Bearer token, so for users with a token configured the "new version available" notice has likely never worked. After the fix it should start working. Note this in the summary and in the 1.8.0 release notes.

### Existing users' exposed token (feeds Phase 126 release notes and deploy)
- **D-08:** The 1.8.0 release notes disclose the exposure factually: since v1.0.0, a configured API token was sent in an `Authorization` header to `api.github.com` (HTTPS) on each UI page load; GitHub rejected it; no other destination received it. Present rotation as **optional**, recommended mainly for instances reachable beyond the user's LAN, with steps: edit `api_token` in `settings.cfg`, then restart.
- **D-09:** Phase 126 production deploy adds a step: after 1.8.0 is live on the NAS, rotate the production `api_token`, then confirm the UI loads, authenticated calls succeed and a scan completes. Deploy first, then rotate, so the new token never reaches GitHub. Before rotating, the planner/executor for 126 checks whether anything else on the NAS uses the current token.
- Phase 121 itself does not write the release notes or touch the NAS. D-08 and D-09 are carried forward to Phase 126.

### How we prove it
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

</decisions>

<specifics>
## Specific Ideas

- The fix must hold in a real browser with a token configured, not only in unit tests (owner chose the E2E addition).
- Disclosure tone: factual and calm. Rotation is optional, not alarmist.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement and scope
- `.planning/REQUIREMENTS.md`: SEC-02 and the Out of Scope table ("Authentication redesign: SEC-02 only restricts where the existing token is attached")
- `.planning/ROADMAP.md` § "Phase 121: Credential Forwarding": success criteria 1–4 and the milestone CI gate (Angular unit tests and Karma `check.global` thresholds when Angular code is touched)

### Code under change
- `src/angular/src/app/services/utils/auth.interceptor.ts`: the interceptor; currently attaches the token to every request
- `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts`: existing interceptor specs to extend or adjust
- `src/angular/src/app/services/utils/version-check.service.ts`: GitHub update check (`https://api.github.com/repos/thejuran/seedsyncarr/releases/latest`)
- `src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts`: existing version-check specs
- `src/angular/src/app/app.config.ts`: interceptor registration (`provideHttpClient(withInterceptors([authInterceptor]))`); unchanged
- `src/python/web/web_app.py`: server-side Bearer check and meta-tag injection; must remain unchanged

### E2E
- `src/e2e/playwright.config.ts`, `src/e2e/tests/`, `src/e2e/urls.ts`, `src/e2e/README.md`: Playwright suite to extend with a token-configured run

### Background
- Tim Deschryver, "Watch out what you expose with Angular Interceptors" (https://timdeschryver.dev/blog/watch-out-what-you-expose-with-angular-interceptors): interceptors leak Authorization headers to third-party APIs
- https://ngtips.com/http/access-control: destination-gated token attachment pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RestService.sendRequest(url)` (`src/angular/src/app/services/utils/rest.service.ts`): the shared request path for config, autoqueue, Sonarr/Radarr test and version check. All app calls use relative `/server/...` URLs; the version check is the only absolute external URL.
- `_resetAuthInterceptorCache()`: test hook already used by the specs; keep it.

### Established Patterns
- Functional `HttpInterceptorFn` with a module-level cached token, read once from the meta tag.
- Specs use `provideHttpClient(withInterceptors([authInterceptor]))` with `HttpTestingController` and the `setupWithMeta()` helper. New cases should follow this.
- Server auth exempts certain paths and prefixes (`_AUTH_EXEMPT_PATHS` and `_AUTH_EXEMPT_PREFIXES` in `web_app.py`), and with no token configured all requests are allowed. Neither changes.
- The live model stream uses `EventSource` (`stream-service.registry.ts`), which never passes through the HTTP interceptor. It is unaffected by this phase.

### Integration Points
- The only behavior change is inside `authInterceptor`. No caller changes are expected.
- The E2E harness currently runs with no API token. The token run needs the app container's `settings.cfg` `api_token` set for that run only.

</code_context>

<deferred>
## Deferred Ideas

- Token rotation UI (regenerate token from Settings): a new capability, not in this phase or milestone. Rotation stays a `settings.cfg` edit plus restart.
- Release-note text and NAS token rotation are decided here (D-08, D-09) but executed in Phase 126.

</deferred>

---

*Phase: 121-credential-forwarding*
*Context gathered: 2026-10-21*
