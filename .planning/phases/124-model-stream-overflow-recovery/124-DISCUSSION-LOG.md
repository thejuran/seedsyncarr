# Phase 124: Model-Stream Overflow Recovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 124-CONTEXT.md. This log preserves the discussion.

**Date:** 2026-10-26
**Phase:** 124-model-stream-overflow-recovery
**Mode:** discuss (default)
**Areas discussed:** How the tab catches up, Which streams are covered, Proof of done, Visibility of a resync

## How the tab catches up

| Option | Selected |
|--------|----------|
| Fresh snapshot on the same connection (Recommended) | ✓ |
| Force reconnect (list empties ~3s; status/log reset) | |

| Repeat cap | Selected |
|--------|----------|
| Once per backlog: at most one pending snapshot per tab (Recommended) | ✓ |
| Rate-limit by time | |

## Which streams are covered

| Option | Selected |
|--------|----------|
| File list only; record status-stream self-healing; log drops to backlog (Recommended) | ✓ |
| File list + log stream | |

## Proof of done

| Option | Selected |
|--------|----------|
| Automated tests only: reproduction, fail-before/pass-after convergence, bounded buffering (Recommended) | ✓ |
| Tests + live NAS sandbox check | |

## Visibility of a resync

| Option | Selected |
|--------|----------|
| Server log only, rate-limited warning (Recommended) | ✓ |
| Also a UI toast | |

## Claude's Discretion
- Detection mechanics, where the check lives, whether to fold in the DEFER-STREAMQUEUE lock, test placement, log wording.

## Deferred Ideas
- Log-stream line loss under overflow (backlog candidate)
- UI resync notice (rejected for now)
- SSE busy-poll → event-driven wakeups
