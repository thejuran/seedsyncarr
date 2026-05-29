# Phase 98: Medium-Priority Angular Coverage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 98-medium-priority-angular-coverage
**Areas discussed:** Delegation posture (carried forward from Phase 97)

---

## Delegation Posture

| Option | Description | Selected |
|--------|-------------|----------|
| Same as 97 — take your recs | Capture CONTEXT.md with Claude's recommended decisions on all gray areas (escape-set scope, skipMessage bypass finding, test depth), following the 97 precedent and trivial-fix policy. | ✓ |
| Discuss the skipMessage finding | Surface the one genuine finding (skipMessage interpolates into innerHTML without escapeHtml) and decide together before locking the rest. | |
| Discuss all gray areas | Walk through each gray area interactively one at a time. | |

**User's choice:** Same as 97 — take your recs
**Notes:** Phase 98 mirrors Phase 97 — locked design spec, test-only work, same trivial-fix policy, same user. In Phase 97 the user said "take your recs for all" and delegated every HOW decision. User confirmed the same delegation carries forward. Claude recorded recommended decisions D-01 through D-06 in CONTEXT.md.

---

## Claude's Discretion (delegated)

All gray areas were delegated to Claude's recommendation. Key calls made:

- **Escape-set scope (D-01):** Do NOT expand beyond `&<>"'`. Backtick/U+2028/U+2029/null-byte are not XSS-exploitable in the two HTML contexts this service uses (element content + double-quoted class attribute). No-op change, mirroring Phase 97's D-05 borderline-defer posture.
- **skipMessage bypass (D-02):** The one un-escaped interpolation site is safe — it carries only a numeric `skipCount`. Asserted-and-documented, not "fixed" (nothing to fix). Not routed through escapeHtml (numeric → no-op).
- **Test depth (D-03/D-04):** Parsed-DOM assertions (no `<script>`, no `on*=`, no `javascript:`) PLUS raw-`innerHTML` escaped-entity string assertions, across all six escaped inputs; plus a direct metacharacter + ampersand-first-ordering unit test of `escapeHtml`.
- **Coverage breadth (D-05):** All six inputs (title, body, okBtn, cancelBtn, okBtnClass, cancelBtnClass), not just title/body — the class attributes are a distinct HTML context needing breakout payloads.
- **Isolation (D-06):** Extend the existing 463-line `confirm-modal.service.spec.ts`; supersede the two partial XSS tests rather than create a parallel file.

## Deferred Ideas

- Expanding the escape set (backtick/U+2028/U+2029/null-byte) — not exploitable here; revisit only if a new sink context appears.
- Routing skipCount through escapeHtml or refactoring the `innerHTML`-building approach to remove the sink — larger redesign, v1.4.0 if ever.
- Any test-surfaced bug exceeding the trivial-fix window → v1.4.0 with a STATE.md entry.
