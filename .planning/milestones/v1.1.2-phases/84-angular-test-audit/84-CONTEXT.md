# Phase 84: Angular Test Audit - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Identify and remove stale Angular unit tests that no longer exercise components and services present in the current SeedSyncarr UI. Additionally, clean up all CI test runner console noise after stale test removal.

</domain>

<decisions>
## Implementation Decisions

### Staleness Criteria
- **D-01:** Same strict rule as Phase 83 — a test is "stale" only if the production code it exercises (component, service, pipe) has been deleted or completely rewritten. Tests that pass and exercise live code stay, regardless of perceived quality or redundancy.
- **D-02:** Renamed components count as deleted if the old file/class no longer exists (e.g., old `FileComponent` → `TransferRowComponent` means tests for `FileComponent` are stale if that file is gone).
- **D-03:** Do not reorganize spec file locations. The 3 co-located specs (about, option, settings-page) and the 37 specs in `tests/unittests/` both stay where they are.

### Removal Granularity
- **D-04:** Remove at individual test method level (carried from Phase 83 D-06). If all methods in a spec file are stale, delete the entire file.
- **D-05:** Clean up orphaned test helpers, mocks, and fixtures in `tests/unittests/mocks/` — if a mock service is no longer imported by any remaining test, remove it.

### Inventory Format
- **D-06:** Document all removals in a markdown table: spec file path | test count removed | reason (e.g., "tests FileComponent deleted in v1.1.0 redesign"). Carried from Phase 83 D-05.

### CI Warning Cleanup
- **D-07:** After stale test removal is complete, clean up all console noise from `ng test --watch=false` output: deprecation warnings, console.error/warn from components during tests, Karma config deprecations, and any other test runner noise.
- **D-08:** Warning cleanup happens after stale removal (not before or concurrently). Some warnings may disappear with deleted tests.

### Coverage Safety Net
- **D-09:** Record Angular coverage baseline before and after removals using `ng test --code-coverage`. Document the numbers for reviewability. No fail_under threshold is enforced.
- **D-10:** The "dead code only" staleness criteria means removed tests should contribute zero unique coverage by definition, but the baseline provides a sanity check.

### Folded Todos
- **Clean up CI test runner warnings** — Address all console noise during Angular test runs. Folded into D-07/D-08 above; handled as a cleanup pass after stale test removal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test Infrastructure
- `src/angular/karma.conf.js` — Karma test runner config (Jasmine 5.1.0, ChromeHeadlessCI)
- `src/angular/angular.json` — Angular build/test configuration (test entry point, polyfills, styles)
- `src/angular/src/test.ts` — Test bootstrap entry point

### Angular Source (verify against)
- `src/angular/src/app/pages/` — All page components (about, files, logs, main, settings)
- `src/angular/src/app/services/` — All services (autoqueue, base, files, logs, server, settings, utils)
- `src/angular/src/app/common/` — Shared pipes and directives

### Test Files (audit targets)
- `src/angular/src/app/tests/unittests/` — Centralized test directory (37 specs + mocks/)
- `src/angular/src/app/pages/about/about-page.component.spec.ts` — Co-located spec
- `src/angular/src/app/pages/settings/option.component.spec.ts` — Co-located spec
- `src/angular/src/app/pages/settings/settings-page.component.spec.ts` — Co-located spec

### Prior Phase Context
- `.planning/phases/83-python-test-audit/83-CONTEXT.md` — Phase 83 decisions (staleness criteria, removal granularity, inventory format)

### Requirements
- `.planning/REQUIREMENTS.md` — NG-01, NG-02, NG-03 requirements for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Test Suite Structure
- 40 Angular spec files total (3 co-located, 37 in tests/unittests/)
- 13 component specs, 25 service specs, 1 pipe spec, 1 app component spec
- Dedicated `tests/unittests/mocks/` directory with mock services (mock-view-file.service.ts, mock-rest.service.ts, mock-model-file.service.ts)
- Karma + Jasmine runner with ChromeHeadlessCI for CI

### Established Patterns
- TestBed with `configureTestingModule` + `compileComponents` for component tests
- `jasmine.createSpyObj()` for service mocks
- `HttpTestingController` for HTTP mocking with `expectOne`/`flush`
- `fakeAsync()` + `tick()` for async timing control
- `overrideTemplate()` to simplify component logic testing

### Key History (staleness sources)
- UI redesign (v1.1.0, M006) — FileComponent/FileListComponent renamed to TransferRowComponent/TransferTableComponent
- Sidebar removed, top nav bar added (M006) — sidebar-related component tests may be stale
- AutoQueue merged into Settings page (M008) — standalone AutoQueue page tests may be stale
- Selection/bulk-bar rewrite (phases 72-74) — old selection component tests may reference deleted components
- Dashboard stats strip added (v1.1.0) — new component, should have live tests

### Integration Points
- `ng test --watch=false` — CI test command
- `ng test --code-coverage` — Coverage report generation to `coverage/` directory

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

### CSP Violation Detection
- **Add CSP violation detection to e2e tests** — Originally folded into Phase 84 but deferred to Phase 85 (E2E Test Audit) where it fits naturally as a Playwright/browser concern.

### Reviewed Todos (not folded)
- **Encrypt stored credentials at rest** — Security concern, not related to test audit (score: 0.4)
- **Add rate limiting to all HTTP endpoints** — Security concern, out of scope (score: 0.2)
- **Remove PYTHONWARNINGS cgi filter once webob drops stdlib cgi import** — Python/upstream dependency, not Angular (score: 0.2)
- **Tighten Shield Semgrep rules to reduce false positives** — Tooling concern, not Angular tests (score: 0.2)

</deferred>

---

*Phase: 84-angular-test-audit*
*Context gathered: 2026-04-24*
