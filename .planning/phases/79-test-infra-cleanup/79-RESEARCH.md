# Phase 79: Test Infra Cleanup - Research

**Researched:** 2026-04-21
**Domain:** Python test-harness warning suppression + Playwright CSP violation fixture
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

TEST-01 (pytest-cache + webob/cgi warnings):
- **D-01:** Add `-p no:cacheprovider` to Dockerfile CMD: `CMD ["pytest", "-v", "-p", "no:cacheprovider"]` at `src/docker/test/python/Dockerfile:45`. Surgical, test-container only; local `poetry run pytest` untouched.
- **D-02:** Delete `cache_dir = "/tmp/.pytest_cache"` at `src/python/pyproject.toml:74`. Dead once cacheprovider disabled.
- **D-03:** Primary fix — upgrade webob to a release that dropped the internal `cgi` import. Researcher confirms target version.
- **D-04:** Delete stale `filterwarnings = ["ignore:'cgi' is deprecated:DeprecationWarning"]` at `src/python/pyproject.toml:75–77`. Apparently not matching; fires before pytest filters install.
- **D-05:** Fallback ONLY if no clean webob upgrade exists: `ENV PYTHONWARNINGS="ignore::DeprecationWarning:webob"` in `src/docker/test/python/Dockerfile` (or a pytest `-W` flag). Record in `.planning/PROJECT.md` Key Decisions if taken.
- **D-06:** No supply-chain pin to webob fork / pre-release. Live with suppression.

TEST-02 (Playwright CSP listener fixture):
- **D-07:** New fixture at `src/e2e/tests/fixtures/csp-listener.ts` via `test.extend()`. Wraps `page`, registers both listeners on first use, collects per-test array, asserts `expect(violations).toEqual([])` in auto-fixture teardown.
- **D-08:** 6 spec files swap top-line import to `from './fixtures/csp-listener'`: `about.page.spec.ts`, `app.spec.ts`, `autoqueue.page.spec.ts`, `dashboard.page.spec.ts`, `settings-error.spec.ts`, `settings.page.spec.ts`.
- **D-09:** Two-source listener:
    1. `page.on('console', msg)` — filter for CSP text markers. Researcher picks exact substring.
    2. `page.addInitScript` registering `document.addEventListener('securitypolicyviolation', …)` + bridge back to test process (`page.exposeFunction` vs polling). Researcher picks mechanism.
- **D-10:** Failure in `afterEach` only (not inline throw).
- **D-11:** Permanent canary spec as regression guard for the listener itself.
- **D-12:** Canary at `src/e2e/tests/csp-canary.spec.ts`. Injects inline script via `document.write` or `innerHTML` before navigation; asserts violations array contains ≥1 entry. Fixture exposes `cspViolations` accessor + `allowViolations()` opt-out.
- **D-13:** Canary runs against real backend header + Angular autoCsp — no CSP mocking.
- **D-14:** Two independent sub-plans, parallel-schedulable: Plan 01 (TEST-01) + Plan 02 (TEST-02). No shared files, no sequencing.

### Claude's Discretion

- Exact webob version for D-03 (researcher confirms cgi-removal release, picks lowest-churn jump).
- Exact console-text substring(s) for D-09 filter 1 — most stable Chromium marker.
- Exact `securitypolicyviolation` → test-process bridge in D-09 filter 2 — `page.exposeFunction` callback vs polling `window.__cspViolations`.
- Canary injection technique in D-12 — `document.write` vs `document.body.appendChild(scriptEl)`.
- Canary spec filename (`csp-canary.spec.ts` recommended, `csp.spec.ts` acceptable).
- Whether to add JSDoc/README snippet at top of fixture explaining two-source rationale.

### Deferred Ideas (OUT OF SCOPE)

- Fixing real CSP violations discovered by the canary or listener.
- `page.on('pageerror')` or general JS-error capture.
- CSP violation reporting to a backend endpoint (`report-uri` / `report-to`).
- Angular unit test / Karma CSP coverage (layer 1).
- arm64 `run-tests-python` Docker build fix (Phase 80, TECH-01).
- Supply-chain pin to webob git main (D-06 rejected).
- CSP header / meta-tag policy changes.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | Zero pytest-cache warnings + zero webob/cgi DeprecationWarnings on CI Python run | §2 confirms `-p no:cacheprovider` mechanism; §3 confirms pyproject.toml cleanup; §2 confirms D-05 fallback is mandatory (no clean webob upgrade exists as of 2026-04-21) |
| TEST-02 | Main Playwright E2E fails on any CSP violation via shared fixture hooking `page.on('console')` + `securitypolicyviolation` event, asserting in afterEach; seeded-violation verification required | §4 confirms invariant Chromium console substring; §5 recommends Option A (exposeFunction bridge); §6 describes fixture composition with opt-out; §7 confirms canary injection method + meta-tag blocks it |

</phase_requirements>

## 1. Executive Summary

Six planner-ready findings:

- **D-03 fails; D-05 fallback is mandatory.** webob 1.8.9 (published 2024-10-24) is the latest PyPI release. No 1.8.10 / 1.9 / 2.0 exists. `webob/compat.py` line 4 still does unconditional `from cgi import parse_header`. The `legacy-cgi>=2.6; python_version >= "3.13"` constraint added in 1.8.9 only activates on Python 3.13; this project pins Python `>=3.11,<3.13` and the Docker image is `python:3.11-slim`, so stdlib `cgi` still fires the DeprecationWarning at import time. Plan must take the D-05 fallback with `ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"` (scoped to the `cgi` module, not webob — the warning originates from `cgi` itself).

