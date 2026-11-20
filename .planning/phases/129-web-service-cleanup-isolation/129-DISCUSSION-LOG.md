# Phase 129: Web-Service Cleanup Isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-11-19
**Phase:** 129-web-service-cleanup-isolation
**Areas discussed:** Stuck web server, Proof

Carried forward without asking (Phase 123 precedent and Job contract): per-step try/except with logged failures; cleanup never raises; steps that do not apply are skipped quietly.

---

## Stuck web server

| Option | Description | Selected |
|--------|-------------|----------|
| Wait briefly, then exit (Recommended) | Bounded wait of a few seconds, then log a warning and continue shutdown | ✓ |
| Skip the wait if stop failed | Scanner precedent: no join after a failed stop | |
| Keep waiting with no limit | Today's behaviour; can hang until Docker kills the container | |

**User's choice:** Wait briefly, then exit.
**Notes:** After the answer, code check found the server thread is non-daemon, so a timed join alone would not let Python exit. Recorded as D-05 (the plan must address it).

---

## Proof

| Option | Description | Selected |
|--------|-------------|----------|
| Tests now, live in the 1.8.1 release check (Recommended) | Injected-failure and partial-startup tests; live restart check folded into Phase 130 smoke test | ✓ |
| Tests plus a live restart check now | Sandbox deploy and repeated restarts in this phase | |
| Tests only | No planned live check | |

**User's choice:** Tests now, live check in the 1.8.1 release check.

---

## Claude's Discretion
- Timeout constant and location; log wording; whether `MyWSGIRefServer.stop()` also calls `shutdown()`; test structure.

## Deferred Ideas
None.
