---
quick_id: 260604-g9c
type: execute
date: 2026-06-04
duration_minutes: 25
status: partial_success
---

# Quick Task 260604-g9c: Handle Open Dependabot PRs and Alerts — Summary

**One-liner:** Merged webob security fix (#51) and ruff bump (#49) to main; fixed Angular v22 istanbul coverage gap on the dependabot branch; PR #50 not merged — blocked by new Angular v22 TypeScript type errors in production build.

## Results

### Task 1: Merge green PRs #51 and #49 — COMPLETE

| PR | Title | Merged At | State |
|----|-------|-----------|-------|
| #51 | bump webob 1.8.9 -> 1.8.10 in /src/python | 2026-06-04T15:46:44Z | MERGED |
| #49 | bump ruff 0.15.14 -> 0.15.15 in /src/python | 2026-06-04T15:46:53Z | MERGED |

Dependabot security alert #19 (webob open-redirect, medium): auto-closed as `fixed` at 2026-06-04T15:47:50Z, ~66 seconds after PR #51 squash-merged.

### Task 2: Add istanbul-lib-instrument to PR #50 dependabot branch — COMPLETE

- Fetched and checked out `dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef` as a local tracking branch.
- Confirmed branch had Angular v22 (`"@angular/core": "^22.0.0"`).
- Added `"istanbul-lib-instrument": "^6.0.3"` to `devDependencies` in `src/angular/package.json` (alphabetically between `globals` and `jasmine-core`).
- Regenerated `src/angular/package-lock.json` via `npm install --legacy-peer-deps` from `src/angular/`.
- Verified `require.resolve('istanbul-lib-instrument')` returns OK locally.
- Staged only `src/angular/package.json` and `src/angular/package-lock.json` (no .planning, no node_modules).
- Committed as `6255efe` with message `build(angular): add istanbul-lib-instrument devDependency for v22 coverage`.
- Pushed to `origin/dependabot/npm_and_yarn/src/angular/npm_and_yarn-e918281aef` (86896f4 -> 6255efe).

### Task 3: Wait for CI on PR #50 and merge — BLOCKED

CI completed for PR #50. The istanbul fix worked:

- Angular unit tests (Karma, with `--code-coverage`): **PASS** (1m25s) — the original failure is resolved.
- Python unit tests: PASS
- All lint jobs: PASS
- CodeQL: PASS

However, the **Build Docker Image** job failed due to NEW, unrelated Angular v22 migration failures in `ng build --configuration=production`:

```
Application bundle generation failed. [43.294 seconds]

TS2532: Object is possibly 'undefined'.
  Error occurs in the template of component NotificationBellComponent.

TS2322: Type 'string | null' is not assignable to type 'string'.
  Error occurs in the template of component SettingsPageComponent.

TS2345: Argument of type 'string' is not assignable to parameter of type 'keyof IConfig'.
  Error occurs in the template of component SettingsPageComponent.

TS2339: Property 'get' does not exist on type 'IGeneral | ILftp | IController | IWeb | IAutoQueue | ISonarr | IRadarr | IAutoDelete'.
  Error occurs in the template of component SettingsPageComponent. (multiple occurrences)
```

These errors are Angular v22's stricter TypeScript template type-checking surfacing real type gaps in `SettingsPageComponent` and `NotificationBellComponent`. This is distinct from the istanbul coverage issue and requires a proper Angular v22 code migration (template type fixes in the app source). Per plan Task 3 constraints: "If it is a NEW, unrelated Angular v22 migration failure... STOP and report the specific error to the orchestrator/user. Do NOT attempt a broad Angular v22 code migration inside this quick task."

PR #50 was NOT merged. The dependabot branch remains open with the istanbul fix committed.

## What Succeeded

- Webob security alert #19 resolved. No open Dependabot security alerts.
- PR #51 and #49 merged to main.
- The istanbul coverage root cause is fixed on the dependabot branch (unit tests pass).

## What Requires Follow-Up

PR #50 (Angular v22 group bump) remains open. The blocking failures are TypeScript errors in production build, affecting two components:

1. **`NotificationBellComponent`** — `TS2532: Object is possibly 'undefined'` in template.
2. **`SettingsPageComponent`** — Multiple failures:
   - `TS2322: string | null` not assignable to `string`
   - `TS2345: string` not assignable to `keyof IConfig`
   - `TS2339: Property 'get' does not exist on type IGeneral | ILftp | ...` (many occurrences)

The `TS2339` errors on `.get` on config sub-interfaces suggest the Angular v22 bump coincides with a stricter type-checking mode that now fails on patterns that worked in v21 (possibly related to `IConfig` being typed as a union where subtypes don't share a `get()` method — likely `Map`-style access pattern that TypeScript v5.8/v6 stricter checking now rejects in templates).

**Recommended action:** Plan a dedicated Angular v22 migration quick task or sub-phase to fix the TypeScript type errors in `NotificationBellComponent` and `SettingsPageComponent`, then re-trigger CI on PR #50 and merge.

## Deviations from Plan

None — plan explicitly directed STOP-and-report for a new, unrelated Angular v22 migration failure (Task 3 constraint), which is what occurred.

## Self-Check

- [x] PR #51 MERGED (confirmed via `gh pr view 51 --json state`)
- [x] PR #49 MERGED (confirmed via `gh pr view 49 --json state`)
- [x] Alert #19 state = `fixed` (confirmed via API)
- [x] Commit `6255efe` on remote dependabot branch (confirmed via `git show origin/...`)
- [x] `istanbul-lib-instrument` present in remote package.json (confirmed via grep)
- [x] No .planning/ files committed to dependabot branch (staged only two Angular manifest files by explicit path)
- [x] No code committed to main by this executor (only GitHub squash-merges via gh CLI)
- [x] Returned to `main` branch locally
- [x] Pulled main (now at 957a896)

## Self-Check: PASSED
