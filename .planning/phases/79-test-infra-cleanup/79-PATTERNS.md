# Phase 79: Test Infra Cleanup — Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 9 (2 Plan 01 + 7 Plan 02)
**Analogs found:** 9 / 9

## File Classification

| Target File | Plan | Role | Data Flow | Closest Analog | Match Quality |
|-------------|------|------|-----------|----------------|---------------|
| `src/docker/test/python/Dockerfile` (MOD, line 45 CMD + ENV add) | 01 | docker-config | build-time config | Self (current Dockerfile lines 42–45) | exact (self-edit; surgical) |
| `src/python/pyproject.toml` (MOD, delete lines 74–77) | 01 | test-config | test-runner config | Self (existing `[tool.pytest.ini_options]` block) | exact (self-edit; subtraction only) |
| `src/e2e/tests/fixtures/csp-listener.ts` (CREATE) | 02 | playwright-fixture | event-driven (browser→Node via exposeFunction) | `src/e2e/tests/fixtures/seed-state.ts` (directory/export convention) + Checkly pattern in RESEARCH §5 | role-match (directory + TS style); new fixture shape (first `test.extend()` in repo) |
| `src/e2e/tests/csp-canary.spec.ts` (CREATE) | 02 | playwright-spec | request-response (navigate + assert) | `src/e2e/tests/about.page.spec.ts` (minimal spec shape) | role-match |
| `src/e2e/tests/about.page.spec.ts` (MOD, line 1 import swap) | 02 | playwright-spec | — | Self | exact |
| `src/e2e/tests/app.spec.ts` (MOD, line 1 import swap) | 02 | playwright-spec | — | Self | exact |
| `src/e2e/tests/autoqueue.page.spec.ts` (MOD, line 1 import swap) | 02 | playwright-spec | — | Self | exact |
| `src/e2e/tests/dashboard.page.spec.ts` (MOD, line 1 import swap) | 02 | playwright-spec | — | Self | exact |
| `src/e2e/tests/settings-error.spec.ts` (MOD, line 1 import swap) | 02 | playwright-spec | — | Self | exact |
| `src/e2e/tests/settings.page.spec.ts` (MOD, line 1 import swap) | 02 | playwright-spec | — | Self | exact |

---

## Pattern Assignments

### Plan 01 — TEST-01

#### `src/docker/test/python/Dockerfile` (docker-config, build-time)

**Analog:** Self — current Dockerfile, lines 40–45.

**Current state** (`src/docker/test/python/Dockerfile:40-45`):
```dockerfile
# src needs to be mounted on /src/
WORKDIR /src/
ENV PYTHONPATH=/src

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["pytest", "-v"]
```

**Delta (after Plan 01 lands):**
```dockerfile
# src needs to be mounted on /src/
WORKDIR /src/
ENV PYTHONPATH=/src
ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["pytest", "-v", "-p", "no:cacheprovider"]
```

Two concrete edits:
1. **D-01 / line 45:** replace `CMD ["pytest", "-v"]` with `CMD ["pytest", "-v", "-p", "no:cacheprovider"]`.
2. **D-05 / insert after line 42:** new line `ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"` (module qualifier is `cgi`, not `webob` — RESEARCH §2 confirms origin module).

**Acceptance greps:**
```bash
grep -c 'CMD \["pytest", "-v", "-p", "no:cacheprovider"\]' src/docker/test/python/Dockerfile
# Expected: 1
grep -c 'ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"' src/docker/test/python/Dockerfile
# Expected: 1
```

Runtime verification (RESEARCH §8 SC 1a/1b):
```bash
make run-tests-python 2>&1 | grep -Ec "pytest-cache|could not create cache"
# Expected: 0
make run-tests-python 2>&1 | grep -Ec "cgi.*deprecated"
# Expected: 0
```

---

#### `src/python/pyproject.toml` (test-config, subtraction only)

**Analog:** Self — current `[tool.pytest.ini_options]` block, lines 71–77.

