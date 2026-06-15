# Phase 106: Mock-Fixture Bundle Hygiene - Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 6 (3 modify, 1 move, 1 create, 1 delete)
**Analogs found:** 5 / 5 (the DELETE needs no analog)

All analogs are **in-file / sibling-file** patterns — this phase extends proven mechanisms already present in the codebase (the existing `fileReplacements` swap, the existing `environment` export shape, the existing `MOCK_MODEL_FILES` export signature). No external RESEARCH.md patterns are needed; every change has an exact local precedent.

## File Classification

| New/Modified File | Op | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|----|------|-----------|----------------|---------------|
| `src/angular/angular.json` | MODIFY | config (build) | transform (build-time replace) | the existing `environment.ts → environment.prod.ts` `fileReplacements` entry in the **same** `production` block (lines 63-68) | exact (extend in place) |
| `src/angular/src/environments/environment.ts` | MODIFY | config (env) | request-response (static config) | the existing `production` + `logger` fields in the **same** file | exact (same object) |
| `src/angular/src/environments/environment.prod.ts` | MODIFY | config (env) | request-response (static config) | the existing `production` + `logger` fields in the **same** file (must stay key-parallel with `environment.ts`) | exact (same object) |
| `src/angular/src/app/services/files/view-file.service.ts` | MODIFY | service | event-driven (rxjs subscribe) | itself — lines 11, 71, 92-106 are the only flag/branch/import sites | exact (in-file edit) |
| `src/angular/src/app/tests/fixtures/mock-model-files.ts` | MOVE | fixture (data) | transform (static dataset) | the file being moved (`services/files/mock-model-files.ts`) + sibling import-depth from `tests/mocks/mock-view-file.service.ts` | exact |
| `src/angular/src/app/tests/fixtures/mock-model-files.prod.ts` | CREATE | fixture (data stub) | transform (empty dataset) | head of `mock-model-files.ts` (lines 1-5) — copy export name/type, empty the map | exact (signature copy) |
| `src/angular/src/app/services/files/screenshot-model-files.ts` | DELETE | fixture (dead) | n/a | n/a (zero importers — see "No Analog" §) | n/a |

## Pattern Assignments

### `src/angular/angular.json` (config, build-time transform)

**Analog:** the existing `fileReplacements` array in this same file, `projects.seedsyncarr.architect.build.configurations.production`.

**Existing pattern to EXTEND** (`src/angular/angular.json` lines 62-68):
```json
"production": {
  "fileReplacements": [
    {
      "replace": "src/environments/environment.ts",
      "with": "src/environments/environment.prod.ts"
    }
  ],
```

**How to apply (D-01, D-03):** add a **second** object to the same `fileReplacements` array — do NOT invent a new array or build step. The `replace`/`with` paths are project-root-relative (rooted at `src/`, since `sourceRoot: "src"` and the existing entry uses `src/environments/...`). The new entry swaps the **relocated** fixture for the prod stub:
```json
"fileReplacements": [
  {
    "replace": "src/environments/environment.ts",
    "with": "src/environments/environment.prod.ts"
  },
  {
    "replace": "src/app/tests/fixtures/mock-model-files.ts",
    "with": "src/app/tests/fixtures/mock-model-files.prod.ts"
  }
]
```
Note: the `replace` path must point at the **new** relocated location (`src/app/tests/fixtures/`), not the old `services/files/` path, because the move (D-05) happens in the same phase. Only the `production` configuration gets the entry — `development` and `test` configs have no `fileReplacements` and must stay that way (dev/test see the real fixture).

---

### `src/angular/src/environments/environment.ts` (config, dev)

**Analog:** the existing `environment` const in this same file.

**Existing export shape** (`src/angular/src/environments/environment.ts` lines 6-13):
```typescript
import {LoggerService} from "../app/services/utils/logger.service";

export const environment = {
    production: false,
    logger: {
        level: LoggerService.Level.DEBUG
    }
};
```

**How to apply (D-02):** add a sibling boolean field `useMockModel: true` to the dev object (alongside `production`/`logger`). Keep the existing `LoggerService` import and the `production: false` / `DEBUG` values untouched:
```typescript
export const environment = {
    production: false,
    useMockModel: true,
    logger: {
        level: LoggerService.Level.DEBUG
    }
};
```

---

### `src/angular/src/environments/environment.prod.ts` (config, prod)

**Analog:** the existing `environment` const in this same file (must remain key-parallel with `environment.ts` so the `fileReplacements` swap stays type-clean).

**Existing export shape** (`src/angular/src/environments/environment.prod.ts` lines 1-8):
```typescript
import {LoggerService} from "../app/services/utils/logger.service";

export const environment = {
    production: true,
    logger: {
        level: LoggerService.Level.WARN
    }
};
```

