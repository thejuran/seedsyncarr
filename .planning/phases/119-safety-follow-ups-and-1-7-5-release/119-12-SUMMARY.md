---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 12
subsystem: settings-ui, e2e, docs
tags: [angular, settings, docs, e2e, imp-01, imp-02, r10, use_temp_file]
requires: [119-06]
provides:
  - Settings UI without the use_temp_file toggle (config key retained)
  - e2e seed queue calls with ?release_unverified=true
  - Configuration docs for always-on temp files and completion holds
affects: [src/angular settings page, src/e2e seed fixture, docs/CONFIGURATION.md, src/python/docs/configuration.md]
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - src/angular/src/app/pages/settings/options-list.ts
    - src/e2e/tests/fixtures/seed-state.ts
    - docs/CONFIGURATION.md
    - src/python/docs/configuration.md
decisions:
  - "Seed fixture appends ?release_unverified=true to every ENDPOINT.queue call (single definition covers all seed paths); no other direct queue POSTs exist in src/e2e"
  - "Docs describe Ambiguous match from the actual gate logic (multiple downloads or an unidentifiable queue entry), not a guess"
metrics:
  duration: ~15min
  completed: 2026-10-14
  tasks: 2
  files: 4
---

# Phase 119 Plan 12: Settings/docs/e2e slice of IMP-01/IMP-02 Summary

Removed the "Rename unfinished/downloading files" (`use_temp_file`) checkbox from Settings while keeping the config key, made the e2e seed helper send `release_unverified=true` on queue, and documented always-on temp files, the five held-item reasons, the confirmed one-shot manual release, and the D-16 limitation.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Remove use_temp_file toggle; e2e seed release flag | 3000994 | options-list.ts, seed-state.ts |
| 2 | Document always-on temp files and completion holds | 931d742 | docs/CONFIGURATION.md, src/python/docs/configuration.md |

## Verification (observed)

- Task 1 verify greps: `TOGGLE_E2E_OK` (0 "Rename unfinished" in options-list.ts; `use_temp_file` still in config.ts; `release_unverified=true` in seed-state.ts).
- e2e type-check: `cd src/e2e && npm ci && npx tsc --noEmit -p tsconfig.json` -> `TSC_E2E_OK` (exit 0).
- Angular runner: Docker was not running, so used `npx ng test --watch=false --browsers=ChromeHeadless` (after `npm ci` from lockfile, CHROME_BIN set to local Google Chrome). Result: `Chrome Headless 155.0.0.0: Executed 618 of 618 SUCCESS` / `TOTAL: 618 SUCCESS`. CI `unittests-angular` remains the authority.
- Angular lint: `npm run lint` (eslint, --max-warnings 0) exited clean.
- No Angular spec named or counted the removed option (grep of src/angular/src and src/e2e); config.spec.ts / config.service.spec.ts keep `use_temp_file` unchanged.
- Task 2 verify: `DOCS_OK`; "Transfer and release this item anyway" count = 1; "Sonarr unavailable" count = 1; `use_temp_file` line in src/python/docs/configuration.md contains "Ignored".
- e2e flag runtime behaviour (backend ignoring the flag when no arr is enabled) was NOT exercised locally — no e2e harness run. It is covered by CI e2e on the 119-09 push. Backend parsing confirmed by reading `src/python/web/handler/controller.py` (`request.query.get("release_unverified", "").lower() == "true"`).

## Deviations from Plan

None in scope. The plan's "harness has no arr enabled" claim was taken from the plan context; the seed comment states it as the reason the flag is normally ignored.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/angular/src/app/pages/settings/options-list.ts, src/e2e/tests/fixtures/seed-state.ts, docs/CONFIGURATION.md, src/python/docs/configuration.md
- FOUND commits: 3000994, 931d742
