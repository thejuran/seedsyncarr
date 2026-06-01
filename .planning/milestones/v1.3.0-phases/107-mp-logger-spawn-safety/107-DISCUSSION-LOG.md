# Phase 107: MP-Logger Spawn Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 107-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-06-01
**Phase:** 107-mp-logger-spawn-safety
**Mode:** discuss
**Areas analyzed:** Production queue context, Test strategy, Scope guard

## Analysis Summary

Pure-infrastructure phase (INFRA-01) with a technical approach already adversarially vetted
during its deferral out of Phase 102 (adversarial round 2, 2026-05-31). The roadmap success
criteria nearly fully specify the fix. Two genuine implementation gray areas were surfaced to
the user; the rest are locked by the requirement + prior finding.

## Questions Asked

### Production queue context
- **Options presented:**
  1. Always spawn context — `multiprocessing.get_context('spawn').Queue(-1)` unconditionally; spawn-context SemLock is shareable with both fork and spawn children (Recommended).
  2. Match the active start method — detect `get_start_method()` and branch.
- **User selected:** Always spawn context.
- **Notes:** Simplest correct fix; fork-context queue would still break the moment a child is spawned. → D-01.

### Test strategy
- **Options presented:**
  1. Explicit spawn-context Process + module-scope picklable targets — deterministically exercises spawn on every platform, including Linux CI (Recommended).
  2. Rely on platform default only — passes but doesn't exercise spawn on Linux; weaker regression net.
- **User selected:** Explicit spawn-context Process + module-scope targets.
- **Notes:** Revives the deferred D-06/D-07 direction, now valid because the production queue is spawn-safe. → D-04.

## Claude's Discretion (not asked — implementation detail)
- Private attribute names and how the spawn context is exposed for the tests to reuse.
- Module-level naming of the promoted picklable target functions.

## Deferred Ideas
- MP-logger listener silent-shutdown gap (`multiprocessing_logger.py:78`, CONCERNS.md:298) — same file, distinct reliability concern, out of scope for INFRA-01.
- No global `set_start_method` change and no conftest start-method fixture — explicitly avoided to keep blast radius minimal.
