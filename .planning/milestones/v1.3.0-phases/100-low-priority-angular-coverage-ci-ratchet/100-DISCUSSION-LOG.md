# Phase 100: Low-Priority Angular Coverage + CI Ratchet - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 100-low-priority-angular-coverage-ci-ratchet
**Areas discussed:** Discussion scope (delegation posture)
**Mode:** discuss (standard)

---

## Discussion Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Take your recs for all | Lock all 4 gray areas (Karma threshold mechanics, ratchet floor strategy, SSE race assertion shape, auth-rotation test realism) to Claude's recommendation, carrying the Phase 97-99 precedent forward. | ✓ |
| Discuss the CI ratchet only | Discuss the irreversible project-wide ratchet (100-03); delegate the two test-shape areas to Claude. | |
| Discuss all 4 areas | Walk through each gray area one at a time. | |

**User's choice:** Take your recs for all
**Notes:** Carries the Phase 97 ("take your recs for all"), Phase 98 ("same as 97"), and Phase 99 ("all yo") delegation posture forward verbatim. The design spec already locks files, plan shape, and tier policy; the four open items are narrow HOW decisions, resolved in CONTEXT.md as D-01 through D-08 (plus D-09 informational trivial-fix posture).

---

## Gray Areas Resolved (Claude's recommendation, per delegation)

The four open HOW gray areas the design spec left unspecified, and how each was resolved in CONTEXT.md:

1. **SSE race assertion shape (COVLOW-03 / 100-01)** → D-01/D-02: drive the heartbeat-vs-timeout race via the existing `fakeAsync`+`MockEventSource` harness; bind on `createEventSource` call count unchanged + no spurious `notifyDisconnected` + paired positive control (timeout DOES fire when no heartbeat).

2. **Auth rotation test realism (COVLOW-04 / 100-02)** → D-03/D-04: prove rotation through the `_resetAuthInterceptorCache()` seam (mirror of the existing cache test), document the implicit page-reload coupling as a comment only — no in-app rotation path added.

3. **Karma threshold mechanics (RATCHET-02 / 100-03)** → D-05/D-06: the `coverageReporter.check.global` block is NET-NEW (does not exist in karma.conf.js); must author it AND confirm CI invokes `--code-coverage` so the gate bites. Python target is `[tool.coverage.report] fail_under` at `pyproject.toml:88` (NOT `--cov-fail-under` as the spec's parenthetical guessed). Both land in one commit.

4. **Floor calibration strategy (RATCHET-02 / 100-03)** → D-07/D-08: set thresholds at floor(measured "now") minus a ~0.5–1% jitter buffer (not exactly at measured, to avoid biting the next PR); re-measure fresh against current HEAD; record before/after in ROADMAP.md + RETROSPECTIVE.md; log floor decision in PROJECT.md Key Decisions.

## Claude's Discretion

- Exact `it()`/`describe` names, concrete `tick()` values + jitter for 100-01, and whether the SSE contrast case is a separate `it()`.
- The exact Karma reporter list and the precise safety-margin within the ~0.5–1% band per layer.
- Whether to also bump a `[tool.pytest.ini_options]` `--cov-fail-under` if one is found (keep both in sync if both exist).
- Re-measure Angular coverage locally vs rely on CI, so long as the "now" number is fresh.

## Deferred Ideas

- In-app token-rotation path / session-cookie auth → v1.4.0.
- `innerHTML → Renderer2` modal redesign + mandatory webhook secret → v1.4.0 (already slated).
- SSE event coalescing / condition-variable timeout checker → backlog.
- Any non-trivial bug surfaced by these tests → v1.4.0 with a STATE.md deferred entry (none anticipated).
