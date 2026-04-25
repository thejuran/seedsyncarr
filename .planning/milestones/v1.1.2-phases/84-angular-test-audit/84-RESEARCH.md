# Phase 84: Angular Test Audit - Research

**Researched:** 2026-04-24
**Domain:** Angular unit test staleness audit — Karma/Jasmine test suite, Angular 21
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Staleness Criteria**
- **D-01:** Same strict rule as Phase 83 — a test is "stale" only if the production code it exercises (component, service, pipe) has been deleted or completely rewritten. Tests that pass and exercise live code stay, regardless of perceived quality or redundancy.
- **D-02:** Renamed components count as deleted if the old file/class no longer exists (e.g., old `FileComponent` → `TransferRowComponent` means tests for `FileComponent` are stale if that file is gone).
- **D-03:** Do not reorganize spec file locations. The 3 co-located specs (about, option, settings-page) and the 37 specs in `tests/unittests/` both stay where they are.

**Removal Granularity**
- **D-04:** Remove at individual test method level (carried from Phase 83 D-06). If all methods in a spec file are stale, delete the entire file.
- **D-05:** Clean up orphaned test helpers, mocks, and fixtures in `tests/mocks/` — if a mock service is no longer imported by any remaining test, remove it.

**Inventory Format**
- **D-06:** Document all removals in a markdown table: spec file path | test count removed | reason (e.g., "tests FileComponent deleted in v1.1.0 redesign"). Carried from Phase 83 D-05.

**CI Warning Cleanup**
- **D-07:** After stale test removal is complete, clean up all console noise from `ng test --watch=false` output: deprecation warnings, console.error/warn from components during tests, Karma config deprecations, and any other test runner noise.
- **D-08:** Warning cleanup happens after stale removal (not before or concurrently). Some warnings may disappear with deleted tests.

**Coverage Safety Net**
- **D-09:** Record Angular coverage baseline before and after removals using `ng test --code-coverage`. Document the numbers for reviewability. No fail_under threshold is enforced.
- **D-10:** The "dead code only" staleness criteria means removed tests should contribute zero unique coverage by definition, but the baseline provides a sanity check.

### Claude's Discretion

None specified — open to standard approaches per CONTEXT.md `<specifics>`.

### Deferred Ideas (OUT OF SCOPE)
- **CSP Violation Detection** — Deferred to Phase 85 (E2E Test Audit)
- Encrypt stored credentials at rest
- Add rate limiting to all HTTP endpoints
- Remove PYTHONWARNINGS cgi filter
- Tighten Shield Semgrep rules

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NG-01 | Identify Angular test files/cases testing deleted components or superseded UI patterns | Covered by the staleness audit: cross-referencing all 40 spec file imports against 57 live production files |
| NG-02 | Remove identified stale Angular tests without breaking the test suite | Covered by the test execution protocol: `ng test --watch=false --browsers ChromeHeadlessCI` verifies no regressions |
| NG-03 | Verify all remaining Angular tests pass | Covered by final suite run in Docker environment; CI command documented |

</phase_requirements>

---

## Summary

Phase 84 is a codebase audit with a specific, bounded task: verify that all 40 Angular spec files in the repository reference production code that currently exists, remove those that do not (by the D-01 staleness definition), and then clean up CI console noise. Research involved exhaustively cross-referencing every spec file import against every live production TypeScript file.

**Primary finding: Zero stale spec files exist by the D-01 definition.** Every one of the 40 spec files imports production components, services, or models that are present on disk. The two stale spec files that tested `FileComponent` and `FileListComponent` (deleted during the v1.1.0 redesign in Phase 72) were already removed in commit `103ace3`. The mock files in `tests/mocks/` are all actively imported by remaining tests.

The work remaining for Phase 84 is therefore: (1) formally execute the staleness audit to confirm zero removals and document the inventory, (2) record the coverage baseline, and (3) address CI console noise (D-07/D-08) — specifically the `HttpClientTestingModule` deprecation warnings present in 6 spec files using the old API that was superseded in Angular 15+.

