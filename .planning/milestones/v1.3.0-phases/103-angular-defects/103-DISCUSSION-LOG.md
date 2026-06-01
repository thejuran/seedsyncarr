# Phase 103: Angular Defects - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in `103-CONTEXT.md` — this log preserves the discussion.

**Date:** 2026-05-31
**Phase:** 103-angular-defects
**Mode:** discuss (interactive, 4 areas in one batch)
**Areas discussed:** Modal build approach, skipCount hardening, SSE fix scope, Plan shape & E2E depth

## Questions Asked

### Q1 — BUG-01: Modal build approach
- **Options presented:**
  - Renderer2 + createText nodes (same service, smallest diff, escaping becomes structural, remove escapeHtml) — *recommended*
  - Standalone Angular component + {{ }} template (idiomatic, but large refactor)
- **User selected:** Renderer2 + createText nodes
- **Note:** Captured as D-01/D-02/D-03. Renderer2 already injected; work is replacing the single innerHTML assignment + removing dead escapeHtml. Slice-1 DOM-level security assertions preserved; mechanism-specific (entity-encoding) assertions updated to structural equivalents.

### Q2 — BUG-01 fold-in: skipCount hardening
- **Options presented:**
  - Coerce Number() + update the slice-1 probe — *recommended*
  - Structural rendering makes it inherently safe (no Number() coercion)
- **User selected:** Coerce Number() + update the slice-1 probe
- **Note:** Captured as D-04/D-05. `const n = Number(options.skipCount); if (Number.isFinite(n) && n > 0)`. The slice-1 runtime-boundary probe (spec lines 690-720) currently pins the un-hardened `<img>`-injection behavior with a "deferred to v1.4.0" comment — this phase resolves that deferral, so the probe is updated to assert no `<img>` and the comment rewritten. In-scope, expected test change.

### Q3 — BUG-04: SSE fix scope
- **Options presented:**
  - Audit + harden teardown ordering, regression-test the same-tick path — *recommended*
  - Add an explicit single-flight reconnect guard (`_reconnectPending` boolean)
- **User selected:** Audit + harden teardown ordering, regression-test the same-tick path
- **Note:** Captured as D-06/D-07/D-08. `_currentSubscription?.unsubscribe()` teardown already exists (registry.ts:181-182); work = audit the three reconnect-arming paths (timeout / error / re-subscribe) for a same-tick double-arm, harden only a confirmed gap, and pin the exactly-one-subscription invariant with a new test. Single-flight boolean is the fallback (D-07) if clear-and-reset proves insufficient. Slice-1 heartbeat-vs-timeout race suite preserved (D-08).

### Q4 — Plan shape & E2E depth
- **Options presented:**
  - Two independent plans (BUG-01, BUG-04), test-first each — *recommended*
  - Single combined plan
- **User selected:** Two independent plans, test-first each
- **Note:** Captured as D-09/D-10. `103-01` = BUG-01, `103-02` = BUG-04; no ordering dependency, separately bisectable. Karma floors 83/68/79/83 hold or rise. Confirm modal is user-visible (UI hint yes) — manual/Playwright smoke deferred to the milestone-end walkthrough; no new heavy E2E spec this phase.

## Claude's Discretion (recorded)
- Element-construction helper structure in `createModal()` (inline vs private `buildModalContent()`).
- Keep `data-action` button hooks (querySelector wiring depends on them).
- Whether BUG-04 needs the `_reconnectPending` single-flight boolean — decided by the audit.
- New BUG-04 test placement (inside existing `heartbeat-vs-timeout race` describe vs new sibling).

## Deferred / Out of Scope
- Full standalone `ConfirmModalComponent` migration — rejected as out-of-scope refactor (could be a future cleanup phase).
- No new deferred items; the slice-1 skipCount "v1.4.0 hardening" deferral is **resolved** by this phase, not re-deferred.

## Key Grounding Facts Surfaced
- BUG-01's "use Renderer2" is partly mis-stated — Renderer2 is already injected; the sink is one `innerHTML` assignment (line 100).
- BUG-04 is partly already fixed — the prior-subscription unsubscribe teardown exists; remaining work is audit + same-tick regression test.
- The slice-1 runtime-boundary probe's "deferred to v1.4.0" comment is now obsolete and updated by this phase.
