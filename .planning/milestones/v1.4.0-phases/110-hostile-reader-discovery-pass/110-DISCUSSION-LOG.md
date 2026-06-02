# Phase 110: Hostile-Reader Discovery Pass - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-06-02
**Phase:** 110-hostile-reader-discovery-pass
**Mode:** discuss (default)
**Areas presented:** Tooling depth & set, Fold-vs-park threshold, Artifact structure & home, Pre-named fix scope

## Gray Areas Presented

A single multiSelect was presented offering four gray areas about HOW the discovery pass is
conducted (the phase delivers an analysis artifact, not code, so the gray areas are about pass
mechanics and artifact shape, not implementation patterns):

| Area | Question posed |
|------|----------------|
| Tooling depth & set | Lock the spec-named set (ruff whole-tree + Semgrep/Shield + dep audit) or add gitleaks/bandit/npm audit? |
| Fold-vs-park threshold | Where exactly is the "genuinely high-visibility" bar that controls downstream scope? |
| Artifact structure & home | Format/location/severity scheme; extend CONCERNS.md vs new FINDINGS.md vs cross-reference? |
| Pre-named fix scope | Treat the 6 spec-committed fix items as locked-confirm-only, or allow re-scoping? |

## User Response

The user **dismissed the question without selecting any area** — a valid signal that they are
comfortable letting Claude lock spec-grounded defaults rather than discuss mechanics the approved
design spec (D-1..D-10) and REQUIREMENTS.md (SCAN-01/02) already constrain tightly.

## Decisions Resolved (Claude's spec-grounded defaults)

All four areas were resolved with defaults anchored to the design spec and CONCERNS.md:

- **Tooling (D-01/D-02):** spec-named set + obvious hostile-reader additions (gitleaks via Shield,
  pip-audit, npm audit); read-only/report-only — no autofix.
- **Fold-vs-park (D-03/D-04):** fold bar = "a skeptical r/selfhosted engineer would visibly hold it
  against the project on launch day"; latent/invisible/externally-blocked items park with rationale.
- **Artifact (D-05/D-06/D-07):** new `110-FINDINGS.md` in the phase dir; severity-ranked; per-finding
  explicit `FOLD → Phase NNN` / `PARK — rationale` disposition; summary rollup at top; cross-reference
  (do not mutate) CONCERNS.md.
- **Pre-named scope (D-08):** the 6 spec-committed fix items are locked + confirm-only, not
  re-litigated; the pass adds value by surfacing *new* findings and giving every finding a disposition.
- **Concrete confirmed gap (D-09):** `LICENSE` missing at repo root → expected `FOLD → Phase 113`.

## Deferred / Reviewed

- Todo `2026-04-24-migrate-config-set-to-post-body.md` (score 0.6) reviewed but **not folded** — it
  belongs to Phase 111 (its match reasons cite "phase, 111"; STATE.md confirms it is Phase 111 scope),
  not this discovery phase.
- Upstream-parked items (DEFER-SHUTDOWN/STREAMQUEUE/TESTHARDEN/WEBOB, NAS-QEMU, dual-GET) expected to
  remain parked in the artifact.

## No Scope Creep

Discussion stayed within the phase boundary (analysis-only, gates 111-112). No new capabilities proposed.
