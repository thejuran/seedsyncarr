---
phase: 72
slug: restore-dashboard-file-selection-and-action-bar
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-19
---

# Phase 72 — Validation Strategy

> Per-phase validation contract. Reconstructed from plan artifacts (State B).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Unit framework** | Angular 20 + Karma/Jasmine (ChromeHeadless) |
| **E2E framework** | Playwright (typescript) |
| **Unit config** | `src/angular/karma.conf.js`, `src/angular/src/tsconfig.spec.json` |
| **E2E config** | `src/e2e/playwright.config.ts`, `src/e2e/tsconfig.json` |
| **Quick run (unit, scoped)** | `cd src/angular && npx ng test --include='**/{component}.component.spec.ts' --watch=false --browsers=ChromeHeadless` |
| **Full unit suite** | `cd src/angular && npx ng test --watch=false --browsers=ChromeHeadless` (489+ specs) |
| **E2E suite** | `cd src/e2e && npx playwright test tests/dashboard.page.spec.ts --reporter=list` (requires Docker test backend via `make run-tests-e2e`) |
| **Typecheck** | `cd src/angular && npx tsc --noEmit -p src/tsconfig.app.json` / `cd src/e2e && npx tsc --noEmit` |
| **Estimated runtime (unit)** | ~30–60s scoped, ~2–3 min full |
| **Estimated runtime (E2E)** | CI-only (Docker harness arm64-fragile locally, see STATE.md tech-debt) |

---

## Sampling Rate

- **After every task commit:** Scoped `ng test --include='**/{changed}.spec.ts'`
- **After every plan wave:** Full unit suite + typecheck
- **Before `/gsd-verify-work`:** Full unit suite green locally; E2E green in CI
- **Max feedback latency:** < 60s (scoped unit), < 3 min (full unit)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 72-01-01 | 01 | 2 | Variant B bar template + SCSS palette (5 action buttons, btn-divider, selection label, no Bootstrap tokens) | T-72-01 | Integer-only interpolation; no filename XSS surface in bar | unit (DOM) | `cd src/angular && npx ng test --include='**/bulk-actions-bar.component.spec.ts' --watch=false --browsers=ChromeHeadless` | ✅ `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` (33 specs) | ✅ green |
| 72-01-02 | 01 | 2 | `[disabled]` bindings on every action button incl. spam-click guard | T-72-02, T-72-03 | Buttons disabled when count=0 OR operationInProgress | unit (DOM) | (same as 72-01-01) | ✅ | ✅ green |
| 72-02-01 | 02 | 1 | Delete 4 obsolete component sets + 2 specs (14 files), preserve bulk-actions-bar | T-72-04, T-72-05 | `ng build` green after delete; preserved files compile | shell + build | `test ! -f src/angular/src/app/pages/files/file-actions-bar.component.ts && test ! -f src/angular/src/app/pages/files/file-list.component.ts && test ! -f src/angular/src/app/pages/files/file.component.ts && test ! -f src/angular/src/app/pages/files/file-options.component.ts && test -f src/angular/src/app/pages/files/bulk-actions-bar.component.ts && cd src/angular && npx ng build --configuration=development` | ✅ filesystem + 489/489 specs | ✅ green |
| 72-03-01 | 03 | 2 | Leading `td.cell-checkbox` + `input.ss-checkbox`, `@HostBinding('class.row-selected')`, `checkboxToggle` emits `{file, shiftKey}` | T-72-06, T-72-07, T-72-08 | Property-bound `aria-label` (no XSS); `appClickStopPropagation` + explicit `stopPropagation()` | unit (DOM) | `cd src/angular && npx ng test --include='**/transfer-row.component.spec.ts' --watch=false --browsers=ChromeHeadless` | ✅ `src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts` (22 specs) | ✅ green |
| 72-04-01 | 04 | 3 | Fallback constants `emptySet` / `emptySetList` in component class | — | — | compile | `cd src/angular && npx tsc --noEmit -p src/tsconfig.app.json` | ✅ | ✅ green |
| 72-04-02 | 04 | 3 | Header `th.col-checkbox` select-all, selection-clear on page/segment/sub-status change, Esc-to-clear with input guard, shift-click range via `_currentPagedFiles` | T-72-13, T-72-14 | `_isInputElement` guard; `beginOperation`/`endOperation` race protection | unit (DOM) | `cd src/angular && npx ng test --include='**/transfer-table.component.spec.ts' --watch=false --browsers=ChromeHeadless` | ✅ `src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts` (42 specs) | ✅ green |
| 72-04-03 | 04 | 3 | Bulk-action dispatch (5 actions: Queue, Stop, Extract, Delete Local, Delete Remote) with confirm-modal preview + escapeHtml | T-72-09, T-72-10, T-72-12 | `escapeHtml` on preview; backend re-validates per-file; `operationInProgress` disables during flight | unit (DOM) | (same as 72-04-02) | ✅ | ✅ green |
| 72-05-01 | 05 | 4 | Page-object helpers (`getRowCheckbox`, `getHeaderCheckbox`, `getActionBar`, `getActionButton`, `selectFileByName`, `clearSelectionViaBar`) | T-72-15 | Stable class selectors enforced by unit-spec acceptance | typecheck | `cd src/e2e && npx tsc --noEmit` | ✅ `src/e2e/tests/dashboard.page.ts` | ✅ green |
| 72-05-02 | 05 | 4 | Restore 5 dashboard selection/action E2E tests (D-19) | T-72-15, T-72-16 | Fresh browser context per test | E2E | `cd src/e2e && npx playwright test tests/dashboard.page.spec.ts --reporter=list` | ✅ `src/e2e/tests/dashboard.page.spec.ts` (7 tests: 2 pre-existing + 5 restored) | ⚠️ CI-gated |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky/CI-gated*

