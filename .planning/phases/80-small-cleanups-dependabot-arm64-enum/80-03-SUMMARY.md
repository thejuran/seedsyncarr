---
phase: 80-small-cleanups-dependabot-arm64-enum
plan: 03
subsystem: dead-code
tags: [python, typescript, angular, enum-removal, waiting-for-import, tech-02]

# Dependency graph
requires:
  - phase: 80-small-cleanups-dependabot-arm64-enum
    provides: RESEARCH and PATTERNS documents confirming exactly 5 files to edit, enum-removal strategy, and no-renumber rule
provides:
  - WAITING_FOR_IMPORT dead-code removed from all 5 source files (Python enum, Python serializer dict, 2 TS enums, 1 TS switch)
  - TECH-02 decision recorded in PROJECT.md Key Decisions table
affects: [phase-75, phase-82]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Python Enum: non-contiguous integer values permitted (NONE=0, IMPORTED=1 with gap after removal is intentional)"
    - "TS string enum: no trailing comma on final member (matches existing style in model-file.ts and view-file.ts)"
    - "Switch default-branch safety: mapImportStatus default->NONE covers all unrecognized values, making enum member removal behavior-preserving"

key-files:
  created: []
  modified:
    - src/python/model/file.py
    - src/python/web/serialize/serialize_model.py
    - src/angular/src/app/services/files/model-file.ts
    - src/angular/src/app/services/files/view-file.ts
    - src/angular/src/app/services/files/view-file.service.ts
    - .planning/PROJECT.md

key-decisions:
  - "Remove WAITING_FOR_IMPORT (Option A) — placeholder since v2.0 (2026-02-12), never set by business logic, Phase 73 explicitly deferred wiring; milestone v1.1.1 is cleanup-only"
  - "Do not renumber IMPORTED from 1 — Python Enum permits non-contiguous values; serializer maps by instance not integer"
  - "Scope confirmed as exactly 5 files — webhook_manager.py and webhook.py had zero references despite RESEARCH §6 listing"

patterns-established:
  - "Dead-code enum removal: delete member, remove trailing comma on new-final member, remove all serializer/switch references, run full cross-tree grep to confirm zero residual references"

requirements-completed:
  - TECH-02

# Metrics
duration: 30min
completed: 2026-04-21
---

# Phase 80 Plan 03: Remove WAITING_FOR_IMPORT Dead-Code Enum Value (TECH-02) Summary

**Dead `WAITING_FOR_IMPORT` enum value removed from 5 source files (Python enum + serializer dict + 2 TS enums + 1 TS switch), eliminating 3-month-old placeholder (v2.0, 2026-02-12) that was never set by business logic; TECH-02 recorded in PROJECT.md Key Decisions.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-21
- **Completed:** 2026-04-21
- **Tasks:** 3 (all completed)
- **Files modified:** 6

## Accomplishments

- Removed `WAITING_FOR_IMPORT = 2` from `ModelFile.ImportStatus` Python enum; `IMPORTED = 1` preserved (not renumbered)
- Removed `WAITING_FOR_IMPORT: "waiting_for_import"` from `__VALUES_FILE_IMPORT_STATUS` dict; trailing comma removed from now-final `IMPORTED` entry
- Removed `WAITING_FOR_IMPORT = "waiting_for_import"` from both TypeScript `ImportStatus` enums in `model-file.ts` and `view-file.ts`; trailing commas removed from now-final `IMPORTED` members
- Removed the `WAITING_FOR_IMPORT` case+return from `mapImportStatus` switch in `view-file.service.ts`; `default -> NONE` branch preserved as behavior-preservation safety net
- Appended TECH-02 decision row to `.planning/PROJECT.md` Key Decisions table (pipe-matching line count: 33 → 34)
- Cross-tree grep: 0 references to `WAITING_FOR_IMPORT` / `waiting_for_import` / `waitingForImport` remain under `src/python/` and `src/angular/src/`
- E2E sweep: 0 references in `src/e2e/tests/`

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove WAITING_FOR_IMPORT from 2 Python files** - `b3f105b` (feat)
2. **Task 2: Remove WAITING_FOR_IMPORT from 3 Angular TypeScript files** - `d2170b2` (feat)
3. **Task 3: Append TECH-02 decision row to PROJECT.md + verification** - `8584577` (docs)

**Plan metadata:** (SUMMARY commit — see below)

