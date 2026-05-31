# Phase 97: Medium-Priority Python Coverage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 97-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-05-28
**Phase:** 97-medium-priority-python-coverage
**Mode:** discuss (default)
**Areas presented:** SSRF IPv6-mapped fix scope, LFTP test layer, Trivial-fix default posture, Baseline capture mechanics

## Context

Phase 97 is heavily pre-specified by `docs/superpowers/specs/2026-05-28-test-coverage-gaps-design.md`, which functions as a locked SPEC (exact files, branches, test-isolation strategy per plan). Discussion therefore focused only on the HOW gray areas the spec left genuinely open. Source files reviewed during analysis: `multiprocessing_logger.py` (full), `config.py:40-99` (`_validate_url`).

## Gray Areas Presented

| Area | Options offered | Resolution |
|------|-----------------|------------|
| SSRF IPv6-mapped fix scope | In-scope trivial fix / v1.4.0 deferral | In-scope trivial fix (D-01, D-02) |
| LFTP test layer | Integration (real lftp) / unit (mocked) | Integration (D-03, D-04) |
| Trivial-fix default posture | Lean fix-inline / lean defer | Lean defer at borderline; clear small fixes stay in (D-05) |
| Baseline capture mechanics | make targets + raw numbers / custom format | make targets, raw totals, committed before tests (D-06) |

## Decision

User responded "take your recs for all" — delegated all four gray areas to Claude's recommendation. Recommendations recorded as D-01 through D-06 in 97-CONTEXT.md with rationale grounded in the spec's tier and trivial-fix policies.

## Corrections Made

None — all recommendations accepted via delegation.

## Deferred Ideas

- Bugs exceeding the trivial-fix window → v1.4.0 (Known Bugs + Security).
- DNS-rebind hardening for `_validate_url` → out of scope (existing inline comment).
- Per-file coverage floors → out of scope milestone-wide.