**How to apply (D-02):** add the **same** key with the prod value `useMockModel: false`. The two environment objects must keep identical key sets (so TS sees one shape regardless of which file the build picks):
```typescript
export const environment = {
    production: true,
    useMockModel: false,
    logger: {
        level: LoggerService.Level.WARN
    }
};
```

---

### `src/angular/src/app/services/files/view-file.service.ts` (service, event-driven)

**Analog:** itself — three edit sites already isolated by CONTEXT.md. This service injects via constructor DI (`LoggerService`, `StreamServiceRegistry`, `FileSelectionService`) and is the **single** consumer of `MOCK_MODEL_FILES`.

**Import block to edit** (`src/angular/src/app/services/files/view-file.service.ts` lines 5-13) — add the `environment` import, repoint the fixture import to the relocated path:
```typescript
import * as Immutable from "immutable";

import {LoggerService} from "../utils/logger.service";
import {ModelFile} from "./model-file";
import {ModelFileService} from "./model-file.service";
import {ViewFile} from "./view-file";
import {MOCK_MODEL_FILES} from "./mock-model-files";          // line 11 — repoint ↓
import {StreamServiceRegistry} from "../base/stream-service.registry";
import {FileSelectionService} from "./file-selection.service";
```
New import (relative depth verified: `services/files/` → `tests/fixtures/` is `../../tests/fixtures/`; matches the inverse depth already used by `tests/mocks/mock-view-file.service.ts` which imports `../../services/files/...`):
```typescript
import {MOCK_MODEL_FILES} from "../../tests/fixtures/mock-model-files";
import {environment} from "../../../environments/environment";
```
> Path check: `view-file.service.ts` is at `src/app/services/files/`; `environments/` is at `src/environments/`. So `../../../environments/environment` (up files→services→app, then into environments). Compare `main.ts` (`./environments/environment`) and `app.config.ts` (`../environments/environment`) — both confirm the relative-path convention (no path alias is used in this project).

**Class field to REMOVE** (`src/angular/src/app/services/files/view-file.service.ts` line 71):
```typescript
private readonly USE_MOCK_MODEL = false;   // DELETE this line (D-02)
```

**Core branch to repoint** (`src/angular/src/app/services/files/view-file.service.ts` lines 92-106) — replace `!this.USE_MOCK_MODEL` with `!environment.useMockModel`; body of both branches unchanged:
```typescript
if (!this.USE_MOCK_MODEL) {                                   // line 92 — change condition ↓
    this.modelFileService.files
        .pipe(takeUntil(this.destroy$))
        .subscribe({
            next: modelFiles => {
                const t0 = performance.now();
                _viewFileService.buildViewFromModelFiles(modelFiles);
                const t1 = performance.now();
                this._logger.debug("ViewFile creation took", (t1 - t0).toFixed(0), "ms");
            }
        });
} else {
    // For layout/style testing
    this.buildViewFromModelFiles(MOCK_MODEL_FILES);          // line 105 — unchanged
}
```
New condition (only the `if (...)` line changes):
```typescript
if (!environment.useMockModel) {
```
> Type note: with the `fileReplacements` swap (D-01), prod builds compile against `mock-model-files.prod.ts` whose `MOCK_MODEL_FILES` is an empty `Immutable.Map<string, ModelFile>()` — identical type, so the `buildViewFromModelFiles(MOCK_MODEL_FILES)` call site stays type-clean even though that branch is dead in prod (`useMockModel: false`).

---

### `src/angular/src/app/tests/fixtures/mock-model-files.ts` (fixture, MOVE)

**Analog:** the file being moved verbatim (`services/files/mock-model-files.ts`, 192 lines) + the import-depth convention from `tests/mocks/mock-view-file.service.ts`.

**Existing head** (`src/angular/src/app/services/files/mock-model-files.ts` lines 1-5):
```typescript
import * as Immutable from "immutable";

import {ModelFile} from "./model-file";

export const MOCK_MODEL_FILES: Immutable.Map<string, ModelFile> = Immutable.Map({
```

**How to apply (D-05):** `git mv` the file to `src/angular/src/app/tests/fixtures/mock-model-files.ts`. The **only** code change inside the moved file is the `ModelFile` import path, which deepens from `./model-file` to `../../services/files/model-file` (new location `tests/fixtures/` → `services/files/`). This exactly mirrors the existing `tests/mocks/mock-view-file.service.ts` import:
```typescript
import {ViewFile} from "../../services/files/view-file";   // tests/mocks/mock-view-file.service.ts line 5 — same ../../services/files/ depth
```
Moved-file new import:
```typescript
import {ModelFile} from "../../services/files/model-file";
```
The 192-line dataset body (the `Immutable.Map({...})` of `ModelFile` entries) is copied unchanged. Use `git mv` so history/blame follow the file (CONCERNS.md notes git history is the preservation mechanism).

