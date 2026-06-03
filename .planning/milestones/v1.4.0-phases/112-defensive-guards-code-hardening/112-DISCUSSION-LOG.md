# Phase 112: Defensive Guards & Code Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 112-defensive-guards-code-hardening
**Areas presented:** GUARD-04 spawn-fix mechanics, GUARD-01/02 warning correctness, GUARD-03 delete-failure logging, GUARD-06 legacy-fallback surfacing
**Outcome:** User dismissed the gray-area selection (declined AskUserQuestion) — same posture as Phase 110. Spec-grounded defaults locked in CONTEXT.md from `110-FINDINGS.md`, the INFRA-01 precedent, REQUIREMENTS.md GUARD-01..06, and direct source reads.

---

## GUARD-04 — AppProcess spawn-context fix

| Option | Description | Selected |
|--------|-------------|----------|
| Shared `get_context("spawn")` (mirror INFRA-01) | Build `Queue()`/`Event()` from a spawn context, as MP-logger did | ✓ (D-01) |
| `__getstate__`/`__setstate__` only | Drop unpicklable state on pickle, like MP-logger's arg shim | ✓ if needed (D-02 — planner decides against live repro) |
| Global `set_start_method("spawn")` | Force spawn everywhere | ✗ (D-03 — too broad; keep fix local) |

**Resolution:** Default to the INFRA-01 spawn-context pattern (D-01); planner determines whether `AppProcess` *also* needs `__getstate__`/`__setstate__` because it subclasses `Process` and the whole instance is pickled on `.start()` (D-02). Acceptance bar: `test_app_process.py:175` green under `spawn`, nothing deleted/skipped, full suite green under `fork` too.

## GUARD-01 / GUARD-02 — Startup-warning prominence + correctness

| Option | Description | Selected |
|--------|-------------|----------|
| Suppress first warning in fail-closed state | Accept-any-caller line fires only when `not secret and not require_secret` | ✓ (D-05 default) |
| Merge to one state-aware message | Single message per config state | ✓ acceptable alternative (D-05) |
| Escalate prominence beyond logging.warning | Raise/exit or interactive prompt | ✗ (D-06 — GUARD-01 says default behavior unchanged) |

**Resolution:** Fix the misleading `empty secret + require_secret=True` cell so each HR-03 matrix cell yields exactly one accurate message (D-05). GUARD-01 text is already accurate; only prominence is raised, staying at `logging.warning` (D-06). Extend existing `test_seedsyncarr.py` warning tests (D-07).

## GUARD-03 — Delete-failure logging

| Option | Description | Selected |
|--------|-------------|----------|
| `onexc`/`onerror` callback logging each failed path | Per-entry granularity | ✓ default (D-08) |
| `try/except OSError` + single `logger.exception` | Coarser, mirrors DeleteRemoteProcess | ✓ acceptable alternative (D-08) |
| Propagate failure / make delete fatal | Raise out of the one-shot | ✗ (D-09 — preserve best-effort) |

**Resolution:** Replace `ignore_errors=True` so a failed delete leaves an observable log signal, while staying best-effort/non-fatal (D-08/D-09). Mirror the `DeleteRemoteProcess` try/except + `logger.exception` precedent; sanitize interpolated paths via `sanitize_log_value()`. Add a failure-path regression test (D-10).

## GUARD-06 — Legacy `~/.seedsync` fallback surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| Surface warning after `_create_logger` | Thread flag out of `_parse_args`, emit via configured logger | ✓ default (D-11) |
| `print(..., file=sys.stderr)` at call site | Pre-logger stderr emit | ✓ acceptable fallback (D-11) |
| Gate fallback behind explicit opt-in | GUARD-06's alternative path | ✗ (D-12 — loud-warning path lower-risk, preserves auto-fallback) |

**Resolution:** Root cause is ordering — the warning fires before the logger is configured (D-11). Make it reach the operator while preserving the auto-fallback behavior. Add a test asserting emission on fallback (D-12).

## GUARD-05 — `.gitignore` tooling artifacts

Mechanical, no gray area. Add `.orchestrator.json` + `.playwright-mcp/` to `.gitignore` alongside existing `.aidesigner/*`/`.bg-shell/`/`.turingmind/` entries; verify with `git status` (D-13).

---

## Claude's Discretion

- Exact warning prefix/format for prominence (D-06), kept consistent and at `logging.warning`.
- GUARD-03 callback-granularity vs single try/except (D-08).
- GUARD-06 flag-threading vs stderr emit (D-11).
- Whether GUARD-04 needs `__getstate__`/`__setstate__` in addition to the spawn context (D-02), decided against a live `spawn` repro.

## Deferred Ideas

- None beyond the six GUARD items — FINDINGS bounded scope tightly.
- Reviewed-not-folded todos: `migrate-config-set-to-post-body` (already Phase 111), `webob-cgi-upstream-unblock` (DEFER-WEBOB, upstream-blocked).
