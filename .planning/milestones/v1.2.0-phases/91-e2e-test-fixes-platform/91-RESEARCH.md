# Phase 91: E2E Test Fixes & Platform - Research

**Researched:** 2026-04-27
**Domain:** Playwright E2E testing — API correctness, CSP enforcement, cross-platform Unicode sorting
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — user elected to skip discussion. All implementation decisions are at Claude's discretion.

### Claude's Discretion

All nine sub-fixes are fully specified in REQUIREMENTS.md. Claude decides implementation detail for:

- **D-01:** innerHTML→innerText fix for E2EFIX-01
- **D-02:** beforeEach ordering for E2EFIX-02 — API calls before navigateTo
- **D-03:** waitForTimeout replacement for E2EFIX-03
- **D-04:** CSP fixture bypass for E2EFIX-04 — beforeAll seed helpers use raw browser.newContext()
- **D-05:** :has-text() migration for E2EFIX-05
- **D-06:** HTTP response checking for E2EFIX-06 — rate-limit config GET calls lack assertions
- **D-07:** _escapeRegex deduplication for E2EFIX-07
- **D-08:** CSP enforcement scope for PLAT-01
- **D-09:** arm64 Unicode sort for PLAT-02

### Deferred Ideas (OUT OF SCOPE)
- Migrate /server/config/set to POST-body (API-01)
- Tighten Semgrep rules (Phase 96 TOOL-01/TOOL-02)
- Rate limiting (Phase 96 RATE-01 through RATE-04)
- webob/cgi upstream (blocked on upstream)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| E2EFIX-01 | Fix `innerHTML()` vs `innerText()` in autoqueue page object | `autoqueue.page.ts:28` confirmed uses `elm.innerHTML()`. Fix: `elm.innerText()`. App class uses `innerText()` as model. |
| E2EFIX-02 | Fix `beforeEach` calling API before `navigateTo()` in `settings-error.spec.ts` | Confirmed: `disableSonarr()` (API call) fires before `navigateTo()`. The page's `request` context works without navigation, but `disableSonarr()` uses `this.page.request` which is separate from the browser page — ordering is mostly fine but navigation-first is the correct pattern. |
| E2EFIX-03 | Replace `waitForTimeout(500)` with proper Playwright wait | `dashboard.page.spec.ts:255` confirmed. A stop command is issued; need to wait for state propagation. Replace with polling via `expect.poll()` or `page.locator(...).waitFor()` for a state change. |
| E2EFIX-04 | Fix `beforeAll` seed context bypassing CSP fixture | Two `beforeAll` blocks at lines 121 and 375 create `browser.newContext()` + raw page. These bypass the `csp-listener` fixture's `exposeFunction` + `addInitScript`. Fix: use `page.request.newContext()` for API-only seeds, OR apply CSP setup manually to the raw page. |
| E2EFIX-05 | Replace deprecated `:has-text()` pseudo-class with `locator.filter({ hasText })` | `autoqueue.page.ts:35` confirmed uses `:has-text()`. Pattern already used at `dashboard.page.ts:55,82`. Fix is one line. |
| E2EFIX-06 | Add HTTP response checking for rate-limit config calls in dashboard spec | `dashboard.page.spec.ts:272` (`rate_limit/100`) and `302` (`rate_limit/0`) use `page.request.get()` with no response assertion. Add `expect(response).toBeOK()` or throw on failure. |
| E2EFIX-07 | Deduplicate `_escapeRegex` helper | `_escapeRegex` lives as private method in `dashboard.page.ts:168` AND as module-private `escapeRegex` in `fixtures/seed-state.ts:44`. Extract to shared `tests/helpers.ts`. |
| PLAT-01 | Add CSP violation detection that fails tests | CSP listener fixture fully implemented. All 7 spec files already import from it. The gap is `beforeAll` raw contexts that bypass the fixture. |
| PLAT-02 | Fix arm64 Unicode sort order failures in dashboard E2E specs | "should have a list of files" test at `dashboard.page.spec.ts:40-41` already has sort-agnostic `byName` comparison. Remaining gap: no `locale` set in `playwright.config.ts`, so Chromium uses system ICU on arm64. Fix: add `locale: 'en-US'` to `playwright.config.ts` `use` block. |
</phase_requirements>

---

## Summary

Phase 91 fixes 7 E2E test quality defects and 2 cross-platform infrastructure issues in the SeedSyncarr Playwright suite. The codebase is a mature, well-structured Playwright suite (7 spec files, 37 specs) using the Page Object Model and a custom CSP listener fixture. All spec files already import from the CSP fixture — no spec-level import changes are needed.