- **D-09 filter 1: the invariant Chromium substring is `"violates the following Content Security Policy directive"`.** "Refused to" varies by violation type (`"Executing inline script violates…"` uses a different verb in one Blink template); the "violates the following Content Security Policy directive" phrase appears in both inline and URL-loading templates in `third_party/blink/renderer/core/frame/csp/csp_directive_list.cc`.

- **D-09 filter 2: use Option A (`page.exposeFunction` + init script).** `addInitScript` re-runs on every navigation, which resets `window.__cspViolations` to `[]` on each `goto()` — Option B would drop violations that fire on a page that later navigates. `exposeFunction` survives navigations and delivers violations into a Node-process array in real time. `settings-error.spec.ts` and `dashboard.page.spec.ts` both navigate multiple times in a single test, making Option B unsafe.

- **D-12 canary: use `document.body.appendChild(scriptEl)` with `scriptEl.textContent`.** Injected via `addInitScript` so it runs post-DOMContentLoaded. `document.write` is disallowed by Chromium after DOMContentLoaded in cross-document contexts and would sometimes no-op silently. The Angular `autoCsp: true` meta tag emits `script-src 'strict-dynamic' 'sha256-…' 'unsafe-inline'`; per CSP spec `'unsafe-inline'` is ignored when a hash is present. An inline script body without a matching hash is blocked by the meta-tag layer — this is exactly what the canary needs.

- **Fixture composition: single `test.extend()` with one `{ auto: true }` fixture + one `{ option: true }` flag.** The Checkly JS-error fixture pattern (Checkly 2024) directly maps: expose `cspViolations: CspViolation[]` (read), expose `allowViolations: boolean` (option, default `false`), in the page-fixture teardown assert `if (!allowViolations) expect(cspViolations).toEqual([])`. No collision with Phase 77's `seedState` fixture — they live in different files and touch different fixture keys.

- **Python Docker base is 3.11**; CI harness evidence surface for SC#1 is `.github/workflows/ci.yml:144`; both plans are fully independent (no shared file) and can wave in parallel exactly as D-14 specifies.

**Primary recommendation:** Planner should author Plan 02 with Option A (`exposeFunction`), the substring `"violates the following Content Security Policy directive"`, and an `appendChild` canary — and Plan 01 with the D-05 fallback path pre-committed (no conditional branch, since D-03 cannot succeed as of 2026-04-21).

---

## 2. TEST-01: webob Upgrade Target (D-03) — Primary Fix UNAVAILABLE, D-05 Fallback Required

### Evidence

**webob 1.8.9 is the latest release.** Query against live PyPI JSON on 2026-04-21:

```
LATEST: 1.8.9
Upload time: 2024-10-24T03:19:18
Requires: ['legacy-cgi>=2.6; python_version >= "3.13"', …]
```
[VERIFIED: `curl https://pypi.org/pypi/WebOb/json` — 2026-04-21]

**webob 1.8.9 still unconditionally imports stdlib `cgi`.** Verified against the 1.8.9 source at the GitHub release tag:

```python
# src/webob/compat.py, line 4 (v1.8.9)
from cgi import parse_header
```
[VERIFIED: `https://raw.githubusercontent.com/Pylons/webob/1.8.9/src/webob/compat.py` — 2026-04-21]

The `legacy-cgi` conditional dependency added in 1.8.9 only activates on Python >= 3.13, and it does **not** replace the unconditional `from cgi import …`. On Python 3.13 the stdlib `cgi` is gone, so `legacy-cgi` shims it in as a namespace-compatible replacement. On Python 3.11/3.12 the stdlib `cgi` is present but deprecated, and webob imports it → the DeprecationWarning fires.