---

### `src/angular/src/app/tests/fixtures/mock-model-files.prod.ts` (fixture stub, CREATE)

**Analog:** the head of `mock-model-files.ts` (export name + type signature) — the stub must match the real module's public surface exactly so the prod compile and the `view-file.service.ts` call site are type-clean.

**Signature to match** (from `src/angular/src/app/services/files/mock-model-files.ts` line 5, re-targeted to the new location's import depth):
```typescript
export const MOCK_MODEL_FILES: Immutable.Map<string, ModelFile> = Immutable.Map({...192 lines...});
```

**How to apply (D-03):** create the stub in the **same** `tests/fixtures/` dir with the identical export name and type, but an **empty** map. Full file content:
```typescript
import * as Immutable from "immutable";

import {ModelFile} from "../../services/files/model-file";

export const MOCK_MODEL_FILES: Immutable.Map<string, ModelFile> = Immutable.Map<string, ModelFile>();
```
> The empty-map type annotation may be inlined as shown (`Immutable.Map<string, ModelFile>()`) — any type-clean form is acceptable (CONTEXT Claude's Discretion). The `ModelFile` import is still required for the generic type parameter (it is a type-only use; keep the import so `tsConfig`/lint stays clean). The annotated `const` type must read `Immutable.Map<string, ModelFile>` to be assignment-compatible with the real module's export.

---

## Shared Patterns

### Build-time module swap (`fileReplacements`)
**Source:** `src/angular/angular.json` lines 62-68 (existing `environment.ts → environment.prod.ts` entry).
**Apply to:** the angular.json edit. Append a parallel array entry — do not create a new mechanism. Both entries live only under `configurations.production`.
```json
{ "replace": "src/app/tests/fixtures/mock-model-files.ts", "with": "src/app/tests/fixtures/mock-model-files.prod.ts" }
```

### Environment flag shape (key-parallel objects)
**Source:** `src/angular/src/environments/environment.ts` (lines 8-13) and `environment.prod.ts` (lines 3-8).
**Apply to:** both env files. The two `environment` objects MUST carry the same key set (`production`, `useMockModel`, `logger`); only the values differ (dev `true` / prod `false`). This keeps the `fileReplacements`-swapped build type-consistent.

### Relative import-path convention (no path aliases)
**Source:** `src/main.ts:6` (`./environments/environment`), `src/app/app.config.ts:7` (`../environments/environment`), `src/app/tests/mocks/mock-view-file.service.ts:5` (`../../services/files/view-file`).
**Apply to:** all import-path edits in `view-file.service.ts` and the relocated/created fixture files. Compute depth from the file's own location; the project uses no `@`-style path aliases.
- `view-file.service.ts` → fixture: `../../tests/fixtures/mock-model-files`
- `view-file.service.ts` → environment: `../../../environments/environment`
- `tests/fixtures/*` → ModelFile: `../../services/files/model-file`

### MOCK_MODEL_FILES export signature (type contract)
**Source:** `src/angular/src/app/services/files/mock-model-files.ts:5`.
**Apply to:** the prod stub. Export name `MOCK_MODEL_FILES`, type `Immutable.Map<string, ModelFile>`. Real module = populated map; prod stub = empty map. Same name/type so the single consumer (`view-file.service.ts:105`) compiles against either.

## No Analog Found

| File | Op | Reason |
|------|----|--------|
| `src/angular/src/app/services/files/screenshot-model-files.ts` | DELETE | No analog needed. Grep across `src/**` (`.ts`/`.html`) confirms **zero importers** — the only match for `screenshot-model-files` / `SCREENSHOT_MODEL_FILES` is the file's own export line. Dead code (~135 lines, confirmed 135 by `wc -l`). `git rm` it; history preserves the dataset (D-04). It is NOT relocated. |

## Metadata

**Analog search scope:** `src/angular/src/` (angular.json, environments/, app/services/files/, app/tests/mocks/, main.ts, app.config.ts).
**Files scanned:** 8 read + 2 grep sweeps across `src/**` for importer confirmation.
**Importer verification:**
- `MOCK_MODEL_FILES` consumers: exactly 1 external (`view-file.service.ts` import line 11, use line 105) + its own export — matches CONTEXT D's "single consumer" claim.
- `SCREENSHOT_MODEL_FILES` consumers: 0 external — matches CONTEXT D-04's "zero importers" claim.
- No path aliases in tsconfig usage — all imports are relative (confirmed via main.ts / app.config.ts / tests/mocks).
**Pattern extraction date:** 2026-06-01
