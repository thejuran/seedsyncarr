# Phase 77: Deferred Playwright E2E (Phases 72 + 73) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 77-deferred-playwright-e2e-phases-72-73
**Areas discussed:** State seeding + fixture, Destructive action + FIX-01, Spec file org + overlap, URL round-trip depth

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| State seeding + fixture | How to reach non-DEFAULT statuses for UAT-02 coverage | ✓ |
| Destructive action + FIX-01 | What bulk-action specs assert + DELETED-reach strategy | ✓ |
| Spec file org + overlap | Where new specs live vs. existing 11 tests | ✓ |
| URL round-trip depth | Shape of the reload/hydration tests | ✓ |

**User's choice:** All four areas selected.

---

## State Seeding + Fixture

### Seeding path

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime HTTP seed in beforeAll | Dispatch backend command endpoints; no fixture changes | ✓ |
| Extend remote Docker fixture | Add diverse files + new seeding container | |
| Button-smoke only | Skip row assertions; assert URL + empty-state only | |
| Hybrid: seed a few, smoke the rest | Partial seed for FIX-01 + operationally-interesting statuses | |

### Seed scope

| Option | Description | Selected |
|--------|-------------|----------|
| Once per file (beforeAll) | Cheapest runtime, state drifts destructively | ✓ |
| beforeAll + afterEach restore | Re-seed after each destructive test | |
| Per-test beforeEach reset | Fully independent tests, highest runtime cost | |
| No automated reset — order carefully | Fragile; easy to break on insertion | |

### Wait style

| Option | Description | Selected |
|--------|-------------|----------|
| Poll row status via .locator().waitFor() | Matches SSE-driven UI exactly | ✓ |
| Fixed sleep (1–2s) | Flaky; machine-speed-dependent | |
| Poll backend /server/status JSON | Decouples seed-readiness from UI render | |
| No wait — assert terminal only | Too racy for real LFTP flows | |

### Seed helper home

| Option | Description | Selected |
|--------|-------------|----------|
| New fixtures/seed-state.ts module | Reusable; matches future file-split potential | ✓ |
| Extend DashboardPage page object | Single home; page object grows | |
| Inline in each spec | Explicit but diverges over time | |

**Notes:** User picked the runtime-seeding path + beforeAll-only + .locator() polling + dedicated module. Clear preference for minimizing fixture/Docker churn.

---

## Destructive Action + FIX-01

### Action-spec assertion depth

| Option | Description | Selected |
|--------|-------------|----------|
| UI dispatch only (toast + clear) | Click → toast + selection cleared; no backend mutation verification | ✓ |
| page.route() intercept | Verify HTTP request shape; stub response | |
| Full E2E — let state mutate | Wait for status transition in row | |
| Hybrid: dispatch + row-disappears or status-changes | Middle-ground verification | |

### FIX-01 DELETED reach

| Option | Description | Selected |
|--------|-------------|----------|
| Seed DELETED in beforeAll via HTTP | Pre-seeded DELETED row, deterministic | ✓ |
| Chain after the Delete Local action test | Re-uses mutation; fragile to reorder | |
| Intercept — simulate DELETED row | Cheapest, furthest from reality | |
| Filter-chip smoke only | Doesn't prove union contract | |

### Destructive isolation

| Option | Description | Selected |
|--------|-------------|----------|
| No isolation — real mutation, ordering | Accept leak; destructive-last ordering | ✓ |
| page.route() for Delete Local/Remote only | Stub the hardest-to-undo actions | |
| Stub all 5 actions | Fastest, most isolated, lowest-fidelity | |
| Per-test state reset via reset endpoint | Significant infra work; out of scope | |

### DELETED-row survival timing

| Option | Description | Selected |
|--------|-------------|----------|
| Seed DELETED pre-test — don't delete in-test | FIX-01 fixture in beforeAll; selection test consumes it | ✓ |
| Filter to Deleted sub after delete | Brittle if row purges from model | |
| Observe backend behavior first, then decide | Planner validates in research | |
| Both seed + observe | Belt + suspenders | |

**Notes:** Answers cohere: UI-only assertions + real mutation in ordering + pre-seeded DELETED row. The planner will need to validate DELETED-row survival via research (noted in CONTEXT specifics).

---

## Spec File Org + Overlap

### File organization