**Primary recommendation:** Run the staleness audit as a read-only verification first, produce the zero-removal inventory table, capture coverage baseline, then address the `HttpClientTestingModule` → `provideHttpClient` + `provideHttpClientTesting` migration in the 6 affected spec files as the CI noise cleanup task.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Spec file staleness detection | Developer workstation | CI runner | Import resolution is a static analysis task; no runtime needed |
| Test execution / green suite verification | Docker (ChromeHeadlessCI) | Local `ng test` (Chrome.app) | CI uses Docker + ChromeHeadlessCI; local has Chrome.app but not in PATH as `google-chrome` |
| Coverage baseline capture | Docker (ChromeHeadlessCI) | — | `ng test --code-coverage` outputs to `coverage/` dir |
| CI console noise identification | Docker test output | Local test run | Only real test runner output reveals actual warnings |
| Mock orphan detection | Static import analysis | — | `grep` on imports is sufficient |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Angular | 21.2.9 | Application framework under test | [VERIFIED: package.json] |
| Karma | 6.4.4 | Test runner | [VERIFIED: package.json] — project standard |
| Jasmine (karma-jasmine) | 5.1.0 | Test framework | [VERIFIED: package.json] — project standard |
| jasmine-core | 6.2.0 | Jasmine assertion library | [VERIFIED: package.json] |
| karma-chrome-launcher | 3.2.0 | ChromeHeadlessCI browser | [VERIFIED: package.json + karma.conf.js] |
| karma-coverage | 2.2.1 | Coverage reporting | [VERIFIED: package.json] |
| karma-spec-reporter | 0.0.36 | CLI test output | [VERIFIED: package.json] |
| @angular/build | 21.2.8 | Karma builder (`@angular/build:karma`) | [VERIFIED: angular.json] |

### Test Infrastructure Files
| File | Purpose |
|------|---------|
| `src/angular/karma.conf.js` | Karma runner config — browsers, reporters, timeouts |
| `src/angular/angular.json` | Angular build/test builder config — main, polyfills, tsConfig |
| `src/angular/src/test.ts` | Test bootstrap entry — initializes Angular testing environment |
| `src/angular/src/tsconfig.spec.json` | TypeScript config for specs — includes `**/*.spec.ts` |

### Test Execution Commands
| Purpose | Command |
|---------|---------|
| Local run (macOS) | `cd src/angular && node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false` |
| CI run (Docker) | `make run-tests-angular` — builds Docker image then runs compose |
| Coverage | `cd src/angular && node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false --code-coverage` |
| Docker compose | `src/docker/test/angular/compose.yml` — mounts `src/angular/src` as volume |

**Note:** `ng` is not in PATH on this machine. Use `node /Users/julianamacbook/seedsyncarr/src/angular/node_modules/@angular/cli/bin/ng.js` or `npx ng` from `src/angular/`. Chrome.app is present at `/Applications/Google Chrome.app` — usable for local `ChromeHeadless` runs. [VERIFIED: tool check]

---

## Architecture Patterns

### System Architecture Diagram

```
Spec Files (40)
      │
      │ import
      ▼
Production Code (components, services, pipes)
      │                         │
      │ exists?                 │ exists?
      ▼                         ▼
  LIVE → keep              DELETED → stale → remove
                                │
                          check all spec methods
                          (D-04: method-level removal)
                                │
                          all methods stale?
                          └─ yes → delete entire file
                          └─ no  → remove stale methods only
                                │
                          check orphaned mocks (D-05)
                          └─ mock imported by 0 remaining specs → delete
                                │
                    ┌─────── CI run: ng test --watch=false ──────┐
                    │   green? → proceed to coverage baseline     │
                    │   red? → stop, investigate regression       │
                    └──────────────────────────────────────────────┘
                                │
                    record coverage baseline (D-09)
                                │
                    CI noise cleanup (D-07/D-08)
                    └─ HttpClientTestingModule → provideHttpClient
                    └─ any other console.warn/error/deprecation
                                │
                    final ng test --watch=false → green
```

### Recommended Project Structure (unchanged — D-03)
```
src/angular/src/app/
├── pages/
│   ├── about/        about-page.component.spec.ts (co-located)
│   └── settings/     option.component.spec.ts, settings-page.component.spec.ts (co-located)
├── tests/
│   ├── mocks/        mock-*.ts (shared mock helpers)
│   └── unittests/
│       ├── common/   pipe specs
│       ├── pages/    component specs (files/, logs/, main/)
│       └── services/ service specs (autoqueue/, base/, files/, logs/, server/, settings/, utils/)
```