**Current state** (`src/python/pyproject.toml:71-77`):
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
timeout = 60
cache_dir = "/tmp/.pytest_cache"
filterwarnings = [
    "ignore:'cgi' is deprecated:DeprecationWarning",
]
```

**Delta (after Plan 01 lands)** — delete lines 74–77, leaving:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
timeout = 60
```

Two concrete deletions in one edit:
1. **D-02 / line 74:** delete `cache_dir = "/tmp/.pytest_cache"`.
2. **D-04 / lines 75–77:** delete the `filterwarnings = [...]` key and its list (including the closing `]`).

No replacement entries. Lines 79+ (`[tool.coverage.*]`) are untouched.

**Acceptance greps:**
```bash
grep -c 'cache_dir' src/python/pyproject.toml
# Expected: 0
grep -c 'filterwarnings' src/python/pyproject.toml
# Expected: 0
grep -c 'cgi.*deprecated' src/python/pyproject.toml
# Expected: 0
# Positive control — ensure we didn't blow away the whole section:
grep -c '\[tool.pytest.ini_options\]' src/python/pyproject.toml
# Expected: 1
grep -c 'pythonpath = \["\."\]' src/python/pyproject.toml
# Expected: 1
```

---

### Plan 02 — TEST-02

#### `src/e2e/tests/fixtures/csp-listener.ts` (CREATE, playwright-fixture, event-driven)

**Analog (directory + TS style):** `src/e2e/tests/fixtures/seed-state.ts` (lines 1–11, 37–44).
**Analog (fixture shape):** Checkly JS-error fixture pattern, already inlined in RESEARCH §5 (code block spanning RESEARCH.md lines 278–345).

**Imports pattern** (`src/e2e/tests/fixtures/seed-state.ts:1-2`):
```typescript
import type { Page } from '@playwright/test';

// Typed seed API — see .planning/phases/77-deferred-playwright-e2e-phases-72-73
```

The new fixture diverges: it needs runtime access to `test.extend`, `expect`, and `Page` (value, not just type). Correct import per RESEARCH §5:
```typescript
import { test as base, expect, type Page } from '@playwright/test';
```

**Exported-types convention** (`src/e2e/tests/fixtures/seed-state.ts:6-11`):
```typescript
export type SeedTarget = 'DOWNLOADED' | 'STOPPED' | 'DELETED';

export interface SeedPlanItem {
    file: string;
    target: SeedTarget;
}
```
Follow this style — name the violation type `CspViolation` and export it as an `interface` (RESEARCH §5 already spells out the 7 fields: `source`, `blockedURI?`, `violatedDirective?`, `originalPolicy?`, `sourceFile?`, `lineNumber?`, `sample?`, `text?`).

**Guard/error-raising convention** (`src/e2e/tests/fixtures/seed-state.ts:37-44`) — function throws with a specific, debug-friendly message:
```typescript
async function expectOk(page: Page, url: string, method: 'POST' | 'DELETED'): Promise<void> {
    const res = method === 'POST'
        ? await page.request.post(url)
        : await page.request.delete(url);
    if (!res.ok()) {
        throw new Error(`Seed call ${method} ${url} failed: ${res.status()} ${await res.text()}`);
    }
}
```
Applied to the CSP fixture: the teardown `expect(cspViolations).toEqual([])` should fail with a message that shows the full violation list — Playwright's `expect` second-argument label (`expect(cspViolations, 'CSP violations detected').toEqual([])`) per RESEARCH §5 satisfies this.

**Fixture body / core pattern** — verbatim from RESEARCH §5 (lines 278–345 in RESEARCH.md). The planner copies that block into `src/e2e/tests/fixtures/csp-listener.ts`. Key structural properties the planner must preserve:

1. **Ordering inside the `page` fixture override** (enforced by RESEARCH §9 R-2):
   - Call `page.exposeFunction('__reportCspViolation', …)` FIRST.
   - Call `page.addInitScript(() => { document.addEventListener('securitypolicyviolation', …) })` SECOND.
   - Register `page.on('console', …)` THIRD.
   - Then `await use(page)`.
   - Then the teardown: `if (!allowViolations) expect(cspViolations, 'CSP violations detected').toEqual([])`.

