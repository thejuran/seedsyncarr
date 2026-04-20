# Security Audit — Phase 72 (restore-dashboard-file-selection-and-action-bar)

**Date:** 2026-04-19
**ASVS Level:** 1
**Block-on:** high
**Result:** SECURED — 16/16 threats closed
**Unregistered flags:** none

## Scope

Phase 72 restored the dashboard file-selection checkboxes and bulk-action bar for the Angular v1.1.0 SeedSync UI. Five plans (72-01 through 72-05) each declared a small threat model. This audit verifies each registered mitigation exists in implementation. No new endpoints, auth flows, or data stores were introduced.

## Threat Verification

### Plan 72-01 — bulk-actions-bar restore

| ID | Category | Disposition | Evidence | Status |
|---|---|---|---|---|
| T-72-01 | Tampering (DOM-XSS via selectedCount) | accept | `bulk-actions-bar.component.html:4` — `{{ selectedCount }}` is an integer getter (`bulk-actions-bar.component.ts:174-176`, returns `this.selectedFiles.size`). Angular interpolation escapes; no filenames rendered in bar. Acceptance rationale holds. | CLOSED |
| T-72-02 | Elevation of Privilege (client button state) | mitigate | `bulk-actions-bar.component.html:17,22,27,33,38` — every action button has `[disabled]="actionCounts.<x> === 0 \|\| operationInProgress"`. Eligibility counts derive from server-owned `ViewFile` flags (`bulk-actions-bar.component.ts:101-116`). Backend re-validates per-file in `bulk-command.service.ts:97` posting to `/server/command/bulk`. | CLOSED |
| T-72-03 | DoS (spam-click) | mitigate | `bulk-actions-bar.component.html:6,17,22,27,33,38` — `[disabled]="... \|\| operationInProgress"` on every action button AND the clear-btn. `operationInProgress` wired in `transfer-table.component.ts:370-388` via `beginOperation`/`endOperation`. | CLOSED |

### Plan 72-02 — delete obsolete components

| ID | Category | Disposition | Evidence | Status |
|---|---|---|---|---|
| T-72-04 | DoS (build failure from dangling refs) | mitigate | Preserved files compile; no `innerHTML` / `bypassSecurity` references (see Grep). Phase summaries confirm `ng build` passing. | CLOSED |
| T-72-05 | Tampering (over-deletion) | mitigate | `test -f` confirms: `bulk-actions-bar.component.ts` (8127 B), `transfer-row.component.ts` (3321 B), `transfer-table.component.ts` (17992 B) all present and non-empty. | CLOSED |

### Plan 72-03 — transfer-row restore

| ID | Category | Disposition | Evidence | Status |
|---|---|---|---|---|
| T-72-06 | Tampering (DOM-XSS via filename) | mitigate | `transfer-row.component.html:5,7-8` — filename flows through `[attr.aria-label]`, `[title]`, and `{{ file.name }}` — all auto-escaping property/interpolation bindings. `transfer-row.component.ts:38-42` builds `hostAriaLabel` as plain string (no HTML). No `innerHTML` or `DomSanitizer.bypass*` anywhere in `pages/files/`. | CLOSED |
| T-72-07 | Tampering (event-bubble hijack) | mitigate | `transfer-row.component.html:1` — `td.cell-checkbox` has `appClickStopPropagation` directive. `click-stop-propagation.directive.ts:8-11` calls `event.stopPropagation()`. `transfer-row.component.ts:44-47` — `onCheckboxClick` also calls `event.stopPropagation()` explicitly. Defense-in-depth present. | CLOSED |
| T-72-08 | Repudiation / state drift (selection signal) | accept | `transfer-row.component.ts:24-29` — row reads via `inject(FileSelectionService)` + `computed(() => selectionService.selectedFiles().has(file.name))`. Single source of truth preserved; no local selection state on row. Acceptance rationale holds. | CLOSED |

### Plan 72-04 — wire transfer-table to selection + bulk actions

