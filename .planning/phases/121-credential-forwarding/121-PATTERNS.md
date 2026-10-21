# Phase 121: Credential Forwarding - Pattern Map

**Mapped:** 2026-10-21
**Files analyzed:** 6 (4 modified, 1 new, 1 optional modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/angular/src/app/services/utils/auth.interceptor.ts` (modify) | middleware (HttpInterceptorFn) | request-response | itself (lines 1-42) | exact (in-place edit) |
| `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` (modify) | test (Karma/Jasmine) | request-response | itself (`setupWithMeta` + `HttpTestingController`, lines 7-156) | exact |
| `src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts` (OPTIONAL modify, D-05 pin) | test (integration) | request-response | `src/angular/src/app/tests/unittests/services/utils/rest.service.spec.ts` (real RestService + HttpTestingController) + interceptor spec providers | role-match |
| `src/e2e/playwright.config.ts` (modify) | config | n/a | itself (`projects` array, lines 24-34) | exact |
| `src/e2e/tests/auth-token.spec.ts` (NEW) | test (Playwright E2E) | request-response | `src/e2e/tests/csp-canary.spec.ts` (fixture import, small spec) + `src/e2e/tests/dashboard.page.spec.ts` lines 277-313 (raw `config/set` call) | role-match |
| `src/e2e/README.md` (modify, Pitfall 6 note) | docs | n/a | itself (`### About` / Notes list, lines 37-53) | exact |

Must remain unchanged (SC4): `app.config.ts`, `rest.service.ts`, `version-check.service.ts`, all of `src/python/`, Docker/compose, Makefile, CI.

## Pattern Assignments

### `src/angular/src/app/services/utils/auth.interceptor.ts` (middleware, request-response)

**Analog:** current file. Keep lines 1-17 and 35-42 verbatim (cache + `_resetAuthInterceptorCache`); change only lines 19-33.

**Imports** (line 1), unchanged:
```typescript
import {HttpInterceptorFn} from "@angular/common/http";
```

**Module-level helper style to copy** (lines 10-17): plain `function` with explicit return type, double quotes, 4-space indent, no class:
```typescript
function getApiToken(): string {
    if (!tokenRead) {
        const meta = document.querySelector("meta[name=\"api-token\"]");
        cachedToken = meta?.getAttribute("content") || "";
        tokenRead = true;
    }
    return cachedToken || "";
}
```
New `isOwnApiRequest(url: string): boolean` goes directly below this, same shape (JSDoc block, explicit `: boolean`). Body per RESEARCH Pattern 1: `new URL(url, window.location.origin)` in try/catch, `parsed.origin === ownOrigin && parsed.pathname.startsWith("/server/")`.

**Code being replaced** (lines 19-33). The JSDoc "attaches Bearer token to all outgoing requests" must be rewritten (now false):
```typescript
/**
 * Functional HTTP interceptor that attaches Bearer token to all outgoing requests.
 * ...
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const token = getApiToken();
    if (token) {
        const authReq = req.clone({
            setHeaders: {Authorization: `Bearer ${token}`}
        });
        return next(authReq);
    }
    return next(req);
};
```
Change: condition becomes `if (token && isOwnApiRequest(req.url))`. Keep the `req.clone({setHeaders: ...})` form. Use `req.url`, not `urlWithParams`.

**Error handling / logging convention:** direct `console.warn` with a generic string is precedent in app code, `src/angular/src/app/pages/files/dashboard-log-pane.component.ts:79`:
```typescript
console.warn("Failed to copy logs to clipboard:", err);
```
For the interceptor catch, use a message only (no URL, no token, no err object carrying the URL), e.g. `console.warn("authInterceptor: request URL could not be parsed; sending without app token");`. Do NOT inject `LoggerService` (functional interceptor has no DI today; keep it that way).

---

### `src/angular/src/app/tests/unittests/services/utils/auth.interceptor.spec.ts` (test)

**Analog:** current file.

**Imports** (lines 1-5), unchanged:
```typescript
import {TestBed} from "@angular/core/testing";
import {HttpClient, provideHttpClient, withInterceptors} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import {authInterceptor, _resetAuthInterceptorCache} from "../../../../services/utils/auth.interceptor";
```

**Setup helper to reuse** (lines 11-38, `setupWithMeta(content: string | null): void`) and teardown (lines 40-48, `httpMock.verify()` + meta removal + cache reset). New cases call `setupWithMeta("secret")` first, exactly like existing tests.

**Positive-case shape to copy** (lines 50-58):
```typescript
it("should add Authorization header when token is present", () => {
    setupWithMeta("my-secret-token");

    httpClient.get("/server/config/get", {responseType: "text"}).subscribe();

    const req = httpMock.expectOne("/server/config/get");
    expect(req.request.headers.get("Authorization")).toBe("Bearer my-secret-token");
    req.flush("ok");
});
```

**Negative-case shape to copy** (lines 60-68): `expect(req.request.headers.has("Authorization")).toBeFalse();`. A local `expectNoAuth(url: string): void` helper inside the `describe` (next to `setupWithMeta`) is consistent with the file's helper style; give it an explicit `: void`.

**D-13 path moves (do in RED commit):**
- Lines 98-99, 110-111 (`"should cache the token..."`): `/api/first` -> e.g. `/server/config/get`, `/api/second` -> e.g. `/server/autoqueue/get`.
- Lines 127-128, 142-143 (`"...token rotation"`): same replacement. Keep the long "Production coupling note" comment block (lines 117-122) intact.

**New cases** (append after line 156, before closing `});`): full table in RESEARCH "Karma case table". Key constraints:
- GitHub case uses the literal `"https://api.github.com/repos/thejuran/seedsyncarr/releases/latest"` (matches `version-check.service.ts:23-24`); this is the D-11 red-first anchor.
- Absolute same-origin and look-alike URLs built from `location.origin` / `location.hostname` / `location.host` at runtime, never hardcoded `localhost:9876` (Pitfalls 1, 2).
- Unparseable case uses `"http://["` (Pitfall 3).
- Optional: `spyOn(console, "warn")` to prove look-alike cases hit the origin compare, not the catch.

---

### `src/angular/src/app/tests/unittests/services/utils/version-check.service.spec.ts` (OPTIONAL, D-05 integration pin)

**Analog:** `src/angular/src/app/tests/unittests/services/utils/rest.service.spec.ts` lines 1-27 (real `RestService` over `HttpTestingController`):
```typescript
import {fakeAsync, TestBed} from "@angular/core/testing";
import {provideHttpClient} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

import {LoggerService} from "../../../../services/utils/logger.service";
import {RestService} from "../../../../services/utils/rest.service";
...
        TestBed.configureTestingModule({
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                RestService,
                LoggerService,
            ]
        });
        httpMock = TestBed.inject(HttpTestingController);
```
Combine with: `provideHttpClient(withInterceptors([authInterceptor]))` (from interceptor spec line 31), the existing providers from `version-check.service.spec.ts` lines 19-26 (`VersionCheckService`, `LoggerService`, `NotificationService`) but with the REAL `RestService` instead of `{provide: RestService, useClass: MockRestService}`, plus the meta tag + `_resetAuthInterceptorCache()` setup/teardown from the interceptor spec. The existing top-level `describe` uses `MockRestService` in `beforeEach`, so this must be a **separate `describe` block** (own `beforeEach`/`afterEach`), not a new `it` inside the existing one. Assert with `httpMock.expectOne(req => req.url.startsWith("https://api.github.com/"))` then `expect(req.request.headers.has("Authorization")).toBeFalse()`.

Existing URL pin to keep untouched (lines 50-54):
```typescript
it("should request the correct github url", fakeAsync(() => {
    expect(restService.sendRequest).toHaveBeenCalledWith(
        "https://api.github.com/repos/thejuran/seedsyncarr/releases/latest"
    );
}));
```

---

### `src/e2e/playwright.config.ts` (config)

**Analog:** current file, `projects` array lines 24-34:
```typescript
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--no-sandbox', '--disable-dev-shm-usage']
        }
      },
    },
  ],
```
Change: add `testIgnore: TOKEN_SPEC` to `chromium`; append a `chromium-token` project with `testMatch: TOKEN_SPEC`, `dependencies: ['chromium']`, identical `use` block. Declare `const TOKEN_SPEC = /auth-token\.spec\.ts/;` above `defineConfig`. Do NOT add `extraHTTPHeaders`. Style: single quotes, 2-space indent (this file's local style differs from Angular's 4-space/double quotes). Top-level `testMatch: '**/*.spec.ts'` (line 9), `workers: 1`, `retries` stay as-is.

---

### `src/e2e/tests/auth-token.spec.ts` (NEW, Playwright E2E)

**Analog A, fixture import + compact spec:** `src/e2e/tests/csp-canary.spec.ts` lines 1-25:
```typescript
import { test, expect } from './fixtures/csp-listener';

test.describe('CSP violation canary', () => {
    test('Loading a script from a disallowed origin fires a CSP violation', async ({ page, cspViolations }) => {
        ...
        await page.goto('/');

        await expect.poll(() => cspViolations.length).toBeGreaterThan(0);
```
Import from `./fixtures/csp-listener` (not `@playwright/test`), so the CSP-violation assertion in the fixture teardown (`csp-listener.ts` lines 63-67) also covers the token run. The stubbed GitHub fetch is `connect-src`; if CSP blocks api.github.com the fixture will flag it, which is the correct signal.

**Analog B, raw `config/set` with ok-check:** `src/e2e/tests/dashboard.page.spec.ts` lines 277-280:
```typescript
const throttleResp = await page.request.post('/server/config/set', {
    data: { section: 'lftp', key: 'rate_limit', value: '100' }
});
if (!throttleResp.ok()) throw new Error(`rate_limit set failed: ${throttleResp.status()}`);
```
And `src/e2e/tests/settings.page.ts` lines 14-22 (same shape with `throw new Error(\`... ${response.status()} ${response.statusText()}\`)`). For the token spec add `headers: { Authorization: \`Bearer ${E2E_TOKEN}\` }` so setup is idempotent across CI retries (RESEARCH Pattern 3). No afterAll reset (config/set rejects empty value).

**Analog C, synthetic-secret comment convention:** `src/e2e/tests/settings-error.spec.ts` lines 22-23:
```typescript
// NOTE: value appears in access logs — use synthetic strings only
await settingsPage.setSonarrApiKey('test-FAKE-not-real-0000');
```
Name the token constant obviously fake (`'e2e-api-token-not-a-secret'`) with a similar note.

**Core pattern:** no existing spec uses `page.route` / `allHeaders` / `waitForRequest`; use the RESEARCH "E2E token spec skeleton" (register `page.route('https://api.github.com/**', ...)` before `page.goto`, fulfill with `Access-Control-Allow-Origin: *`, `allHeaders()` absence check, positive control on `/server/config/get` with `Bearer` + 200, unauthenticated `request.get('/server/config/get')` -> 401). Use `Paths` from `../urls` for navigation if going to `/settings` (as `settings.page.ts` line 11 does). Indentation: existing specs use 4 spaces with single quotes.

---

### `src/e2e/README.md` (docs)

**Analog:** current Notes list, lines 47-53:
```markdown
Notes:
1. In dev mode, the app is visible at [http://localhost:8800](http://localhost:8800)
...
2. The app requires a fully configured settings.cfg.
   This is done automatically in during the start of the docker image that runs the app.
```
Append note 3: the `chromium-token` project runs last and leaves `api_token` set on `myapp`; in `DEV=1` re-runs, recreate the container first. (Alternatively a header comment in the spec; RESEARCH Pitfall 6 allows either.)

## Shared Patterns

### Angular code style (lint `--max-warnings 0`)
**Source:** `auth.interceptor.ts`, `auth.interceptor.spec.ts`
**Apply to:** all `src/angular` edits
- Double quotes, 4-space indent, `{Named}` imports without inner spaces, explicit return types on every function (`: void`, `: boolean`, `: string`).
- Relative spec imports `"../../../../services/utils/..."`.

### Test isolation for module-level token cache
**Source:** `auth.interceptor.spec.ts` lines 26-27 and 40-48
**Apply to:** interceptor spec and the optional version-check integration describe
```typescript
_resetAuthInterceptorCache();
...
afterEach(() => {
    httpMock.verify();
    const meta = document.querySelector("meta[name=\"api-token\"]");
    if (meta) {
        meta.remove();
    }
    _resetAuthInterceptorCache();
});
```

### No secret logging
**Apply to:** interceptor catch path and E2E spec. Never log token, `Authorization` header, or request URL in the warn message. E2E token is a named fake fixture.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/e2e/tests/auth-token.spec.ts` (network-interception portion only) | test | request-response | No existing spec uses `page.route`, `route.fulfill`, `request.allHeaders()` or `page.waitForRequest`; use RESEARCH Code Examples skeleton and Pitfalls 5 and 7 |
| `src/e2e/playwright.config.ts` (`dependencies`/`testMatch` per project) | config | n/a | Single-project config today; use RESEARCH Pattern 3 |

## Conventions

Derived via `gsd-tools verify conventions --derive --scope src/angular/src/app`:

| Axis | Dominant | Share | Entropy | Status |
|------|----------|-------|---------|--------|
| File-name casing | other (dotted kebab, e.g. `auth.interceptor.ts`) | 77% | 0.63 | named contract |
| Identifier casing | PascalCase (exported types/classes) | 87% | 0.39 | named contract |
| Export style | ESM `export` | 100% | 0.00 | named contract |
| Import style | ESM `import` | 98% | 0.13 | named contract |

**Contested hotspots (author's choice):** none in the Angular scope. Repo-wide, the CJS<->SDK dual resolver split (`bin/lib/**` CJS `module.exports`/`require` vs `sdk/src/**` ESM) is the prototype intentional-contested pattern; match the directory's local style. Same principle here for quoting: `src/angular` uses double quotes / 4 spaces, `src/e2e` uses single quotes (config at 2 spaces, specs at 4 spaces). New file names follow `<name>.spec.ts` (kebab + dotted suffix).

## Metadata

**Analog search scope:** `src/angular/src/app/services/utils/`, `src/angular/src/app/tests/unittests/services/utils/`, `src/angular/src/app/pages/`, `src/e2e/` (config, tests, fixtures, README)
**Files scanned:** 12
**Pattern extraction date:** 2026-10-21