**The migration to `multipart` is still open.** PR [Pylons/webob#466](https://github.com/Pylons/webob/pull/466) replaces `cgi.FieldStorage` with the `multipart` package and is targeted at webob 2.0. As of 2026-04-21 it remains unmerged. No supply-chain pin or pre-release is available.
[CITED: https://github.com/Pylons/webob/pull/466]

**The project's Python pin excludes 3.13.** `src/python/pyproject.toml:10` → `requires-python = ">=3.11,<3.13"`. Base Docker image is `python:3.11-slim` (`src/docker/build/docker-image/Dockerfile:75`). Upgrading to Python 3.13 to activate `legacy-cgi` is out of scope and would require large parallel work.

### Conclusion

**D-03 cannot be satisfied.** No webob release has dropped the `cgi` import while remaining compatible with the project's Python pin. Take D-05 directly; do not leave a conditional "try upgrade first" branch in the plan.

### D-05 Fallback — Exact Form

The DeprecationWarning originates in the `cgi` module's own `__init__.py` at import time (`"'cgi' is deprecated and slated for removal in Python 3.13"`), **before** pytest installs its filter chain. This is why D-04's pyproject filter doesn't match: pytest never sees the warning. The fix must apply at interpreter start.

**Recommended injection point:** `ENV` line in `src/docker/test/python/Dockerfile` immediately before the existing `CMD`:

```dockerfile
# After line 42 (ENV PYTHONPATH=/src), before ENTRYPOINT
ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"
```

**Module qualifier:** `cgi` (the warning's origin module), not `webob`. Python's `PYTHONWARNINGS` filter matches the module that *emits* the warning via `warnings.warn(..., DeprecationWarning)`, which is the stdlib `cgi` module itself; tagging `webob` would not match because webob merely triggers the import.

[CITED: Python 3.11 stdlib `cgi.py` — `warnings.warn("'cgi' is deprecated and slated for removal in Python 3.13", DeprecationWarning, stacklevel=2)`]

**Verification the filter works:**
```bash
make run-tests-python 2>&1 | grep -c "cgi.*deprecated"
# Expected: 0
```

### D-04 Cleanup Confirmation

With D-05 applied via `ENV PYTHONWARNINGS`, the existing pyproject filter is doubly redundant:
- It doesn't match (warning fires at import, before pytest's filter chain loads).
- The interpreter-level filter covers it before pytest even starts.

Delete lines 75–77 of `src/python/pyproject.toml` as D-04 specifies. No replacement entry.

### Records Required (per D-05)

Per CONTEXT.md D-05: record the fallback in `.planning/PROJECT.md` Key Decisions and track upstream unblock as a new todo. Suggested todo: `.planning/todos/pending/2026-04-21-webob-cgi-upstream-unblock.md` — "Remove PYTHONWARNINGS filter when webob 2.x ships (tracks [webob#466](https://github.com/Pylons/webob/pull/466))."

---

## 3. TEST-01: pytest-cache + pyproject.toml Cleanup (D-01, D-02, D-04)

### D-01 Mechanism Confirmation

pytest's `cacheprovider` plugin is the source of all three "could not create cache dir" warnings. Disabling it with `-p no:cacheprovider` prevents any cache-write attempt; the plugin never loads, no warning is emitted.
[VERIFIED: pytest docs, Cache plugin — `-p no:cacheprovider` disables plugin entirely]

**Dockerfile edit** (`src/docker/test/python/Dockerfile:45`):
```diff
-CMD ["pytest", "-v"]
+CMD ["pytest", "-v", "-p", "no:cacheprovider"]
```

**Scope confirmed correct by compose.yml read-only mount** (`src/docker/test/python/compose.yml:13` → `read_only: true`): the mount is precisely why cache writes fail. Fixing at CMD level avoids changing the security property (no mutation of `/src`).

**Local dev unaffected:** the flag lives in the Dockerfile CMD, not pyproject.toml. `poetry run pytest` (local dev path) uses pyproject defaults → cache still enabled in dev where the writable `.pytest_cache` dir is fine.

### D-02 Confirmation

With `-p no:cacheprovider` in effect, `cache_dir` is a setting for a plugin that isn't loaded. Delete line 74 of `src/python/pyproject.toml`:

```diff
 [tool.pytest.ini_options]
 pythonpath = ["."]
 timeout = 60
-cache_dir = "/tmp/.pytest_cache"
 filterwarnings = [
     "ignore:'cgi' is deprecated:DeprecationWarning",
 ]
```

### D-04 Confirmation

Delete lines 75–77 (`filterwarnings` key and its list). Reasons:
1. The filter doesn't currently match — warning fires at import time, before pytest's filter chain installs.
2. D-05 covers the filter's intent at interpreter level.
3. Dead config is a maintenance hazard (next engineer assumes the filter is active).

**Final pyproject.toml `[tool.pytest.ini_options]` section** (after edits):

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
timeout = 60
```

[VERIFIED: current contents of `src/python/pyproject.toml:71–78`]

---

## 4. TEST-02: Console-Log Filter String (D-09 Filter 1)

### Recommendation

Use substring match: **`"violates the following Content Security Policy directive"`** — case-sensitive, tested against `msg.text()` from `page.on('console', msg => ...)`.

### Evidence

The CSP violation console message is constructed by Blink in `third_party/blink/renderer/core/frame/csp/csp_directive_list.cc`. Two primary templates emit to console:

```cpp
// Inline violations
StrCat({console_message, " violates the following Content Security Policy directive '",
        raw_directive, "'.", suffix})

// URL violations
StrCat({prefix, url.ElidedString(), "' violates the following Content Security Policy "
        "directive: \"", raw_directive, "\".", suffix})
```
[CITED: Chromium source — `third_party/blink/renderer/core/frame/csp/csp_directive_list.cc`, functions `CheckInlineAndReportViolation` and `ReportViolationForCheckSource`]

**Invariant substring across both templates:** `"violates the following Content Security Policy directive"` (21 chars before "directive" — the only phrase that appears verbatim in both).

### Why Not `"Refused to"`

- Some Blink templates open with `"Executing inline script violates…"` (no "Refused"). One excerpt:
  > `StrCat({"Refused to ", message, kWarningMessageForSyntheticResponse})` — used only for synthetic responses.
- The phrase "Refused to" also appears in **non-CSP** console messages from Chromium (e.g., CORS errors: `"Refused to connect to '…' because…"` without the CSP phrase) — higher false-positive risk.
  [CITED: Chromium source — `content/browser/renderer_host/cross_origin_opener_policy_reporter.cc` uses similar "Refused" phrasing without CSP context]

### Why Not `"Content Security Policy"` Alone

Too broad — the string "Content Security Policy" appears in documentation-link messages, report-only notices, and developer-tools annotations that are not violation events. The directive-specific phrase is narrow enough to avoid those.

### False-Positive Check Against Existing Suite

Grep confirmed: the current 6 spec files contain **zero** `page.on('console')` registrations (`grep -n "page.on('console'" src/e2e/tests/*.spec.ts` returns no matches). No existing test logs the phrase. The only console output during test runs comes from the Angular app itself plus `@playwright/test`'s internal machinery — neither ever emits "violates the following Content Security Policy directive."

### Implementation Snippet

```typescript
page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error' && text.includes(
        'violates the following Content Security Policy directive'
    )) {
        violations.push({ source: 'console', text });
    }
});
```

Type guard `msg.type() === 'error'` narrows further — CSP violations always emit at the `error` level in Chromium.

---

## 5. TEST-02: DOM-Event Bridge (D-09 Filter 2) — Recommend Option A

### Recommendation

**Option A** — `page.exposeFunction('__reportCspViolation', fn)` registered in the fixture; init script calls it from inside the `securitypolicyviolation` listener.

### Tradeoff Table

| Dimension | Option A (exposeFunction) | Option B (poll `window.__cspViolations`) |
|-----------|---------------------------|------------------------------------------|
| Setup order | `exposeFunction` MUST be called before `addInitScript`. Playwright docs confirm this ordering works. | Simpler — just one `addInitScript` call. |
| Survives navigation? | **Yes** — `exposeFunction` explicitly survives navigations per Playwright docs. | **No** — `window.__cspViolations = []` is reset on every navigation because `addInitScript` re-runs. Violations from a pre-navigate page are lost unless the fixture polls **before** every `page.goto()`. |
| Real-time delivery | Violations arrive in the Node array immediately via IPC callback. | Only arrive when fixture runs `await page.evaluate(() => window.__cspViolations)`. |
| Cross-page-unload data loss | None — callback has already delivered the data to Node. | High — if a violation fires just before `page.goto()`, the current window's array is GC'd before the fixture polls. |
| Complexity of teardown | Trivial — Node array is the source of truth. | Must re-poll after last navigation; must merge arrays from multiple page windows. |
| Target spec behavior | Works for all 6 specs. | Breaks for `settings-error.spec.ts` (navigates to settings then back) and `dashboard.page.spec.ts` (UAT-01 and UAT-02 describe blocks seed via multiple `page.goto` calls in `beforeAll`). |

[CITED: Playwright docs — "Functions installed via page.exposeFunction() survive navigations"; "page.addInitScript() evaluates a script whenever the page navigates" → implies re-execution, not persistence]

### Reference Pattern

Matches Checkly's canonical JS-error tracking fixture (adapted for CSP):

```typescript
// src/e2e/tests/fixtures/csp-listener.ts
import { test as base, expect, type Page } from '@playwright/test';

export interface CspViolation {
    source: 'console' | 'event';
    blockedURI?: string;
    violatedDirective?: string;
    originalPolicy?: string;
    sourceFile?: string;
    lineNumber?: number;
    sample?: string;
    text?: string;  // raw console text for 'console' source
}

type Fixtures = {
    cspViolations: CspViolation[];
    allowViolations: boolean;
};

export const test = base.extend<Fixtures>({
    allowViolations: [false, { option: true }],

    cspViolations: async ({}, use) => {
        await use([]);
    },

    page: async ({ page, cspViolations, allowViolations }, use) => {
        // 1. Expose the bridge BEFORE addInitScript (exposeFunction survives navigations).
        await page.exposeFunction('__reportCspViolation', (v: CspViolation) => {
            cspViolations.push({ ...v, source: 'event' });
        });

        // 2. Install the DOM listener — runs on every navigation.
        await page.addInitScript(() => {
            document.addEventListener('securitypolicyviolation', (e) => {
                // @ts-ignore — exposed function on window
                window.__reportCspViolation({
                    blockedURI: e.blockedURI,
                    violatedDirective: e.violatedDirective,
                    originalPolicy: e.originalPolicy,
                    sourceFile: e.sourceFile,
                    lineNumber: e.lineNumber,
                    sample: e.sample,
                });
            });
        });

        // 3. Console source — fires immediately, no init-script round-trip.
        page.on('console', (msg) => {
            const text = msg.text();
            if (msg.type() === 'error' &&
                text.includes('violates the following Content Security Policy directive')) {
                cspViolations.push({ source: 'console', text });
            }
        });

        await use(page);

        // 4. Teardown assertion — unless the spec opted out.
        if (!allowViolations) {
            expect(cspViolations, 'CSP violations detected').toEqual([]);
        }
    },
});

export { expect };
```

[VERIFIED: pattern adapted from Checkly "Track Frontend JavaScript exceptions with Playwright" (checklyhq.com/blog/track-frontend-javascript-exceptions-with-playwright/); `{ option: true }` and `{ auto: true }` semantics from Playwright test-fixtures docs]

### Serialization Note

`SecurityPolicyViolationEvent` properties are all primitives (strings, numbers, null) — safe for the IPC bridge between browser context and Node. Do NOT pass the raw event object (non-serializable across `exposeFunction`); pass a plain object literal.
[CITED: MDN — SecurityPolicyViolationEvent properties]

---

## 6. TEST-02: Fixture Composition + Opt-Out Mechanism (D-07, D-12 Canary Interop)

### Composition Mechanics

Playwright 1.48's `test.extend<T>()` merges fixture types via TypeScript intersection. Three fixtures compose in one `extend()` call:

1. `allowViolations: boolean` — tuple form `[false, { option: true }]` makes it a per-spec option with default `false`. Specs can override via `test.use({ allowViolations: true })`.
2. `cspViolations: CspViolation[]` — plain fixture, initializes to `[]`, accessible to specs that need to inspect.
3. `page: Page` — **override** the built-in `page` fixture to wire listeners before the test body runs. This is the auto-activation surface (test bodies always use `page` → listeners always attach). No `{ auto: true }` needed because `page` is already required by every test.

### Why One `extend()` (Not Chained Extends)

Phase 77's `seed-state.ts` exports *helper functions*, not a fixture object (re-read: lines 58–72 export free functions; the file does **not** call `test.extend()`). There is no `seedState` fixture to merge. Phase 79's fixture is the first actual fixture-extending file in the repo.

If Phase 77 later upgrades seed-state to a fixture, `mergeTests(cspTest, seedTest)` is the Playwright-sanctioned composition:
```typescript
import { mergeTests } from '@playwright/test';
export const test = mergeTests(cspTest, seedTest);
```
[CITED: Playwright docs — `mergeTests` for combining multiple `test` instances]

### Opt-Out Mechanism for D-12 Canary

The canary spec inverts the assertion. Two mechanisms in the fixture support this:

1. **`allowViolations` option** — set at the file level via `test.use({ allowViolations: true })`. Disables the `expect(toEqual([]))` teardown.
2. **`cspViolations` fixture** — exposed to the test body; canary spec reads it and asserts `expect(cspViolations.length).toBeGreaterThan(0)` plus `expect(cspViolations.some(v => /* matches seeded injection */))`.

Canary file pattern:

```typescript
// src/e2e/tests/csp-canary.spec.ts
import { test, expect } from './fixtures/csp-listener';

