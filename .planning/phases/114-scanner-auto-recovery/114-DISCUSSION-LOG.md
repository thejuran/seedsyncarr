# Phase 114: Scanner Auto-Recovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 114-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-06-21
**Phase:** 114-scanner-auto-recovery
**Mode:** discuss
**Areas discussed:** Transient vs config disambiguation, Where retry lives, Controller restart bound

## Questions Asked

### Transient vs. config-error disambiguation
- **Options presented:**
  - Retry-then-surface (Recommended) — all name-resolution failures transient first; bounded retry is the test.
  - Keep first-run strictness gate — name-resolution fatal before first successful scan, transient after.
- **User selected:** Retry-then-surface.
- **Notes:** Satisfies SCAN-01 + SCAN-02 + SCAN-03 together without up-front heuristic guessing. A blip recovers within the retry window; a real wrong hostname costs a few bounded retries, then surfaces exactly as today.

### Where the bounded retry lives
- **Options presented:**
  - Inside the scan attempt (Recommended) — bounded retry loop with backoff in `remote_scanner.scan()` / `scanner_process.run_loop()`; one scan cycle = one bounded recovery window (seconds).
  - Across scan intervals — failure counter incremented per failed interval; escalate after N consecutive; recovery spans minutes.
- **User selected:** Inside the scan attempt.
- **Notes:** Recovery tight to the failure site, self-contained, easy to unit-test. No existing retry helper in the codebase — this is the one piece of new (small) code.

### Controller auto-restart bound
- **Options presented:**
  - Capped consecutive restarts (Recommended) — restart up to ~3 consecutive times; stayed-up run resets counter; after cap, fall through to today's `server.up=False` surface.
  - Restart with backoff, no hard cap — increasing backoff forever, never a hard stop.
- **User selected:** Capped consecutive restarts.
- **Notes:** Bounds a true unrecoverable loop while letting intermittent failures recover indefinitely over time. Reuses the existing `ServiceRestart` + outer `main()` restart path.

## Claude's Discretion (delegated)

- Exact retry attempt cap, backoff schedule, and per-attempt sleep ceiling (D-02).
- Exact consecutive-restart cap and stayed-up reset threshold (D-03).
- Whether scan-retry and restart-bound share a helper.
- Test approach (existing pytest suite is the regression net).

## Deferred / Out of Scope (redirected)

- UI-configurable retry counts/backoff — Out of Scope (hardcoded defaults).
- Alerting/notification on scanner death — separate concern.
- New SSH/scanner transport — reuse existing infrastructure.
- `webob-cgi-upstream-unblock` todo (matched score 0.6) — reviewed, not folded; upstream-blocked and unrelated.