2. **Console filter substring (D-09 filter 1)** — exact literal: `'violates the following Content Security Policy directive'`. Paired with `msg.type() === 'error'` type guard.

3. **Option/fixture tuples (Playwright TS):**
   - `allowViolations: [false, { option: true }]` — makes the flag overridable per-file via `test.use({ allowViolations: true })`.
   - `cspViolations: async ({}, use) => { await use([]); }` — plain array fixture, fresh `[]` per test.

4. **Exports** — `export const test = base.extend<Fixtures>({ … })` AND `export { expect }` so import-swapping callers keep the same API surface they had with `@playwright/test`.

**Error handling / IPC safety** — RESEARCH §5 "Serialization Note": do NOT pass the raw `SecurityPolicyViolationEvent`; project it into a plain object literal inside the init-script listener. The RESEARCH §5 code block already does this correctly (six primitive fields destructured).

**Acceptance greps:**
```bash
# File exists with the right exports:
grep -c "^export const test = base.extend" src/e2e/tests/fixtures/csp-listener.ts
# Expected: 1
grep -c "^export { expect }" src/e2e/tests/fixtures/csp-listener.ts
# Expected: 1
grep -c "exposeFunction('__reportCspViolation'" src/e2e/tests/fixtures/csp-listener.ts
# Expected: 1
grep -c "addEventListener('securitypolicyviolation'" src/e2e/tests/fixtures/csp-listener.ts
# Expected: 1
grep -c "violates the following Content Security Policy directive" src/e2e/tests/fixtures/csp-listener.ts
# Expected: 1
grep -c "allowViolations: \[false, { option: true }\]" src/e2e/tests/fixtures/csp-listener.ts
# Expected: 1
```

---

#### Spec file import swap (×6) — `about.page.spec.ts`, `app.spec.ts`, `autoqueue.page.spec.ts`, `dashboard.page.spec.ts`, `settings-error.spec.ts`, `settings.page.spec.ts`

**Analog:** self — each file's current line 1.

**Current state (uniform across all 6 files, verified by grep on 2026-04-21):**
```typescript
import { test, expect } from '@playwright/test';
```

**Delta — single-line edit to line 1 of each file:**
```typescript
import { test, expect } from './fixtures/csp-listener';
```

Notes per file (from earlier reads — all confirmed line 1 is the target):

| File | Lines | Line 2 (unchanged, shown for anchor) |
|------|-------|--------------------------------------|
| `about.page.spec.ts` | 21 | `import { AboutPage } from './about.page';` |
| `app.spec.ts` | 32 | `import { App } from './app';` |
| `autoqueue.page.spec.ts` | 77 | `import { AutoQueuePage } from './autoqueue.page';` |
| `dashboard.page.spec.ts` | 516 | `import { DashboardPage, FileInfo } from './dashboard.page';` — **also imports `./fixtures/seed-state` on line 3; the new `./fixtures/csp-listener` import on line 1 does not conflict (different module, different symbols).** |
| `settings-error.spec.ts` | 29 | `import { SettingsPage } from './settings.page';` |
| `settings.page.spec.ts` | 14 | `import { SettingsPage } from './settings.page';` |

**Acceptance greps (run once, expects 6-of-6 conversion):**
```bash
# After-state: each file imports from the new fixture exactly once on line 1
for f in about.page.spec.ts app.spec.ts autoqueue.page.spec.ts dashboard.page.spec.ts settings-error.spec.ts settings.page.spec.ts; do
  grep -c "^import { test, expect } from './fixtures/csp-listener';" "src/e2e/tests/$f"
done | grep -c '^1$'
# Expected: 6

# Negative control — no file still imports test/expect directly from @playwright/test:
grep -l "^import { test, expect } from '@playwright/test';" src/e2e/tests/*.spec.ts
# Expected: (empty — no output)
```

