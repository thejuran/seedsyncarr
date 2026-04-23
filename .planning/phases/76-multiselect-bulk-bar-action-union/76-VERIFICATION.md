---
phase: 76-multiselect-bulk-bar-action-union
verified: 2026-04-20T00:00:00Z
status: passed
score: 4/4 roadmap success criteria verified — unit-test + browser UAT complete
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Dashboard smoke — select a single DELETED file in the transfer table"
    expected: "Bulk-actions bar appears with Queue (re-queue from remote) and Delete Remote buttons enabled; Stop, Extract, Delete Local disabled."
    why_human: "Unit tests cover createViewFile transform (service spec) and the bar's consumption of eligibility flags (bar spec), but no unit test observes the rendered DOM with the real backend model emission path stitched through TransferTable. The original user symptom was 'the bar doesn't show at all' — a visual confirmation on a running app closes the feedback loop even though the unit suite is exhaustive."
  - test: "Dashboard smoke — select a DELETED file mixed with a DOWNLOADING row"
    expected: "Bar shows Queue enabled (1 eligible), Stop enabled (1 eligible), Delete Remote enabled (2 eligible), Extract and Delete Local disabled. Clicking Queue dispatches only against the DELETED row's filename; clicking Stop dispatches only against the DOWNLOADING row's filename."
    why_human: "End-to-end dispatch verification — ensures per-row filtering survives the full wire (bar → BulkActionDispatcher → BulkCommandService → backend). Unit tests assert the Angular EventEmitter payload but not the HTTP call or backend acknowledgement."
  - test: "Visual parity — compare the bulk bar's rendered appearance before and after phase 76"
    expected: "Pixel-identical. No changes to Queue label text, button icons, button order, spacing, or colors. D-06/D-07 visual freeze."
    why_human: "Byte-identical HTML/SCSS is verified (git diff empty between e991b19 and HEAD) but visual regression at runtime (e.g., an indirect SCSS import that starts behaving differently) cannot be fully excluded without a human eyeballing the rendered bar."
---

# Phase 76: Multiselect Bulk-Bar Action Union Verification Report

**Phase Goal:** Users selecting any mix of file states (including deleted files) see every action that applies to at least one selected row, with inapplicable actions disabled per-row rather than hidden wholesale.
**Verified:** 2026-04-20T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Selecting a deleted file (alone or mixed) exposes "Re-Queue from Remote" in the bulk-actions bar | VERIFIED (unit-level) | `view-file.service.ts:348-351` — DELETED short-circuits the `remoteSize > 0` gate so `isQueueable=true`; `view-file.service.spec.ts:1005-1038` (RED target test) asserts `file.isQueueable === true` after a model push with `state=DELETED, remote_size=null`. Browser-level confirmation deferred to human smoke test + Phase 77 E2E. |
| 2 | Mixed selections show the union of applicable actions across the selection | VERIFIED | `bulk-actions-bar.component.spec.ts:372-571` — three D-09 cases (All-DELETED n=3, DELETED+DOWNLOADING, DELETED+DOWNLOADED+STOPPED) assert every `actionCounts.X` value matches the union rule. Case 3 in particular asserts `queueable=2` (DELETED+STOPPED), `extractable=1` (DOWNLOADED), `locallyDeletable=2` (DOWNLOADED+STOPPED), `remotelyDeletable=3` (all three) — the full union stress matrix. |
| 3 | Each action dispatches only to rows where it is valid; non-applicable rows in the selection are unaffected | VERIFIED | `bulk-actions-bar.component.spec.ts:407-426, 471-488, 545-570` — every D-09 case spies on all 5 emitters. Click handlers for eligible actions emit filtered arrays (`jasmine.arrayContaining` + `.length` assertion pins exact membership); click handlers with zero eligible rows do NOT emit (per `if (files.length > 0)` guard). Production dispatch path unchanged per D-08. |
| 4 | Unit tests cover the union logic for at least three representative mixed selections | VERIFIED | Three D-09 cases exist in `bulk-actions-bar.component.spec.ts` describe block `FIX-01 DELETED union regression (D-09 coverage)` at line 371. Cases span all-single-status (DELETED×3), two-status (DELETED+DOWNLOADING), and three-status (DELETED+DOWNLOADED+STOPPED) mixes. Plus 2 service-level characterization tests in `view-file.service.spec.ts:1004-1074`. |

