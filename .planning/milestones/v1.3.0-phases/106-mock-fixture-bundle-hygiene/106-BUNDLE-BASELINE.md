# 106-BUNDLE-BASELINE.md

**D-06 artifact (parts 1 + 3) + D-07** — Phase-106 production bundle before/after delta,
dist filename-literal absence-grep, symbol-grep (informational), and Karma floor record.

---

## BEFORE (pre-Phase-106, mock-model-files.ts still in services/files/)

`ng build --configuration production` — run from `src/angular/` (main repo copy, identical
source to worktree) on 2026-06-01T17:38:10Z, **before any Task-1 edits**. HEAD at capture:
`00a77a4fbb2c31d47a33c3e223f929ed6b90bfd6` (same commit as Phase-105 AFTER HEAD, the
Phase-106 start point). This is the TRUE Phase-106 BEFORE figure.

This build is identical to the Phase 105 AFTER record: same HEAD, same source, same chunk
hashes — this is expected. The Phase-105 AFTER figure is retained below as a secondary
sanity anchor confirming no drift.

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-TCM2BFVM.js      | main          | 574.61 kB |               134.16 kB
styles-T2SQYWCH.css   | styles        | 442.21 kB |                40.33 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-B7LGQ2G6.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.13 MB |               207.70 kB

Application bundle generation complete. [3.540 seconds] - 2026-06-01T17:38:14.665Z
```

Build exit: 0 (green). No errors or warnings.
BEFORE commit SHA: `00a77a4fbb2c31d47a33c3e223f929ed6b90bfd6`

---

## AFTER (post-Phase-106 Task-1 edits)

`ng build --configuration production` — run from `src/angular/` (worktree) on
2026-06-01T17:41:08Z, after Task-1 edits committed (fixture relocated to `tests/fixtures/`,
empty prod stub added, `environment.useMockModel` flag added, `view-file.service.ts` branching
updated, second `fileReplacements` entry in `angular.json`, `screenshot-model-files.ts` deleted).
HEAD at capture: `2ead43856c9d4b90af31264d226cadef8ef843e5` (Task-1 commit).

```
Initial chunk files   | Names         |  Raw size | Estimated transfer size
main-JT345XEE.js      | main          | 569.74 kB |               133.69 kB
styles-T2SQYWCH.css   | styles        | 442.21 kB |                40.33 kB
scripts-TTWY4XDY.js   | scripts       |  80.45 kB |                21.60 kB
polyfills-JS56QHPN.js | polyfills     |  35.78 kB |                11.61 kB

                      | Initial total |   1.13 MB |               207.23 kB