The 9 fixes divide into three tiers: (1) single-line mechanical fixes (innerHTML→innerText, :has-text() migration, HTTP response assertion additions), (2) ordering and structural fixes (beforeEach navigation ordering, waitForTimeout replacement), and (3) infrastructure fixes (CSP fixture bypass in beforeAll contexts, arm64 locale, _escapeRegex extraction).

The most nuanced fix is PLAT-01/E2EFIX-04: the two `test.beforeAll` blocks in `dashboard.page.spec.ts` create raw browser contexts via `browser.newContext()` that bypass the CSP fixture's page override. These contexts load the app during seed setup, meaning any CSP violation during that load goes undetected. The correct fix is to use `page.request.newContext()` for the HTTP API seed calls (avoiding a full browser page), OR to extract a helper that applies the CSP setup to any raw page.

**Primary recommendation:** Implement all 9 fixes as targeted one-to-three line edits in the affected files. Extract `escapeRegex` to `tests/helpers.ts`. Add `locale: 'en-US'` to `playwright.config.ts`. For beforeAll CSP bypass, use `request.newContext()` (API-only contexts) or accept the limitation with a code comment explaining why beforeAll contexts cannot use the fixture.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| E2E test execution | Test runner (Playwright) | Docker Compose stack | Tests run inside Docker on `http://myapp:8800` |
| Page Object Model | Test layer (TypeScript) | — | Page objects wrap browser interactions |
| CSP enforcement | Browser (Chromium) | Test fixture (csp-listener.ts) | Browser fires `securitypolicyviolation` events; fixture captures them |
| Seed state setup | HTTP API layer | Browser page (for badge polling) | `seedMultiple` uses `page.request.*` for commands + `page.locator()` for status polling |
| Unicode sort | Angular app (ICU/localeCompare) | Playwright locale config | App sorts via `localeCompare`; Playwright locale controls which ICU data Chromium uses |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @playwright/test | 1.59.1 | E2E test framework | Already installed [VERIFIED: npm registry + local node_modules] |
| TypeScript | 5.3.x | Type-safe test authoring | Already in use throughout suite [VERIFIED: local package.json] |

### No new dependencies required
All 9 fixes are modifications to existing TypeScript files. No new npm packages needed.

**Version verification:** `@playwright/test@1.59.1` is the current latest on npm registry. [VERIFIED: `npm view @playwright/test version` = 1.59.1]

---

## Architecture Patterns

### System Architecture Diagram

```
Test Spec (.spec.ts)
        |
        | imports {test, expect}
        v
CSP Listener Fixture (fixtures/csp-listener.ts)
        |                           |
        | wraps `page`              | extends base.extend<Fixtures>
        v                           v
Playwright `page` object       cspViolations[]
        |                           ^
        | page.exposeFunction()     | securitypolicyviolation events
        | page.addInitScript()      | + console CSP errors
        v                           |
Chromium Browser <-----------------+
        |
        | HTTP requests to
        v
myapp:8800 (Docker Compose)
        |
        | SSE + JSON API
        v
Angular Frontend + Python Backend
```

**beforeAll seed bypass gap (E2EFIX-04/PLAT-01):**

```
test.beforeAll({ browser }) ──► browser.newContext()
                                          |
                                          | RAW context — no CSP setup
                                          v
                                    ctx.newPage()  ──► myapp:8800
                                          |               (unmonitored)
                                          v
                                    seedMultiple(page, [...])
                                    [page.request.* + page.locator()]
```

### Recommended Project Structure
```
src/e2e/tests/
├── fixtures/
│   ├── csp-listener.ts      # CSP violation fixture (already exists)
│   ├── seed-state.ts        # State seeding helpers (already exists)
│   └── helpers.ts           # NEW: shared escapeRegex + other pure utils (E2EFIX-07)
├── app.ts                   # Base App class (innerText pattern model)
├── autoqueue.page.ts        # AutoQueue page object (E2EFIX-01, E2EFIX-05)
├── dashboard.page.ts        # Dashboard page object (E2EFIX-07)
├── dashboard.page.spec.ts   # Dashboard specs (E2EFIX-03, E2EFIX-04, E2EFIX-06, PLAT-02)
├── settings-error.spec.ts   # Settings error specs (E2EFIX-02)
└── settings.page.ts         # Settings page object (reference for response-checking pattern)
playwright.config.ts         # PLAT-02: add locale: 'en-US'
```

