# Phase 95: Test Coverage -- E2E - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 95-test-coverage-e2e
**Areas discussed:** Logs page test scope, Settings test scope & approach, SSE log delivery strategy, Config persistence verification

---

## Logs Page Test Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Structural smoke | Page load + all toolbar elements present (5 level buttons, search input, auto-scroll/clear/export buttons) + at least 1 log row renders + status bar text visible | ✓ |
| Criteria-literal | Only page load, log rows render, auto-scroll button visible. Minimal footprint | |
| Behavioral | Full behavioral coverage: filter clicks, search debounce, clear, export download, scroll mechanics | |

**User's choice:** Structural smoke (Recommended)
**Notes:** Consistent with shallow structural probe pattern used by other non-Dashboard page specs. Unit tests already cover behavioral logic.

---

## Settings Test Scope & Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Representative sample | Cover 1 field per conceptual group (text, checkbox, toggle) + floating save bar confirmation. Skip Radarr, API token, AutoQueue. ~6-8 tests | ✓ |
| All 8 cards, render-only | Assert all card headings visible + one field each. No mutations. ~12-15 assertions | |
| Two spec files (render + edit) | Separate render assertions from mutation tests. ~20 assertions across 2 files | |

**User's choice:** Representative sample (Recommended)
**Notes:** Sonarr already covered by settings-error.spec.ts, AutoQueue by autoqueue.page.spec.ts. Clipboard API unreliable in headless for token tests.

---

## SSE Log Delivery Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| API-triggered | Dispatch a command that produces predictable log entry. Tests real SSE pipeline. Organic logs as fallback | ✓ |
| Organic logs only | Wait for app's natural output. Simpler but non-deterministic timing | |
| Route interception | Mock SSE via Playwright page.route(). Deterministic but skips real pipeline | |

**User's choice:** API-triggered (Recommended)
**Notes:** Matches project pattern of E2E tests using real API endpoints against live stack. No precedent for route interception in codebase.

---

## Config Persistence Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid | One UI-to-UI round-trip test (fill → Save → reload → verify) + API shortcuts for remaining fields | ✓ |
| API-only | All fields use API shortcuts. Fast and stable but doesn't test UI input binding or save bar | |
| Full UI-to-UI | Every field through UI input → Save → reload. Thorough but slow and restart-fragile | |

**User's choice:** Hybrid (Recommended)
**Notes:** Config changes apply immediately in-memory via GET call. Save button triggers restart for LFTP reconnection/disk persistence. One UI-to-UI test proves the full flow; rest use cheaper API pattern.

---

## Claude's Discretion

None — all four areas were discussed and decided by the user.

## Deferred Ideas

None — discussion stayed within phase scope. Reviewed todos (CSP violation detection, arm64 sort, config/set migration, webob/cgi) were all either already complete or explicitly out of scope.
