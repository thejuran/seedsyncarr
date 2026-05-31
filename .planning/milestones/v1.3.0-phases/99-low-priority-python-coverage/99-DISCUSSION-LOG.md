# Phase 99: Low-Priority Python Coverage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 99-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-05-29
**Phase:** 99-low-priority-python-coverage
**Mode:** discuss (standard)
**Areas analyzed:** COVLOW-01 Timer realism, COVLOW-01 both toggles, COVLOW-02 eviction shape, Trivial-fix posture

## Context

Phase 99 is governed by a locked design spec (`docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md`) that already fixes the files, the one-test-per-plan shape, and the two plans (99-01, 99-02). The only open questions were narrow HOW choices. Prior phases (97, 98) under the same spec established the "user delegates spec-open gray areas to Claude's recommendation" pattern.

## Gray Areas Presented

Single multiSelect turn presenting four HOW gray areas:

1. **COVLOW-01 Timer realism** — real `threading.Timer` (schedule → flip → fire) vs. direct `__execute_auto_delete` call after flipping config.
2. **COVLOW-01 both toggles** — cover both `enabled=false` and `dry_run=true` flips, or just the primary disabled case.
3. **COVLOW-02 eviction shape** — assertion surface (eviction return value + `as_list()` vs. also `total_evictions`) and concrete N.
4. **Trivial-fix posture** — carry Phase 97's posture forward, or discuss.

## User Selection

User answered: **"all yo"** — delegate all four to Claude's recommendation (same posture as Phase 97's "take your recs for all"). No corrections requested.

## Decisions (Claude's recommendation, accepted)

| Area | Decision |
|------|----------|
| COVLOW-01 Timer realism (D-01/D-01a) | Real `threading.Timer` via `__schedule_auto_delete`; short delay; flip config after scheduling, before fire; join timer + assert via `delete_local` mock (no fixed sleep); timeout guard against hang. The existing tests already cover the direct-call path, so only the live-Timer path closes the gap. |
| COVLOW-01 both toggles (D-02) | Two tests: `enabled True→False` and `dry_run False→True`, both asserting `delete_local.assert_not_called()`. Log-message assertions optional. |
| COVLOW-02 eviction shape (D-03) | `maxlen=3`, `from_iterable(['a','b','c'])`, `touch('a')`, `add('d')`; assert evicted=='b', order==['c','a','d'], total_evictions==1. |
| Trivial-fix posture (D-04) | Carry Phase 97 posture verbatim. No fix anticipated (code already correct); tests are pure regression nets. |

## Todos Reviewed (not folded)

- `2026-04-21-webob-cgi-upstream-unblock` — generic keyword match only; upstream-blocked, unrelated. Not folded.
- `2026-04-24-migrate-config-set-to-post-body` — generic keyword match only; separate-milestone API change, unrelated. Not folded.

## Deferred Ideas

- Non-trivial bugs surfaced by tests → v1.4.0 (none anticipated).
- Auto-delete Timer TOCTOU / in-flight-callback cancellation hardening → out of scope.
- CI threshold ratchet (RATCHET-02) → Phase 100.
