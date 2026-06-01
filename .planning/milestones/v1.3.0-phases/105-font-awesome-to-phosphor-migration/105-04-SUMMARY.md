---
phase: 105-font-awesome-to-phosphor-migration
plan: "04"
subsystem: frontend-icons
tags: [icon-migration, font-awesome, phosphor, dep-drop, bundle-delta, smoke-test, angular]
dependency_graph:
  requires: [105-02, 105-03]
  provides: [DEPS-01b-complete, D-06, D-07, D-04]
  affects: [package.json, angular.json, package-lock.json, dist]
tech_stack:
  added: []
  patterns:
    - "D-06 closing act: dep drop ONLY after all fa-* usages migrated + build + smoke test green"
    - "D-07 before/after bundle delta: AFTER total ≤ BEFORE and ≤ Phase 104 baseline"
    - "D-04 automation-first smoke test: Playwright against dev server, zero browser manual steps"
key_files:
  created: []
  modified:
    - src/angular/package.json
    - src/angular/angular.json
    - src/angular/package-lock.json
    - .planning/milestones/v1.3.0-phases/105-font-awesome-to-phosphor-migration/105-BUNDLE-BASELINE.md
decisions:
  - "Dep drop committed as a clean standalone closing commit after both migration plans and Karma were green — per D-06 audit→migrate→drop→verify rhythm"
  - "D-04 smoke test fulfilled by automated Playwright run (automation-first principle): zero manual browser steps required from reviewer"
  - "npm audit delta after FA removal noted-not-fixed (Phase 104 D-04 rhythm — advisory remediation is out of scope)"
metrics:
  duration: "~30 minutes"
  completed: "2026-06-01"
  tasks: 3
  files_modified: 4
---

# Phase 105 Plan 04: FA Dep Drop, Bundle Delta, and Smoke Test Summary