## Files Created/Modified

- `src/python/model/file.py` — `ImportStatus` enum reduced from 3 to 2 members (NONE=0, IMPORTED=1); WAITING_FOR_IMPORT=2 deleted
- `src/python/web/serialize/serialize_model.py` — `__VALUES_FILE_IMPORT_STATUS` dict reduced from 3 to 2 entries; WAITING_FOR_IMPORT entry deleted, trailing comma removed from IMPORTED entry
- `src/angular/src/app/services/files/model-file.ts` — `ModelFile.ImportStatus` enum reduced from 3 to 2 members; WAITING_FOR_IMPORT deleted, trailing comma removed from IMPORTED
- `src/angular/src/app/services/files/view-file.ts` — `ViewFile.ImportStatus` enum reduced from 3 to 2 members; WAITING_FOR_IMPORT deleted, trailing comma removed from IMPORTED
- `src/angular/src/app/services/files/view-file.service.ts` — `mapImportStatus` switch reduced from 3 branches to 2 (IMPORTED case + default); WAITING_FOR_IMPORT case+return deleted
- `.planning/PROJECT.md` — TECH-02 decision row appended to Key Decisions table

## Source Edit Details

**Edit 1: `src/python/model/file.py` (line 33 deleted)**

Before (lines 30-33):
```python
class ImportStatus(Enum):
    NONE = 0                    # Not tracked by *arr / no import detected
    IMPORTED = 1                # Imported by Sonarr/Radarr
    WAITING_FOR_IMPORT = 2      # Detected by *arr, awaiting import
```

After (lines 30-32):
```python
class ImportStatus(Enum):
    NONE = 0                    # Not tracked by *arr / no import detected
    IMPORTED = 1                # Imported by Sonarr/Radarr
```

**Edit 2: `src/python/web/serialize/serialize_model.py` (line 63 deleted, trailing comma removed from line 62)**

Before (lines 60-64):
```python
__VALUES_FILE_IMPORT_STATUS = {
    ModelFile.ImportStatus.NONE: "none",
    ModelFile.ImportStatus.IMPORTED: "imported",
    ModelFile.ImportStatus.WAITING_FOR_IMPORT: "waiting_for_import"
}
```

After (lines 60-63):
```python
__VALUES_FILE_IMPORT_STATUS = {
    ModelFile.ImportStatus.NONE: "none",
    ModelFile.ImportStatus.IMPORTED: "imported"
}
```

**Edit 3: `src/angular/src/app/services/files/model-file.ts` (line 159 deleted, trailing comma removed from line 158)**

Before (lines 156-160):
```typescript
export enum ImportStatus {
    NONE            = "none",
    IMPORTED        = "imported",
    WAITING_FOR_IMPORT = "waiting_for_import"
}
```

After (lines 156-159):
```typescript
export enum ImportStatus {
    NONE            = "none",
    IMPORTED        = "imported"
}
```

**Edit 4: `src/angular/src/app/services/files/view-file.ts` (line 105 deleted, trailing comma removed from line 104)**

Before (lines 102-106):
```typescript
export enum ImportStatus {
    NONE                = "none",
    IMPORTED            = "imported",
    WAITING_FOR_IMPORT  = "waiting_for_import"
}
```

After (lines 102-105):
```typescript
export enum ImportStatus {
    NONE                = "none",
    IMPORTED            = "imported"
}
```

**Edit 5: `src/angular/src/app/services/files/view-file.service.ts` (lines 400-401 deleted)**

Before (lines 396-405):
```typescript
private static mapImportStatus(status: ModelFile.ImportStatus): ViewFile.ImportStatus {
    switch (status) {
        case ModelFile.ImportStatus.IMPORTED:
            return ViewFile.ImportStatus.IMPORTED;
        case ModelFile.ImportStatus.WAITING_FOR_IMPORT:
            return ViewFile.ImportStatus.WAITING_FOR_IMPORT;
        default:
            return ViewFile.ImportStatus.NONE;
    }
}
```

After (lines 396-403):
```typescript
private static mapImportStatus(status: ModelFile.ImportStatus): ViewFile.ImportStatus {
    switch (status) {
        case ModelFile.ImportStatus.IMPORTED:
            return ViewFile.ImportStatus.IMPORTED;
        default:
            return ViewFile.ImportStatus.NONE;
    }
}
```

