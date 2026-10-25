# Phase 123: Startup and Shutdown Lifecycle - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 123-CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-10-25
**Phase:** 123-startup-and-shutdown-lifecycle
**Areas discussed:** The lftp shutdown error, The startup delay, What happens after a failed start, How it's proven

---

## The lftp shutdown error

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, fix it in this phase (Recommended) | Root-cause lftp not stopping in time and the scanner "died" errors on a normal shutdown, fix both, prove with a clean sandbox restart | ✓ |
| Investigate only, fix if it's small | Diagnose; fix here only if small, otherwise write up and backlog | |
| Keep it separate | Phase 123 does only the injected-failure gaps; restart errors stay a backlog item | |

**User's choice:** Yes, fix it in this phase

---

## The startup delay

| Option | Description | Selected |
|--------|-------------|----------|
| Only if it's linked to the restart errors (Recommended) | Leave it unless the lftp investigation shows it causes the errors; then fix it as part of that | ✓ |
| Yes, replace it now | Swap the fixed wait for each job's "ready" signal with a time limit | |
| No, leave it | Out of scope entirely; rare and already noted in the backlog | |

**User's choice:** Only if it's linked to the restart errors

---

## What happens after a failed start

| Option | Description | Selected |
|--------|-------------|----------|
| Keep today's behaviour, just clean up first (Recommended) | Stop everything that started, then surface the failure into the existing limited auto-restart and web-page error | ✓ |
| Run with whatever started | Keep going without the failed part; risk of looking healthy while scanning is off | |
| Exit the whole app | Clean up and stop the container so Docker restarts it; web page goes down too | |

**User's choice:** Keep today's behaviour, just clean up first

---

## How it's proven

| Option | Description | Selected |
|--------|-------------|----------|
| Tests plus a short live restart check (Recommended) | Simulated-failure tests plus a few live restarts of the test container on the new build, each must log no errors and come back up normally | ✓ |
| Tests plus a full live check | Also a live transfer and import through a restart (~1 h more; mostly repeats Phase 122) | |
| Tests only | No sandbox work; nothing confirms live that the restart errors are gone | |

**User's choice:** Tests plus a short live restart check

---

## Claude's Discretion

- Exact cleanup-on-partial-start code shape (must mirror `Controller.exit()`'s existing per-component pattern, no new lifecycle abstraction)
- Per-process independent cleanup in `ScanManager` / `FileOperationManager`
- Completing the list of gaps across `ControllerJob`, mp logger and the top-level job start
- Bounded timeouts for any new join/terminate waits

## Deferred Ideas

- Modern RAR `.partN.rar` redundant extraction passes (not a lifecycle issue)
- DEFER-SHUTDOWN replacement if unrelated to the restart errors
- Phase 122 re-review follow-ups WR-04, IN-04, IN-05 (already in the ROADMAP Backlog)
