---
phase: 119-safety-follow-ups-and-1-7-5-release
verified: 2026-10-15T16:23:52Z
status: human_needed
score: 7/7 roadmap success criteria verified (1 criterion's NAS-production-deploy clause formally deferred to Phase 119.1)
has_blocking_gaps: false
overrides_applied: 0
human_verification:
  - test: "Open the Angular file list in a browser with a file held (hold_reason set, e.g. sonarr_unavailable) and visually confirm the secondary 'Waiting' badge, its tooltip, and the file-meta reason text render as intended."
    expected: "A DEFAULT file with a hold reason shows a visually correct secondary-styled 'Waiting' badge; hovering shows the reason label (e.g. 'Sonarr unavailable') as the title; the same label appears in the file-meta line."
    why_human: "Visual appearance/styling cannot be confirmed by grep or unit tests. 119-08-SUMMARY.md explicitly notes 'grep -rn \"Waiting\" src/e2e returns no matches' and no e2e seed puts a file into a held state, so no automated browser-level check exists. The NAS smoke test (119-REL03-EVIDENCE.md step 7) confirmed the backend JSON carries hold_reason and the shipped JS bundle contains the 'Waiting'/'Sonarr unavailable' strings, but explicitly states 'the badge was not looked at in a browser.'"
  - test: "Trigger a Queue action on a 428-held file through the Angular UI (not the raw API) and confirm the confirm-modal shows the exact text 'Completion could not be verified. Transfer and release this item anyway?', that clicking OK re-queues exactly that file with release_unverified, and that clicking Cancel sends nothing."
    expected: "Modal appears with verbatim D-08 text plus the file preview; OK re-dispatches once; Cancel sends no request."
    why_human: "The 119-10 NAS smoke test exercised this path via raw HTTP POST to the bulk command endpoint, not through the Angular confirm-modal UI. Unit tests (bulk-action-dispatcher.service.spec.ts) assert the dispatcher logic in isolation but do not confirm the modal renders and behaves correctly end-to-end in a browser."
deferred:
  - truth: "The tested 1.7.5 image is deployed to the NAS production container and verified there (ROADMAP Phase 119 success criterion 7, NAS-production-deploy clause)."
    addressed_in: "Phase 119.1"
    evidence: "ROADMAP.md Phase 119.1 explicitly states requirements 'SEC-01, REL-03 (NAS-verification portion carried from Phase 119), REL-04' and scope item 3: 'Deploy 1.7.6 to the NAS production container by digest (supersedes 119-11)'. Owner decision recorded verbatim in 119-REL03-EVIDENCE.md 'Deploy gate (Plan 119-10 Task 3): HOLD' and 119-11-SUMMARY.md: plan superseded, not executed, owner HOLD because of a pre-existing (since v1.0.0) secrets-in-startup-log finding unrelated to 1.7.5's own changes."
---

# Phase 119: Safety Follow-ups and 1.7.5 Release Verification Report

**Phase Goal:** Deliver the contained safety follow-ups, the two Done-group incident fixes, and the packaging repair as 1.7.5 before the Reliability milestone begins.
**Verified:** 2026-10-15T16:23:52Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, merged with PLAN must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | XFER-06: a delayed prompt from a timed-out command cannot turn the next status into a trusted empty job list; normal status resumes after verified sentinel resync | VERIFIED | `src/python/lftp/lftp.py`: `__synced` flag, `SEEDSYNCARR-SYNC-` sentinel, guard raising `LftpError("lftp command stream not synchronized")` at top of `__run_command`; `status()` catches it and returns `None`. `test_lftp_resync.py` (228 lines, 6 tests) re-run live: **6 passed**. |
| 2 | DEL-01: a pending auto-delete Timer cannot delete a submitted-but-unobserved transfer; defers and safely retries once status is observed, with existing guards still enforced | VERIFIED | `controller/root_reservation.py` (`RootReservations`/`RootReservation`), `controller.py` `__execute_auto_delete` defer reason `"transfer submitted, awaiting lftp status"`, `lftp_manager.py` `__submitted_lock`. Re-ran `test_auto_delete_rearm.py`, `test_root_reservation.py`, `test_file_operation_manager.py`, `test_lftp_manager.py` as part of the full suite below — all pass. |
| 3 | REL-02: built distributions have valid member paths, pass packaging checks, install cleanly, and publish to PyPI; Dependabot #93 addressed | VERIFIED | Rebuilt the package live in a scratch venv: `PACKAGE_OK`, wheel members=85, sdist members=84, no `./`-prefixed or forbidden members. `node scripts/verify-release-metadata.mjs 1.7.5` passes. PyPI `pypi.org/pypi/seedsyncarr/json` confirms `info.version == "1.7.5"` and `1.7.5` present in `releases`. `gh api .../dependabot/alerts/93` → `fixed`; `gh api .../dependabot/alerts?state=open` → none open. |
| 4 | IMP-01/IMP-02: an incomplete/unverified copy is never importable; completion requires reliable arr-queue evidence, not just stability; holds are visible and a one-shot manual release exists | VERIFIED | `arr_queue.py`/`completion_gate.py` exist with the documented non-blocking worker/poll contract, `MAX_RESPONSE_BYTES`/`FETCH_DEADLINE_SECS`; `lftp_manager.py`/`scan_manager.py` force `use_temp_file=True`; `command_processor.py` re-checks the gate inside the reservation (428 for USER, quiet skip for AUTO, `release_unverified` one-shot, `invalidate()` on submit); `model/file.py` `hold_reason` → `model_builder.set_hold_reasons` → `model_pipeline.py` → `serialize_model.py` `"hold_reason"` key, full chain traced to Angular (`model-file.ts` → `view-file.service.ts holdReason` → `transfer-row.component.ts isHeld`/"Waiting" badge). Live-ran `test_arr_queue.py`+`test_completion_gate.py`+`test_import_credit.py`: **112 passed**. NAS smoke (119-REL03-EVIDENCE.md step 7) shows a live hold (`hold_reason: "sonarr_unavailable"`), a 428, and a successful manual release producing `downloaded`/`hold_reason: null`. |
| 5 | IMP-03: an import notice for a uniquely identified, fully transferred episode is credited and persisted while siblings transfer, survives restart, and alone never authorizes whole-folder deletion | VERIFIED | `controller.py` `_PendingNotice`, `add_imported_child` child-credit branch, `_discard_pending_notices`, arm-on-commit pass; `seedsyncarr.py` `persist_callback`/`__persist_lock`. Live-ran the Days-of-Hope-replay test (`test_root_commit_then_last_child_webhook_arms_and_deletes`) and `test_credit_alone_never_deletes`: **2 passed**. |
| 6 | Targeted regressions fail before fix / pass after; full Python suite + whole-tree Ruff + release CI gates pass; release image passes startup/transfer/import/cleanup/persistence/restart smoke | VERIFIED | Independently re-ran the full host suite: **1685 passed, 0 failed, 19 subtests passed** — exact match to 119-REL03-EVIDENCE.md's recorded GREEN. `ruff check src/python/` (0.15.9): **All checks passed**. Angular: `ng test --browsers=ChromeHeadless` → **643/643 SUCCESS**; `npm run lint` clean; e2e `tsc --noEmit` exit 0. Independently fetched CI run `38729554457` (tag push) via `gh run view`: all 9 gate jobs + 5 publish jobs **success** (1 skipped as expected for a tag ref). Independently confirmed the two documented release-gate catches are real via `gh api code-scanning/alerts?ref=refs/pull/127/head`: alerts #6 and #7 (`py/weak-sensitive-data-hashing`) both `state: fixed`; current `arr_queue.py` contains no `hashlib`/`hmac`/`sha256`. Smoke evidence (119-REL03-EVIDENCE.md) documents all 8 steps PASS with real command transcripts. |
| 7 | 1.7.5 ships through Docker/GitHub/PyPI and the tested image is verified on the NAS (incl. scan recovery), before Reliability begins | VERIFIED for Docker/GitHub/PyPI + NAS-scratch verification; NAS **production**-deploy clause formally DEFERRED to Phase 119.1 | GHCR digest `sha256:b061d95a…` confirmed via registry API and `docker inspect` on NAS; GitHub Release `v1.7.5` confirmed via `gh release view` (`isDraft:false`); PyPI confirmed live. NAS scratch-setup smoke (not production) ran the exact published digest and passed all 8 checks incl. no startup-scanner-error / successful scan. Independently re-checked NAS via `ssh nas docker inspect`: production `seedsyncarr` is `:1.7.4@sha256:682d129d…` running, `wud` exited — exactly matching the evidence file's recorded HOLD state. Per explicit owner decision (recorded verbatim in 119-REL03-EVIDENCE.md and 119-11-SUMMARY.md) and ROADMAP.md Phase 119.1 ("REL-03 (NAS-verification portion carried from Phase 119)"), the production-deploy portion is formally transferred, not a Phase 119 gap. |

**Score:** 7/7 roadmap success criteria verified at the Phase 119 scope boundary (criterion 7's production-NAS-deploy clause explicitly carried forward to Phase 119.1 by owner decision, not a gap).

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | NAS production deploy + production verification of the tested image | Phase 119.1 | ROADMAP.md Phase 119.1 scope item 3 and requirements line; 119-REL03-EVIDENCE.md "Deploy gate (Plan 119-10 Task 3): HOLD"; 119-11-SUMMARY.md (plan superseded, not executed) |

### Required Artifacts (representative; full list in each PLAN's `must_haves.artifacts`)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/python/lftp/lftp.py` | `__synced` flag + sentinel resync | VERIFIED | Present, wired, test-covered (6/6 live) |
| `src/python/controller/root_reservation.py` | Per-root reservation primitive | VERIFIED | `RootReservation`/`RootReservations` present, used by controller/command_processor/file_operation_manager |
| `src/python/controller/arr_queue.py` | Non-blocking arr queue client | VERIFIED | `ArrQueueClient`, `MAX_RESPONSE_BYTES`, `FETCH_DEADLINE_SECS` present; no hashing of API key (post-CodeQL-fix) |
| `src/python/controller/completion_gate.py` | Verdict/hold engine | VERIFIED | `CompletionGate.evaluate/verdict/invalidate` present and wired into `controller.py`/`command_processor.py`/`auto_queue.py` |
| `src/python/model/file.py` | `hold_reason` property | VERIFIED | Present, part of `__eq__`, DEFAULT-root-only application confirmed in `model_builder.py` |
| `src/python/web/serialize/serialize_model.py` | `"hold_reason"` JSON key | VERIFIED | Present; confirmed present in live NAS smoke JSON payloads |
| `src/angular/.../transfer-row.component.ts` | "Waiting" badge | VERIFIED (code) / unverified (visual) | Badge logic present and unit-tested (643/643 Angular tests pass); not visually confirmed in a browser — see Human Verification |
| `scripts/verify-python-package.py` + CI job | Packaging member-path checker gating publish | VERIFIED | Script re-run live (`PACKAGE_OK`); CI wiring confirmed (`needs:` lists `verify-python-package` on `build-docker-image` and `publish-pypi`) |
| `.planning/.../119-REL03-EVIDENCE.md` | REL-03 gate evidence | VERIFIED | 933-line evidence file with real command transcripts; cross-checked against live re-runs, GitHub API, and NAS SSH — all consistent |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `Lftp.__run_command` | `Lftp.__resync` | unsynced guard raising `LftpError` | WIRED |
| `Controller.__execute_auto_delete` | `RootReservations.acquire` / `LftpManager.submitted_unobserved_file_names()` | guard before `__model_lock`, defer on submitted-unobserved | WIRED |
| `AutoQueue.process` | `Controller.evaluate_completion` → `CompletionGate.evaluate` | one batched call per cycle before cooldown stamp | WIRED |
| `CommandProcessor._handle_queue` | `CompletionGate.verdict` / `.invalidate` | inside `with reservation:`, before/after `lftp.queue` | WIRED |
| `ModelPipeline.feed_model_builder` | `ModelBuilder.set_hold_reasons` | `self._completion_gate.holds` | WIRED |
| `ModelPipeline` lifecycle hooks | `Controller._on_root_lifecycle_reset` → gate invalidate + pending-notice discard | `on_lifecycle_reset=` kwarg | WIRED |
| `SerializeModel` | `model_file.hold_reason` | `json_dict["hold_reason"]` | WIRED |
| `view-file.service.ts` | `model-file.ts hold_reason` | `holdReason: modelFile.hold_reason ?? null` | WIRED |
| `transfer-row.component.ts` | `holdReason` | `isHeld` getter, "Waiting" badge | WIRED (code); visual not confirmed |
| `bulk-action-dispatcher.service.ts` | `bulk-command.service.ts` | 428 collection → confirm → `{releaseUnverified: true}` re-dispatch | WIRED |
| `.github/workflows/ci.yml publish-pypi` / `build-docker-image` | `verify-python-package` job | `needs:` list | WIRED |
| `git tag v1.7.5` | GHCR / GitHub Release / PyPI | tag-push CI (`38729554457`, success) | WIRED, independently confirmed live |

### Data-Flow Trace (Level 4): Completion-gate hold reason

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `transfer-row.component.ts` | `holdReason` | `ModelFile.hold_reason` (Python) → `completion_gate.holds` (live arr queue evidence, not static) → SSE → `model-file.ts` → `view-file.ts` | Yes — confirmed non-static via live NAS smoke: `hold_reason` transitioned `null → "sonarr_unavailable" → null` across real Sonarr-unreachable / manual-release / disable-Sonarr steps | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| XFER-06 resync regression | `pytest test_lftp_resync.py` | 6 passed | PASS |
| DEL-01 + reservation regression | included in full-suite run below | 1685 passed overall | PASS |
| IMP-01/02 arr-queue/completion-gate/import-credit | `pytest test_arr_queue.py test_completion_gate.py test_import_credit.py` | 112 passed, 19 subtests passed | PASS |
| Obsession replay (IMP-01/02) | `pytest test_auto_queue.py -k obsession` | 2 passed | PASS |
| Days-of-Hope replay (IMP-03) | `pytest test_import_credit.py -k "test_root_commit_then_last_child_webhook_arms_and_deletes or test_credit_alone_never_deletes"` | 2 passed | PASS |
| Full host suite (single run, matches documented host exclusions) | `pytest tests/unittests --ignore=... (4 files)` | 1685 passed, 0 failed, 19 subtests passed | PASS |
| Whole-tree Ruff | `ruff check src/python/` (0.15.9) | All checks passed | PASS |
| Packaging | fresh `python -m build` + `verify-python-package.py` | PACKAGE_OK, 85/84 members, 0 forbidden | PASS |
| Release metadata | `node scripts/verify-release-metadata.mjs 1.7.5` | All 6 checks pass | PASS |
| Angular unit tests | `ng test --browsers=ChromeHeadless` | 643/643 SUCCESS | PASS |
| Angular lint | `npm run lint` | clean | PASS |
| e2e type-check | `tsc --noEmit` | exit 0 | PASS |
| Tag CI (live) | `gh run view 38729554457` | 9 gate + 5 publish jobs success, 1 skipped (expected) | PASS |
| PyPI publish (live) | `pypi.org/pypi/seedsyncarr/json` | version 1.7.5 present | PASS |
| GitHub Release (live) | `gh release view v1.7.5` | isDraft:false, isPrerelease:false | PASS |
| Dependabot #93 (live) | `gh api dependabot/alerts/93` | state: fixed; 0 open alerts repo-wide | PASS |
| CodeQL catches claimed in SUMMARY (live) | `gh api code-scanning/alerts?ref=refs/pull/127/head` | alerts #6, #7 `py/weak-sensitive-data-hashing`, both `state: fixed` | PASS |
| NAS production state (live, read-only) | `ssh nas docker inspect seedsyncarr / wud` | prod `:1.7.4` running, wud exited — matches evidence | PASS (confirms documented HOLD, not a deploy) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention or explicit probe declarations found in this phase's PLAN/SUMMARY files; the phase's verification mechanism is its pytest/Angular/Ruff/packaging/CI/NAS-smoke gates, all independently re-run above. Step 7c: SKIPPED (no probe scripts declared or found).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| XFER-06 | 119-01 | LFTP resync after status timeout | SATISFIED | Code + live test re-run (above) |
| DEL-01 | 119-03 | Auto-delete submitted-unobserved guard + root reservation | SATISFIED | Code + full-suite re-run |
| IMP-01 | 119-06, 119-08, 119-12 | Incomplete-copy never importable (forced temp files) | SATISFIED | Code + NAS smoke step 2 (`.lftp` rename observed) |
| IMP-02 | 119-04, 119-06, 119-07, 119-08, 119-12 | Arr-queue-based completion gate, hold visibility, manual release | SATISFIED | Code, full chain traced, NAS smoke step 7 live hold/428/release |
| IMP-03 | 119-05 | Early per-episode import credit, persisted, restart-safe | SATISFIED | Code + live Days-of-Hope-replay test re-run |
| REL-02 | 119-02, 119-09, 119-10 | Packaging repair, PyPI publish | SATISFIED | Live rebuild + live PyPI check |
| REL-03 | 119-09, 119-10, 119-11(superseded) | Release through Docker/GitHub/PyPI; NAS verification | SATISFIED for Docker/GitHub/PyPI + NAS-scratch; NAS-**production** clause DEFERRED to 119.1 (see Deferred Items) | Live CI run check, live GHCR/PyPI/GitHub-release check, live NAS SSH check |

**Orphaned requirements check:** `.planning/REQUIREMENTS.md` traceability table maps exactly XFER-06, DEL-01, IMP-01, IMP-02, IMP-03, REL-02, REL-03 to Phase 119 — all seven appear in at least one Phase 119 PLAN's `requirements:` frontmatter field (confirmed by reading all 12 PLAN files). No orphaned requirements.

**Documentation inconsistency (non-blocking, informational):** `.planning/REQUIREMENTS.md`'s checkbox list and its own Traceability table still show `Pending` / unchecked for XFER-06, DEL-01, IMP-01, IMP-02, IMP-03 and (correctly, for a different reason) REL-03, even though the underlying code and tests for the first five are implemented, wired, and passing as verified above. Only REL-02 is checked. This looks like requirements-doc bookkeeping that was not updated after each plan closed, not an implementation gap — recommend updating the checkboxes/traceability status alongside closing this phase.

### Anti-Patterns Found

None. Scanned every file touched by this phase's 12 plans (Python controller/model/web/lftp modules, Angular file-list/settings/localization files, e2e seed fixture, CI workflow, packaging script, docs) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and "not yet implemented"/"coming soon" phrasing: zero matches.

### Human Verification Required

### 1. "Waiting" badge visual rendering

**Test:** Hold a file (e.g., enable Sonarr with an unreachable URL and queue a new release) and open the Angular file list in a browser.
**Expected:** The file shows a secondary-styled "Waiting" badge; hovering shows the reason ("Sonarr unavailable", etc.) as a tooltip; the same reason text appears in the file-meta line.
**Why human:** Visual styling/rendering cannot be confirmed from source or unit tests alone. 119-08-SUMMARY.md explicitly records this was never checked in a browser, and no e2e spec seeds a held file.

### 2. Manual-release confirm modal, end-to-end in the UI

**Test:** With a held file visible in the Angular UI, click Queue and confirm the resulting modal.
**Expected:** Modal text reads exactly "Completion could not be verified. Transfer and release this item anyway?" plus the file preview; OK re-queues once with the release flag; Cancel sends nothing.
**Why human:** The NAS smoke test exercised the underlying API directly (raw HTTP), not the Angular modal; unit tests cover the dispatcher logic in isolation, not the rendered modal interaction.

### Gaps Summary

No blocking gaps. All seven ROADMAP success criteria for Phase 119 are backed by code that exists, is wired end-to-end (including a traced data-flow for the hold-visibility feature), and is independently re-verified here via live test runs, live CI/GitHub/PyPI API calls, and a live read-only NAS check — all of which matched the SUMMARY/evidence claims exactly (1685/1685 tests, 643/643 Angular tests, PACKAGE_OK, CI green, PyPI live, Dependabot alert fixed, CodeQL alerts fixed, NAS state matching the recorded HOLD).

The only two open items are (a) a visual/UI check of the new "Waiting" badge and confirm-modal flow, which is inherently human-only and was explicitly flagged as unverified in the phase's own evidence, and (b) the NAS **production** deploy, which is not a gap — it was deliberately and explicitly deferred to Phase 119.1 by owner decision after the 1.7.5 smoke test surfaced a pre-existing (since v1.0.0), out-of-scope secrets-in-startup-log issue unrelated to any Phase 119 change. That deferral is tracked in ROADMAP.md, STATE.md, and 119-REL03-EVIDENCE.md and should not be reopened as a Phase 119 gap.

---

_Verified: 2026-10-15T16:23:52Z_
_Verifier: Claude (bm-verifier)_

## Extraction/import half — completed by Phase 122 (2026-10-23)

The browser half of this verification passed 2026-10-18 (`119-HUMAN-UAT.md`). The
extraction/import/auto-delete half — left open by this report — is now complete: Phase 122
ran all six required live-acceptance scenarios (D-06(a)-(e) import/auto-delete, D-07
extraction staging and auto-delete re-arm) against the sandbox `seedsyncarr-test` on the
build that ships as 1.8.0, plus an independent repeat of the D-06(c) deferral/revalidation
race on a second root. Full evidence, log excerpts, timestamps and verdicts:
`.planning/phases/122-safety-acceptance-and-logging-fixes/122-SAFE01-EVIDENCE.md`.

**Verdict: SAFE-01 PASSED** (all six scenarios PASS; see the evidence file's "SAFE-01
verdict" table). Production `seedsyncarr` was never touched by any Phase 122 live check; the
sandbox was restored to its original 1.7.6 pin and independently re-verified after the last
check.
