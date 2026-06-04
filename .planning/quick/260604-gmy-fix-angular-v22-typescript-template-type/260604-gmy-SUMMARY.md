---
phase: quick-260604-gmy
plan: 01
subsystem: angular-frontend
tags: [angular-v22, strict-templates, typescript, type-safety, dependabot, pr-merge]
dependency_graph:
  requires: []
  provides: [angular-v22-migration-complete]
  affects: [src/angular/src/app/pages/settings, src/angular/src/app/pages/main]
tech_stack:
  added: []
  patterns: [typed-accessor-pattern, nullish-coalesce, keyof-narrowing]
key_files:
  created: []
  modified:
    - src/angular/src/app/pages/main/notification-bell.component.html
    - src/angular/src/app/pages/settings/options-list.ts
    - src/angular/src/app/pages/settings/settings-page.component.ts
    - src/angular/src/app/pages/settings/settings-page.component.html
    - src/angular/src/app/pages/settings/option.component.ts
decisions:
  - "Typed accessor getConfigValue() isolates the one unavoidable Immutable Record cast to a single commented .ts location — zero casts in templates, strictTemplates preserved"
  - "IOption.valuePath[0] retyped as keyof IConfig to propagate type narrowing from options-list through template bindings"
  - "OptionComponent description @Input widened to string | null (matching all call sites) rather than using $any() in templates"
metrics:
  duration: ~40 minutes
  completed: 2026-06-04
  tasks_completed: 2
  files_changed: 5
---

# Quick Task 260604-gmy: Fix Angular v22 Strict-Template Type Errors

**One-liner:** Angular v22 migration complete — 5 TS errors resolved via typed accessor, keyof narrowing, and nullish-coalesce; PR #50 squash-merged with all CI green.

## What Was Done

PR #50 bumped Angular v21 to v22. Angular v22 enables stricter template type-checking by default, surfacing latent type errors in templates that v21 tolerated. The only failing CI job was "Build Docker Image" (production `ng build --configuration=production`). All source files were identical to `main`; the fixes landed on the Dependabot branch.

## Changes Applied

### Task 1: Type fixes on Dependabot branch (commit de24bc9)

**FIX 1 — notification-bell.component.html (TS2532)**
- Line 5: `@if (notifs?.size > 0)` → `@if ((notifs?.size ?? 0) > 0)`
- `notifs?.size` is `number | undefined`; nullish-coalesce to 0 before comparison.

**FIX 2 — options-list.ts (TS2345)**
- Added `import {IConfig}` from config.ts
- `valuePath: [string, string]` → `valuePath: [keyof IConfig, string]`
- All literal values in the options-list (`"lftp"`, `"controller"`, etc.) are valid `keyof IConfig` members — no data changes required.

**FIX 3 — settings-page.component.ts (TS2339 / TS2345)**
- Added `IConfig` to the existing config import
- `onSetConfig(section: string, ...)` → `onSetConfig(section: keyof IConfig, ...)`
- Added `getConfigValue(config: Config | null, section: keyof IConfig, option: string): string | number | boolean` — a typed accessor that performs the Immutable `.get()` chain in one isolated, type-safe place. Any cast is localized to this single method with an explanatory comment. Returns `string | number | boolean` with `""` as the null/undefined fallback.

**FIX 4 — settings-page.component.html (TS2339 / TS2322)**
- Replaced all 30 occurrences of `(config | async)?.get(...)?.get(...)` chained calls with `getConfigValue(config | async, section, option)` — including `app-option [value]` bindings, `[ngModel]` toggles, `fieldset [attr.disabled]`, `[class.settings-card-body--disabled]`, `[attr.inert]`, webhook URL string concatenations, and `formatMs(...)` arguments.
- Zero template casts; strictTemplates intact.

### Deviation fix during CI (commit 222e8cb)

**FIX 5 — option.component.ts (TS2322 follow-on)**

CI surfaced a second wave of TS2322 errors at `[description]="option.description"` bindings across 5 locations. Root cause: `@Input() description!: string` was non-nullable, but `IOption.description: string | null` (and all options-list call sites) passes null. v22's strict input binding check now rejects this.

Fix: `@Input() description!: string` → `@Input() description: string | null = null`. The component template already guards with `@if (description)` at all 3 usage sites — no behavior change.

This was an inline fix of the same error class (TS2322, strict template type-checking) per the plan's "same-class follow-on" protocol.

## Commits

| Commit | Branch | Description |
|--------|--------|-------------|
| de24bc9 | dependabot/... | fix(angular): resolve v22 strict-template type errors (TS2532/TS2339/TS2345/TS2322) |
| 222e8cb | dependabot/... | fix(angular): allow nullable description @Input in OptionComponent (TS2322) |
| ac087a5 | main | chore(deps): bump the npm_and_yarn group in /src/angular with 18 updates (#50) [squash merge] |

## CI Results

| Job | Result |
|-----|--------|
| Build Docker Image | pass (6m22s) |
| End-to-end tests on Docker Image (amd64) | pass (3m44s) |
| Angular unit tests | pass |
| Lint (Angular) | pass |
| Lint (Python) | pass |
| Python unit tests | pass |
| CodeQL | pass |
| Analyze (actions/javascript-typescript/python) | pass |
| Release metadata verifier tests | pass |
| Verify release metadata | pass |
| Publish/E2E/Docs | skipping (non-release PR — expected) |

## PR #50 Status

- **Merged:** 2026-06-04T16:30:21Z (squash merge)
- **Dependabot branch deleted:** confirmed (`git ls-remote` returns empty)
- **Local main:** rebased and up-to-date at ac087a5

## Verification Gates (all passed)

- No bare `notifs?.size >` in notification-bell.html
- No `(config | async)?.get(` in settings-page.component.html (0 matches)
- `getConfigValue(` count in settings-page.component.html: 30 occurrences
- `getConfigValue` defined in settings-page.component.ts
- No `$any(` or `as any` in templates
- `valuePath: [keyof IConfig` present in options-list.ts
- `strictTemplates` not disabled in any tsconfig

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical type fix] Nullable description @Input in OptionComponent**
- **Found during:** Task 2 (first CI run exposed TS2322 at [description]= bindings)
- **Issue:** `@Input() description!: string` was non-nullable; all `IOption.description` values and options-list call sites use `string | null`. Angular v22's strict input binding check rejects passing `null` to a non-nullable `@Input`.
- **Fix:** Widened to `@Input() description: string | null = null`; component template already guards with `@if (description)` — no behavioral change.
- **Files modified:** `src/angular/src/app/pages/settings/option.component.ts`
- **Commit:** 222e8cb
- **Classification:** Same-class TS2322 follow-on per plan's inline-fix protocol.

## Self-Check

- [x] All 5 modified files exist on disk
- [x] Commits de24bc9 and 222e8cb exist on the remote and are in the squash commit ac087a5 on main
- [x] PR #50 state=MERGED, mergedAt=2026-06-04T16:30:21Z
- [x] Remote dependabot branch deleted
- [x] Local HEAD is main at 6b4e475 (planning commit on top of ac087a5)

## Self-Check: PASSED
