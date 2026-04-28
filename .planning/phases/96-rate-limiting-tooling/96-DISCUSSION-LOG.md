# Phase 96: Rate Limiting & Tooling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 96-rate-limiting-tooling
**Areas discussed:** Rate limit thresholds, Decorator design, Semgrep tightening approach

---

## Rate Limit Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform 30 req/60s | Single constant across all three endpoints. Simplest but risks 429s mid-settings-save. | |
| Per-endpoint | config/set=60, test=5, status=120. Three distinct limits tuned to each endpoint's usage pattern. | |
| Two-tier | 60 req/60s for config/set and status, 5 req/60s for test-connection endpoints. Two constants, covers all usage patterns. | ✓ |

**User's choice:** Two-tier (Recommended)
**Notes:** Research showed /server/config/set is called per-field on save (20+ rapid calls in a burst). Uniform 30 req/60s would cause 429s mid-save. Test-connection endpoints make expensive outbound HTTP calls to Sonarr/Radarr and deserve tight limits.

---

## Decorator Design

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone decorator | New web/rate_limit.py module with sliding_window_rate_limiter function. State per-instance, pure Python, easy to test. | ✓ |
| Bottle plugin | Install via web_app.install(). Single installation but global state and route-string matching. | |
| Mixin on IHandler | Shared base class method. Groups state with handler but adds inheritance to a flat interface. | |

**User's choice:** Standalone decorator (Recommended)
**Notes:** Matches existing helper-method idiom. Avoids Bottle plugin lifecycle complexity. Refactors existing ControllerHandler._check_bulk_rate_limit() to eliminate duplication.

---

## Semgrep Tightening Approach

### TOOL-01: js-nosql-injection-where (617 FPs)

| Option | Description | Selected |
|--------|-------------|----------|
| metavariable-regex | Constrain $WHERE to literal ^\$where$ via metavariable-regex. ~3 lines, eliminates all FPs. | ✓ |
| MongoDB import chain | Add pattern-inside requiring MongoDB import. More readable but overengineered. | |
| Delete the rule | Remove entirely. Zero FPs but loses detection for future MongoDB scanning. | |

**User's choice:** metavariable-regex (Recommended)

### TOOL-02: js-xss-eval-user-input (11 FPs)

| Option | Description | Selected |
|--------|-------------|----------|
| pattern-not exclusions | Add pattern-not for arrow/named function callbacks. Matches existing eval("...") exclusion style. | ✓ |
| metavariable-pattern | Require $INPUT to be a string literal. Semantically precise but needs Semgrep version verification. | |

**User's choice:** pattern-not exclusions (Recommended)
**Notes:** Both changes confined to javascript.yaml. Validate with semgrep --test if fixture files exist.

---

## Claude's Discretion

None -- all areas were user-decided.

## Deferred Ideas

- e2e-csp-violation-detection -- already complete (PLAT-01, Phase 91)
- arm64-unicode-sort-e2e-failures -- already complete (PLAT-02, Phase 91)
- webob-cgi-upstream-unblock -- blocked on upstream
- migrate-config-set-to-post-body -- out of scope for this milestone