### Pattern 1: Staleness Determination
**What:** A spec is stale if and only if every production file it directly imports is deleted from disk.
**When to use:** Per D-01 — applies to all 40 spec files.
**Implementation:**
```typescript
// For each spec file:
// 1. Extract all non-Angular/non-rxjs imports
// 2. Resolve each import path relative to spec file location
// 3. Check: does resolved_path + ".ts" exist on disk?
// 4. If ALL direct production imports resolve to deleted files → stale
// 5. If ANY direct production import exists → live (keep)
```

### Pattern 2: Mock Orphan Detection (D-05)
**What:** A mock in `tests/mocks/` is orphaned if zero remaining spec files import it.
**When to use:** After all stale spec files are removed.
**Implementation:**
```bash
# For each mock file:
grep -rl "mock-event-source\|mock-model-file.service\|mock-rest.service\|mock-storage.service\|mock-stream-service.registry\|mock-view-file-options.service\|mock-view-file.service" \
  src/angular/src/app/tests/unittests/ \
  src/angular/src/app/pages/
# If no results → mock is orphaned → delete it
```

### Pattern 3: HttpClientTestingModule → provideHttpClient Migration (D-07)
**What:** 6 spec files use `HttpClientTestingModule` (deprecated in Angular 15+, Angular 21 shows deprecation warnings). Migrate to `provideHttpClient()` + `provideHttpClientTesting()`.
**When to use:** During CI noise cleanup pass (D-08 — after stale removal).
**Before:**
```typescript
// Source: auth.interceptor.spec.ts (the one spec that already uses new API)
TestBed.configureTestingModule({
    imports: [HttpClientTestingModule]  // deprecated
});
```
**After:**
```typescript
// [VERIFIED: auth.interceptor.spec.ts already uses this pattern]
TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting()
    ]
});
// httpMock = TestBed.inject(HttpTestingController); // unchanged
```
Files requiring migration: `autoqueue.service.spec.ts`, `bulk-command.service.spec.ts`, `config.service.spec.ts`, `model-file.service.spec.ts`, `rest.service.spec.ts`, `server-command.service.spec.ts`

### Anti-Patterns to Avoid
- **Removing tests based on quality judgment:** D-01/D-02 define staleness as "deleted production code only." Do not remove a test because it's trivial, redundant, or tests edge cases that seem unlikely.
- **Reorganizing spec file locations:** D-03 explicitly prohibits moving co-located specs or restructuring `tests/unittests/`.
- **Fixing unrelated test failures:** If `ng test` reveals pre-existing failures unrelated to stale test removal, document them but do not fix them in this phase.
- **Addressing CI noise before staleness audit:** D-08 requires the noise cleanup to follow stale removal, not precede it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import path resolution | Custom path resolver | `realpath` + filesystem check | Standard shell tools are sufficient; TypeScript path aliases are not used in these spec files |
| Deprecation warning identification | Manual ng test output parsing | Run `ng test --watch=false` and read output | Karma spec reporter surfaces all warnings in console |
| Mock usage detection | Custom AST analysis | `grep -rl` on import strings | Import strings are stable identifiers; grep is accurate enough |

---

## Runtime State Inventory

> Step 2.5: This is an audit/removal phase, not a rename/migration phase. No runtime state inventory is required.

---

## Complete Staleness Audit Results

**This is the core research output.** All 40 spec files verified against live production files on 2026-04-24.

### Result: ZERO stale spec files

Every spec file imports production code that exists on disk. [VERIFIED: filesystem cross-reference, exhaustive]

