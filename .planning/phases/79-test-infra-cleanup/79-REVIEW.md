---
phase: 79
phase_name: test-infra-cleanup
status: clean
reviewed: 2026-04-21
depth: standard
files_reviewed: 10
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
---

# Phase 79: Code Review Report

## Summary

Phase 79 ships two tightly-scoped, low-risk changes:

- **79-01 (Python CI stderr cleanup):** Surgical edits to `src/docker/test/python/Dockerfile` (adds `PYTHONWARNINGS="ignore::DeprecationWarning:cgi"` env + `-p no:cacheprovider` to pytest CMD) and `src/python/pyproject.toml` (removes dead `cache_dir` and non-matching `filterwarnings` entries). Both changes are correct, scoped to the test container, and do not affect production.

- **79-02 (Playwright CSP fixture):** New shared `test.extend()` fixture at `src/e2e/tests/fixtures/csp-listener.ts` bridges `page.on('console')` CSP messages with `securitypolicyviolation` DOM events via `page.exposeFunction`. The load-bearing ordering (`exposeFunction` → `addInitScript` → `page.on('console')` → `use(page)` → teardown assertion) is preserved exactly as specified in RESEARCH §9 R-2. Six existing spec files receive single-line import swaps; a new canary spec self-verifies the fixture by seeding an inline-script violation.

No Critical or Warning findings. Three Info-level suggestions follow — all advisory, none block the phase.

## Critical Issues

_None._

## Warnings

_None._

## Info

### IN-01: Prefer `@ts-expect-error` over `@ts-ignore`

**File:** `src/e2e/tests/fixtures/csp-listener.ts:33`

**Issue:** Line 33 uses `// @ts-ignore — exposed function on window at runtime`. `@ts-ignore` silently suppresses any error; `@ts-expect-error` additionally fails if the line ever stops having an error (e.g., if someone later adds a proper `declare global { interface Window { __reportCspViolation: ... } }` or the type surface changes). This makes the suppression self-healing.

**Fix:**
```typescript
// @ts-expect-error — exposed function on window at runtime
window.__reportCspViolation({ ... });
```

Alternatively, add a `declare global` block scoped to the file so the cast is unnecessary:
```typescript
declare global {
    interface Window {
        __reportCspViolation: (v: Omit<CspViolation, 'source'>) => void;
    }
}
```

### IN-02: `expect.poll` relies on default timeout in canary

**File:** `src/e2e/tests/csp-canary.spec.ts:17`

**Issue:** `await expect.poll(() => cspViolations.length).toBeGreaterThan(0);` uses Playwright's default poll timeout (5s). The canary is self-verifying and load-bearing for the whole fixture. If CI has a cold Chromium start or the init-script roundtrip is slow, a default timeout could flake. The risk is low (seeded violations fire as soon as DOMContentLoaded runs and the injected script is parsed), but a modest explicit timeout would harden the canary against CI variance.

**Fix:**
```typescript
await expect.poll(
    () => cspViolations.length,
    { timeout: 10_000, message: 'Canary never observed a CSP violation — fixture bridge may be broken' },
).toBeGreaterThan(0);
```

### IN-03: `cspViolations` fixture uses empty-destructure pattern

**File:** `src/e2e/tests/fixtures/csp-listener.ts:22`

**Issue:** `cspViolations: async ({}, use) => { await use([]); }` uses the `{}` empty-destructure for the first argument. This is the standard Playwright idiom for a fixture with no dependencies, but some ESLint configs flag it as `no-empty-pattern`. Not a bug — just worth knowing if the repo later enables that rule. No change needed unless the rule fires.

**Fix (only if ESLint flags it):**
```typescript
// eslint-disable-next-line no-empty-pattern
cspViolations: async ({}, use) => {
    await use([]);
},
```

## Verification Notes

- **R-2 ordering (RESEARCH §9):** Confirmed. `exposeFunction` (line 27) precedes `addInitScript` (line 31), which precedes `page.on('console')` (line 45), which precedes `use(page)` (line 53). Teardown assertion is last (lines 55-57). Any reordering would be a Critical issue; none detected.
- **Serialization safety:** The `addInitScript` body (lines 34-41) explicitly enumerates 6 primitive fields of `SecurityPolicyViolationEvent` rather than passing the raw event. Matches RESEARCH §5 IPC-safety guidance.
- **`source` field integrity:** The spread `{ ...v, source: 'event' }` on line 28 overwrites any `source` key the browser side might inject; the browser body never sends `source`, so this is belt-and-braces and correct.
- **6 line-1 import swaps:** All verified identical — `import { test, expect } from './fixtures/csp-listener';`.
- **`PYTHONWARNINGS` module qualifier:** `ignore::DeprecationWarning:cgi` matches Python's documented `action::category:module:lineno` format. RESEARCH R-5 already documents the fallback (drop `:cgi` qualifier) if it fails empirically.
- **No secrets, dangerous calls, or injection surfaces introduced by this diff.** The canary's inline-script injection is the intentional test subject and is scoped to a single opted-out spec file.

## Files Reviewed

- `src/docker/test/python/Dockerfile` — Python test container (79-01)
- `src/python/pyproject.toml` — `[tool.pytest.ini_options]` slimmed (79-01)
- `src/e2e/tests/fixtures/csp-listener.ts` — new CSP listener fixture (79-02)
- `src/e2e/tests/csp-canary.spec.ts` — new canary spec (79-02)
- `src/e2e/tests/about.page.spec.ts` — line-1 import swap (79-02)
- `src/e2e/tests/app.spec.ts` — line-1 import swap (79-02)
- `src/e2e/tests/autoqueue.page.spec.ts` — line-1 import swap (79-02)
- `src/e2e/tests/dashboard.page.spec.ts` — line-1 import swap (79-02)
- `src/e2e/tests/settings-error.spec.ts` — line-1 import swap (79-02)
- `src/e2e/tests/settings.page.spec.ts` — line-1 import swap (79-02)
