---
phase: 103
slug: angular-defects
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-31
---

# Phase 103 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Karma 6.4.4 + Jasmine 5.1 |
| **Config file** | `src/angular/karma.conf.js` (existing — `coverageReporter.check.global` floors 83/68/79/83) |
| **Quick run command** | `make run-tests-angular` (Docker) |
| **Full suite command** | `make run-tests-angular` (Docker) |
| **Estimated runtime** | ~60–120 seconds (Angular unit suite) |

---

## Sampling Rate

- **After every task commit:** Run `make run-tests-angular`
- **After every plan wave:** Run `make run-tests-angular`
- **Before `/gsd:verify-work`:** Full Angular suite must be green; Karma `check.global` floors (83/68/79/83) hold or rise
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 103-01-* | 01 | 1 | BUG-01 | CWE-79 (DOM XSS) | `createModal()` makes no `innerHTML`/`outerHTML`/`insertAdjacentHTML` assignment; user strings rendered as text nodes (inert) | unit + DOM | `make run-tests-angular` | ✅ | ⬜ pending |
| 103-01-* | 01 | 1 | BUG-01 (skipCount fold-in) | CWE-79 | `Number(skipCount)` coercion: a `toString()`-overriding object injects no `<img>`; slice-1 probe (spec:690-720) inverted to `toBeNull()` | unit + DOM | `make run-tests-angular` | ✅ | ⬜ pending |
| 103-01-* | 01 | 1 | BUG-01 | CWE-79 | Slice-1 XSS outcome assertions pass: `querySelector("script")` null, button `textContent` contains literal payload, no `on*`/`javascript:` | unit + DOM | `make run-tests-angular` | ✅ | ⬜ pending |
| 103-02-* | 02 | 1 | BUG-04 | — (availability/correctness) | `reconnectDueToTimeout()` tears down the prior subscription before scheduling; exactly one active EventSource after a same-tick timeout+error collision | unit + fakeAsync | `make run-tests-angular` | ✅ | ⬜ pending |
| 103-02-* | 02 | 1 | BUG-04 | — | Slice-1 heartbeat-vs-timeout race tests (spec:209-260) still pass unchanged | unit + fakeAsync | `make run-tests-angular` | ✅ | ⬜ pending |
| COMPAT | 01+02 | 1 | BUG-01, BUG-04 | — | Karma `check.global` floors 83/68/79/83 hold or rise; no client-visible regression | coverage | `make run-tests-angular` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The two target spec files already exist with the relevant `describe` structures:
- `src/angular/src/app/tests/unittests/services/utils/confirm-modal.service.spec.ts` (slice-1 XSS suite + skipCount probe)
- `src/angular/src/app/tests/unittests/services/base/stream-service.registry.spec.ts` (slice-1 heartbeat-vs-timeout race describe)
- `src/angular/src/app/tests/mocks/mock-stream-service.registry.ts` (mock EventSource harness for the new BUG-04 collision test)

No new test files, no new framework config, no fixture changes needed. Karma + Jasmine already installed and wired in CI (amd64 + arm64).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confirm modal renders & behaves identically (visual parity, focus trap, Esc/Tab) | BUG-01 (COMPAT) | Visual parity is a human judgment; unit tests assert DOM structure but not pixel-level rendering | Milestone-end walkthrough (Phase 4): open a confirm dialog (e.g. a bulk delete with a skip count), verify title/body/buttons render, focus starts on Cancel, Tab cycles, Esc closes, backdrop click cancels |

*All security-relevant behaviors (no executable markup, single SSE subscription) have automated verification; only visual parity is manual.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (existing Karma suite covers all)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — existing infra sufficient)
- [x] No watch-mode flags (`make run-tests-angular` is single-run, headless)
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