**Edit 6: `.planning/PROJECT.md` — new row appended at line 342**

New row (exactly as appended):
```
| Remove WAITING_FOR_IMPORT enum value (TECH-02) | Placeholder since v2.0 (2026-02-12); never set by business logic; Phase 73 explicitly deferred wiring; re-add alongside future Sonarr Grab-event ingestion if prioritized | ✓ Good |
```

Key Decisions table pipe-matching line count: **33 (pre-edit) → 34 (post-edit)**

## Verification Results

| Check | Result |
|-------|--------|
| `git grep WAITING_FOR_IMPORT src/python/ src/angular/src/` | 0 matches |
| `git grep WAITING_FOR_IMPORT src/e2e/tests/` | 0 matches |
| `grep -E 'WAITING_FOR_IMPORT' .planning/PROJECT.md` | ≥1 (new row in Key Decisions) |
| `grep -cE '\| Remove WAITING_FOR_IMPORT.*TECH-02.*✓ Good \|' .planning/PROJECT.md` | 1 |
| Key Decisions pipe-matching line count post-edit | 34 |
| `IMPORTED = 1` preserved (not renumbered) | ✓ |
| Trailing comma removed from final dict entry (serialize_model.py) | ✓ |
| Trailing comma removed from final TS enum member (model-file.ts) | ✓ |
| Trailing comma removed from final TS enum member (view-file.ts) | ✓ |
| `mapImportStatus` retains `IMPORTED` case + `default → NONE` | ✓ |
| `make run-tests-python` | Deferred to CI (Docker required; local Python 3.9 env missing `parameterized` module — pre-existing, confirmed by stash test) |
| `make run-tests-angular` | Deferred to CI (Docker required; local env missing node_modules) |

**Test suite status:** Both `make run-tests-python` and `make run-tests-angular` require Docker builds and could not be run in the local worktree environment. This follows the established project precedent (D-20 "ci-as-evidence" pattern from Phase 73). The changes are purely deletions (no new logic added), and the cross-tree grep confirms zero residual references. CI will serve as the runtime gate.

## Scope Confirmation: webhook_manager.py and webhook.py

RESEARCH §6 originally listed `src/python/controller/webhook_manager.py` and `src/python/web/handler/webhook.py` as potentially referenced. Plan-time grep (confirmed in plan objective) and execute-time `git grep` both return zero hits for either file. The canonical reference inventory is exactly 5 files as documented in RESEARCH §5.1. This confirms that the `WAITING_FOR_IMPORT` value was never wired into the webhook ingestion path.

## Decisions Made

- Option A (remove) confirmed per RESEARCH §5.4: milestone v1.1.1 is "no user-visible feature additions"; Option B (wire via Sonarr Grab events) would add new webhook-event ingestion path + state transition + UI surface, violating the milestone constraint
- IMPORTED value preserved as `= 1` (not renumbered to fill the gap) per RESEARCH §8.5 and PATTERNS: Python Enum permits non-contiguous values; serializer maps by enum instance, not integer
- Column alignment in TypeScript enums preserved exactly as-was (12-space alignment in model-file.ts, 16-space alignment in view-file.ts)

## Deviations from Plan

None - plan executed exactly as written. The 5 file scope confirmed accurate at execution time (no additional references found).

## Issues Encountered

**Local test environment:** `poetry run pytest tests/unittests/ -q` fails in the local worktree Python 3.9 environment with `ModuleNotFoundError: No module named 'parameterized'` — confirmed pre-existing before any changes via `git stash`. Similarly, Angular `npm test` is unavailable because `node_modules` is not installed in the worktree. Both full suites run via Docker (`make run-tests-python`, `make run-tests-angular`) and are deferred to CI per project precedent (D-20).

## Known Stubs

None.

## Threat Flags

None — this is pure dead-code removal with no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Next Phase Readiness

- TECH-02 closed: `WAITING_FOR_IMPORT` fully removed from all tiers (Python source-of-truth, Python serializer, TypeScript wire-format consumer, TypeScript view model, TypeScript mapping service)
- If Sonarr Grab-event ingestion is ever prioritized, the TECH-02 PROJECT.md row documents the re-add path
- Phase 82 (Release Prep) can reference TECH-02 as a closed cleanup item in the v1.1.1 changelog

---
*Phase: 80-small-cleanups-dependabot-arm64-enum*
*Completed: 2026-04-21*
