# Phase 122: Safety Acceptance and Logging Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-21
**Phase:** 122-safety-acceptance-and-logging-fixes
**Areas discussed:** Build under test, Test material, Incident record review, Log fix scope & wording

---

## Build under test

| Option | Description | Selected |
|--------|-------------|----------|
| Main after log fixes | Merge log fixes, deploy main build to sandbox only, run checks there | ✓ |
| Current 1.7.6 sandbox | Run now on 1.7.6, no redeploy | |
| Both | 1.7.6 now, then the new build | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, sandbox only | Digest-pinned `:dev` on seedsyncarr-test; restore original pin at end | ✓ |
| No, wait for 1.8.0 | Run acceptance in Phase 126 on the release image | |

| Option | Description | Selected |
|--------|-------------|----------|
| Diagnose, then ask | Record + diagnose, owner approves fix scope before code changes | ✓ |
| Fix in this phase | Small contained fix with fail-before/pass-after test | |
| Record and defer | Close SAFE-01 as failed, open follow-up | |

---

## Test material

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic, signed webhooks | Fake seedbox files + HMAC-signed Download webhooks, deterministic timing; cite Phase 120 for real queue gate | ✓ |
| Real Sonarr grab | Realistic; costs private-tracker ratio, uncontrolled timing | |
| Synthetic plus one real grab | Both | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, one restart | Restart sandbox mid-flow to prove credit persistence | ✓ |
| No restart | Rely on unit test | |

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-part RAR, ~1 GB | Burbs-shaped, wide enough window to observe staging | ✓ |
| Small archive | Fast, before/after evidence only | |

---

## Incident record review

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, read-only | ls/stat, logs, persist, GET-only arr API on production | ✓ |
| No production access | Owner checks leftovers | |

| Option | Description | Selected |
|--------|-------------|----------|
| Checklist; you confirm | Exact checklist, nothing done on production | ✓ |
| I do it with your go-ahead | Per-item approved production changes | |

| Option | Description | Selected |
|--------|-------------|----------|
| All findings verified + cleanup confirmed | Close only then; D–G carried to backlog, don't block | ✓ |
| Keep both open this phase | Never close in this phase | |

---

## Log fix scope & wording

| Option | Description | Selected |
|--------|-------------|----------|
| All four modules | webhook, controller, config handlers + rate_limit; secret review of newly visible lines | ✓ |
| Webhook handler only | LOG-01 literal scope | |

| Option | Description | Selected |
|--------|-------------|----------|
| Every path without proof | Prune and no-arr-enabled both say "dropped" | ✓ |
| Candidate path only | Only the Phase 120 path | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 'cleared', add 'dropped' | Release message unchanged; two "dropped (<reason>)" lines | ✓ |
| Make release explicit too | "released ... (completion verified)"; breaks existing greps | |

---

## Claude's Discretion

- Synthetic webhook construction/signing, fake file sizing/timing, RAR tooling, evidence file layout, internal shape of the `_clear_hold` change, scenario ordering.

## Deferred Ideas

- Extract-staging deep-review items D–G → ROADMAP backlog by name.
- Real-grab end-to-end run not chosen; Phase 126 REL-06 smoke test covers the release image.
