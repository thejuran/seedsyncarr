# Phase 91: E2E Test Fixes & Platform - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 91-e2e-test-fixes-platform
**Areas discussed:** None (user elected Claude's discretion)

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| CSP enforcement scope | PLAT-01: CSP listener fixture exists, dashboard beforeAll bypasses it | |
| arm64 Unicode sort strategy | PLAT-02: locale-dependent collation options | |
| Deprecated selector migration | E2EFIX-05/07: :has-text() and _escapeRegex dedup | |
| Skip — all Claude's discretion | Requirements fully specified, let Claude decide all | ✓ |

**User's choice:** Skip — all Claude's discretion
**Notes:** Same approach as Phase 90 (Angular Test Fixes). Requirements are specific enough that no discussion needed.

---

## Claude's Discretion

All 9 implementation decisions (D-01 through D-09) delegated to Claude:
- E2EFIX-01: innerHTML→innerText in autoqueue.page.ts
- E2EFIX-02: beforeEach ordering in settings-error.spec.ts
- E2EFIX-03: waitForTimeout replacement in dashboard.page.spec.ts
- E2EFIX-04: CSP fixture bypass in dashboard beforeAll
- E2EFIX-05: :has-text() migration in autoqueue.page.ts
- E2EFIX-06: HTTP response checking in dashboard spec
- E2EFIX-07: _escapeRegex deduplication
- PLAT-01: CSP enforcement scope
- PLAT-02: arm64 Unicode sort strategy

## Deferred Ideas

None mentioned during discussion.
