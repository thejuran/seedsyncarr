---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 08
subsystem: angular-file-list
tags: [angular, ui, waiting-badge, confirm-modal, imp-02, r5, r6]
requires:
  - "119-06: bulk endpoint per-file error_code 428 + release_unverified (strict bool, queue only)"
  - "119-07: file JSON key hold_reason (sibling plan; not present in the backend at this plan's base)"
provides:
  - "ModelFile.hold_reason / ViewFile.holdReason plumbing"
  - "TransferRowComponent.isHeld / holdReasonLabel; 'Waiting' secondary badge with reason in meta line + badge title"
  - "Localization.Hold label map; Modal.RELEASE_UNVERIFIED_TITLE/MESSAGE"
  - "BulkCommandService.executeBulkAction(action, files, {releaseUnverified})"
  - "BulkActionDispatcher: 428 -> one confirm -> one-shot re-queue of exactly the 428 files"
affects:
  - src/angular file list (transfer-row), Queue bulk action
tech-stack:
  added: []
  patterns: ["optional DispatchOptions on BulkActionDispatcher._dispatch (onResult hook, requestOptions, quietOnConfirmationOnly)"]
key-files:
  created: []
  modified:
    - src/angular/src/app/common/localization.ts
    - src/angular/src/app/services/files/model-file.ts
    - src/angular/src/app/services/files/view-file.ts
    - src/angular/src/app/services/files/view-file.service.ts
    - src/angular/src/app/pages/files/transfer-row.component.ts
    - src/angular/src/app/pages/files/transfer-row.component.html
    - src/angular/src/app/services/files/bulk-action-dispatcher.service.ts
    - src/angular/src/app/services/server/bulk-command.service.ts
    - src/angular/src/app/tests/unittests/services/files/model-file.spec.ts
    - src/angular/src/app/tests/unittests/services/files/view-file.service.spec.ts
    - src/angular/src/app/tests/unittests/pages/files/transfer-row.component.spec.ts
    - src/angular/src/app/tests/unittests/services/files/bulk-action-dispatcher.service.spec.ts
    - src/angular/src/app/tests/unittests/services/server/bulk-command.service.spec.ts
decisions:
  - "When every failure in a queue response is a 428, the partial-failure toast is skipped and the confirm modal is shown instead; any non-428 failure keeps the normal partial toast"
  - "The release re-dispatch carries no onResult hook, so a 428 on the release attempt never prompts a second time (one confirm per user attempt, D-08)"
  - "Unknown hold codes display as the raw code (Angular-escaped interpolation), so a newer backend reason is still visible"
metrics:
  duration: "~25 min"
  completed: 2026-10-14
  tasks: 2
  files: 13
---

# Phase 119 Plan 08: Waiting badge and confirmed manual release in the file list Summary

Held files now show a secondary "Waiting" badge with their reason (Sonarr unavailable, Radarr unavailable, Ambiguous match, Still downloading, No matching queue entry) in the file meta line and as the badge tooltip. When a Queue request comes back with per-file 428s, the user gets one confirm with the verbatim D-08 text. On OK, exactly those files are re-queued once with `release_unverified: true`.

## Tasks

| Task | Name | Commits | Files |
| ---- | ---- | ------- | ----- |
| 1 | Hold plumbing + Waiting badge | 41cc7aa (RED), 8719d05 (GREEN) | model-file.ts, view-file.ts, view-file.service.ts, transfer-row.component.ts/.html, localization.ts + 3 specs |
| 2 | Confirmed one-shot manual release | 4736763 (RED), b7bb74b (GREEN) | bulk-action-dispatcher.service.ts, bulk-command.service.ts + 2 specs |

## Behavior

- `isHeld` is true only when the status is DEFAULT and `holdReason` is set. A stale reason on any other status (for example DOWNLOADING) is ignored. `isSkippedRemote` is still checked first.
- `BADGE_LABELS` and `BADGE_CLASSES` are unchanged. The diff touches neither table.
- `executeBulkAction` adds `release_unverified: true` to the body only when `options.releaseUnverified` is truthy. Without that flag the body is exactly `{action, files}`, so the existing body-equality specs still pass. `isTransientFailure` is unchanged, which keeps 428 non-transient.
- `dispatchQueue` passes an `onResult` hook to `_dispatch`. The hook runs after the result is handled, the `_inProgress` gate is released and the selection is processed. It collects the `!success && error_code === 428` files and asks once (title "Release unverified transfer", okBtn "Release", `btn btn-outline-danger`, body = verbatim message + the existing preview suffix). On OK it calls `_dispatch("queue", files, ..., {requestOptions: {releaseUnverified: true}})` a single time. On cancel nothing is sent. Stop, extract and delete never offer a release.