---

## Wave 0 Requirements

Existing Angular/Karma + Playwright/TypeScript infrastructure covered every phase requirement — no framework installs or fixture scaffolding were needed. `ClickStopPropagation` directive and `FileSelectionService` were already present (pre-phase), consumed unchanged.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard E2E runtime (5 restored tests in `dashboard.page.spec.ts`) | 72-05-02 | Playwright backend runs inside Docker via `make run-tests-e2e`; harness is arm64-fragile locally (documented tech-debt in STATE.md: `rar` package is amd64-only). CI executes the suite on every push. | Push branch and monitor CI `e2e` job OR on an amd64 host: `make run-tests-e2e`. |
| Visual/interaction polish of bar + row-selected styling (Variant B palette) | 72-01-01, 72-03-01 | Unit specs assert DOM/class contracts; final amber palette + row-selected wash are pixel-level choices that only a human eye validates. | Run `ng serve`, select 1–3 files in the dashboard, confirm: (a) amber action bar appears card-internal, (b) `row-selected` rows get the amber wash + 3px left border, (c) pagination/segment change clears selection. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or documented manual-only reason
- [x] Sampling continuity: every plan has at least one automated verify per wave
- [x] Wave 0 covers all MISSING references (no gaps — existing infra covered all requirements)
- [x] No watch-mode flags (`--watch=false` on every `ng test` invocation)
- [x] Feedback latency < 60s scoped / < 3 min full
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-19

---

## Validation Audit 2026-04-19

| Metric | Count |
|--------|-------|
| Requirements tracked | 9 |
| COVERED (automated green) | 8 |
| PARTIAL (CI-gated) | 1 |
| MISSING | 0 |
| Gaps filled this run | 0 |

Input state: B (reconstructed from 5 PLANs + 5 SUMMARYs; no prior VALIDATION.md). All 104 unit specs (bulk-actions-bar 33 + transfer-row 22 + transfer-table 42 + existing dashboard-log-pane/stats-strip) reported green in respective plan summaries. The single PARTIAL (72-05-02) is an environment-level runtime gap, not a test-authorship gap — tests exist, typecheck clean, execute in CI.
