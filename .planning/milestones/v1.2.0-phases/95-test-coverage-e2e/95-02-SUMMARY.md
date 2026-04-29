---
phase: 95-test-coverage-e2e
plan: "02"
subsystem: e2e-tests
tags: [e2e, playwright, settings, coverage, COVER-03]
dependency_graph:
  requires: []
  provides: [settings-fields-e2e-coverage]
  affects: [src/e2e/tests/settings.page.ts, src/e2e/tests/settings-fields.spec.ts]
tech_stack:
  added: []
  patterns: [page-object-model, api-set-reload-verify, floating-save-bar-confirmation, afterEach-cleanup]
key_files:
  modified:
    - src/e2e/tests/settings.page.ts
  created:
    - src/e2e/tests/settings-fields.spec.ts
decisions:
  - "D-07: Representative sample of 3 field types (text, checkbox, interval) rather than exhaustive coverage"
  - "D-08: Skip Radarr, API/Security token, and AutoQueue fields per plan spec"
  - "D-11: API-set -> reload -> verify pattern for 3 cheaper tests; UI-to-UI round-trip for 2 costlier tests"
  - "D-12: afterEach restores original config values via API-set with .catch(() => {}) to prevent cross-test pollution"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-28T20:55:23Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 95 Plan 02: Settings Fields E2E Coverage Summary

**One-liner:** Extended SettingsPage page object with API-set/locator/UI methods and created 8-test E2E spec covering text field, checkbox, and interval fields with floating save bar confirmation and API round-trip persistence.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend SettingsPage page object with config field methods | c5ead8d | src/e2e/tests/settings.page.ts |
| 2 | Create Settings fields E2E specs | a38b42e | src/e2e/tests/settings-fields.spec.ts |

## What Was Built

### Task 1: SettingsPage page object extension

Added to `src/e2e/tests/settings.page.ts`:

- Added `Locator` to the `@playwright/test` import
- 3 API-set methods following exact existing pattern (check `.ok()`, throw on failure):
  - `setRemoteAddress(address: string)` — sets `lftp/remote_address`
  - `setUseSshKey(enabled: boolean)` — sets `lftp/use_ssh_key`
  - `setRemoteScanInterval(ms: string)` — sets `controller/interval_ms_remote_scan`
- 5 locator methods using `app-option` + `.filter({ hasText })` (brittle CSS-position-free):
  - `getServerAddressInput()`, `getSshKeyCheckbox()`, `getRemoteScanIntervalInput()`
  - `getFloatingSaveBar()`, `getSaveSettingsButton()`
- 3 UI interaction/value methods:
  - `fillServerAddress(address)`, `getServerAddressValue()`, `getSshKeyChecked()`, `getRemoteScanIntervalValue()`

All existing Sonarr methods unchanged.

### Task 2: settings-fields.spec.ts (8 tests)

Imports from `./fixtures/csp-listener` (not `@playwright/test` directly).

| Test | Coverage requirement |
|------|---------------------|
| should display Server Address field with current value | D-07 (text field visible) |
| should persist Server Address via API-set and reload | D-11 (API-set -> reload) |
| should display SSH key auth checkbox | D-07 (checkbox visible) |
| should persist SSH key auth toggle via API-set and reload | D-11 (API-set -> reload) |
| should display Remote Scan Interval field | D-07 (interval visible) |
| should persist Remote Scan Interval via API-set and reload | D-11 (API-set -> reload) |
| should show Changes Saved after UI field edit | D-09 (floating save bar) |
| should persist value after UI edit and page reload | D-10 (UI-to-UI round-trip) |

Key implementation details:
- `beforeEach` (not `beforeAll`) per E2EFIX-04
- `afterEach` restores all 3 fields via API-set with `.catch(() => {})` (D-12)
- `toContainText('Changes Saved', { timeout: 5000 })` absorbs 1000ms debounce + network (no `waitForTimeout`)
- No `page.route()`, no Radarr/AutoQueue/token fields (D-08)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all tests exercise real functionality.

## Threat Flags

None - test-only files, no new trust boundaries or network endpoints introduced.

## Self-Check

Checking files exist and commits are present:

- FOUND: src/e2e/tests/settings.page.ts
- FOUND: src/e2e/tests/settings-fields.spec.ts
- FOUND: .planning/phases/95-test-coverage-e2e/95-02-SUMMARY.md
- FOUND: commit c5ead8d (Task 1)
- FOUND: commit a38b42e (Task 2)

## Self-Check: PASSED