**Scope fence** — `playwright.config.ts` imports `defineConfig, devices` from `@playwright/test` and MUST stay untouched (not a spec). Page-object files (`about.page.ts`, `dashboard.page.ts`, etc.) do not import `test`/`expect` and stay untouched too.

---

#### `src/e2e/tests/csp-canary.spec.ts` (CREATE, playwright-spec)

**Analog (spec shape):** `src/e2e/tests/about.page.spec.ts` (minimal 21-line spec — smallest structural template).
**Analog (canary body):** RESEARCH §6 "Opt-Out Mechanism for D-12 Canary" code block (RESEARCH.md lines 386–416).

**Imports pattern** (from `about.page.spec.ts:1-2`, adapted):
```typescript
// about.page.spec.ts line 1 — before swap:
import { test, expect } from '@playwright/test';
// Canary spec (new file) — use the swapped-in fixture path:
import { test, expect } from './fixtures/csp-listener';
```

**Core spec pattern** — two building blocks, both already present in the codebase and RESEARCH:

1. **Per-file opt-out** (new in this phase; no existing analog — come from RESEARCH §6):
   ```typescript
   test.use({ allowViolations: true });
   ```
   Placed at file top, before the `test(...)` call.

2. **Spec body** — verbatim from RESEARCH §6 (lines 392–415 in RESEARCH.md). The planner copies that body. Key invariants:
   - Injection via `page.addInitScript(() => { window.addEventListener('DOMContentLoaded', () => { const el = document.createElement('script'); el.textContent = 'window.__canaryRan = true;'; document.body.appendChild(el); }); })` — **not** `document.write`, **not** `eval` (RESEARCH §7 rejects both).
   - Navigation target: `await page.goto('/')` (matches the default app landing; no auth interaction needed per CONTEXT.md `<code_context>` "CSP fixture does not interact with auth").
   - Primary assertion: `await expect.poll(() => cspViolations.length).toBeGreaterThan(0)`.
   - Tighter matcher: `expect(cspViolations.some(v => (v.source === 'event' && v.violatedDirective?.startsWith('script-src')) || (v.source === 'console' && v.text?.includes('script-src')))).toBe(true)`.

**describe-block convention** (observed across all 6 existing specs — `about.page.spec.ts:4`, `app.spec.ts:4`, `autoqueue.page.spec.ts:4`, `settings.page.spec.ts:4`):
```typescript
test.describe('Testing <domain>', () => {
    test('<behavior>', async ({ page }) => { … });
});
```
Canary file may or may not wrap in `test.describe` — the repo has both styles (UAT blocks in `dashboard.page.spec.ts` use `describe`, simple specs wrap all tests in one `describe`). Recommend one `test.describe('CSP violation canary', …)` around the single test for grep/report readability.

**Error handling** — none required in the test body; the fixture teardown is the safety net (but since `allowViolations: true` is set, the teardown no-ops). The spec's own `expect.poll` is the failure surface.

**Acceptance greps:**
```bash
# File lands:
test -f src/e2e/tests/csp-canary.spec.ts && echo OK
# Expected: OK

# Imports from the new fixture:
grep -c "^import { test, expect } from './fixtures/csp-listener';" src/e2e/tests/csp-canary.spec.ts
# Expected: 1

# Opts out of the default assertion:
grep -c "test.use({ allowViolations: true })" src/e2e/tests/csp-canary.spec.ts
# Expected: 1

# Injection technique is correct (NOT document.write, NOT eval):
grep -c "document.createElement('script')" src/e2e/tests/csp-canary.spec.ts
# Expected: 1
grep -c "document.write" src/e2e/tests/csp-canary.spec.ts
# Expected: 0
grep -c "eval(" src/e2e/tests/csp-canary.spec.ts
# Expected: 0

# Runtime verification (RESEARCH §8 SC 3a):
# cd src/e2e && npx playwright test csp-canary.spec.ts
# Expected: 1 passed
```