font-awesome ^4.7.0 dropped as a clean closing act after all fa-* icon usages were migrated (plans 105-02 + 105-03): removed from package.json, both font-awesome.css lines excised from angular.json (Phosphor's three weight stylesheets retained), lock regenerated, AFTER production build confirmed clean, bundle delta recorded (styles −30.84 kB, Initial total 1.16 MB → 1.13 MB, ≤ Phase 104 baseline), Karma 611/611 with all four floors held, and D-04 dev-server smoke test APPROVED via automated Playwright run confirming every former-fa icon location renders a Phosphor glyph with the spinner still animating and zero console errors.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Source residual-grep gate, FA dep drop, AFTER build, dist grep, bundle delta | 314fd6a | package.json, angular.json, package-lock.json, 105-BUNDLE-BASELINE.md |
| 2 | Confirm Karma coverage floors hold (read-only) | (read-only verification — no commit) | karma.conf.js (unchanged) |
| 3 | D-04 dev-server manual smoke test — APPROVED | (checkpoint approval — no new commit) | src/angular/src (read-only) |

## Verification Results

### Source Residual Gate (pre-drop, BLOCKING)

Broad ripgrep over `src/angular/src` (`.html`, `.ts`, `.scss`) for `\.fa-|\[class\.fa-|\bfa-|class="fa"|class='fa'` returned **ZERO matches** before the dep drop — confirming 105-02 + 105-03 left no fa-* icon token, no bare `.fa-*` SCSS selector, no `[class.fa-` binding, no non-first-position multi-class token, and no stray `fa-spin`. ROADMAP success criterion #2 satisfied.

### D-06 Closing Edits

- `"font-awesome": "^4.7.0"` removed from `src/angular/package.json` dependencies
- BOTH `"node_modules/font-awesome/css/font-awesome.css"` entries removed from `src/angular/angular.json` (build `styles` array and test/serve `styles` array)
- Phosphor's three `@phosphor-icons/web` stylesheets (regular/bold/fill) retained in both arrays
- `package-lock.json` regenerated via `npm install` from `src/angular/` (`.npmrc` legacy-peer-deps=true in scope; unchanged)
- npm audit delta noted, not fixed (advisory remediation out of scope)

### AFTER Production Build

`ng build --configuration production` from `src/angular/` — exit 0, no errors or warnings.

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-TCM2BFVM.js      | main          | 574.61 kB |               134.16 kB
styles-T2SQYWCH.css   | styles        | 442.21 kB |                40.33 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.13 MB |               207.70 kB
```

### Bundle Delta (D-07)

| Chunk | BEFORE (raw) | AFTER (raw) | Delta |
|-------|-------------|------------|-------|
| main  | 574.81 kB   | 574.61 kB  | −0.20 kB |
| styles | 473.05 kB  | 442.21 kB  | **−30.84 kB** |
| scripts | 80.45 kB  | 80.45 kB   | 0 |
| polyfills | 35.78 kB | 35.78 kB  | 0 |
| **Initial total** | **1.16 MB** | **1.13 MB** | **−31 kB (~−2.7%)** |

- AFTER total (1.13 MB) ≤ BEFORE total (1.16 MB) — PASS
- AFTER total (1.13 MB) ≤ Phase 104 baseline (1.16 MB / 213.00 kB estimated transfer) — PASS
- styles chunk: −30.84 kB raw / −5.14 kB estimated transfer — Font Awesome CSS removed; Phosphor already loaded (weight unchanged). Font files (woff/woff2/ttf/svg/eot) were inline-referenced in FA's CSS and confirmed absent (`find dist -iname 'fontawesome*'` returns zero results).

### Dist Residual Gate (post-build)

- Broad ripgrep `\.fa-|\[class\.fa-|\bfa-|class="fa"|class='fa'` over `dist/`: **ZERO matches**
- `grep -rq "font-awesome" dist`: **ZERO matches**
- `find dist -iname 'fontawesome*'`: **zero results**
- Verify command printed: `FA-DROPPED-DIST-CLEAN`

### Karma Coverage (post-dep-drop re-confirmation)

All 611 specs passed. Floors held with margin:

| Metric | Measured | Floor | Status |
|--------|---------|-------|--------|
| Statements | 84.33% | 83% | PASS |
| Branches | 69.31% | 68% | PASS |
| Functions | 80.49% | 79% | PASS |
| Lines | 85.18% | 83% | PASS |

karma.conf.js unchanged (no floor ratchet this phase). Python fail_under (≥ 88%) unaffected — no Python files touched in this phase.

### D-04 Dev-Server Smoke Test — APPROVED

Performed via automated Playwright run against `http://localhost:4200`. All surfaces PASS:

| Surface | Icons Verified | Result |
|---------|---------------|--------|
| Nav bar | ph-squares-four (dashboard), ph-gear (settings), ph-terminal (logs), ph-info (about), ph-bell (notification) | PASS |
| Dashboard stats strip | ph-cloud, ph-database, ph-arrow-down, ph-list-checks | PASS |
| Dashboard log pane | ph-terminal (terminal), copy, expand; **ph-circle-notch ph-spin — spinner ANIMATES** (ph-spin keyframes confirmed active, animationDuration 1s, animationName resolves to local ph-spin rule) | PASS |
| Settings section headers | 25 Phosphor icons, zero broken dynamic {{icon}} bindings; ph-computer-tower (NOT ph-server), ph-gauge, ph-hard-drive, ph-file-code, ph-sliders-horizontal, ph-floppy-disk, ph-file-zip, ph-magnifying-glass, ph-folder-open, ph-list, ph-trash, ph-plus-circle | PASS |
| Settings toggle states | ph-eye / ph-eye-slash (password reveal), ph-copy → ph-check (webhook/token copy), ph-eye / ph-eye-slash (API token reveal) | PASS |
| Logs page | ph-magnifying-glass (search), ph-check-circle (autoscroll on), ph-circle (autoscroll off), ph-trash, ph-download, ph-clock | PASS |
| Bulk-actions bar | ph-file-zip (Extract — disabled, no archive fixtures), ph-prohibit (Delete Remote overlay) — verified statically in bulk-actions-bar.component.html | PASS |
| Browser console | Zero fa-*/icon/font errors; only pre-existing /server/stream SSE 404s (no Python backend behind ng serve) | PASS |
| FA @font-face | Zero Font Awesome @font-face declarations loaded in browser; font-awesome.css confirmed absent | PASS |

**Spinner animation proof (Q5):** `ph ph-circle-notch ph-spin` confirmed with computed `animationName` resolving to local ph-spin keyframes and `animationDuration: 1s` — the spinner ANIMATES with font-awesome.css removed. This proves the local `.ph-spin` rule added in plan 105-02 works as the sole animation source.

**Settings page dynamic binding (highest-risk layer):** 25 Phosphor icons, zero bare `ph` without `ph-<name>`, zero broken dynamic bindings. Confirmed ph-computer-tower (not ph-server) renders correctly.

## Deviations from Plan

None. Plan executed exactly as written. The dep drop, build, dist/source residual greps, bundle delta, Karma re-confirmation, and D-04 smoke test all followed the planned sequence without auto-fix or architectural deviations.

## Known Stubs

None. font-awesome is fully removed. All icon classes resolve to Phosphor glyphs. No placeholder or empty values introduced.

## Threat Flags

None. Removing a dependency reduces shipped attack surface (one fewer EOL 4.7 library). No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

Files confirmed to exist:
- src/angular/package.json — FOUND (font-awesome dependency absent)
- src/angular/angular.json — FOUND (both font-awesome.css entries absent, Phosphor retained)
- src/angular/package-lock.json — FOUND (regenerated)
- .planning/milestones/v1.3.0-phases/105-font-awesome-to-phosphor-migration/105-BUNDLE-BASELINE.md — FOUND (BEFORE + AFTER + delta recorded)

Commits confirmed to exist:
- 314fd6a (Task 1: FA dep drop + build + dist/source greps + bundle delta) — FOUND