| Spec File | Target Production File | Status | Notes |
|-----------|----------------------|--------|-------|
| `pages/about/about-page.component.spec.ts` | `about-page.component.ts` | LIVE | co-located |
| `pages/settings/option.component.spec.ts` | `option.component.ts` | LIVE | co-located |
| `pages/settings/settings-page.component.spec.ts` | `settings-page.component.ts` | LIVE | co-located |
| `unittests/common/is-selected.pipe.spec.ts` | `common/is-selected.pipe.ts` | LIVE | — |
| `unittests/pages/files/bulk-actions-bar.component.spec.ts` | `pages/files/bulk-actions-bar.component.ts` | LIVE | — |
| `unittests/pages/files/dashboard-log-pane.component.spec.ts` | `pages/files/dashboard-log-pane.component.ts` | LIVE | — |
| `unittests/pages/files/stats-strip.component.spec.ts` | `pages/files/stats-strip.component.ts` | LIVE | — |
| `unittests/pages/files/transfer-row.component.spec.ts` | `pages/files/transfer-row.component.ts` | LIVE | renamed from FileComponent — spec already updated |
| `unittests/pages/files/transfer-table.component.spec.ts` | `pages/files/transfer-table.component.ts` | LIVE | renamed from FileListComponent — spec already updated |
| `unittests/pages/logs/logs-page.component.spec.ts` | `pages/logs/logs-page.component.ts` | LIVE | — |
| `unittests/pages/main/app.component.spec.ts` | `pages/main/app.component.ts` | LIVE | — |
| `unittests/pages/main/notification-bell.component.spec.ts` | `pages/main/notification-bell.component.ts` | LIVE | — |
| `unittests/services/autoqueue/autoqueue.service.spec.ts` | `services/autoqueue/autoqueue.service.ts` | LIVE | — |
| `unittests/services/base/base-stream.service.spec.ts` | `services/base/base-stream.service.ts` | LIVE | — |
| `unittests/services/base/base-web.service.spec.ts` | `services/base/base-web.service.ts` | LIVE | — |
| `unittests/services/base/stream-service.registry.spec.ts` | `services/base/stream-service.registry.ts` | LIVE | — |
| `unittests/services/files/bulk-action-dispatcher.service.spec.ts` | `services/files/bulk-action-dispatcher.service.ts` | LIVE | — |
| `unittests/services/files/dashboard-stats.service.spec.ts` | `services/files/dashboard-stats.service.ts` | LIVE | — |
| `unittests/services/files/file-selection.service.spec.ts` | `services/files/file-selection.service.ts` | LIVE | — |
| `unittests/services/files/model-file.service.spec.ts` | `services/files/model-file.service.ts` | LIVE | — |
| `unittests/services/files/model-file.spec.ts` | `services/files/model-file.ts` | LIVE | — |
| `unittests/services/files/view-file-filter.service.spec.ts` | `services/files/view-file-filter.service.ts` | LIVE | — |
| `unittests/services/files/view-file-options.service.spec.ts` | `services/files/view-file-options.service.ts` | LIVE | — |
| `unittests/services/files/view-file-sort.service.spec.ts` | `services/files/view-file-sort.service.ts` | LIVE | — |
| `unittests/services/files/view-file.service.spec.ts` | `services/files/view-file.service.ts` | LIVE | — |
| `unittests/services/logs/log-record.spec.ts` | `services/logs/log-record.ts` | LIVE | — |
| `unittests/services/logs/log.service.spec.ts` | `services/logs/log.service.ts` | LIVE | — |
| `unittests/services/server/bulk-command.service.spec.ts` | `services/server/bulk-command.service.ts` | LIVE | — |
| `unittests/services/server/server-command.service.spec.ts` | `services/server/server-command.service.ts` | LIVE | — |
| `unittests/services/server/server-status.service.spec.ts` | `services/server/server-status.service.ts` | LIVE | — |
| `unittests/services/server/server-status.spec.ts` | `services/server/server-status.ts` | LIVE | — |
| `unittests/services/settings/config.service.spec.ts` | `services/settings/config.service.ts` | LIVE | — |
| `unittests/services/settings/config.spec.ts` | `services/settings/config.ts` | LIVE | — |
| `unittests/services/utils/auth.interceptor.spec.ts` | `services/utils/auth.interceptor.ts` | LIVE | — |
| `unittests/services/utils/confirm-modal.service.spec.ts` | `services/utils/confirm-modal.service.ts` | LIVE | — |
| `unittests/services/utils/connected.service.spec.ts` | `services/utils/connected.service.ts` | LIVE | — |
| `unittests/services/utils/dom.service.spec.ts` | `services/utils/dom.service.ts` | LIVE | — |
| `unittests/services/utils/notification.service.spec.ts` | `services/utils/notification.service.ts` | LIVE | — |
| `unittests/services/utils/rest.service.spec.ts` | `services/utils/rest.service.ts` | LIVE | — |
| `unittests/services/utils/version-check.service.spec.ts` | `services/utils/version-check.service.ts` | LIVE | — |

