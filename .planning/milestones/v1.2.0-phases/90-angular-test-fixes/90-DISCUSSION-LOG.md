# Phase 90: Angular Test Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 90-angular-test-fixes
**Areas discussed:** None (user elected Claude's discretion)

---

## Gray Areas Presented

| Option | Description | Selected |
|--------|-------------|----------|
| Subscription teardown strategy | How to clean up subscriptions across 4 affected spec files | |
| Optional chaining guard approach | How to handle ~30 optional-chained assertions that silently pass on undefined | |
| fakeAsync cleanup scope | Which fakeAsync specs need discardPeriodicTasks() | |
| Skip -- Claude's discretion | Same as Phases 87/88: requirements are fully specified | ✓ |

**User's choice:** Skip -- Claude's discretion
**Notes:** Consistent with Phases 87 and 88 where user also skipped discussion for well-specified test fix phases. All 7 requirements (ANGFIX-01 through ANGFIX-07) have exact file locations and bug descriptions in REQUIREMENTS.md.

---

## Claude's Discretion

All implementation decisions deferred to Claude:
- Subscription teardown strategy (afterEach unsubscribe vs per-test vs DestroyRef)
- fakeAsync cleanup scope (named spec only vs audit all 23)
- Optional chaining guard approach (toBeDefined() guards vs restructuring)
- Double-cast fix approach
- EventEmitter leak fix approach

## Deferred Ideas

None -- discussion stayed within phase scope.