### Pattern 1: innerText() for text content assertions
**What:** Use `elm.innerText()` not `elm.innerHTML()` for text content — innerText returns rendered text, innerHTML returns raw HTML markup.
**When to use:** Any time you need visible text content from an element.
**Example:**
```typescript
// Source: https://playwright.dev/docs/api/class-locator#locator-inner-text
// BEFORE (E2EFIX-01 bug):
return Promise.all(elements.map(elm => elm.innerHTML()));

// AFTER:
return Promise.all(elements.map(elm => elm.innerText()));
```

### Pattern 2: locator.filter({ hasText }) replacing :has-text()
**What:** The CSS pseudo-class `:has-text()` is Playwright-proprietary and deprecated. Replace with `.filter({ hasText: text })` on the locator.
**When to use:** Any `locator(':has-text("…")')` or `locator('.class:has-text("…")')`.
**Example:**
```typescript
// Source: https://playwright.dev/docs/locators#filter-by-text
// BEFORE (E2EFIX-05 bug — autoqueue.page.ts:35):
await this.page.locator(`.pattern-section .pattern-chip-text:has-text("${pattern}")`).waitFor({ state: 'visible' });

// AFTER:
await this.page.locator('.pattern-section .pattern-chip-text')
    .filter({ hasText: pattern })
    .waitFor({ state: 'visible' });
```

### Pattern 3: Replacing waitForTimeout with explicit wait
**What:** `page.waitForTimeout()` is a fixed sleep — flaky and slow. Replace with condition-based waiting.
**When to use:** Any `waitForTimeout()` call.
**Example:**
```typescript
// Source: https://playwright.dev/docs/best-practices#avoid-using-pagewaitfortimeout
// BEFORE (E2EFIX-03 bug — dashboard.page.spec.ts:255):
await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
await page.waitForTimeout(500);  // waiting for stop to propagate

// AFTER (option A — wait for state visible in UI):
await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
// No wait needed: stop is a no-op if file not QUEUED/DOWNLOADING.
// The subsequent Queue enablement check provides implicit synchronization.

// AFTER (option B — if state propagation is needed):
await expect.poll(async () => {
    // some observable condition
}).toBeTruthy();
```

**Research finding:** The `waitForTimeout(500)` at line 255 follows a deliberately ignored stop command (the comment says "Ignore non-OK responses — stop is a no-op if file not QUEUED/DOWNLOADING"). The wait is the only thing ensuring stop has propagated before Queue becomes enabled. The correct replacement is to either (a) remove the wait entirely because the Queue enablement check via `getActionButton('Queue').toBeEnabled()` at line 277 provides sufficient synchronization via Playwright auto-wait, or (b) use `expect.poll()` if explicit propagation confirmation is needed. [VERIFIED: Playwright auto-waiting waits for actions to be actionable before assertion]

### Pattern 4: HTTP response assertion
**What:** Assert `page.request.get/post` results are OK before proceeding.
**When to use:** Any fire-and-check API call where failure should abort the test.
**Example:**
```typescript
// Source: https://playwright.dev/docs/api/class-apiresponseassertions#api-response-assertions-to-be-ok
// BEFORE (E2EFIX-06 bug — dashboard.page.spec.ts:272,302):
await page.request.get('/server/config/set/lftp/rate_limit/100');

// AFTER:
const resp = await page.request.get('/server/config/set/lftp/rate_limit/100');
expect(resp.ok(), `rate_limit set failed: ${resp.status()}`).toBe(true);
// OR the dedicated assertion:
await expect(resp).toBeOK();
```

Note: `settings.page.ts` already demonstrates the correct pattern with throw-on-failure:
```typescript
// Source: src/e2e/tests/settings.page.ts:15-19 [VERIFIED: codebase]
const response = await this.page.request.get('/server/config/set/sonarr/enabled/true');
if (!response.ok()) {
    throw new Error(`enableSonarr failed: ${response.status()} ${response.statusText()}`);
}
```

### Pattern 5: Shared utility extraction (E2EFIX-07)
**What:** Private `_escapeRegex` in `dashboard.page.ts:168` and module-private `escapeRegex` in `seed-state.ts:44` are identical functions. Extract to a shared `tests/helpers.ts` file.
**Example:**
```typescript
// NEW: src/e2e/tests/helpers.ts
export function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// In dashboard.page.ts — replace private method with import:
import { escapeRegex } from './helpers';
// Remove private _escapeRegex method
// Change: this._escapeRegex(fileName) -> escapeRegex(fileName)

// In seed-state.ts — replace module function with import:
import { escapeRegex } from './helpers';
// Remove local escapeRegex function definition
```