Application bundle generation complete. [2.905 seconds] - 2026-06-01T17:41:12.009Z
```

Build exit: 0 (green). No errors or warnings.
AFTER commit SHA: `7aa11d058989f63f4e8fb40bf7cc5a32b00aeab9` (includes test env fix)

Note: The test environment fix commit (`7aa11d0`) does not affect the production bundle
(environment.test.ts is only used by the Karma `test` config, not the `production` config).
The AFTER bundle numbers above reflect the Task-1 changes only.

---

## Before/After Delta

| Chunk | BEFORE (raw) | AFTER (raw) | Delta (raw) | BEFORE (xfer) | AFTER (xfer) | Delta (xfer) |
|-------|-------------|------------|-------------|--------------|-------------|-------------|
| main  | 574.61 kB   | 569.74 kB  | **-4.87 kB** | 134.16 kB    | 133.69 kB   | **-0.47 kB** |
| styles | 442.21 kB  | 442.21 kB  | 0            | 40.33 kB    | 40.33 kB    | 0           |
| scripts | 80.45 kB  | 80.45 kB   | 0            | 21.60 kB    | 21.60 kB    | 0           |
| polyfills | 35.78 kB | 35.78 kB  | 0            | 11.61 kB    | 11.61 kB    | 0           |
| **Initial total** | **1.13 MB** | **1.13 MB** | **-4.87 kB (~-0.4%)** | **207.70 kB** | **207.23 kB** | **-0.47 kB** |

The `main` chunk shrank by 4.87 kB (raw). This reflects the 192-line mock dataset
(~12 kB source) being tree-shaken entirely from the production bundle — the empty prod stub
exports only an empty `Immutable.Map()` call, eliminating all fixture string literals and
`new ModelFile({...})` constructors from the minified output. The smaller delta vs.
source size is expected after minification + gzip compression.

---

## Phase 105 AFTER — Secondary Sanity Anchor

Per plan requirement, the Phase 105 AFTER figure is recorded here as a secondary sanity
anchor (the BEFORE measurement this phase must be ≤). The Phase-106 BEFORE equals the
Phase-105 AFTER (same HEAD), confirming no drift between phases.

| Metric | Phase 105 AFTER | Phase 106 AFTER | Gate |
|--------|----------------|----------------|------|
| Initial total (raw) | 1.13 MB | 1.13 MB | AFTER ≤ Phase-105 AFTER |
| Initial total (xfer) | 207.70 kB | 207.23 kB | AFTER ≤ Phase-105 AFTER |

Result: PASS — Phase-106 AFTER (207.23 kB) < Phase-105 AFTER (207.70 kB).

---

## Verification Gates

### Gate 1: Bundle size (PASS)

- AFTER total (1.13 MB raw / 207.23 kB xfer) **≤ Phase-106 BEFORE** (1.13 MB / 207.70 kB) — **PASS**
- AFTER total (207.23 kB) **≤ Phase-105 AFTER secondary anchor** (207.70 kB) — **PASS**
- Main chunk shrank by 4.87 kB raw — consistent with 192-line mock dataset tree-shaken

### Gate 2: Dist filename-literal absence grep — HARD GATE (PASS)

```
grep -rl "A Really Cool Video About Cats" dist/   → ZERO matches (PASS)
grep -rl "Super.Secret.Folder.With.A.Long.Name" dist/ → ZERO matches (PASS)
```

**MOCK-ABSENT-FROM-PROD-DIST**

Both distinctive fixture filename literals are physically absent from the production bundle.

### Gate 3: MOCK_MODEL_FILES symbol grep — INFORMATIONAL (symbol tree-shaken)

```
grep -rl "MOCK_MODEL_FILES" dist/ → ZERO matches (INFORMATIONAL)
```

The `MOCK_MODEL_FILES` symbol was completely tree-shaken from the production bundle —
the empty prod stub (`Immutable.Map<string, ModelFile>()`) was itself eliminated as a
pure value with no side effects. Zero symbol hits confirms complete elimination.

---

## Karma Coverage Floor Record

Run: `ng test --no-watch --browsers=ChromeHeadless --code-coverage`
Date: 2026-06-01
Total tests: 611 / 611 PASS (2 additional tests vs. BEFORE: 609 → 611 delta from prior Karma
count; 611 counts include the full suite including view-file.service tests that now pass
with the test environment fix).

| Metric | Measured | Floor (check.global) | Gate |
|--------|----------|---------------------|------|
| Statements | 84.33% (1734/2056) | 83 | PASS (84 ≥ 83) |
| Branches | 69.31% (463/668) | 68 | PASS (69 ≥ 68) |
| Functions | 80.49% (425/528) | 79 | PASS (80 ≥ 79) |
| Lines | 85.18% (1673/1964) | 83 | PASS (85 ≥ 83) |

All four `check.global` floors hold. No Python files were changed in this phase;
Python `fail_under=88` is unaffected.

---

## Deviation Note

**[Rule 1 - Bug] Test environment environment.test.ts added**

The Task-1 addition of `useMockModel: true` to `environment.ts` (dev) caused the Karma
test suite to fail: `ViewFileService` constructor took the mock branch (calling
`buildViewFromModelFiles(MOCK_MODEL_FILES)` immediately) instead of subscribing to
`modelFileService.files`. The 29 failing tests all expected the service to start empty
and update from the mock model service injected in `TestBed`.

Fix: added `src/environments/environment.test.ts` with `useMockModel: false` and a
`fileReplacements` entry in the angular.json `test` config that swaps `environment.ts`
for `environment.test.ts`. This preserves the real populated fixture in test (no
`mock-model-files.prod.ts` swap in test config — as required by the plan) while
correcting the env flag for test correctness. Result: 611/611 tests pass.

---

*Plan: 106-01 | D-06 artifact | Status: COMPLETE*
