---
phase: 72
slug: restore-dashboard-file-selection-and-action-bar
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-19
---

# Phase 72 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user→DOM (counts) | Integer `selectedCount` rendered inside bulk-actions-bar label | Non-sensitive integer |
| user→DOM (filenames) | `file.name` rendered in transfer-row aria-label/title and confirm-modal preview | User-controlled string |
| component→SCSS | Hard-coded palette values only | None |
| row→service | Checkbox click emits `{file, shiftKey}` to parent | `ViewFile` object |
| client→server | BulkCommandService POSTs file names to `/server/command/bulk` | Action + filename list |
| document→component | `@HostListener('document:keydown')` on transfer-table | Keyboard events |
| repo→build | Source-file deletion could leave dangling imports | Angular module graph |
| test→app | Playwright drives a real browser against the dev server | DOM class selectors |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-72-01 | Tampering (DOM-XSS) | bulk-actions-bar template | accept | Integer `selectedCount` rendered via `{{ }}` only — no filename displayed. `bulk-actions-bar.component.html:4`, getter at `bulk-actions-bar.component.ts:174-176`. | closed |
| T-72-02 | Elevation of Privilege | action button disabled state | mitigate | `[disabled]="actionCounts.<x> === 0 \|\| operationInProgress"` on every action button; backend re-validates per-file in `bulk-command.service.ts:97`. | closed |
| T-72-03 | Denial of Service (spam-click) | action buttons + clear-btn | mitigate | `\|\| operationInProgress` disables all action buttons AND clear-btn during in-flight ops (`bulk-actions-bar.component.html:6,17,22,27,33,38`). | closed |
| T-72-04 | Denial of Service (build failure) | src/angular/src/app | mitigate | Pre-delete exhaustive grep + post-delete `ng build` green gate; no `innerHTML`/`bypassSecurity` introduced. | closed |
| T-72-05 | Tampering (accidental over-deletion) | bulk-actions-bar, transfer-row, transfer-table | mitigate | `test -f` preserved on `bulk-actions-bar.component.ts`, `transfer-row.component.ts`, `transfer-table.component.ts`. | closed |
| T-72-06 | Tampering (DOM-XSS via filename) | transfer-row template | mitigate | `[attr.aria-label]`, `[title]`, and `{{ file.name }}` — all auto-escaped property/interpolation bindings; no `innerHTML`. `transfer-row.component.html:5,7-8`. | closed |
| T-72-07 | Tampering (event-bubble hijack) | row click handlers | mitigate | `appClickStopPropagation` directive on row (`click-stop-propagation.directive.ts:8-11`) + explicit `event.stopPropagation()` in `transfer-row.component.ts:44-47`. | closed |
| T-72-08 | Repudiation / state drift | selection signal | accept | FileSelectionService is the single source of truth; row only reads via `inject(FileSelectionService)` + `computed()` (`transfer-row.component.ts:24-29`). | closed |
| T-72-09 | Tampering (DOM-XSS via filename preview) | confirm-modal body | mitigate | `ConfirmModalService.createModal` calls `escapeHtml(options.body)` before `innerHTML` insertion (`confirm-modal.service.ts:33-40,52,107`). | closed |
| T-72-10 | Elevation of Privilege | client disabled state (bulk) | mitigate | Client disable is UX only; backend re-validates per-file eligibility on POST to `/server/command/bulk` and returns per-file `BulkFileResult` (`bulk-command.service.ts:101`). | closed |
| T-72-11 | CSRF on bulk endpoint | `/server/command/bulk` POST | accept | No new endpoint; inherits Phase-50 API-token authentication / HttpClient interceptor. | closed |
| T-72-12 | Denial of Service (spam bulk op) | action buttons + selection service | mitigate | `beginOperation`/`endOperation` set `operationInProgress` signal; both success and error branches call `endOperation` (`transfer-table.component.ts:370,380,388`). | closed |
| T-72-13 | Keyboard hijack (Esc while typing) | `@HostListener('document:keydown')` | mitigate | `_isInputElement(target)` guard bails for `input`/`textarea`/`select` (`transfer-table.component.ts:239-245,247-251`). | closed |
| T-72-14 | Race condition: file list updates mid-bulk-op | FileSelectionService pruneSelection | mitigate | `pruneSelection` early-returns while `_operationInProgress()` (`file-selection.service.ts:207-222,232-234,240-242`); `endOperation` called on both branches. | closed |
| T-72-15 | Tampering (brittle-selector regression) | E2E page-object selectors | mitigate | `src/e2e/tests/dashboard.page.ts` uses stable class selectors (`.transfer-table`, `app-transfer-row`, `td.cell-checkbox input.ss-checkbox`, `app-bulk-actions-bar`, `button.action-btn`, `button.clear-btn`) matching template classes enforced by plans 01/03/04. | closed |
| T-72-16 | Repudiation (test isolation) | Playwright `beforeEach navigateTo` | accept | `src/e2e/tests/dashboard.page.spec.ts:9-12` uses `test.beforeEach` with fresh per-test browser context (Playwright default). | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-72-01 | T-72-01 | bulk-actions-bar renders only integer `selectedCount` via Angular interpolation — no filename path where XSS could land in this component. | gsd-security-auditor | 2026-04-19 |
| AR-72-02 | T-72-08 | FileSelectionService is the single writer; transfer-row reads via `computed()` only, so no mutation race is possible from the row itself. | gsd-security-auditor | 2026-04-19 |
| AR-72-03 | T-72-11 | Bulk endpoint inherits Phase-50 API-token / CSRF infrastructure. This phase adds no new endpoints or auth surface. | gsd-security-auditor | 2026-04-19 |
| AR-72-04 | T-72-16 | Playwright spawns a fresh browser context per test by default and `beforeEach` navigates to a clean route — cross-test selection leakage is structurally prevented. | gsd-security-auditor | 2026-04-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-19 | 16 | 16 | 0 | gsd-security-auditor |

### Audit 2026-04-19 — Initial

| Metric | Count |
|--------|-------|
| Threats found | 16 |
| Closed | 16 |
| Open | 0 |

Input state: B (no prior SECURITY.md; built from 5 PLANs). All 12 `mitigate` threats verified against implementation; all 4 `accept` threats confirmed to still hold (no new code introduces the accepted risk pattern).

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-19
