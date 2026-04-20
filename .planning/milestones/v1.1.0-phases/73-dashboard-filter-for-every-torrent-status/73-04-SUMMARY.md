---
phase: 73-dashboard-filter-for-every-torrent-status
plan: 04
type: execute
status: complete
completed: 2026-04-19
---

<objective-recap>
Update `transfer-table.component.spec.ts` to cover the new Done segment, Pending sub-status, and URL query-param persistence introduced by Plans 01–03. Mock `Router` + `ActivatedRoute` so TestBed compiles after Plan 03's constructor changes; extend `TEST_TEMPLATE` so DOM-query tests match the production template; add 17 new tests covering filter logic + URL hydration + URL write-back + D-12 carry-forward for the `done` segment.
</objective-recap>

<commits>
- `dc700dd`: test(73-04): add Router/ActivatedRoute mocks + update TEST_TEMPLATE + 4-button assertion
- `bfe58d9`: test(73-04): add 6 filter-logic tests — Done branch + Pending sub + selection-clear
- `3bc69e7`: test(73-04): add URL query-param persistence describe — 11 new tests (D-09/D-10/D-11)
</commits>

<key-files>
<modified>
- path: src/angular/src/app/tests/unittests/pages/files/transfer-table.component.spec.ts
  change: +259 / -4 lines. Imports `Router` + `ActivatedRoute` from `@angular/router`. Adds `mockQueryParamMap`, `mockActivatedRoute`, `mockRouter` at describe scope; `beforeEach` resets both. `TestBed.providers` gains 2 provider entries. `TEST_TEMPLATE` gains Done parent + Done expand block + Pending sub button. Parent-button-count test updated from 3→4 with ordered assertion. 17 new tests added across 2 sections (6 filter-logic + 11 URL persistence).
</modified>
</key-files>

<test-count-delta>
- Baseline (pre-plan): 549 total tests in full Angular suite
- After Task 1: 549 (existing 3-button test replaced by 4-button test, net +0)
- After Task 2: 555 (+6 filter-logic tests)
- After Task 3: 566 (+11 URL persistence tests)
- **Total delta: +17 tests**, all passing under Karma/Jasmine via `ng test --watch=false --browsers=ChromeHeadless`.

The acceptance-criteria command in the plan (`npx jest transfer-table.component.spec`) did not match this project's actual test runner (Karma/Jasmine, not Jest). Tests were verified via `ng test` which is the project's `npm test` script.
</test-count-delta>

<decision-impact>
- D-01: 3 new statuses (DEFAULT, DOWNLOADED, EXTRACTED) all have single-sub-status filter tests.
- D-04: 4-parent assertion locks in the All/Active/Done/Errors order.
- D-05: `should include DEFAULT (Pending) in 'active' segment results` — 4 files, proving Plan 01 Task 2's Active-branch extension with a DEFAULT file.
- D-06: Done segment with no sub returns DOWNLOADED ∪ EXTRACTED (group-OR).
- D-09: URL round-trip — hydration reads `?segment=&sub=`; write-back pushes the same shape.
- D-10: All write-back calls asserted to use `queryParamsHandling: "merge"`; segment change also asserted `replaceUrl: true`.
- D-11: Silent-fallback enforcement — invalid segment → `'all'`; mismatched sub → `null`; **`notificationMock.show` asserted NOT called** on both invalid-param paths (no user-facing error); page + search NOT persisted (explicit assertions).
- D-12: Carry-forward locked in — `onSegmentChange("done")` clears file selection via `selectionService.getSelectedCount()`.
</decision-impact>

<deviations>
- The plan spec called the selection-clear assertion `selectionService.getSelectedFiles().size` — the actual `FileSelectionService` API in this codebase is `getSelectedCount()`. The existing "selection clearing (D-04)" describe block (spec line 559) uses `getSelectedCount()`, so the new D-12 test uses the same API for consistency. Behaviourally identical.
- The existing test at spec line ~213 ("should filter to active statuses") was intentionally NOT modified — its test data does not include a DEFAULT file, so the existing `length === 3` assertion still holds. The new Task 2 test `should include DEFAULT (Pending) in 'active' segment results` is the additional coverage for Plan 01's Active-branch extension (per plan's explicit note).
</deviations>

<createwithquery-pattern>
Because URL hydration runs in `ngOnInit` (invoked during `TestBed.createComponent`), each hydration test must seed `mockQueryParamMap` BEFORE creating a fresh component instance. The `createWithQuery(params)` helper encapsulates this:

```typescript
function createWithQuery(params: { [k: string]: string | null }) {
    for (const k of Object.keys(mockQueryParamMap)) { delete mockQueryParamMap[k]; }
    Object.assign(mockQueryParamMap, params);
    fixture = TestBed.createComponent(TransferTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
}
```

This gives each hydration test an independent component instance with its own `ngOnInit` run, avoiding cross-test pollution of hydrated state.
</createwithquery-pattern>

<verification>
- `ng test --watch=false --browsers=ChromeHeadless`: 566 SUCCESS (0 failures).
- All acceptance-criteria greps pass in the final spec file.
- Task 3's `notificationMock.show` not-called assertions explicitly enforce D-11's silent-fallback rule.
- All existing tests continue to pass under the new TestBed providers.
</verification>

<self-check>PASSED</self-check>
