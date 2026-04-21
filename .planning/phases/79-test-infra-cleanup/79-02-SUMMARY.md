---
phase: 79
plan: 02
status: complete
requirements: [TEST-02]
completed: 2026-04-21
deferred_verifications:
  - task: 79-02-01 (manual headed pre-flight)
  - task: 79-02-05 (make run-tests-e2e full-suite run)
key-files:
  created:
    - src/e2e/tests/fixtures/csp-listener.ts
    - src/e2e/tests/csp-canary.spec.ts
  modified:
    - src/e2e/tests/about.page.spec.ts
    - src/e2e/tests/app.spec.ts
    - src/e2e/tests/autoqueue.page.spec.ts
    - src/e2e/tests/dashboard.page.spec.ts
    - src/e2e/tests/settings-error.spec.ts
    - src/e2e/tests/settings.page.spec.ts
---

# Plan 79-02 — Playwright CSP fail-the-build fixture

## What shipped

A shared `test.extend()` Playwright fixture that fails any spec (unless opted out) where a CSP violation fires. Two detection sources run in parallel:

1. `page.on('console')` filtered by the invariant substring `"violates the following Content Security Policy directive"` (Chromium emits this in both inline and URL-violation templates — verified against `third_party/blink/renderer/core/frame/csp/csp_directive_list.cc` per RESEARCH §4).
2. `document.addEventListener('securitypolicyviolation', …)` injected via `addInitScript`, bridged back to Node via `page.exposeFunction('__reportCspViolation', …)`.

### Commits

| Task | Commit | What |
|------|--------|------|
| Task 2 | `2253353` | New fixture `src/e2e/tests/fixtures/csp-listener.ts` — 61 lines, exports `{ test, expect }`, composes 3 fixtures (`allowViolations` option, `cspViolations` array, `page` override) |
| Task 3 | `8d28c94` | Line-1 import swap on 6 existing spec files (`about.page`, `app`, `autoqueue.page`, `dashboard.page`, `settings-error`, `settings.page`) — single-line diff each, zero collateral |
| Task 4 | `a5f8c88` | New canary spec `src/e2e/tests/csp-canary.spec.ts` — opts out via `test.use({ allowViolations: true })`, injects inline `<script>` via `appendChild` on `DOMContentLoaded`, asserts poll ≥1 + `script-src` match |

### Load-bearing ordering inside the `page` fixture (RESEARCH §9 R-2)

```
1. exposeFunction('__reportCspViolation', …)       // survives navigations; Node-side sink
2. addInitScript(() => addEventListener('securitypolicyviolation', …))   // re-runs every nav
3. page.on('console', msg => …)                    // defense-in-depth
4. await use(page)                                  // hand to test body
5. if (!allowViolations) expect(cspViolations).toEqual([])   // teardown assertion
```

Verified via awk-based line-order check in worktree — see commit `2253353` and 79-02-PLAN.md Task 2 acceptance.

## Decisions realized

- **D-07** fixture module naming (`fixtures/csp-listener.ts` — follows `seed-state.ts` convention, no barrel file).
- **D-08** drop-in import swap (one line per spec, no test-body changes).
- **D-09** two-source detection (console filter + DOM event bridge).
- **D-10** per-test opt-out (`allowViolations` as an option tuple so `test.use()` per-file override works).
- **D-11** permanent canary spec lives in the main suite (not one-shot).
- **D-12** injection method: `appendChild` on `DOMContentLoaded` (RESEARCH §7 ruled out `document.write` — Chromium intervention disallows it post-DCL — and `eval` — its console template lacks the invariant substring).
- **D-13** canary hits real backend CSP header + real Angular autoCsp meta tag, no mocks.

## Static acceptance (all passed in worktree)

### Fixture file

```
export const test = base.extend                              → 1
export { expect }                                             → 1
exposeFunction('__reportCspViolation'                         → 1
addInitScript                                                 → 1
addEventListener('securitypolicyviolation'                   → 1
page.on('console'                                             → 1
violates the following Content Security Policy directive     → 1
allowViolations: [false, { option: true }]                   → 1
toEqual([])                                                   → 1
export interface CspViolation                                 → 1
Load-bearing line order (expose < init < console < use < expect)  → ORDER-OK
```

### Import swaps

```
grep -l "^import { test, expect } from './fixtures/csp-listener';" (6 specs)  → 6
grep -l "^import { test, expect } from '@playwright/test';" (any spec)        → 0
dashboard line 3 seed-state import intact                                     → yes
playwright.config.ts still imports from '@playwright/test'                    → unchanged
```

### Canary spec

```
import from './fixtures/csp-listener'                  → 1
test.use({ allowViolations: true })                     → 1
document.createElement('script')                        → 1
document.write (forbidden)                              → 0
eval (forbidden)                                        → 0
expect.poll                                             → 1
script-src                                              → 2
```

## Runtime verifications (deferred)

Two tasks in this plan require a live app stack that is not available from the orchestrator environment. Both are deferred to manual / CI execution, consistent with Plan 01's arm64 deferral pattern.

| Task | What | Why deferred | Owner |
|------|------|--------------|-------|
| 79-02-01 | Manual headed Playwright + Chromium DevTools pre-flight (CSP clean-room check per RESEARCH §9 R-1) | Requires GUI Chromium session with DevTools Console inspection — cannot be automated | Human operator, before merge OR post-merge if canary passes |
| 79-02-05 | `make run-tests-e2e` full-suite run (SC #2/#3/#4 automation) | Requires pre-staged Docker image from the registry + `STAGING_VERSION` / `SEEDSYNCARR_ARCH` env vars + full Docker Compose stack spin-up | CI run on the merge commit (`.github/workflows/ci.yml`) |

**Safety net:** Task 5's automated full-suite run is itself the fallback for Task 1. If real CSP violations exist on the paths exercised by the 6 existing specs, every spec will fail with `CSP violations detected` in its fixture teardown. The remediation path (CONTEXT.md `<deferred>`) is the same either way: roll back the 6 import swaps (trivial) and surface a follow-up phase for real-violation cleanup.

**Canary self-verification (RESEARCH §9 R-2 A1/A2/A3):** If the canary spec passes on first CI run, three research assumptions are simultaneously validated:
- A1: current CSP is clean (the seeded injection gets blocked → current policy is active and effective)
- A2: `exposeFunction` → `addInitScript` bridge wiring is correct (violation reached Node side)
- A3: Chromium CSP console text still contains the invariant substring (console source matched)

A single green canary run closes the same research risks the manual pre-flight was designed to close.

**If canary fails in CI:** see 79-02-PLAN.md Task 5 "If failures" decision tree — maps failure mode → root cause (bridge broken, substring drift, CSP weakened).

## Follow-ups

None required pre-merge. Post-merge CI is the live runtime verification checkpoint.

## Self-Check: PASSED (static acceptance; runtime deferred per documented plan exemption for GUI + full-stack verifications)