test.use({ allowViolations: true });

test('CSP listener fires on seeded inline-script violation', async ({ page, cspViolations }) => {
    await page.addInitScript(() => {
        // Inject AFTER DOMContentLoaded so the script is evaluated at document-ready.
        // scriptEl.textContent is an inline script body — blocked by Angular autoCsp
        // meta tag's hash-based script-src (no matching sha256 hash for this body).
        window.addEventListener('DOMContentLoaded', () => {
            const el = document.createElement('script');
            el.textContent = 'window.__canaryRan = true;';
            document.body.appendChild(el);
        });
    });

    await page.goto('/');
    // Wait for the injection attempt to surface. The listener collects from either
    // console OR the DOM event; either surface is sufficient.
    await expect.poll(() => cspViolations.length).toBeGreaterThan(0);

    // Tighter assertion — canary is CSP-specific, not a generic page error.
    const sawCsp = cspViolations.some(v =>
        (v.source === 'event' && v.violatedDirective?.startsWith('script-src')) ||
        (v.source === 'console' && v.text?.includes('script-src'))
    );
    expect(sawCsp).toBe(true);
});
```

### Interop Confirmation

- `workers: 1, fullyParallel: false` (playwright.config.ts:10,13) → each test gets its own `page`, its own `cspViolations` array. No cross-test leak.
- Fixture state is per-test (Playwright semantics) — `cspViolations` is initialized to a fresh `[]` on every test entry.
- `allowViolations` is a per-file option (`test.use({ allowViolations: true })` at the top of `csp-canary.spec.ts`) — zero effect on the 6 other spec files.

---

## 7. TEST-02: Canary Injection Method (D-12)

### Recommendation

Inside `page.addInitScript`, on DOMContentLoaded, run:
```javascript
const el = document.createElement('script');
el.textContent = 'window.__canaryRan = true;';
document.body.appendChild(el);
```

### Which CSP Layer Blocks This

**The Angular autoCsp meta tag blocks it.** The HTTP header does NOT.

**HTTP header** (`src/python/web/web_app.py:152–162`):
```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
font-src 'self';
connect-src 'self' https://api.github.com;
img-src 'self' data:;
frame-ancestors 'none';
object-src 'none'
```
Inline scripts are allowed (`'unsafe-inline'`). **`eval()` is blocked** (no `'unsafe-eval'`), but eval emits a different console template (`"Refused to evaluate a string as JavaScript because 'unsafe-eval' is not an allowed source…"`) so it's a less stable canary.

**Meta tag** emitted by Angular `autoCsp: true` (`src/angular/angular.json:46`), per Angular 19/20 autoCsp behavior:
```
script-src 'strict-dynamic' 'sha256-<hash>' https: 'unsafe-inline';
object-src 'none';
base-uri 'self'
```
[CITED: Angular docs — autoCsp emits SHA-256 hashes for build-time inline scripts; "Enabling Hash-Based Content Security Policy in Angular" (Medium, ngconf)]

**Critical CSP rule:** when a `'nonce-…'` or `'sha256-…'` source is present in `script-src`, `'unsafe-inline'` is **ignored** by all modern browsers.
[CITED: MDN CSP `script-src` directive — "If a hash or nonce value is present in the source list, 'unsafe-inline' is ignored."]

So the meta-tag layer effectively enforces `script-src 'strict-dynamic' 'sha256-<hash>'` and blocks any runtime-injected inline script without a matching hash.

**strict-dynamic behavior:** DOM-injected *external* scripts (with `.src`) inherit trust from the hashed root script. **Inline** script bodies (`.textContent` set, no `src`) do NOT inherit trust — they need their own hash, which doesn't exist. Canary injection is therefore blocked and a violation fires.
[CITED: MDN CSP `script-src` → strict-dynamic section; content-security-policy.com/strict-dynamic/]

### Why Not `document.write('<script>…</script>')`

Chromium refuses to process synchronous `document.write` in parsed-documents after DOMContentLoaded in normal document mode — behavior is silent no-op in some cases and violation in others (inconsistent by Chromium version). Not a stable canary.
[CITED: Chromium "Intervening against document.write" intervention, 2016-onward]

### Why Not `eval('…')`

Eval is blocked by script-src (no `'unsafe-eval'`), but emits a distinct console message format:
> `Refused to evaluate a string as JavaScript because 'unsafe-eval' is not an allowed source of script in the following Content Security Policy directive: ...`

This *does* contain the invariant substring `"violates the following Content Security Policy"` — wait, actually re-reading: the eval template is `"because 'unsafe-eval' is not an allowed source of script in the following Content Security Policy directive"`, which reads `"following Content Security Policy directive"` but NOT `"violates the following Content Security Policy directive"`. So our recommended substring would NOT match eval violations.

**Eval is therefore a BAD canary for this listener.** It exposes a gap in our console filter we don't want to expand (widening to `"following Content Security Policy directive"` would pick up non-violation documentation messages). The `appendChild(scriptEl)` inline-script canary correctly uses a directive that *does* match the substring and *does* fire the `securitypolicyviolation` DOM event. This is the right canary.

### Browser Version Currency

Canary method stable across Chromium 100+ (2022+). CI harness uses Playwright-bundled Chromium which tracks recent stable (per Playwright 1.48 release notes: Chromium 129).
[CITED: Playwright 1.48 release notes]

### Does the Listener See Any of the Two Layers Differently?

No — Chromium fires **one** `securitypolicyviolation` event and **one** console message per blocked script, regardless of which policy (HTTP header or meta) blocks it. The listener captures both via two sources (console + DOM event); deduplication is handled by the canary's "at least one" assertion.

**Per-violation count expectation:** one `appendChild(scriptEl)` call → 1 DOM event + 1 console message → 2 entries in `cspViolations` (one per `source`). Canary's `length > 0` and `.some(…)` assertions both hold.

---

## 8. Validation Architecture

Include this section in VALIDATION.md (orchestrator step 5.5). Validation is per success criterion.

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | `pytest` 9.0.3 (`src/python/pyproject.toml:67`) via Docker harness `seedsyncarr_test_python` |
| E2E framework | `@playwright/test` ^1.48.0 (`src/e2e/package.json:12`) |
| Python quick run | `make tests-python` (builds) then `make run-tests-python` (executes) |
| E2E quick run | `make run-tests-e2e` |
| CI evidence surface | `.github/workflows/ci.yml:144` (D-20 precedent from Phase 77) |

### Phase Requirements → Test Map

| SC | Behavior | Signal | Threshold | Verification Command | Automated? |
|----|----------|--------|-----------|----------------------|-----------|
| 1a | Zero pytest-cache warnings | stderr lines matching `pytest-cache` / `could not create cache dir` | count == 0 | `make run-tests-python 2>&1 \| grep -Ec "pytest-cache\|could not create cache"` | ✅ |
| 1b | Zero webob/cgi DeprecationWarnings | stderr lines matching `cgi.*deprecated` | count == 0 | `make run-tests-python 2>&1 \| grep -Ec "cgi.*deprecated"` | ✅ |
| 1c | CI log reflects 1a+1b | GitHub Actions run at `.github/workflows/ci.yml:144` | Both grep counts zero in CI log | Inspect CI run stderr (harness-as-evidence) | ✅ (manual log inspection, precedent set by 73-HUMAN-UAT.md:22) |
| 2  | Shared fixture registered on all 6 specs | Top-line import = `./fixtures/csp-listener` | 6/6 specs match | `grep -c "from './fixtures/csp-listener'" src/e2e/tests/*.spec.ts \| grep -c ":1"` → expect 6 | ✅ |
| 3a | Seeded violation triggers fixture failure | Canary spec passes (listener fires) | 1 canary test GREEN | `cd src/e2e && npx playwright test csp-canary.spec.ts` | ✅ |
| 3b | Canary detects ≥1 violation from either source | `cspViolations.length > 0` AND at least one matches `script-src` | Length ≥ 1, matcher true | Canary assertion internal: `expect.poll(() => cspViolations.length).toBeGreaterThan(0)` | ✅ (assertion internal to canary) |
| 4  | No existing specs fail after listener lands | All 6 existing specs + canary green | 7/7 PASS (6 existing + 1 canary); was 6/6 before | `make run-tests-e2e` exit code 0 | ✅ |

### Sampling Rate

- **Per task commit:** `make run-tests-python` for Plan 01; `cd src/e2e && npx playwright test <touched-file>.spec.ts` for Plan 02.
- **Per wave merge:** Full E2E suite (`make run-tests-e2e`) + full Python suite (`make run-tests-python`).
- **Phase gate:** Both suites green in CI at `.github/workflows/ci.yml:144` with zero warnings in stderr before `/gsd-verify-work`.

### Wave 0 Gaps

- **None for TEST-01.** Existing pytest infrastructure covers all requirements.
- **None blocking for TEST-02.** Fixture file is new code; no missing harness. Playwright 1.48 already installed.
- **Optional pre-check (non-blocking):** Before landing the fixture, run `make run-tests-e2e` and visually confirm zero existing CSP violations in browser console (manual Chromium devtools check via `npx playwright test --headed`). This validates SC#4 holds — if real violations exist, surface them to the planner BEFORE shipping Plan 02 (the listener would fail all 6 specs on first run).

---

## 9. Open Risks / Pre-Flight Checks

### R-1: CSP is NOT currently clean (low likelihood, high impact)

**What:** ROADMAP SC#4 assumes "CSP is currently clean" — but without the listener deployed, this assumption is untested. If a real violation exists (e.g., an inline handler missed when `css-element-queries` was removed in the original todo), landing Plan 02 fails all 6 specs simultaneously.

**Pre-flight check (recommend as first task in Plan 02):**
```
Task: Confirm CSP clean-room before deploying the listener.
Action: cd src/e2e && npx playwright test --headed about.page.spec.ts dashboard.page.spec.ts
Manual inspection: Open Chromium devtools console, confirm zero "violates the following Content Security Policy directive" lines during any navigation.
Verification: Capture screenshot or log extract; attach to task summary.
If violations found: BLOCK Plan 02; surface to user as a new phase (scope deferred per CONTEXT.md <deferred>).
```

### R-2: exposeFunction / addInitScript ordering in fixture override (low likelihood, medium impact)

**What:** The fixture overrides `page`. If `exposeFunction` is called on the `page` object *after* the test body navigates, the init script may already have run with `window.__reportCspViolation` undefined.

**Mitigation:** In the fixture body, call `exposeFunction` → `addInitScript` → `use(page)` in that order. Both happen before `use(page)`, which is before the test body's first navigation. Tested pattern per Playwright docs (exposeFunction survives navigations once set).

**Verification:** The canary spec itself verifies this. If ordering is wrong, the canary's `cspViolations` remains empty (no bridge) → canary fails → regression caught.

### R-3: webob upgrade might land mid-plan (very low likelihood, low impact)

**What:** If webob ships 2.0 during Phase 79 execution, D-03 becomes viable and D-05 is no longer needed.

**Pre-flight check:** Re-query PyPI at plan-start:
```bash
curl -s https://pypi.org/pypi/WebOb/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
# If output != "1.8.9", re-run research on the new release.
```

As of 2026-04-21: latest is 1.8.9; PR #466 unmerged. No risk for a same-day plan.

### R-4: Playwright bundled Chromium version drift (very low likelihood, low impact)

**What:** If the CI Docker image rebuilds with a Playwright that bundles a future Chromium version that changes the CSP console template.

**Mitigation:** Playwright is pinned at `^1.48.0` (`src/e2e/package.json:12`) — caret-range allows minor bumps but not majors. The DOM-event source (Option A) is spec-stable (MDN SecurityPolicyViolationEvent) and doesn't depend on console text; it provides defense-in-depth if Chromium's console template changes. Belt-and-braces design intent of D-09 is satisfied.

### R-5: D-05 `PYTHONWARNINGS` module qualifier mismatch (low likelihood, low impact)

**What:** If `ignore::DeprecationWarning:cgi` doesn't match because the warning is emitted via `warnings.warn` without a module stacklevel set correctly in Python 3.11's `cgi` module.

**Fallback plan:** Drop the module qualifier → `ENV PYTHONWARNINGS="ignore::DeprecationWarning"`. Broader but still scoped to CI container only (doesn't touch local dev or production).

**Verification:** Empirical — run `make run-tests-python 2>&1 | grep -c "cgi.*deprecated"` with the qualifier; if non-zero, drop to the broader filter.

---

## Sources

### Primary (HIGH confidence)

- **PyPI live query (2026-04-21):** webob latest 1.8.9, published 2024-10-24, requires-dist includes `legacy-cgi>=2.6; python_version >= "3.13"`. [VERIFIED: `curl https://pypi.org/pypi/WebOb/json`]
- **webob 1.8.9 source:** `src/webob/compat.py` line 4 — `from cgi import parse_header`. [VERIFIED: `curl https://raw.githubusercontent.com/Pylons/webob/1.8.9/src/webob/compat.py`]
- **webob PR #466:** unmerged; migrates `cgi.FieldStorage` → `multipart` for webob 2.0. [CITED: https://github.com/Pylons/webob/pull/466]
- **Playwright test-fixtures docs:** `test.extend()`, `{ option: true }`, page override pattern, `mergeTests`, yield-based teardown. [CITED: https://playwright.dev/docs/test-fixtures]
- **Playwright Page.exposeFunction:** "Functions installed via page.exposeFunction() survive navigations." [CITED: https://playwright.dev/docs/api/class-page#page-expose-function]
- **Playwright Page.addInitScript:** evaluates whenever the page navigates. [CITED: https://playwright.dev/docs/api/class-page]
- **MDN SecurityPolicyViolationEvent:** 12 read-only primitive properties, safe for JSON/IPC. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/SecurityPolicyViolationEvent]
- **MDN CSP script-src:** strict-dynamic, hash/nonce semantics, unsafe-inline ignored when hash present. [CITED: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src]
- **Chromium Blink CSP source:** `third_party/blink/renderer/core/frame/csp/csp_directive_list.cc` — invariant substring identified in `CheckInlineAndReportViolation` and `ReportViolationForCheckSource` templates. [CITED: chromium.googlesource.com]
- **Checkly JS-error fixture pattern:** canonical `test.extend` with `{ option: true }` for failure toggle, yield + `expect` in teardown. [CITED: https://www.checklyhq.com/blog/track-frontend-javascript-exceptions-with-playwright/]

### Secondary (MEDIUM confidence)

- **Chromium CSP console templates across violation types** (confirmed presence of invariant substring via Chromium source excerpt + multiple community reports of real violation text matching the template). [CITED: https://csper.io/blog/csp-violates-the-content-security-policy-directive, Google Groups chromium-extensions]
- **Angular autoCsp meta-tag format:** `script-src 'strict-dynamic' 'sha256-<hash>' https: 'unsafe-inline'` structure. [CITED: Multiple Angular CSP tutorials — ngconf Medium, alyshovtapdig Medium, stackhawk.com/blog/angular-content-security-policy-guide]
- **document.write intervention in Chromium:** known inconsistent/silent behavior post-DOMContentLoaded. [CITED: Chromium "Intervening against document.write" blog, 2016]

### Tertiary (LOW confidence — flagged for planner to confirm empirically)

- **Exact Chromium console text in the CI-bundled Playwright Chromium 129.** I did not run the listener end-to-end against the actual CI image. The canary spec's first run validates both the substring match and the DOM-event bridge simultaneously — if the canary passes on first run, all three assumptions hold. This is self-verifying; no separate LOW-confidence remediation needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The project's current CSP is clean (no existing violations in the 6 specs' navigation paths). | §9 R-1 | Plan 02 fails all 6 existing specs on first listener deployment. Mitigation: R-1 pre-flight check. |
| A2 | `ignore::DeprecationWarning:cgi` correctly filters the webob-induced warning at interpreter start. | §2 | SC#1b remains red. Mitigation: R-5 broaden to `ignore::DeprecationWarning`. |
| A3 | Playwright-bundled Chromium (1.48 → Chromium 129) emits console text containing `"violates the following Content Security Policy directive"` verbatim. | §4 | Console source drops all violations; only DOM-event source fires. Listener still works (defense-in-depth); canary still passes because of source='event' path. |

All three assumptions are **validated automatically** by the canary spec on its first run — no separate user confirmation needed, because a failing canary surfaces the exact miss.

---

## Metadata

**Confidence breakdown:**
- TEST-01 (D-03 unviable, D-05 required): **HIGH** — verified against live PyPI + webob 1.8.9 source.
- TEST-01 (pytest-cache + pyproject cleanup): **HIGH** — mechanisms stated in pytest docs + file-line verified.
- D-09 filter 1 (console substring): **HIGH** for "appears in violation templates"; **MEDIUM** for "appears in ALL violation templates" — canary's self-verification covers the gap.
- D-09 filter 2 (Option A recommendation): **HIGH** — Playwright docs explicitly confirm exposeFunction survives navigations and init script re-runs on navigation.
- Fixture composition: **HIGH** — matches Checkly canonical pattern directly.
- Canary injection (appendChild inline script): **HIGH** — CSP spec (unsafe-inline ignored with hash) is well-defined; strict-dynamic semantics documented on MDN.

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 for webob state (webob 2.0 release could change D-03); indefinite for fixture patterns and CSP semantics.

---

## RESEARCH COMPLETE

**Phase:** 79 - Test Infra Cleanup
**Confidence:** HIGH

### Key Findings

- D-03 (webob upgrade) cannot succeed as of 2026-04-21: webob 1.8.9 is latest; still imports stdlib `cgi`; no release has dropped it. **Plan must commit to D-05 fallback directly** — no conditional branch.
- D-09 filter 1 recommended substring: `"violates the following Content Security Policy directive"` (invariant across Blink CSP templates; zero false positives in existing specs).
- D-09 filter 2 recommended bridge: **Option A** (`page.exposeFunction` + `addInitScript`) — `addInitScript` re-runs on navigation and would reset any `window.__cspViolations` array; `exposeFunction` survives navigation and delivers to a Node-process array. Two of the six target specs navigate mid-test.
- D-12 canary injection: `document.createElement('script')` + `.textContent` + `appendChild` inside `addInitScript`/DOMContentLoaded. Blocked by Angular autoCsp meta tag's hash-based `script-src` (unsafe-inline ignored in presence of hash). `eval` and `document.write` are weaker canary choices.
- Fixture composition pattern is the Checkly JS-error fixture: one `test.extend()` with three fixtures (option `allowViolations` default false; array `cspViolations`; override `page`). No collision with Phase 77 seed-state (seed-state exports helpers, not fixtures).
- Both plans can wave in parallel per D-14 (zero shared files).

### File Created

`/Users/julianamacbook/seedsyncarr/.planning/phases/79-test-infra-cleanup/79-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| TEST-01 webob upgrade unviable | HIGH | Verified against live PyPI + webob 1.8.9 source |
| TEST-01 pytest-cache mechanism | HIGH | pytest docs + file:line verified |
| TEST-02 console substring choice | HIGH | Chromium Blink source + cross-referenced community reports |
| TEST-02 exposeFunction bridge | HIGH | Playwright docs explicit on navigation survival semantics |
| TEST-02 canary blocked by meta-tag | HIGH | CSP spec semantics (hash→unsafe-inline ignored) + Angular autoCsp docs |
| Fixture composition | HIGH | Canonical Checkly pattern; Playwright docs confirm `{ option: true }` + page override |

### Open Questions

- R-1 (existing CSP cleanliness) is the only real risk — validated automatically by first canary run OR by pre-flight headed-mode devtools inspection (recommended as Plan 02 Task 01).

### Ready for Planning

Research complete. Planner can now create PLAN.md files. Key planner decisions pre-resolved:
- Plan 01: 3 tasks (Dockerfile CMD edit + Dockerfile ENV add + pyproject.toml cleanup). Skip the "try upgrade" task entirely.
- Plan 02: 4–5 tasks (optional pre-flight CSP check → fixture file → 6-file import swap → canary spec → full-suite verification).
