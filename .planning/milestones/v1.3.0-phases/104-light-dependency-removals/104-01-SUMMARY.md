---
phase: 104-light-dependency-removals
plan: "01"
subsystem: frontend-dependencies
tags: [deps, npm, jquery, css-element-queries, bundle, cleanup]
dependency_graph:
  requires: []
  provides: [DEPS-01a, DEPS-01c]
  affects: [src/angular/package.json, src/angular/package-lock.json]
tech_stack:
  added: []
  patterns: [phantom-dep-removal, npm-uninstall, lockfile-regen]
key_files:
  created:
    - .planning/milestones/v1.3.0-phases/104-light-dependency-removals/104-BUNDLE-BASELINE.md
  modified:
    - src/angular/package.json
    - src/angular/package-lock.json
decisions:
  - D-03 honored: two separate atomic commits, one per requirement (DEPS-01a jquery, DEPS-01c css-element-queries)
  - D-04 honored: lockfile regenerated via npm uninstall from src/angular/ (.npmrc in scope); 4 pre-existing moderate vulns unchanged, not pursued
  - D-01 BEFORE gate satisfied: ng build --configuration production exited 0 pre-removal; Bootstrap-surface pre-state recorded
  - D-02 satisfied: pre-removal build table recorded in 104-BUNDLE-BASELINE.md (main 574.86 kB / scripts 80.45 kB / polyfills 35.78 kB / styles 473.05 kB)
metrics:
  duration: "~15 minutes"
  completed_date: "2026-06-01"
  tasks_completed: 3
  files_modified: 2
  files_created: 1
---

# Phase 104 Plan 01: Light Dependency Removals Summary

**One-liner:** Removed phantom npm deps jquery 4.0.0 and css-element-queries 1.2.3 from Angular package.json as two atomic commits after confirming zero source usage and capturing a pre-removal production build baseline.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Audit zero-usage + capture pre-removal bundle baseline (D-01 BEFORE gate) | dde9d95 | 104-BUNDLE-BASELINE.md (created) |
| 2 | Remove jQuery (DEPS-01a) — atomic commit 1 | 9a46375 | package.json, package-lock.json |
| 3 | Remove css-element-queries (DEPS-01c) — atomic commit 2 | 1a42cdb | package.json, package-lock.json |

---

## Outcome

Both DEPS-01a and DEPS-01c satisfied at the manifest level:

- `jquery ^4.0.0` removed from `src/angular/package.json` and `package-lock.json`; `node_modules/jquery` pruned
- `css-element-queries ^1.1.1` removed from `src/angular/package.json` and `package-lock.json`; `node_modules/css-element-queries` pruned
- Two atomic commits per D-03 (one referencing DEPS-01a, one DEPS-01c)
- `package-lock.json` regenerated after each removal via `npm uninstall` from `src/angular/` with `.npmrc` (`legacy-peer-deps=true`) in scope per D-04
- `src/angular/.npmrc` unchanged throughout

---

## D-01 BEFORE Gate (Pre-Removal Baseline)

**Phantom-dependency audit result:**

```
grep -rniE "jquery|css-element-queries|ResizeSensor|ElementQueries|window\.\$|import\(['\"]jquery|require\(['\"]jquery" src/angular/src/
# exit code: 1 (ZERO-USAGE-CONFIRMED)
```

Additional checks:
- `grep -c "<script" src/angular/src/index.html` → 0
- `npm explain jquery css-element-queries` (from `src/angular/`) → both depended-on by root only; no transitive consumers
- `angular.json` scripts array → only `node_modules/bootstrap/dist/js/bootstrap.bundle.min.js`

**Production build (BEFORE) — ng build --configuration production:**

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-PHJ4DNY7.js      | main          | 574.86 kB |               134.21 kB
styles-KZG6GNQT.css   | styles        | 473.05 kB |                45.47 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.16 MB |               212.89 kB
Build exit: 0
```

Bootstrap-surface pre-state recorded in 104-BUNDLE-BASELINE.md: nav, notification bell, dashboard file rows/stats, bulk action bar, settings form controls, and confirm modal (Renderer2-based) all build green pre-removal.

---

## npm audit (D-04)

Both removals resulted in 4 moderate severity vulnerabilities — identical to the pre-removal baseline:
- `brace-expansion` (DoS)
- `ws` (uninitialized memory)
- `engine.io` (depends on ws)
- `socket.io-adapter` (depends on ws)

No change in advisory count from either removal. None attributable to jquery or css-element-queries. No unrelated advisory was pursued per D-04.

---

## Deviations from Plan

None — plan executed exactly as written.

The RESEARCH note flagging `--stats-json` as supported was superseded by the PLAN.md note; the build output table was used as the primary D-02 record as planned.

---

## Retained Deps Verification

The following deps were confirmed still present in `src/angular/package.json` after both removals:
- `bootstrap ^5.3.3`
- `@popperjs/core ^2.11.8`
- `@phosphor-icons/web ^2.1.2`
- `font-awesome ^4.7.0` (Phase 105 scope — untouched)

---

## Build Verification Status

**Local build ran:** Yes — `ng build --configuration production` executed locally for the D-01/D-02 BEFORE gate (Task 1, pre-removal). The AFTER production build (post-removal) is deferred to plan 104-02 per the plan design (104-02 supplies the AFTER no-regression comparison).

**Note:** The AFTER build verification (confirming bundle sizes are <= BEFORE values and no residual library strings in dist) is the responsibility of plan 104-02.

---

## Known Stubs

None.

---

## Threat Flags

None. The threat model for this plan was evaluated:
- T-104-01 (lockfile regeneration): accepted — only two removed deps change the lockfile
- T-104-05 (.npmrc flag): mitigated — all npm commands run from `src/angular/` with `.npmrc` in scope
- T-104-SC (package legitimacy): N/A — phase performs zero new installs
- T-104-02 (Dockerfile --legacy-peer-deps): mitigated — Dockerfile not touched

---

## Self-Check: PASSED