**Score:** 4/4 success criteria verified at the unit-test layer.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/angular/src/app/services/files/view-file.service.ts` | DELETED short-circuit on `isQueueable` and `isRemotelyDeletable` predicates | VERIFIED | Lines 348-351 + 364-369 both now start with `status === ViewFile.Status.DELETED ||` — confirmed via direct read. No other production code touched in this phase. |
| `src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` | 2 FIX-01 characterization tests exercising createViewFile transform | VERIFIED | Describe block at line 1004 contains `DELETED + remote_size=null must be queueable (RED target)` and `DELETED + remote_size>0 is queueable (GREEN control)` — both fakeAsync, both subscribe to `viewService.files` and assert `file.isQueueable === true` after pushing a ModelFile with `state=DELETED`. |
| `src/angular/src/app/tests/unittests/pages/files/bulk-actions-bar.component.spec.ts` | 3 D-09 coverage tests asserting union counts + per-row dispatch | VERIFIED | Describe block at line 371 contains 3 `it(...)` blocks (All-DELETED, DELETED+DOWNLOADING, DELETED+DOWNLOADED+STOPPED). Each asserts all 5 `actionCounts.X` values AND per-click emit filtering. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Wave 1 RED target test | `createViewFile` isQueueable predicate | mockModelService push → `viewService.files` observable | WIRED | `view-file.service.spec.ts:1027-1034` pushes a ModelFile through the real `ViewFileService.createViewFile()` transform. Asserts on the emitted `ViewFile.isQueueable`. This test would fail if the service produced the flag incorrectly — the exact bug that existed before commit `46ecfff`. |
| Wave 2 fix | Wave 1 RED test green | Predicate restructured so DELETED skips `remoteSize > 0` gate | WIRED | Git diff e991b19..HEAD on `view-file.service.ts` shows exactly 20 lines changed (+10/-10) with two hunks (lines 348-351, 364-369). The `TOTAL: 599 SUCCESS` captured in `/tmp/76-04-full-suite.txt` demonstrates that RED target now green. |
| Wave 3 D-09 tests | `BulkActionsBarComponent.actionCounts` + 5 emit handlers | `setInputsAndDetectChanges` harness → ngOnChanges → `_recomputeCachedValues` | WIRED | Each D-09 test uses the existing harness (defined at bar spec lines 63-77) to set `visibleFiles` and `selectedFiles`, then reads `component.actionCounts` (the real getter, not a mock) and calls the real click handlers with spied emitters. The bar's full aggregation + dispatch path is exercised. |
| Option A relocation | 5 FIX-01 tests across 2 specs | Two describe blocks under distinct labels (`FIX-01 DELETED isQueueable regression` in service spec, `FIX-01 DELETED union regression (D-09 coverage)` in bar spec) | WIRED | Grep confirms both describe labels present. The split correctly isolates concerns: service spec asserts status→flag mapping (the bug site), bar spec asserts flag→action-set forwarding (the consumer contract). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `view-file.service.ts::createViewFile` | `isQueueable`, `isRemotelyDeletable` | Computed from `status`, `remoteSize`, `localSize` derived from real `ModelFile` input | Yes — pure function driven by the backend-sourced ModelFile fields normalized on lines 303-306 | FLOWING |
| `bulk-actions-bar.component.ts::actionCounts` | Per-action count derived from `_cachedSelectedViewFiles` | `_recomputeCachedValues()` filters `visibleFiles` by `selectedFiles` and inspects each ViewFile's eligibility flags | Yes — flags consumed come from the real ViewFile carried in `visibleFiles` | FLOWING |

The fix site is a pure predicate on inputs that the test suite proves are exercised end-to-end at both layers (service transform and bar aggregation). No hollow props, no empty sources.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full Angular suite passes | `cd src/angular && npm test -- --watch=false --browsers=ChromeHeadless` (captured as `/tmp/76-04-full-suite.txt`) | `TOTAL: 599 SUCCESS` | PASS |
| FIX-01 describe blocks present in expected files | `grep -c 'FIX-01' src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts` and same on bar spec | Service spec: 3 matches (comment + describe + withContext). Bar spec: 5 matches (comment + describe + 3 it-labels). | PASS |
| Production change is minimal (D-03 scope) | `git diff --name-only e991b19 HEAD -- 'src/angular/src/app/' | grep -v '\.spec\.ts$'` | `src/angular/src/app/services/files/view-file.service.ts` (single entry) | PASS |
| Visual/DOM freeze (D-06/D-07) | `git diff e991b19 HEAD -- bulk-actions-bar.component.html bulk-actions-bar.component.scss | wc -l` | `0` lines | PASS |
| Queue label count parity with baseline | `grep -c 'Queue' ... .html` vs `git show e991b19:... | grep -c 'Queue'` | Both return `2` | PASS |
| Commit `46ecfff` is the fix with expected scope | `git show --stat 46ecfff` | Touches only `view-file.service.ts` (+10/-10) and `76-02-SUMMARY.md` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FIX-01 | 76-01, 76-02, 76-03, 76-04 | When the multiselect bulk-actions bar shows for a selection that includes one or more deleted files, "Re-Queue from Remote" is available in the bar. For mixed selections, the bar shows the union of applicable actions across the selection, disabling individual actions only for rows where they do not apply. Regression from v1.1.0. | SATISFIED (unit-level) | All 4 ROADMAP success criteria PASS at the unit layer. REQUIREMENTS.md line 14 has FIX-01 marked `[x]`. Browser-level UX is deferred to Phase 77 (UAT-01) per D-11 — not a Phase 76 gap. Note: the status table at REQUIREMENTS.md line 78 still shows `FIX-01 | Phase 76 | Pending` — this is a bookkeeping inconsistency for orchestrator to reconcile before final sign-off but does not indicate missing implementation. |

No orphaned requirements — FIX-01 is the only requirement mapped to Phase 76 in both ROADMAP.md and REQUIREMENTS.md, and all 4 plans declare it in their `requirements:` frontmatter.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Playwright E2E covering FIX-01 browser-level behavior | Phase 77 | ROADMAP Phase 77 SC #4: "The FIX-01 union behavior is covered by at least one of the new selection specs." Phase 76 D-11 explicitly defers E2E to Phase 77. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | `grep -cE 'TODO|FIXME|XXX|HACK|PLACEHOLDER'` on `view-file.service.ts` returns 0. No stubs, no placeholders, no hardcoded empty returns in the modified predicate region. |

### Human Verification Required

See frontmatter `human_verification:` block. Three items:

1. **Dashboard smoke — single DELETED selection.** Open a dashboard with a DELETED file (e.g., navigate to errors → deleted sub-status, or find one in the "all" segment). Select the row via its checkbox. Confirm the bulk-actions bar appears with Queue and Delete Remote buttons enabled; Stop / Extract / Delete Local disabled. Clicking Queue should initiate a re-download from remote.

2. **Dashboard smoke — DELETED + DOWNLOADING mix.** Select at least one DELETED row and one DOWNLOADING row together. Confirm the bar shows Queue (1 eligible), Stop (1), Delete Remote (2); Extract and Delete Local disabled. Click Queue and confirm ONLY the DELETED row is queued; the DOWNLOADING row is unaffected. Click Stop and confirm only the DOWNLOADING row is stopped.

3. **Visual parity.** Compare the rendered bar against a pre-phase screenshot (or just quick eyeball): Queue button label stays literal "Queue", icons/spacing/color unchanged. No count badges, no per-row checkbox disabling, no new tooltips.

### Gaps Summary

No gaps at the unit-test layer. The code fix is surgical (10 lines added, 10 removed, one file), the test coverage is comprehensive (5 tests across 2 spec files spanning service-transform characterization and bar-consumer aggregation), the visual freeze is verified (byte-identical bulk-actions-bar HTML+SCSS since e991b19), and the full Angular suite is green (599/599).

Status is `human_needed` rather than `passed` solely because the original user symptom was a visual one ("the bar doesn't show at all") and the Phase 76 plan explicitly defers Playwright browser-level verification to Phase 77 per D-11. A 2-minute dashboard smoke check by a human closes that final feedback loop ahead of the E2E coverage landing later in the milestone.

### Minor Bookkeeping Observation

REQUIREMENTS.md has an internal inconsistency worth noting for the orchestrator:
- Line 14: `- [x] **FIX-01` (checkbox marked complete)
- Line 78: `| FIX-01 | Phase 76 | Pending |` (status table shows Pending)

And ROADMAP.md Phase 76 header is still `- [ ]` (unchecked). These are final-ship-step bookkeeping tasks the phase summary acknowledges in its Phase 77 Handoff Note. Not a verification gap — flagging so the orchestrator can reconcile during the phase-close commit.

---

_Verified: 2026-04-20T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