### Pattern 6: beforeEach navigation ordering (E2EFIX-02)
**What:** API setup calls in `beforeEach` should come AFTER `navigateTo()` if they depend on page context, or be structured so navigation establishes the page context first.
**Research finding:** In `settings-error.spec.ts`, `disableSonarr()` uses `this.page.request.get()` which is the Playwright request context — this works without navigation. However, the correct pattern is navigation-first so the test page context is established before any API calls that affect server state visible to that page. The fix is to call `await settingsPage.navigateTo()` first in `beforeEach`. [VERIFIED: existing pattern in app.spec.ts, autoqueue.page.spec.ts, settings.page.spec.ts all navigate in beforeEach before any other operations]

```typescript
// BEFORE (E2EFIX-02 bug — settings-error.spec.ts):
test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);
    await settingsPage.disableSonarr();  // API call before navigation
});

// AFTER:
test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);
    await settingsPage.navigateTo();     // Navigate first
    await settingsPage.disableSonarr(); // API call after page is ready
});
```

Note: the `test('should show error...')` body also calls `navigateTo()` at line 22 after setting Sonarr config — this is intentional (re-navigate after enabling). The `beforeEach` navigation is still correct as setup. [VERIFIED: codebase inspection]

### Pattern 7: Playwright locale for arm64 consistency (PLAT-02)
**What:** Set `locale: 'en-US'` in `playwright.config.ts` so Chromium uses a deterministic ICU locale regardless of the host system (amd64 vs arm64 have different default locales in their Chromium builds).
**Example:**
```typescript
// Source: https://playwright.dev/docs/emulation#locale--timezone [VERIFIED: Context7]
// src/e2e/playwright.config.ts:
export default defineConfig({
  use: {
    baseURL: process.env.APP_BASE_URL || 'http://myapp:8800',
    locale: 'en-US',  // ADD THIS
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  // ...
});
```

**Research finding:** The Angular app sorts files using `localeCompare` (locale-aware). On arm64 Chromium builds, the system ICU data resolves Unicode sort order differently from amd64 — `'áßç déÀ.mp4'` and `'üæÒ'` sort differently depending on the ICU collation rules in effect. Setting `locale: 'en-US'` in Playwright forces Chromium to use en-US collation consistently. The "should have a list of files" test already handles this via the `byName` sort-agnostic comparison (binary code point order), but other tests that rely on specific display positions could still fail. Setting the locale is a defense-in-depth fix. [ASSUMED: the specific ICU divergence between arm64/amd64 Chromium is based on known ARM Chromium behavior; the locale fix is the standard Playwright remedy]

### Pattern 8: CSP fixture bypass in beforeAll (E2EFIX-04 / PLAT-01)
**What:** The two `test.beforeAll` blocks in `dashboard.page.spec.ts` create raw `browser.newContext()` pages that bypass the CSP listener fixture. The fixture's `page` override (which calls `exposeFunction` and `addInitScript`) only applies to the fixture-managed page context.
**Research finding:** [VERIFIED: codebase inspection]
- Both `beforeAll` blocks at lines 121 and 375 create a raw context, call `dash.navigateTo()` (loading the app without CSP monitoring), run `seedMultiple()`, then close the context.
- `seedMultiple()` uses `page.request.*` for HTTP commands and `page.locator()` for badge polling.
- The seed page does NOT need to observe CSP violations — it is infrastructure, not the app under test.
- **Recommended fix:** Replace `browser.newContext() + ctx.newPage()` with `browser.newContext()` wrapped in a helper that also calls the CSP setup, OR (simpler) use `request.newContext()` + a separate polling page if needed. The cleanest solution given the codebase pattern: create a helper `createCspMonitoredContext(browser)` that applies `exposeFunction` + `addInitScript` to any new context.
- **Alternative (accepted limitation):** Keep raw contexts for beforeAll, add a comment explaining why CSP monitoring is intentionally absent during seed setup (infrastructure context, not app-under-test). This is defensible because no seed operation introduces new script sources.

