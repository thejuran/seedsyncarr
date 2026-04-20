---
phase: 73-dashboard-filter-for-every-torrent-status
plan: 05
type: execute
status: complete
completed: 2026-04-19
---

<objective-recap>
Add page-object locators for the new Done parent + Pending/Downloaded/Extracted sub-buttons and three Playwright tests proving Done expand, Pending reveal, and URL round-trip. Verify (via existing Phase 72 tests and the Plan 04 unit test) that D-12 selection-clearing carry-forward still holds — no new e2e test required.
</objective-recap>

<commits>
- `14d456c`: test(73-05): add getSegmentButton and getSubButton to DashboardPage page-object
- `c2d3407`: test(73-05): add 3 e2e tests — Done expand, Pending reveal, URL round-trip
</commits>

<key-files>
<modified>
- path: src/e2e/tests/dashboard.page.ts
  change: +8 lines. Added `getSegmentButton(name)` and `getSubButton(name)` methods between `getActionButton` and `selectFileByName`. Parent locator scopes to `.segment-filters` and uses `getByRole('button', { name, exact: true })`. Sub locator scopes to `.segment-filters button.btn-sub` and uses `getByText(name, { exact: true })` so the accent-dot span inside each button is ignored.
- path: src/e2e/tests/dashboard.page.spec.ts
  change: +24 lines. 3 new tests appended to the `Testing dashboard page` describe block, after the existing 7 tests.
</modified>
</key-files>

<method-signatures>
```typescript
getSegmentButton(name: 'All' | 'Active' | 'Done' | 'Errors'): Locator
getSubButton(name: 'Pending' | 'Syncing' | 'Queued' | 'Extracting' | 'Downloaded' | 'Extracted' | 'Failed' | 'Deleted'): Locator
```
</method-signatures>

<test-count-delta>
- Baseline: 7 dashboard e2e tests
- After this plan: 10 dashboard e2e tests (+3)
- Tests added:
  - `should expand Done segment to reveal Downloaded and Extracted subs`
  - `should reveal Pending sub under Active`
  - `should persist Done filter via URL query param (D-09)`
</test-count-delta>

<decision-impact>
- D-01: New statuses (DOWNLOADED, EXTRACTED, DEFAULT) now reachable end-to-end via page-object locators.
- D-03: Visible labels `Downloaded`, `Extracted`, `Pending` asserted by `getByText(..., { exact: true })`.
- D-04: Done parent + 2 subs render in the right place (expand test).
- D-05: Pending lives under Active (reveal test).
- D-09: URL round-trip asserted by `toHaveURL(/[?&]segment=done(&|$)/)` — proves Plan 02 + Plan 03 integrate in a real browser.
- D-12 (carry-forward from Phase 72): verified by Plan 04's unit test `should clear file selection when 'done' segment selected` — no new e2e test added per PATTERNS.md "keep it minimal and parity-focused". The existing Phase 72 dashboard tests (selection, action-bar visibility) continue to run against the new filter UI without modification — if selection-clearing on segment change regressed, the Plan 04 unit test would fail.
</decision-impact>

<deviations>
None.
</deviations>

<verification>
- `cd src/e2e && npx tsc --noEmit` exits 0 after both tasks.
- All grep-based acceptance criteria pass (11/11 from Task 1 + Task 2).
- **Runtime e2e suite is CI-gated via `make run-tests-e2e`** (per src/e2e/README.md the suite requires a docker-compose stack: `myapp` serving Angular, `chrome` running Selenium/Playwright, `remote` SSH). This session cannot spin up docker-compose, so runtime Playwright verification is deferred to CI / local `make run-tests-e2e`. The test bodies are structurally identical to existing dashboard tests that pass in CI, and the locators exercise DOM selectors already present in the post-Plan-02 template (verified via `ng build` in Wave 2).
- Browser back/forward filter navigation is explicitly NOT tested here per CONTEXT line 133 (deferred follow-up).
</verification>

<self-check>PASSED — runtime verification deferred to `make run-tests-e2e` per repo convention; structural checks (tsc + greps + locator scoping) all pass.</self-check>