| Option | Description | Selected |
|--------|-------------|----------|
| Split into selection + filter files | Three small focused files | |
| All in dashboard.page.spec.ts | Single source of truth, 26 tests | ✓ |
| One new file: dashboard.multi-select-filter.spec.ts | Existing untouched | |
| Keep existing, restructure later | Defer split if file gets unwieldy | |

### Coverage counting

| Option | Description | Selected |
|--------|-------------|----------|
| Add 15 net-new, keep existing as-is | Paper-clean; some redundant coverage | ✓ |
| Count overlapping existing toward 15 | Tighter mapping, fewer tests | |
| Hybrid: absorb exact-overlaps | Mapping table in CONTEXT.md | |
| Rewrite existing + add 15 in new files | Highest churn, cleanest end-state | |

### Page object evolution

| Option | Description | Selected |
|--------|-------------|----------|
| Extend DashboardPage + add helpers | One home; matches pattern | ✓ |
| Compose: DashboardPage + SelectionHarness + FilterHarness | Cleaner boundary; more scaffolding | |
| Inline locators in specs | Pragmatic; risks drift | |
| Planner picks | Claude's discretion | |

### Page object v2 — selector coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Add selectors for status badge, empty-state, toast, header checkbox, sub buttons | Up-front harness investment | ✓ |
| Minimal — add selectors per-spec as needed | Smaller per-commit surface | |
| Generate from existing DOM audit first | Highest up-front investment | |

**Notes:** Consistent single-file + page-object extension + up-front helper investment. The "Wave 1 helpers" decision derived here.

---

## URL Round-Trip Depth

### Round-trip coverage depth

| Option | Description | Selected |
|--------|-------------|----------|
| One round-trip per parent + 1 sub | 5 tests: 4 parent + 1 sub | ✓ |
| Every (segment, sub) pair | ~9 tests; heavy overlap | |
| Parent-only + drill-down + invalid | Skips sub-status hydration | |
| Full matrix | Proves state machine fully; ~12 tests | |

### UAT-02 spec budget split

| Option | Description | Selected |
|--------|-------------|----------|
| One per ViewFile.Status (8) + 2 round-trip | Maximum status coverage | ✓ |
| Parent-group semantics (4) + drill-down (2) + round-trip (3) + invalid (1) | Behavior-weighted | |
| Sub-button per status (8) + round-trip (2) | Same as option 1, relabeled | |
| Planner picks the split | Leave to research | |

### Reload mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| page.reload() on dashboard | Tests warm hydration | ✓ |
| page.goto(capturedURL) in fresh context | Cold-load / bookmark path | |
| Both, separate specs | More coverage; more specs | |
| goto-only | Stricter contract, fewer specs | |

### Back/forward coverage

| Option | Description | Selected |
|--------|-------------|----------|
| No — out of scope for this phase | Phase 73 deferred; keep deferred | ✓ |
| One optional smoke spec | Cheap piggyback | |
| Full — back/forward per parent | Likely redundant | |

**Notes:** The "one round-trip per parent + 1 sub" (5 tests intent) conflicts with the "8 status + 2 round-trip" budget (10 total). CONTEXT.md resolves this: 2 round-trip tests total, shape = 1 parent + 1 sub (representative), with the remaining 8 being status-filter specs. Claude's Discretion covers this reconciliation explicitly in D-14.

---

## Claude's Discretion

Areas left to the planner (captured in CONTEXT.md §Claude's Discretion):
- Exact file chosen to seed into DELETED (`joke` suggested)
- Exact helper naming conventions
- UAT-01 item 4 packaging: one spec vs 5 per-action specs (D-19)
- Ordering within describe beyond destructive-last rule
- `test.describe.serial()` usage
- Toast assertion precision (partial vs exact match)
- Empty-state selector shape (if empty-state panel exists)

## Deferred Ideas

Explicitly surfaced and deferred (captured in CONTEXT.md §Deferred):
- Back/forward browser navigation E2E (Phase 73 deferred → stays deferred)
- Cold-load URL via `page.goto(capturedURL)` in fresh context
- `page.route()` intercept for destructive actions
- Toast localization matrix
- CSP violation detection (Phase 79 owns it)
- 9-UAT-01 per-action split variant
- Extracting existing 11 tests to their own file
- Per-test state reset via reset endpoint
