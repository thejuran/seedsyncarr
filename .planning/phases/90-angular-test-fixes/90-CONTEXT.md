# Phase 90: Angular Test Fixes - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 7 specific Angular test quality defects: add fakeAsync zone cleanup for pending periodic tasks, fix double-cast hiding nullable type, fix subscription leaks in 4 spec files (view-file.service, notification.service, file-selection.service, transfer-row.component), and add definedness guards where optional chaining masks test gaps.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User elected to skip discussion -- all implementation decisions are at Claude's discretion. Requirements are fully specified in REQUIREMENTS.md (ANGFIX-01 through ANGFIX-07) with exact file locations and bug descriptions. No ambiguity in what needs fixing.

Key areas left to Claude:
- **D-01:** Subscription teardown strategy for ANGFIX-03/04/05/06 -- afterEach unsubscribe, per-test teardown, or DestroyRef pattern across 4 affected spec files
- **D-02:** fakeAsync cleanup scope for ANGFIX-01 -- whether to add `discardPeriodicTasks()` only to the specific spec named or audit all 23 fakeAsync-using specs
- **D-03:** Optional chaining guard approach for ANGFIX-07 -- `expect(result).toBeDefined()` before each chained assertion vs restructuring variable declarations
- **D-04:** Double-cast fix for ANGFIX-02 -- use `ViewFileFilterCriteria | undefined` type annotation instead of `undefined as unknown as ViewFileFilterCriteria`
- **D-05:** EventEmitter leak + non-null assertion fix for ANGFIX-06 -- cleanup pattern for transfer-row.component.spec.ts

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test Audit Findings
- `.planning/REQUIREMENTS.md` -- ANGFIX-01 through ANGFIX-07 requirement definitions with file locations and bug descriptions

### Affected Test Files
- `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` -- ANGFIX-03 missing subscription teardown (0 unsubscribe/teardown calls, multiple subscribes)
- `src/angular/src/app/tests/unittests/services/utils/notification.service.spec.ts` -- ANGFIX-04 subscription leaks (7 subscribes, 0 afterEach cleanup)
- `src/angular/src/app/tests/unittests/services/files/file-selection.service.spec.ts` -- ANGFIX-05 signal-derived observable subscription leaks (4 subscribes, 0 cleanup)
- `src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts` -- ANGFIX-06 EventEmitter leak + non-null assertion (2 subscribes, 0 cleanup)
- `src/angular/src/app/tests/unittests/services/files/view-file-filter.service.spec.ts` -- ANGFIX-02 double-cast at line 30 (`undefined as unknown as ViewFileFilterCriteria`)
- `src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts` -- ANGFIX-07 optional chaining in ~30 assertions (e.g., `expect(result?.success)`)

### fakeAsync Specs (ANGFIX-01 audit scope)
- 23 spec files use `fakeAsync` -- full list available via `grep -rl "fakeAsync" src/angular/src/app/tests --include="*.spec.ts"`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing teardown/cleanup patterns in Angular specs -- this phase establishes the pattern
- `jasmine.createSpyObj()` used extensively for mocking services
- `HttpTestingController` with `httpMock.verify()` in afterEach -- the only existing afterEach cleanup pattern

### Established Patterns
- Angular 21.x with standalone components
- Karma 6.4.4 + Jasmine 5.1.0 test runner
- `fakeAsync()` + `tick()` for async control (23 specs)
- `TestBed.configureTestingModule()` with providers array
- No `takeUntil`/`destroy$` pattern in spec files (exists in production code)
- Double quotes, 2-space indent, semicolons required

### Integration Points
- All fixes must pass `ng test --watch=false` (599 tests)
- Angular coverage baselines: Statements 83.34%, Branches 69.01%, Functions 79.73%, Lines 84.21%
- CI runs on both amd64 and arm64

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches for all fixes.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 90-angular-test-fixes*
*Context gathered: 2026-04-25*
