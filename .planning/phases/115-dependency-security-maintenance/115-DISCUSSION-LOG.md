# Phase 115: Dependency & Security Maintenance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 115-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-06-22
**Phase:** 115-dependency-security-maintenance
**Mode:** discuss
**Areas discussed:** Merge mechanism, Merge order, Post-merge verification

## Pre-discussion state verification

Before discussing, verified the live dependency landscape (roadmap was written 2026-06-21):
- `gh pr list --state open` → all 7 PRs (#60–#66) open + `MERGEABLE`.
- `gh pr checks <n>` per PR → active CI gates green on all 7, including #64's full Angular/Karma/E2E gate.
- `gh api .../dependabot/alerts` → 8 open (3 HIGH, 5 MEDIUM), matching the roadmap.
- Drift found: PR #65 is hono 4.12.23→**4.12.26** (roadmap said 4.12.25). Newer, still fixes CORS HIGH.

## Questions Asked

### Merge mechanism
| Options presented | Selected |
|-------------------|----------|
| (a) Squash-merge via `gh`, re-check CI each [recommended]; (b) Enable auto-merge on all 7 at once | **(a)** Squash-merge via gh, re-check CI each |

Notes: deterministic one-at-a-time merge matches "CI green per merge"; rejected blanket auto-merge for loss of ordering control around the #64 npm group.

### Merge order
| Options presented | Selected |
|-------------------|----------|
| (a) Security-criticals first (#64→#65→#66→#60–#63) [recommended]; (b) Low-risk Python dev-deps first; (c) Strict numeric #60→#66 | **(a)** Security-criticals first, then rest |

Notes: closes the 3 HIGH alerts soonest; a mid-phase stop still leaves the important fixes landed.

### Post-merge verification (end-state check)
| Options presented | Selected |
|-------------------|----------|
| (a) Verify 0 open alerts + local ruff whole-tree [recommended]; (b) Trust per-PR CI + alert auto-close | **(a)** Verify 0 open alerts + local ruff whole-tree |

Notes: belt-and-suspenders for the ruff separate-gate risk STATE.md flagged — CI only checks the merge commit, a local whole-tree `ruff check src/python/` against ruff 0.15.17 independently confirms cleanliness.

## Todos Reviewed

- `2026-04-21-webob-cgi-upstream-unblock.md` (score 0.9) — **reviewed, not folded.** Blocked on upstream webob 2.0 (DEFER-WEBOB); not a Dependabot PR/alert; stays deferred.

## Claude's Discretion Items

- Exact `gh` merge flags, CI-polling method, and bounded Dependabot-rebase wait time left to planning/execution.

## Deferred Ideas

None — discussion stayed within phase scope.