| ID | Category | Disposition | Evidence | Status |
|---|---|---|---|---|
| T-72-09 | Tampering (DOM-XSS via filename preview in modal) | mitigate | `transfer-table.component.ts:316-317, 335-336` build preview via `_buildPreviewSuffix` (plain string concat). `confirm-modal.service.ts:52` calls `escapeHtml(options.body)` before injecting into `modalElement.innerHTML` (`confirm-modal.service.ts:107`). escapeHtml escapes `& < > " '` (`confirm-modal.service.ts:33-40`). | CLOSED |
| T-72-10 | Elevation of Privilege (client disabled state) | mitigate | Client `[disabled]` on bulk-actions-bar is UX only; server-side re-validation occurs in `bulk-command.service.ts:101` POST to `/server/command/bulk`. Per-file result set in `BulkActionResponse.results` indicates server enforces eligibility. | CLOSED |
| T-72-11 | CSRF on bulk endpoint | accept | No new endpoint; `/server/command/bulk` uses existing HttpClient interceptor / API-token mechanism inherited from Phase 50. No auth code introduced in this phase. Acceptance rationale holds. | CLOSED |
| T-72-12 | DoS (spam bulk op) | mitigate | `transfer-table.component.ts:370-388` — `beginOperation()` called before dispatch; `endOperation()` in both `next` and `error` branches. `bulkOperationInProgress = true` sets UX signal → buttons disable (see T-72-03). | CLOSED |
| T-72-13 | Keyboard hijack (Esc while typing) | mitigate | `transfer-table.component.ts:239-245` — `@HostListener("document:keydown", ["$event"])` guards with `!this._isInputElement(event.target)`. `_isInputElement` (lines 247-251) returns true for `input`, `textarea`, `select` — Esc in a form field is a no-op. | CLOSED |
| T-72-14 | Race condition (file list updates mid-bulk-op) | mitigate | `file-selection.service.ts:207-222` — `pruneSelection` early-returns when `this._operationInProgress()` is true. `beginOperation` (line 232-234) sets the signal; `endOperation` (line 240-242) resets it. Caller wires both: `transfer-table.component.ts:370` begin, `:380` end (success), `:388` end (error). | CLOSED |

### Plan 72-05 — E2E Playwright restore

| ID | Category | Disposition | Evidence | Status |
|---|---|---|---|---|
| T-72-15 | Brittle selector regression | mitigate | `src/e2e/tests/dashboard.page.ts:19-22, 38, 42-46, 57, 61, 66, 69, 77` — page object uses stable class-name selectors enforced by 72-01/03/04 templates: `.transfer-table`, `app-transfer-row`, `td.cell-name .file-name`, `td.cell-status .status-badge`, `td.cell-checkbox input.ss-checkbox`, `app-bulk-actions-bar`, `button.action-btn`, `button.clear-btn`. All selectors match actual class names in implementation HTML. | CLOSED |
| T-72-16 | Repudiation (test isolation) | accept | `src/e2e/tests/dashboard.page.spec.ts:9-12` — `test.beforeEach(async ({ page }) => { ... await dashboardPage.navigateTo(); })`. Playwright creates a fresh browser context per test by default. Acceptance rationale holds. | CLOSED |

## Unregistered Flags

None — SUMMARY.md files (72-01..72-05) contain no additional `## Threat Flags` section.

## Accepted Risks Log

| ID | Risk | Rationale |
|---|---|---|
| T-72-01 | Selection-count interpolation | Integer-only value via Angular `{{ }}` auto-escape; no filename surface in bar. |
| T-72-08 | Signal-based selection state | `FileSelectionService` is the single source of truth, read-only via `computed()`; no duplicate state. |
| T-72-11 | CSRF on bulk endpoint | Reuses Phase-50 API-token / HttpClient interceptor. No new auth surface added. |
| T-72-16 | E2E isolation via `beforeEach` navigateTo | Playwright default per-test context provides browser-level isolation. |

## Audit Conclusion

All 16 registered threats are closed. No implementation changes required. No unregistered attack surface detected during audit. Phase 72 is cleared for merge under `block_on: high`.
