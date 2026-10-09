# Phase 118: Durable State - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-09
**Phase:** 118-Durable State
**Areas discussed:** Release flow, Merge to main, Rollback runbook

---

## Release flow

| Option | Description | Selected |
|--------|-------------|----------|
| Tag → CI image → test → NAS | Merge, push v1.7.4, smoke-test the CI-built image, deploy the same digest; one approval before tag push | ✓ |
| Local image first, tag after | Smoke-test a local build, then tag; NAS runs a different (CI-built) image than tested | |
| Defer tag + deploy to milestone end | Phase stops at a code-side release candidate; REL-01 not complete here | |

**User's choice:** Tag → CI image → test → NAS

---

## Merge to main

| Option | Description | Selected |
|--------|-------------|----------|
| Merge branch, keep history | Push local main (11 planning commits), merge the branch, tag from main | ✓ |
| Squash the code into main | One commit; loses per-fix SHAs referenced by evidence | |
| Tag on the branch, merge later | Fastest; main lags released code | |

**User's choice:** Merge branch, keep history

---

## Rollback runbook

| Option | Description | Selected |
|--------|-------------|----------|
| Full runbook in release notes | Backup persist files; rollback steps with auto-delete off until reconciled; plus Stop behavior change | ✓ |
| Short note only | A few lines | |

**User's choice:** Full runbook in release notes

---

## Claude's Discretion

- Temp-file mechanism, failure-injection technique, smoke-test mechanics, CHANGELOG wording.

## Deferred Ideas

- Backlog 999.2 stays out of 1.7.4.
