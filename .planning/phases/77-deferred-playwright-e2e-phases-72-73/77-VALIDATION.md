---
phase: 77
slug: deferred-playwright-e2e-phases-72-73
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 77 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright @playwright/test ^1.48.0 (TypeScript ^5.3.0) |
| **Config file** | `src/e2e/playwright.config.ts` |
| **Quick run command** | `cd src/e2e && npx playwright test tests/dashboard.page.spec.ts --reporter=line` |
| **Full suite command** | `make run-tests-e2e` |
| **Estimated runtime** | ~8–15 min full Docker harness; ~60–180s for a focused spec on a running target |

---

## Sampling Rate

- **After every task commit:** Run the focused quick command on the specific spec/helper being touched (e.g., `npx playwright test -g "FIX-01 union"`)
- **After every plan wave:** Run the full dashboard spec locally: `cd src/e2e && npx playwright test tests/dashboard.page.spec.ts`
- **Before `/gsd-verify-work`:** `make run-tests-e2e` must be green on amd64 (arm64 matrix validated in CI)
- **Max feedback latency:** ~180s for per-task focused runs; ~15 min for the full Docker harness

---

## Per-Task Verification Map

*Plans will populate task IDs. The skeleton below enumerates one row per net-new spec/helper so the planner can slot each task into a concrete automated command. All commands run from `src/e2e/`.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 77-01-01 | 01 | 1 | UAT-01, UAT-02 | — | N/A (test-only) | e2e-helper | `npx tsc --noEmit` (type check `seed-state.ts`) | ❌ W0 | ⬜ pending |
| 77-01-02 | 01 | 1 | UAT-01, UAT-02 | — | N/A | e2e-helper | `npx tsc --noEmit` (type check `dashboard.page.ts`) | ✅ | ⬜ pending |
| 77-02-01 | 02 | 2 | UAT-01 | — | N/A | e2e | `npx playwright test -g "per-file selection"` | ✅ | ⬜ pending |
| 77-02-02 | 02 | 2 | UAT-01 | — | N/A | e2e | `npx playwright test -g "shift-range"` | ✅ | ⬜ pending |
| 77-02-03 | 02 | 2 | UAT-01 | — | N/A | e2e | `npx playwright test -g "page-scoped header"` | ✅ | ⬜ pending |
| 77-02-04 | 02 | 2 | UAT-01 | — | N/A | e2e | `npx playwright test -g "bulk bar visibility"` | ✅ | ⬜ pending |
| 77-02-05 | 02 | 2 | UAT-01 | — | N/A | e2e | `npx playwright test -g "FIX-01 union"` | ✅ | ⬜ pending |
| 77-02-06..10 | 02 | 2 | UAT-01 | — | N/A | e2e | `npx playwright test -g "bulk action (queue|stop|extract|delete local|delete remote)"` | ✅ | ⬜ pending (optional D-19 split) |
| 77-03-01..08 | 03 | 3 | UAT-02 | — | N/A | e2e | `npx playwright test -g "status filter (pending|syncing|queued|extracting|synced|extracted|failed|deleted)"` | ✅ | ⬜ pending |
| 77-03-09 | 03 | 3 | UAT-02 | — | N/A | e2e | `npx playwright test -g "URL round-trip parent"` | ✅ | ⬜ pending |
| 77-03-10 | 03 | 3 | UAT-02 | — | N/A | e2e | `npx playwright test -g "URL round-trip sub"` | ✅ | ⬜ pending |
| 77-04-01 | 04 | 4 | UAT-01, UAT-02 | — | N/A | e2e-ci | `make run-tests-e2e` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: Task ID shape `{phase}-{plan}-{task}` — final numbering set by planner. EXTRACTING + QUEUED specs may collapse to empty-state assertions per research (A2) since fixture files are not archives.*

---

## Wave 0 Requirements

- [ ] `src/e2e/tests/fixtures/seed-state.ts` — new module, typed API (`seedStatus`, `seedMultiple`, `queueFile`, `stopFile`, `deleteLocal`, `deleteRemote`, `extract`) per CONTEXT D-04
- [ ] Extend `src/e2e/tests/dashboard.page.ts` — add 9 helpers per CONTEXT D-11 (`shiftClickFile`, `clickHeaderCheckbox`, `getSelectedCount`, `getStatusBadge`, `getEmptyStatePanel` or empty-row equivalent, `getToast`, `getClearSelectionLink`, `waitForFileStatus`, `clickConfirmModalConfirm`)
- [ ] No framework install (Playwright already present in `src/e2e/package.json`)

*Wave 0 is the single up-front plan per CONTEXT D-12: helpers land before any spec work.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| arm64 CI green | UAT-01, UAT-02 Success #3 | Local dev is typically amd64; arm64 path runs only on CI matrix | Push to branch, observe both amd64 + arm64 `run-tests-e2e` CI jobs green |

*All UAT assertions at the spec level have automated verification via Playwright.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`seed-state.ts` + new `DashboardPage` helpers)
- [ ] No watch-mode flags (Playwright runs one-shot; `--ui` / `--debug` disallowed in commit-time verify)
- [ ] Feedback latency < 180s for per-task focused runs
- [ ] `nyquist_compliant: true` set in frontmatter after planner + checker sign-off

**Approval:** pending