## Verification

- **Runner:** local Karma run with `npx ng test --watch=false --browsers=ChromeHeadless`, using `CHROME_BIN` pointed at the installed Google Chrome. Docker/`make run-tests-angular` was not used. CI `unittests-angular` is the authority.
- **RED observed:** Task 1 failed to compile (TS2353 `holdReason` not in `Partial<ViewFile>`, TS2339 `isHeld`/`holdReasonLabel`). Task 2 failed to compile (TS2554, expected 2 arguments but got 3).
- **GREEN observed:** after Task 1, `Executed 632 of 632 SUCCESS`. After Task 2, `TOTAL: 643 SUCCESS` (0 failures).
- `npm run lint` (eslint `--max-warnings 0`) is clean.
- `tsconfig.app.json` does not exist in this project. The type-check is the Angular compile that runs inside `ng test`, and it passed.
- **Acceptance greps:**

  | Check | Count | Required |
  | ----- | ----- | -------- |
  | `"Waiting"` in transfer-row.ts | 2 | >= 1 |
  | `BADGE_LABELS: Record` | 1 (unchanged) | 1 |
  | verbatim confirm text in localization.ts | 1 | 1 |
  | `hold_reason` in model-file.ts | 5 | >= 4 |
  | `holdReason` in view-file.ts | 3 | >= 3 |
  | `release_unverified` in bulk-command | 1 | 1 |
  | `releaseUnverified` in bulk-command | 2 | >= 2 |
  | `428` in dispatcher | 1 | >= 1 |
  | `RELEASE_UNVERIFIED_MESSAGE` in dispatcher | 1 | 1 |
  | `"Release"` in dispatcher | 1 | 1 |

- **e2e labels:** `grep -rn "Waiting" src/e2e` returns no matches, before and after. No e2e spec or seed-state LABEL table needs the new label, because no seed puts a file into a held state. No existing badge label was renamed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Spec file paths**
- **Found during:** Task 1
- **Issue:** The plan lists the specs next to their sources (for example `services/files/model-file.spec.ts`), but this project keeps them under `src/angular/src/app/tests/unittests/...`.
- **Fix:** Added the specs to the existing files under `tests/unittests/`.

**2. [Rule 1 - Test bug] Confirm-body assertion**
- **Found during:** Task 2 GREEN
- **Issue:** `not.toContain("C")` matched the "C" in "Completion".
- **Fix:** The test now asserts the exact body (`message + "\n\nB"`). The fix landed in commit b7bb74b.

**3. Additional specs (beyond the plan's list)**
- Specs added: the release attempt never prompts a second time, Stop never offers a release, and the toast is skipped or kept for the all-428 and mixed cases.
- The transfer-row spec also gained a describe that renders the production template, because the existing suite overrides the template and would not cover `.hold-reason` or the badge `title`.

## Assumption Drift (advisory)

- **Found during:** Task 1 context check
- **Planned:** The backend already sends `hold_reason` in the file JSON (contract described as "119-06/119-07").
- **Actual:** At this plan's base (5dae83d), `src/python` has no `hold_reason`. The key is expected from sibling plan 119-07, which runs in parallel.
- **Why it matters:** Until 119-07 lands, the Waiting badge never appears. The UI falls back cleanly (`hold_reason ?? null`).
- The 428 / `release_unverified` path depends only on 119-06, which is already merged.

## Known Stubs

None.

## Threat Flags

None. The only new outbound field is `release_unverified`, which is sent only after an explicit confirm, only for the 428 files, and only once (T-119-28). Hold text is rendered through Angular interpolation and `[attr.title]`, with no `innerHTML` (T-119-29).

## Self-Check: PASSED

- Commits 41cc7aa, 8719d05, 4736763 and b7bb74b are present in `git log`.
- All modified files exist. No STATE.md or ROADMAP.md changes.