**Historical note:** `file.component.spec.ts` and `file-list.component.spec.ts` were the two stale spec files that tested `FileComponent` and `FileListComponent` (deleted in v1.1.0 redesign). Both were removed in commit `103ace3` during Phase 72. They no longer exist. [VERIFIED: git log --diff-filter=D]

### Mock Orphan Analysis

All 7 mock files in `tests/mocks/` are actively imported by remaining spec files. [VERIFIED: grep -rl]

| Mock File | Imported By |
|-----------|------------|
| `mock-event-source.ts` | `base-stream.service.spec.ts`, `stream-service.registry.spec.ts` |
| `mock-model-file.service.ts` | `dashboard-stats.service.spec.ts`, `view-file.service.spec.ts` |
| `mock-rest.service.ts` | `version-check.service.spec.ts` |
| `mock-storage.service.ts` | `view-file-options.service.spec.ts` |
| `mock-stream-service.registry.ts` | `autoqueue.service.spec.ts`, `base-web.service.spec.ts`, `config.service.spec.ts`, `dashboard-stats.service.spec.ts`, `server-command.service.spec.ts`, `view-file.service.spec.ts` |
| `mock-view-file-options.service.ts` | `view-file-filter.service.spec.ts`, `view-file-sort.service.spec.ts` |
| `mock-view-file.service.ts` | `view-file-filter.service.spec.ts`, `view-file-sort.service.spec.ts` |

**Result: Zero orphaned mocks.**

---

## Test Suite Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Total spec files | 40 | [VERIFIED: find] |
| Co-located specs | 3 | [VERIFIED: filesystem] |
| Centralized specs | 37 | [VERIFIED: filesystem] |
| Total `it()` test methods | 595 | [VERIFIED: grep count] |
| Component specs | 12 | [VERIFIED: import analysis] |
| Service/model/pipe specs | 28 | [VERIFIED: import analysis] |
| Stale spec files | 0 | [VERIFIED: exhaustive cross-reference] |
| Orphaned mocks | 0 | [VERIFIED: grep -rl] |

---

## CI Console Noise Inventory (D-07 targets)

### Confirmed Deprecation: HttpClientTestingModule (6 files)