```typescript
// OPTION A: helper to apply CSP setup to raw context pages
// src/e2e/tests/fixtures/csp-listener.ts — export setup helper
export async function applyCspMonitoring(page: Page, violations: CspViolation[]): Promise<void> {
    await page.exposeFunction('__reportCspViolation', (v: unknown) => { /* ... */ });
    await page.addInitScript(() => { /* same script as fixture */ });
    page.on('console', (msg) => { /* ... */ });
}

// OPTION B (minimal): document the accepted limitation with a comment
test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext();  // CSP monitoring intentionally absent — seed infrastructure context
    const page = await ctx.newPage();
    // ...
});
```

### Anti-Patterns to Avoid
- **`elm.innerHTML()` for text assertions:** Returns HTML markup including tags; use `elm.innerText()` for user-visible text.
- **`:has-text()` pseudo-class:** Deprecated Playwright CSS extension. Use `locator.filter({ hasText })`.
- **`page.waitForTimeout(N)`:** Fixed sleep creates flaky tests. Use Playwright auto-waiting or `expect.poll()`.
- **Unasserted `page.request` calls:** Config-altering API calls without response status checks can silently fail, corrupting test state.
- **Locale-dependent ordering assertions:** Never assert exact file order in UI when the sort is locale-dependent; use order-independent comparison or fix locale in config.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Response status assertion | Custom response checker | `expect(resp).toBeOK()` or `response.ok()` | Playwright's built-in assertion |
| Wait for state propagation | `waitForTimeout(N)` | `locator.waitFor()` / `expect.poll()` | Auto-waits, no fixed sleep |
| CSP violation capture | Custom event listener in test | Existing `csp-listener.ts` fixture | Already handles both `securitypolicyviolation` events and console messages |

**Key insight:** All infrastructure for this phase is already in place. Every fix is a targeted modification to an existing file — no new frameworks, no new tooling.

---

## Common Pitfalls

### Pitfall 1: innerHTML vs innerText behavioral difference
**What goes wrong:** `innerHTML()` returns HTML markup (`<span>text</span>`), not rendered text. Assertions against expected plain strings fail for elements that contain child tags.
**Why it happens:** Both `innerHTML` and `innerText` are valid Playwright locator methods; `innerHTML` is not obviously wrong until the selector matches a container element.
**How to avoid:** Use `innerText()` for all user-visible text assertions. The App base class and settings page already model the correct pattern.
**Warning signs:** Test assertions comparing against plain strings fail when the element has nested markup.

### Pitfall 2: Deprecated :has-text() emitting Playwright warnings
**What goes wrong:** Playwright emits a deprecation warning in test output when `:has-text()` is used; future Playwright versions may remove support.
**Why it happens:** `:has-text()` was a Playwright-proprietary CSS extension; the official API is `locator.filter({ hasText })`.
**How to avoid:** Always use `locator.filter({ hasText })` for filtering by text content.
**Warning signs:** Console output contains "Playwright: :has-text() selector is deprecated".

### Pitfall 3: waitForTimeout removal breaking test semantics
**What goes wrong:** Naively removing `waitForTimeout(500)` without a replacement causes race conditions if the subsequent assertion doesn't have enough implicit wait.
**Why it happens:** The timeout was masking a real timing dependency (stop command propagation).
**How to avoid:** The `getActionButton('Queue').toBeEnabled()` assertion at line 277 uses Playwright auto-wait — it will poll until Queue is enabled or timeout. This provides equivalent synchronization without the sleep. Verify the assertion timeout is sufficient (CI uses 10s expect timeout per `playwright.config.ts`).
**Warning signs:** Test fails intermittently on the Queue button enabled assertion.

