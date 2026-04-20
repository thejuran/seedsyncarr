# Phase 76: Multiselect Bulk-Bar Action Union - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 76-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 76-multiselect-bulk-bar-action-union
**Areas discussed:** Repro case (root-cause discovery), "Re-Queue from Remote" labeling, Union + disable semantics

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Repro case | What is the actual visible symptom \u2014 bar hidden vs. buttons disabled vs. dispatch no-op? | ✓ |
| Union + disable semantics | Is count-based disable the right contract, or does the spec require per-row / badge behaviors? | (implicit) ✓ |
| Per-row dispatch UX | Should non-applicable rows stay selected after success? Partial-toast wording? | |
| Unit test matrix | Which mixed selections are "representative" per SC #4? | (covered implicitly) |

**User's choice:** "Repro case (Recommended)". Union + disable semantics and test matrix discussion folded in later.

---

## Repro Case

### Q1: Symptom

| Option | Description | Selected |
|--------|-------------|----------|
| Bar doesn't show at all | The whole bar stays hidden for deleted-file selections. | ✓ |
| Bar shows, Queue disabled | Bar appears, but Queue is greyed out for deleted selections. | |
| Bar shows, Queue enabled, nothing happens | Click fires but backend or dispatch is a no-op. | |
| Not sure \u2014 need to repro | Filed off report/memory, needs live verification. | |

**User's choice:** "Bar doesn't show at all."

### Q2: Selection composition

| Option | Description | Selected |
|--------|-------------|----------|
| Both \u2014 alone and mixed | Single-deleted AND mixed selections both fail. | ✓ |
| Only mixed selections | Alone works, mixed fails. | |
| Only all-deleted selections | 2+ deleted together hits the bug. | |
| Don't know yet | Will repro during research / planning. | |

**User's choice:** "Both \u2014 alone and mixed."

**Notes:** Claude's static code analysis contradicts the reported symptom:
- `BulkActionsBarComponent.hasSelection` is purely `selectedFiles.size > 0`.
- `ViewFile.isQueueable` includes `DELETED` when `remoteSize > 0`.
- `FileSelectionService` has no status-based filter.

This tension is the reason D-01 mandates a characterization unit test as the
first planner task \u2014 the bug's root cause is not visible from code read alone.
Candidate hypotheses are listed in CONTEXT.md D-02.

---

## Repro Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Bug-hunt as part of plan | Planner writes a failing unit test first; fix follows from red-green. | ✓ (Recommended) |
| I'll repro live first | User reproduces symptom with screenshot + console state before planning. | |
| Pair: write a probe script | Planner writes a Playwright/unit probe enumerating (status \u00d7 remoteSize \u00d7 localSize). | |

**User's choice:** "Bug-hunt as part of plan (Recommended)."

**Notes:** Accepted as D-01. Planner owns the characterization task.

---

## Label

| Option | Description | Selected |
|--------|-------------|----------|
| Existing Queue, no relabel | Keep Queue as-is; "Re-Queue from Remote" is descriptive shorthand only. | ✓ (Recommended) |
| Dynamic label | Switch label to "Re-Queue" when selection is all-DELETED. | |
| Second button | Add a separate "Re-Queue from Remote" button. | |

**User's choice:** "Existing Queue, no relabel (Recommended)."

**Notes:** Locks D-06 and D-07 \u2014 no UI string, tooltip, or button count changes.

---

## Union Spec

| Option | Description | Selected |
|--------|-------------|----------|
| Yes \u2014 count === 0 is fine | Current contract (button enabled if \u22651 row eligible; dispatch filters) stands. | ✓ (Recommended) |
| Add per-selection count badges | "(N/M)" badges on each button. | |
| Per-row disabled states on checkboxes | Grey out checkboxes when no action applies. | |

**User's choice:** "Yes \u2014 count === 0 is fine (Recommended)."

**Notes:** Locks D-04 and D-05. The contract is correct on paper; phase 76's
job is to find and fix whatever is actually breaking it in practice.

---

## Final Check

| Option | Description | Selected |
|--------|-------------|----------|
| Write CONTEXT.md now | Decisions are enough; proceed to create phase dir and CONTEXT.md. | ✓ (Recommended) |
| Test matrix specifics | Lock exact mixed cases before planning. | |
| Dispatch UX edge | Decide partial-success toast wording + selection-preservation policy now. | |

**User's choice:** "Write CONTEXT.md now (Recommended)."

---

## Claude's Discretion

- Exact root cause of the bar-doesn't-show symptom (see CONTEXT.md D-02 candidate list).
- Fix site: `BulkActionsBarComponent`, `ViewFileService.createViewFile()`, `FileSelectionService`, or `TransferTable` wiring.
- Whether `isQueueable`/`isRemotelyDeletable` edge cases for DELETED rows need adjustment.
- Test file and test name conventions (match existing ~400-line `bulk-actions-bar.component.spec.ts` style).
- Whether to add a 4th mixed-selection case beyond the three required by D-09.

## Deferred Ideas

- Per-action count badges on buttons.
- Dynamic label swap "Queue" \u2194 "Re-Queue from Remote".
- Row-checkbox disabling for no-applicable-action rows.
- New E2E specs (\u2192 Phase 77 / UAT-01).
- Refactor `_recomputeCachedValues` to signals (off-scope).
- Any backend/`BulkCommandService` changes (not required).