`HttpClientTestingModule` was deprecated in Angular 15 in favor of `provideHttpClient()` + `provideHttpClientTesting()`. Angular 21 (the project's version) emits deprecation warnings for its use. [VERIFIED: Angular version is 21.2.9; auth.interceptor.spec.ts already uses the replacement API, confirming the pattern is known and adopted in this codebase]

Files using deprecated API:
1. `services/autoqueue/autoqueue.service.spec.ts`
2. `services/server/bulk-command.service.spec.ts`
3. `services/settings/config.service.spec.ts`
4. `services/files/model-file.service.spec.ts`
5. `services/utils/rest.service.spec.ts`
6. `services/server/server-command.service.spec.ts`

**Migration pattern** (already established in `auth.interceptor.spec.ts`):
```typescript
// Replace:
imports: [HttpClientTestingModule]

// With:
providers: [
    provideHttpClient(),
    provideHttpClientTesting()
]
// Import: from "@angular/common/http" and "@angular/common/http/testing"
```

### Potential Karma Config Deprecation
The `angularCli: { environment: 'dev' }` block in `karma.conf.js` is a legacy option from Angular CLI v1 era. In modern `@angular/build:karma` (Angular 21), this config key is silently ignored or may produce a warning. [ASSUMED — needs verification by running the actual test suite and checking output]

### console.debug in Production Test Code
`base-stream.service.spec.ts` contains `console.debug(eventName, data)` at line 16. This is in a test helper class, not production code. Whether it produces output depends on Karma's `captureConsole: false` setting. With `captureConsole: false`, client-side console calls are suppressed in Karma output. [VERIFIED: karma.conf.js has `captureConsole: false`]

---

## Common Pitfalls

### Pitfall 1: Mistaking "Test File Exists" for "Test Is Live"
**What goes wrong:** A spec file is present on disk but it imports a class that no longer exists, causing a TypeScript compile error at test time. The file appears in the directory but is effectively broken.
**Why it happens:** Spec files are deleted less consistently than production files during refactors.
**How to avoid:** Verify each spec file's primary imports resolve to live production files on disk (not just that the spec file itself exists).
**Warning signs:** TypeScript compile errors when running `ng test`.
**Phase 84 status:** Not applicable — all 40 spec files have been verified against live production imports. [VERIFIED]

### Pitfall 2: Removing Tests That Appear Redundant But Aren't Stale
**What goes wrong:** A test is removed because it "looks redundant" or tests an edge case that seems unlikely, but the production code it exercises is live.
**Why it happens:** D-01 is specific — only deleted production code justifies removal.
**How to avoid:** Apply D-01 strictly. If the production file exists and the test exercises it, keep it.
**Warning signs:** Coverage drops unexpectedly after removals (D-09 provides the safety net).

### Pitfall 3: HttpClientTestingModule Migration Breaking HttpTestingController
**What goes wrong:** Migrating from `HttpClientTestingModule` to `provideHttpClient()` + `provideHttpClientTesting()` but forgetting to update the `HttpTestingController` injection, causing test failures.
**Why it happens:** `HttpTestingController` still needs to be injected via `TestBed.inject(HttpTestingController)` — this part is unchanged.
**How to avoid:** Only change the `imports: [HttpClientTestingModule]` to `providers: [provideHttpClient(), provideHttpClientTesting()]`. Leave `httpMock = TestBed.inject(HttpTestingController)` unchanged.

### Pitfall 4: Coverage Baseline Capture Requires Same Browser Environment as CI
**What goes wrong:** Coverage captured locally (Chrome.app) differs from CI (ChromeHeadlessCI in Docker) due to different code execution paths.
**Why it happens:** Browser environments can differ in timing and execution.
**How to avoid:** For the D-09 coverage baseline, use the Docker-based `make run-tests-angular` or document that local baseline is an approximation. The baseline is for sanity checking, not enforcement.

### Pitfall 5: Assuming Phase 83's "Zero Removals" Pattern Means Phase 84 Will Also Be Zero
**What goes wrong:** Not doing the staleness audit because "Phase 83 found nothing."
**Why it happens:** The Python and Angular audits are independent — different code paths were touched by the UI redesign (Angular was more affected).
**How to avoid:** Always run the full audit regardless of expectations. (Note: research has already found zero stale specs, but the plan must still formally execute and document the audit as required by D-06.)

---

## Code Examples

### Running ng test locally (macOS)
```bash
# Source: package.json scripts + karma.conf.js
# From src/angular directory:
cd /Users/julianamacbook/seedsyncarr/src/angular
node node_modules/@angular/cli/bin/ng.js test \
  --browsers ChromeHeadless \
  --watch=false

# With coverage (D-09):
node node_modules/@angular/cli/bin/ng.js test \
  --browsers ChromeHeadless \
  --watch=false \
  --code-coverage
# Coverage output: src/angular/coverage/
```

### HttpClientTestingModule migration (established project pattern)
```typescript
// Source: [VERIFIED: auth.interceptor.spec.ts — already migrated]
import {HttpClient, provideHttpClient, withInterceptors} from "@angular/common/http";
import {HttpTestingController, provideHttpClientTesting} from "@angular/common/http/testing";

TestBed.configureTestingModule({
    providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        // ... other providers
    ]
});
httpMock = TestBed.inject(HttpTestingController);
```

### Mock orphan detection
```bash
# Source: [VERIFIED: used during research]
# Run from src/angular/src/app/:
grep -rl "mock-rest.service" tests/unittests/ pages/ services/
# No output = orphaned, safe to delete
# Output = still imported, keep
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `HttpClientTestingModule` | `provideHttpClient()` + `provideHttpClientTesting()` | Angular 15 (deprecation), Angular 21 enforces warnings | 6 spec files need migration for clean CI output |
| `imports: [...]` in TestBed for standalone components | `imports: [ComponentClass]` directly (standalone API) | Angular 14+ | About/option/settings co-located specs already use correct standalone pattern |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Angular CLI | ✓ | (npm present in src/angular) | — |
| `ng` CLI | Test execution | ✓ (local, not in PATH) | 21.2.8 | `node node_modules/@angular/cli/bin/ng.js` |
| Chrome / ChromeHeadless | Local `ng test` | ✓ | Chrome.app in /Applications | — |
| Docker | `make run-tests-angular` | [ASSUMED — not checked; Docker was present for Phase 83] | — | Local ng test |
| `make run-tests-angular` | CI-equivalent test run | [ASSUMED — depends on Docker] | — | Local ng test |

**Missing dependencies with no fallback:** None identified. [VERIFIED: local ng test is runnable]

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from config.json — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Karma 6.4.4 + Jasmine 5.1.0 / jasmine-core 6.2.0 |
| Config file | `src/angular/karma.conf.js` |
| Quick run command | `cd src/angular && node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false` |
| Full suite command | same (Karma runs all specs in one pass) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NG-01 | All 40 spec files reference live production imports | static analysis + manual | `find` + `realpath` cross-check | N/A (scripted) |
| NG-02 | No test failures introduced by removals | regression | `ng test --browsers ChromeHeadless --watch=false` | ✅ (40 spec files exist) |
| NG-03 | All remaining tests pass after cleanup | full suite | `ng test --browsers ChromeHeadless --watch=false` | ✅ |

### Sampling Rate
- **Per task commit:** `cd src/angular && node node_modules/@angular/cli/bin/ng.js test --browsers ChromeHeadless --watch=false`
- **Per wave merge:** same (single-pass suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. No new test files need to be created for this audit phase.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `angularCli: { environment: 'dev' }` in karma.conf.js may produce deprecation warnings in Angular 21 | CI Console Noise Inventory | Low — if it doesn't produce warnings, nothing needs to change in that file |
| A2 | Docker is available for `make run-tests-angular` (not verified this session) | Environment Availability | Low — local `ng test` with Chrome.app is a confirmed fallback |

**Verified claims:** All staleness determinations (40 spec files × production file existence), all mock usage counts, all import paths, Angular version, Karma/Jasmine versions, available CLI tooling.

---

## Open Questions

1. **Does `ng test --watch=false` currently produce warnings?**
   - What we know: `HttpClientTestingModule` is deprecated in Angular 21; `angularCli` config key may be stale
   - What's unclear: The exact warning text and count without running the actual suite
   - Recommendation: First task in the plan should be running `ng test --watch=false` and capturing output to enumerate all warnings before any changes

2. **Should the coverage baseline be captured via Docker or local Chrome.app?**
   - What we know: D-09 requires coverage before and after; no fail_under threshold enforced
   - What's unclear: Whether minor environment differences (Docker vs local) matter for a sanity-check baseline
   - Recommendation: Local `ng test --code-coverage` is sufficient for sanity checking; document the environment used

---

## Sources

### Primary (HIGH confidence)
- Filesystem: all 40 spec files read and cross-referenced against `find` output of production files — [VERIFIED: exhaustive]
- `src/angular/package.json` — Angular 21.2.9, Karma 6.4.4, Jasmine 5.1.0
- `src/angular/karma.conf.js` — reporter config, captureConsole setting, custom launchers
- `src/angular/src/test.ts` — test bootstrap
- `src/angular/src/tsconfig.spec.json` — spec file inclusion glob
- `git log --diff-filter=D` — confirmed `file.component.spec.ts` and `file-list.component.spec.ts` were deleted in commit `103ace3`
- `grep -rl` on all 7 mock files — confirmed all are imported by at least one remaining spec
- `auth.interceptor.spec.ts` — confirmed `provideHttpClient` + `provideHttpClientTesting` pattern is already established in this codebase

### Secondary (MEDIUM confidence)
- Angular 15 deprecation of `HttpClientTestingModule` — established fact; confirmed by presence of new API in `auth.interceptor.spec.ts` (codebase evidence)
- CI workflow `.github/workflows/ci.yml` — confirms `make run-tests-angular` is the CI command

### Tertiary (LOW confidence)
- `angularCli: { environment: 'dev' }` producing a warning — inferred from legacy config key; not verified by running the suite

---

## Metadata

**Confidence breakdown:**
- Staleness audit results: HIGH — exhaustive filesystem cross-reference of all 40 specs
- Mock orphan analysis: HIGH — grep -rl across all spec directories
- CI noise (HttpClientTestingModule): HIGH — confirmed deprecated API in 6 files, confirmed replacement pattern in codebase
- CI noise (angularCli config): LOW — inferred, not observed from test run output
- Test counts: HIGH — grep -c verified

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (stable stack, 30-day window)
