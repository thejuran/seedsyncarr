---
phase: 98
slug: medium-priority-angular-coverage
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-29
---

# Phase 98 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `98-RESEARCH.md` §"Validation Architecture" and `98-01-PLAN.md` (3 tasks, wave 1).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Jasmine 6.2 + Karma 6.4.4 (Angular `^21.2.12`) |
| **Config file** | `src/angular/karma.conf.js` (no changes needed — no `check.global` coverage threshold present) |
| **Quick run command** | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI --include=src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` |
| **Full suite command** | `cd src/angular && ng test --watch=false --browsers=ChromeHeadlessCI` |
| **Lint command** | `cd src/angular && npx eslint "src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts" --max-warnings 0` |
| **Estimated runtime** | ~5 seconds (single spec, headless Chrome) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (spec file only — fast, ~5s) + lint.
- **After the plan wave:** Run full suite command.
- **Before `/gsd:verify-work`:** Full suite must be green.
- **Max feedback latency:** ~5 seconds (quick run); full suite within standard CI budget.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 98-01-01 | 01 | 1 | COVMED-04 | T-98-02 / — | `escapeHtml` maps each of `& < > " '` to its entity; `&`-first ordering does not double-escape; documented no-op for backtick/U+2028/U+2029/null (D-01) | unit | quick run command | ✅ (extend existing spec) | ⬜ pending |
| 98-01-02 | 01 | 1 | COVMED-04 | T-98-01 / — | All six escaped inputs (title, body, okBtn, cancelBtn, okBtnClass, cancelBtnClass) produce no `<script>`, no `on*` attribute, no `javascript:`; raw `innerHTML` carries escaped entities; supersede partial XSS tests preserving their `textContent` assertions (D-03/D-05/D-06) | integration (end-to-end within unit test) | quick run command | ✅ (extend existing spec) | ⬜ pending |
| 98-01-03 | 01 | 1 | COVMED-04 | T-98-03 / — | `skipCount`/`skipMessage` site is numeric-only and exempt from escaping; no attacker string reaches it; all six string inputs route through `escapeHtml` — no bypass call site (D-02) | unit + code audit (test + comment) | quick run + full suite | ✅ (extend existing spec) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Threat refs map to `98-01-PLAN.md` `<threat_model>`: T-98-01 = XSS via `innerHTML` sink (confirm-modal.service.ts:100); T-98-02 = escape-set completeness; T-98-03 = `skipCount` bypass-site audit. All are mitigated/accepted by the tests in this phase — no production code change (D-01/D-02 no-ops).*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* No new spec files, no new config, no framework installs — the spec `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` already exists (463 lines) and is extended in place. Karma + Jasmine + ChromeHeadlessCI are already installed and CI-gated.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.* The XSS neutralization is fully observable via parsed-DOM assertions (`querySelector("script")` null, `on*`-attribute walk, `javascript:` href/src check) plus raw-`innerHTML` escaped-entity string assertions — no manual visual inspection required.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (3/3 tasks have automated Karma commands)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (all 3 verified)
- [x] Wave 0 covers all MISSING references (no MISSING references — existing infra)
- [x] No watch-mode flags (`--watch=false` disables watch mode)
- [x] Feedback latency < 10s (~5s quick run)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-29