---

## Shared Patterns

### Pattern S-1 — Fixtures directory convention (Plan 02 scope)

**Source:** `src/e2e/tests/fixtures/seed-state.ts` (existing; Phase 77 Pattern).
**Apply to:** `src/e2e/tests/fixtures/csp-listener.ts` (new file placement).

Fixtures go in `src/e2e/tests/fixtures/` alongside `seed-state.ts`. Specs import them via relative path `./fixtures/<name>` (confirmed by `dashboard.page.spec.ts:3` — `import { seedMultiple, seedStatus } from './fixtures/seed-state';`).

No barrel file (`fixtures/index.ts`) exists; do NOT create one. Each fixture module is imported directly.

### Pattern S-2 — Top-line test/expect import uniformity

**Source:** all 6 spec files as of HEAD (`import { test, expect } from '@playwright/test'` on line 1 of each).
**Apply to:** the import-swap task — mechanical across all 6 files.

RESEARCH §8 SC#2 verification grep depends on this uniformity:
```bash
for f in src/e2e/tests/{about.page,app,autoqueue.page,dashboard.page,settings-error,settings.page}.spec.ts; do
  grep -c "from './fixtures/csp-listener'" "$f"
done | grep -c '^1$'
# Expected: 6
```

### Pattern S-3 — TypeScript strictness (no `any` without escape hatch)

**Source:** `src/e2e/tests/fixtures/seed-state.ts:14` — `const ENDPOINT = { … } as const;` (readonly-narrowed types).
**Apply to:** `src/e2e/tests/fixtures/csp-listener.ts` — the `CspViolation` interface must fully type all 7 fields. The RESEARCH §5 code block uses a `// @ts-ignore — exposed function on window` comment on the single line where the init script calls `window.__reportCspViolation`; this is acceptable (the function is injected by Playwright at runtime and has no static declaration). No other `any` or `@ts-ignore` is expected.

### Pattern S-4 — Backend CSP sources are READ-ONLY

**Source:** CONTEXT.md `<canonical_refs>` "CSP policy sources (read-only — do not modify)":
- `src/python/web/web_app.py:152-162`
- `src/angular/angular.json:46`

**Apply to:** every file in both plans. Neither plan reads these files during implementation; the fixture and canary must work against the *live* headers served by the running app, not by mocking/reshaping the policy. RESEARCH §7 explicitly relies on Angular autoCsp's hash-based `script-src` remaining as-is.

---

## No Analog Found

None. Every target file has an adequate analog:

- **Dockerfile CMD/ENV edits:** self-edits (subtractive/additive on existing lines).
- **pyproject.toml edits:** self-edits (pure subtraction).
- **Fixture file:** directory convention from `seed-state.ts`; fixture shape from RESEARCH §5 (Checkly pattern inlined in research doc, not elsewhere in repo).
- **Canary spec:** spec-shell shape from `about.page.spec.ts`; body from RESEARCH §6 (already inlined).
- **6 import swaps:** self-edits (line-1 replacement).

RESEARCH §5 and §6 function as the *effective* code-level analog for the two new TS files — the planner should copy those RESEARCH code blocks directly rather than paraphrase.

---

## Metadata

**Analog search scope:**
- `src/docker/test/python/` (2 files — Dockerfile + compose.yml)
- `src/python/pyproject.toml` (self)
- `src/e2e/tests/fixtures/` (1 file — `seed-state.ts`)
- `src/e2e/tests/*.spec.ts` (6 target files, all sampled for line-1 import)
- `src/e2e/playwright.config.ts` (scope-fence: stays on `@playwright/test`)

**Files scanned:** 11
**Pattern extraction date:** 2026-04-21
**Upstream docs read:** `79-CONTEXT.md` (full), `79-RESEARCH.md` (full). Project `CLAUDE.md` absent in repo root (no project-level constraints beyond the global MEMORY note, which the AIDesigner HTML-identity rule explicitly excludes test-infra).
