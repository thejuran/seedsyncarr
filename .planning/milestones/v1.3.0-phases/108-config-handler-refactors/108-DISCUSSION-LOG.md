# Phase 108: Config + Handler Refactors - Discussion Log

> **Audit trail only.** Not consumed by downstream agents (researcher, planner, executor).
> Decisions captured in 108-CONTEXT.md — this log preserves the reasoning.

**Date:** 2026-06-01
**Phase:** 108-config-handler-refactors
**Mode:** discuss
**Areas discussed:** Secret-discovery API shape, `_SECRET_FIELD_PATHS` 2nd consumer, Dispatch helper scope, Plan/commit structure

## Area Selection

Presented four phase-specific gray areas; user selected **all four** to discuss.

## Questions & Decisions

### Secret-discovery API shape (ARCH-02)
- **Options:** (a) `secret=True` + derive section from owning class [recommended]; (b) `secret=True` + explicit `section=` string; (c) metadata-built registry object.
- **Chosen:** (a) `secret=True` + derive section structurally from the owning `InnerConfig` subclass.
- **Note:** Matches CONCERNS.md "declare it `secret=True`, nothing else"; avoids re-duplicating section strings.

### `_SECRET_FIELD_PATHS` second consumer (ARCH-02)
- **Options:** (a) remove tuple, repoint `seedsyncarr.py` at new dynamic API [recommended]; (b) keep as derived backward-compat shim.
- **Chosen:** (a) fully remove the tuple, expose a dynamic discovery API, update `seedsyncarr.py` (import line 18 + loop line 413).
- **Note:** Requirement explicitly says remove the hand-maintained tuple; a same-named alias would mislead future readers.

### Dispatch helper scope (ARCH-03)
- **Options:** (a) single-action handlers only [recommended]; (b) single + bulk share one helper.
- **Chosen:** (a) `_dispatch_command(...)` backs the 5 `__handle_action_*` methods only; `_process_bulk_commands` left untouched.
- **Note:** Bulk has different async/aggregation/partial-failure semantics that success criteria require to stay byte-identical; CONCERNS.md lists bulk sharing as optional.

### Plan / commit structure
- **Options:** (a) two separate plans (108-01 ARCH-02, 108-02 ARCH-03) [recommended]; (b) one combined plan.
- **Chosen:** (a) two separate plans — disjoint files, no interdependency, cleaner review + bisect.

## Deferred Ideas Raised
- Bulk dispatch unification (out of scope, D-03 boundary).
- Pre-existing bulk-command cancellation/timeout-leaves-in-queue bugs (separate from this behavior-preserving refactor).

## Claude's Discretion Items
- Exact name/return shape of the secret-discovery API.
- Exact `_dispatch_command` signature details.
- One-wave-parallel vs sequential execution of the two plans.
- Test shape proving auto-discovery of a new `secret=True` field.