### Pitfall 4: beforeEach navigation order affecting page.request
**What goes wrong:** `page.request` in Playwright is independent of the browser navigation state — API calls work without navigation. However, if `disableSonarr()` modifies server-side state that the page reads during its initial load, navigating BEFORE the API call can result in stale state being rendered.
**Why it happens:** The settings page reads Sonarr config on load. If `navigateTo()` fires before `disableSonarr()`, the page might briefly render enabled Sonarr state.
**How to avoid:** Navigate first, then issue API calls that set up state for the NEXT navigation or test action. The individual `test` body already calls `navigateTo()` after API state setup — this is the pattern the `beforeEach` should follow (navigate so the page is ready, then state can be set before the test's own navigation).
**Warning signs:** Settings page shows wrong initial state; `getSonarrTestResult()` fails because Sonarr is still enabled.

### Pitfall 5: escapeRegex extraction breaking existing imports
**What goes wrong:** Moving `escapeRegex` to `helpers.ts` requires updating imports in `dashboard.page.ts` (private method → imported function) and `seed-state.ts` (module function → imported function). Missing either update causes a TypeScript compilation error.
**Why it happens:** Both files currently have self-contained definitions; they won't auto-update.
**How to avoid:** Update all three files atomically: create `helpers.ts`, update imports in both `dashboard.page.ts` and `seed-state.ts`, and verify TypeScript compilation.

### Pitfall 6: CSP listener fixture not applying to beforeAll contexts
**What goes wrong:** CSP violations during `beforeAll` seed setup go undetected because the fixture's `page` override only applies to fixture-managed pages.
**Why it happens:** Playwright fixtures override the `page` object per-test, but `browser.newContext()` creates a raw context outside fixture control.
**How to avoid:** Either (a) apply CSP monitoring to raw pages via a helper function, or (b) document the accepted limitation. The seed operations only make HTTP requests and observe DOM state — they do not introduce new CSP-violating scripts.

### Pitfall 7: locale setting affecting test fixture isolation
**What goes wrong:** Setting `locale: 'en-US'` in `playwright.config.ts` applies globally to all Playwright contexts. If any test depends on system locale behavior, it will now get en-US instead.
**Why it happens:** Global `use` options apply to all test contexts.
**How to avoid:** All existing tests use ASCII-clean selectors (`getByRole`, `getByText`, CSS selectors); no test checks locale-specific number or date formatting. The change is safe for this test suite. [VERIFIED: codebase inspection]

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### E2EFIX-01: innerHTML → innerText (autoqueue.page.ts:28)
```typescript
// Before:
return Promise.all(elements.map(elm => elm.innerHTML()));
// After:
return Promise.all(elements.map(elm => elm.innerText()));
```

### E2EFIX-02: beforeEach navigation ordering (settings-error.spec.ts)
```typescript
// Before:
test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);
    await settingsPage.disableSonarr();
});
// After:
test.beforeEach(async ({ page }) => {
    settingsPage = new SettingsPage(page);
    await settingsPage.navigateTo();
    await settingsPage.disableSonarr();
});
```

### E2EFIX-03: Remove waitForTimeout (dashboard.page.spec.ts:251-255)
```typescript
// Before:
await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
await page.waitForTimeout(500);
// After:
await page.request.post(`/server/command/stop/${encodeURIComponent('testing.gif')}`);
// (no wait — the Queue button enabled assertion below provides synchronization via auto-wait)
```

### E2EFIX-05: :has-text() migration (autoqueue.page.ts:35)
```typescript
// Before:
await this.page.locator(`.pattern-section .pattern-chip-text:has-text("${pattern}")`).waitFor({ state: 'visible' });
// After:
await this.page.locator('.pattern-section .pattern-chip-text')
    .filter({ hasText: pattern })
    .waitFor({ state: 'visible' });
```

### E2EFIX-06: HTTP response assertion (dashboard.page.spec.ts:272,302)
```typescript
// Before:
await page.request.get('/server/config/set/lftp/rate_limit/100');
// ... (in finally block)
await page.request.get('/server/config/set/lftp/rate_limit/0');

// After:
const throttleResp = await page.request.get('/server/config/set/lftp/rate_limit/100');
if (!throttleResp.ok()) throw new Error(`rate_limit set failed: ${throttleResp.status()}`);
// ... (in finally block)
const restoreResp = await page.request.get('/server/config/set/lftp/rate_limit/0');
if (!restoreResp.ok()) throw new Error(`rate_limit restore failed: ${restoreResp.status()}`);
```

### E2EFIX-07: _escapeRegex extraction
```typescript
// NEW: src/e2e/tests/helpers.ts
export function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// dashboard.page.ts: import + remove private method:
import { escapeRegex } from './helpers';
// change this._escapeRegex(fileName) → escapeRegex(fileName)

// seed-state.ts: import + remove module function:
import { escapeRegex } from './helpers';
// remove: function escapeRegex(s: string): string { ... }
```

### PLAT-01: beforeAll CSP bypass — accepted limitation with comment
```typescript
// dashboard.page.spec.ts — both beforeAll blocks:
test.beforeAll(async ({ browser }) => {
    test.setTimeout(120_000);
    // CSP monitoring intentionally absent: raw context used for seed-state API calls only.
    // The fixture's page override applies to per-test pages. Seed operations do not
    // introduce new script sources; violations here would indicate infrastructure issues,
    // not app CSP regressions.
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    // ...
});
```

### PLAT-02: locale in playwright.config.ts
```typescript
// src/e2e/playwright.config.ts:
export default defineConfig({
  use: {
    baseURL: process.env.APP_BASE_URL || 'http://myapp:8800',
    locale: 'en-US',  // Force deterministic ICU locale; prevents arm64/amd64 sort divergence
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  // ...
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `:has-text()` CSS pseudo-class | `locator.filter({ hasText })` | Playwright ~v1.33 | Old syntax still works but emits deprecation warnings; removed in future |
| `waitForTimeout(N)` | `locator.waitFor()` / `expect.poll()` | Playwright v1.0+ | `waitForTimeout` always discouraged; still exists but flagged as "debugging only" |
| `innerHTML()` for text | `innerText()` | Playwright v1.14+ | `innerText()` matches user-visible text; `innerHTML()` returns markup |

**Deprecated/outdated:**
- `:has-text()` selector: deprecated in favor of `locator.filter({ hasText })` [CITED: https://playwright.dev/docs/locators#filter-by-text]
- `page.waitForTimeout()`: officially discouraged — "should only be used for debugging" [CITED: https://playwright.dev/docs/api/class-page#page-wait-for-timeout]

---

## Runtime State Inventory

> This is a code/test-only phase — no runtime state migrations, renames, or data model changes. Not applicable.

None — verified by phase scope analysis. All 9 fixes are TypeScript source edits with no database migrations, OS registration changes, or stored data impact.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | TypeScript compilation | ✓ | v25.5.0 | — |
| npm | Package management | ✓ | 11.8.0 | — |
| @playwright/test | E2E runner | ✓ | 1.59.1 | — |
| Docker | `make run-tests-e2e` | ✓ | 29.2.0 | — |
| make | Test orchestration | ✓ | system | — |

**No missing dependencies.** All required tooling is available locally.

**Note:** Full E2E test run requires `STAGING_VERSION`, `SEEDSYNCARR_ARCH`, and a staging Docker image (per Makefile). These are CI/CD requirements; local file edits can be validated by TypeScript compilation (`tsc --noEmit`) without running the full Docker stack.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright 1.59.1 |
| Config file | `src/e2e/playwright.config.ts` |
| Quick run command | `cd src/e2e && npx playwright test --reporter=list` (requires Docker stack) |
| Full suite command | `make run-tests-e2e STAGING_VERSION=X SEEDSYNCARR_ARCH=amd64` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| E2EFIX-01 | `getPatterns()` returns plain text, not HTML | E2E (autoqueue.page.spec.ts) | `npx playwright test autoqueue` | ✅ |
| E2EFIX-02 | Settings error page renders correctly after beforeEach | E2E (settings-error.spec.ts) | `npx playwright test settings-error` | ✅ |
| E2EFIX-03 | No waitForTimeout in specs | static (TypeScript grep) + E2E | `grep -r waitForTimeout src/e2e/tests/` | ✅ (grep check) |
| E2EFIX-04 | CSP fixture covers all test contexts | E2E (csp-canary.spec.ts) | `npx playwright test csp-canary` | ✅ |
| E2EFIX-05 | :has-text() removed from all specs | static (TypeScript grep) | `grep -r ':has-text(' src/e2e/tests/` | ✅ (grep check) |
| E2EFIX-06 | Rate-limit config calls assert response OK | E2E (dashboard.page.spec.ts) | `npx playwright test dashboard` | ✅ |
| E2EFIX-07 | Single escapeRegex definition | static (TypeScript compilation) | `cd src/e2e && npx tsc --noEmit` | ✅ Wave 0: create helpers.ts |
| PLAT-01 | CSP violations fail tests | E2E (csp-canary.spec.ts) | `npx playwright test csp-canary` | ✅ |
| PLAT-02 | Dashboard specs pass on arm64 | E2E (dashboard.page.spec.ts) | `make run-tests-e2e SEEDSYNCARR_ARCH=arm64` | ✅ (requires CI/Docker) |

### Sampling Rate
- **Per task commit:** `cd src/e2e && npx tsc --noEmit` (TypeScript compilation — verifies no import/type errors)
- **Per wave merge:** Full Playwright suite via `make run-tests-e2e` on Docker stack
- **Phase gate:** Full suite green (amd64 + arm64) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `src/e2e/tests/helpers.ts` — does not exist yet; needed for E2EFIX-07 escapeRegex extraction

*(All other test files exist; no new spec files needed for this phase.)*

---

## Security Domain

> `security_enforcement` not explicitly disabled — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | Test-only code; no user input handling |
| V6 Cryptography | no | — |
| V14 Configuration | yes | CSP enforcement via `csp-listener.ts` fixture catches misconfigured CSP headers |

### Known Threat Patterns for Playwright E2E stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSP misconfiguration passing silently | Elevation of Privilege | CSP listener fixture (PLAT-01) — already in place |
| Test credentials in plain text | Information Disclosure | Acknowledged in configure/setup_seedsyncarr.sh comment: "test-only credentials visible in container logs" — accepted for test infrastructure |
| Rate-limit config silently failing | Tampering | E2EFIX-06 adds response assertions to detect failures |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Setting `locale: 'en-US'` in playwright.config.ts fixes arm64 sort divergence (the byName sort-agnostic test may already be sufficient without the locale fix) | PLAT-02 / Pattern 7 | Low: locale fix is additive and non-breaking; worst case is the fix provides no benefit for already-fixed tests |
| A2 | Removing `waitForTimeout(500)` without replacement is safe because `getActionButton('Queue').toBeEnabled()` auto-wait at line 277 provides sufficient synchronization | E2EFIX-03 / Pattern 3 | Medium: if stop propagation takes longer than the expect timeout (10s on CI), the Queue test might fail intermittently; mitigation: watch for flakes after removal |
| A3 | The `beforeAll` CSP bypass (E2EFIX-04) is acceptable as a documented limitation rather than requiring a full fix, because seed operations do not introduce new script sources | E2EFIX-04 / Pitfall 6 | Low: the seed operations are HTTP API calls + DOM polling; no new script tags or eval-equivalent calls |

**If this table is empty:** It is not — three assumptions are documented above.

---

## Open Questions

1. **PLAT-02: Is the `byName` sort fix sufficient or is `locale: 'en-US'` also needed?**
   - What we know: The `byName` binary code-point sort at line 40-41 is already in HEAD and makes the "file list" test order-independent. This should handle arm64 divergence for that test.
   - What's unclear: Whether other tests in the suite fail on arm64 due to locale-dependent behavior not caught by `byName`.
   - Recommendation: Apply `locale: 'en-US'` as a defense-in-depth fix (one line, no risk) to prevent future sort-sensitive test additions from being fragile.

2. **E2EFIX-04: Accepted limitation or full fix?**
   - What we know: The seed beforeAll contexts bypass CSP monitoring. Seed operations are HTTP API + badge polling — no new script sources.
   - What's unclear: Whether the app's initial load in the seed context (via `dash.navigateTo()`) could trigger CSP violations that are signs of real bugs.
   - Recommendation: Document as accepted limitation with a code comment. If CI reveals CSP violations from seed contexts in the future, upgrade to a `createCspMonitoredContext()` helper.

---

## Sources

### Primary (HIGH confidence)
- `src/e2e/tests/autoqueue.page.ts` — line 28 (innerHTML bug), line 35 (:has-text bug) [VERIFIED: codebase]
- `src/e2e/tests/settings-error.spec.ts` — beforeEach ordering bug [VERIFIED: codebase]
- `src/e2e/tests/dashboard.page.spec.ts` — lines 121, 255, 272, 302, 375 [VERIFIED: codebase]
- `src/e2e/tests/dashboard.page.ts` — line 168 (_escapeRegex) [VERIFIED: codebase]
- `src/e2e/tests/fixtures/csp-listener.ts` — full fixture implementation [VERIFIED: codebase]
- `src/e2e/tests/fixtures/seed-state.ts` — line 44 (escapeRegex duplicate) [VERIFIED: codebase]
- Context7 `/microsoft/playwright.dev` — innerText, locator.filter, waitForTimeout, locale, request.ok() [VERIFIED: Context7 docs]
- `src/e2e/playwright.config.ts` — no locale set, workers:1, retries:2 on CI [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- npm registry: `@playwright/test` current version 1.59.1 [VERIFIED: `npm view @playwright/test version`]

### Tertiary (LOW confidence)
- ICU data divergence between arm64/amd64 Chromium builds causing `localeCompare` differences [ASSUMED — based on known ARM Chromium behavior; the standard mitigation `locale: 'en-US'` is documented in Playwright]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — installed versions verified against npm registry
- Architecture: HIGH — all affected files inspected directly
- Pitfalls: HIGH — identified from direct code inspection; LOW for arm64 ICU specifics (assumed)
- Fix patterns: HIGH — verified against Context7 Playwright docs and existing codebase patterns

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (Playwright stable; no breaking changes expected in 30 days)
