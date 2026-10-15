---
phase: 119-safety-follow-ups-and-1-7-5-release
plan: 05
subsystem: controller / webhook import credit
tags: [webhook, import-credit, days-of-hope, persist, imp-03, regression-red-first, pending-notice-lifecycle]
requires:
  - "119-03 lock order (reservation -> __model_lock -> __auto_delete_lock)"
provides:
  - "Controller._discard_pending_notices(root_name, cause) -> int (for 119-07 re-grab reset / root removal)"
  - "Controller persist_callback kwarg; Seedsyncarr._persist_controller_now"
  - "Arm-on-commit pass in __check_webhook_imports"
affects:
  - src/python/controller/controller.py
  - src/python/seedsyncarr.py
tech-stack:
  added: []
  patterns:
    - "Pending notice bound to resolved model path + per-root lifecycle generation, revalidated every cycle"
    - "Level-triggered arm-on-commit (covers restart)"
    - "Immediate persist via callback outside controller locks, serialized by a persist-file lock"
key-files:
  created:
    - src/python/tests/unittests/test_controller/test_import_credit.py
  modified:
    - src/python/controller/controller.py
    - src/python/seedsyncarr.py
    - src/python/tests/unittests/test_controller/test_controller.py
decisions:
  - "A notice is kept pending only while its root is a remote release in QUEUED/DOWNLOADING; any other non-committed root gets the existing 'no transfer evidence' drop"
  - "Persist callback fires on any persisted import change (credit, accept, arm-on-commit), not only early credits"
  - "USER is any QUEUE whose origin is not AUTO (Command defaults origin to USER)"
metrics:
  duration: "~40 min"
  completed: 2026-10-14
  tasks: 2
  files: 4
---

# Phase 119 Plan 05: IMP-03 Early Per-Episode Import Credit Summary

When Sonarr or Radarr imports an episode from a season pack that is still transferring, the import is now credited to that pack and saved to disk straight away. Before this change it was thrown away as "no transfer evidence". Credit never deletes anything by itself: the whole folder is only deleted after the pack finishes transferring and every video in it has been imported. Import notices that arrive before the file shows as complete are held, rechecked every cycle, and dropped if the root is re-queued, removed, changes path, becomes ambiguous or the notice expires.

## What was built

**controller.py**
- Module constants `_PENDING_NOTICE_MAX = 1000` and `_PENDING_NOTICE_TTL_SECS = 6 * 3600`.
- `_PendingNotice(NamedTuple)` with fields `root_name, matched_name, path, generation, inserted_at`.
- Constructor additions:
  - `persist_callback` kwarg.
  - `__pending_child_notices` (an OrderedDict keyed `(root, matched)`).
  - `__root_lifecycle_generation` (`defaultdict(int)`).
- `__check_webhook_imports`:
  - **Revalidation:** after Window 1, each pending notice goes through `_revalidate_pending_notice`. The checks run in this order: lifecycle generation (DEBUG), ambiguity (Phase 116 phrase), path gone (WARNING "no longer resolves", Phase 116 phrase), then TTL (WARNING "expired").
  - **Event list:** surviving pending notices come first, then fresh `WebhookManager.process` events, de-duplicated by key.
  - **Window 2, root not committed and no root-level evidence:**
    - If the root is not a remote QUEUED/DOWNLOADING release, the existing "no transfer evidence" warning is logged and the notice is dropped.
    - Otherwise a child-level notice is credited when its child is the unique non-dir descendant with that name, is DOWNLOADED, and has local == remote. That calls `add_imported_child` only and logs INFO "Credited early import ...".
    - Anything else is held as a pending notice.
  - **Branch boundaries:** the child-credit branch is lines 715-745. It contains no `downloaded_file_names.add(` or `imported_file_names.add(`; those are on lines 751 and 758, in the committed-root accept path.
  - **Arm on commit** (line 784): any root in `imported_children` that is also in `downloaded_file_names`, not in `imported_file_names`, and still in the model, gets marked imported and badged. It is then added to `accepted_roots`, which the existing after-lock block schedules for auto-delete. The INFO line reads "Import credit for '<root>' applied on commit".
  - **Persist callback** (line 806): called outside `__model_lock` when persist changed. Exceptions are logged by type name only and never raised.
- `_discard_pending_notices(root, cause)` drops the root's notices and always bumps its generation. It logs INFO "Discarded N pending import notice(s) ..." when something was dropped (DEBUG otherwise) and returns the count.
- `__process_commands` calls `_discard_pending_notices(command.filename, "user requeue")` on a successful non-AUTO QUEUE. This is line 1261, after `__command_processor.handle(` on line 1245 and inside the success path.
- Lock discipline: no new lock was added. Everything new runs on the controller thread, and the callback is invoked with no controller lock held.

**seedsyncarr.py**
- `self.__persist_lock = threading.Lock()` is created first in `__init__`, and `persist()` now holds it.
- New `_persist_controller_now()` writes only the controller persist, under the same lock.
- `Controller(..., persist_callback=self._persist_controller_now)`.

## RED evidence (commit 7a73d8b, before the fix)

```
FAILED TestEarlyChildCredit::test_arm_on_commit_without_further_webhook
FAILED TestEarlyChildCredit::test_child_notices_before_commit_are_credited_not_dropped
  AssertionError: 'Days.of.Hope.1975.DVDRip.x264-HANDJOB' not found in OrderedDict() : early child notices must be credited, not dropped
FAILED TestEarlyChildCredit::test_credit_alone_never_deletes
FAILED TestEarlyChildCredit::test_credit_persists_immediately_via_callback
  TypeError: Controller.__init__() got an unexpected keyword argument 'persist_callback'
FAILED TestEarlyChildCredit::test_credit_survives_persist_round_trip
FAILED TestEarlyChildCredit::test_restart_with_persisted_credit_arms_on_commit
FAILED TestEarlyChildCredit::test_root_commit_then_last_child_webhook_arms_and_deletes
FAILED TestEarlyCreditGuards::test_pending_notice_expires_with_warning
FAILED TestEarlyCreditGuards::test_pending_notice_reevaluated_when_child_becomes_downloaded
FAILED TestPendingNoticeLifecycle::test_discard_pending_notices_returns_count_and_bumps_generation
FAILED TestPendingNoticeLifecycle::test_pending_notice_discarded_on_user_requeue_cannot_credit_new_attempt
  AssertionError: [] is not true : USER requeue must discard the pending notice
FAILED TestPendingNoticeLifecycle::test_pending_notice_discarded_when_resolved_path_changes
FAILED TestPendingNoticeLifecycle::test_pending_notice_discarded_when_root_leaves_model
FAILED TestPendingNoticeLifecycle::test_pending_notice_revalidated_against_current_model_rejects_new_ambiguity
FAILED TestPendingNoticeLifecycle::test_pending_notice_with_stale_generation_never_credits
15 failed, 2 passed
```

The two tests that passed are the preservation guards: `test_foreign_local_only_dir_never_credited` and `test_ambiguous_child_still_rejected`. Both required tests (core replay and USER requeue) fail with AssertionError.

## GREEN evidence (commits 9309bab, 2e53cbb)

```
$ poetry run pytest test_import_credit.py test_import_ambiguity.py test_auto_delete.py test_auto_delete_rearm.py \
    test_controller_unit.py test_webhook_manager.py test_controller.py -q -p no:cacheprovider
373 passed, 12 warnings in 1.21s
$ poetry run ruff check .     (src/python, whole tree)
All checks passed!
```

Grep gates, as run:

| Gate | Result |
|------|--------|
| "Credited early import" | 1 |
| `_PENDING_NOTICE_MAX = 1000` | 1 |
| `_PENDING_NOTICE_TTL_SECS` | 4 |
| "applied on commit" | 1 |
| `class _PendingNotice` | 1 |
| `def _discard_pending_notices` / `def _revalidate_pending_notice` | 2 |
| `_discard_pending_notices(` | 2 |
| "Discarded" | 1 |
| "no import credit or automatic cleanup authorized" | 2 |
| `def test_` in test_import_credit.py | 17 |
| `__persist_lock` in seedsyncarr.py | 3 |
| `persist_callback` in seedsyncarr.py | 1 |

Command_processor.py is unchanged.

**Full unit suite (not fully run):** `pytest tests/unittests` hangs in `test_controller/test_extract/test_extract_process.py` on this macOS host. That file is about multiprocessing extract and is unrelated. With it excluded the result was **1638 passed, 15 failed, 3 errors**. Every failure is environment-bound and in a file this plan does not touch:
- `test_ssh/test_sshcp.py` needs ssh to localhost.
- `test_controller/test_scan/test_scanner_process.py` uses macOS multiprocessing.
- `test_system/test_scanner.py::test_scan_file_with_latin_chars` depends on APFS name normalization.

CI (Linux) has not been observed for this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test bug] `test_credit_alone_never_deletes` scenario corrected**
- **Found during:** Task 2 (GREEN run)
- **Issue:** With all four parts DOWNLOADED, the root's local size equalled its remote size. The existing evidence rule (a complete local copy of a remote release) therefore legitimately committed the root and armed the Timer, so the test scenario was not "still transferring".
- **Fix:** Added an in-flight subtitle file so the root really is still short of its remote size. `_transferring_pack` now adds extra children's sizes to the root totals. The test still fails on the pre-fix code, because no credit is recorded.
- **Files modified:** test_import_credit.py
- **Commit:** 9309bab

**2. [Rule 1 - Test vs. D-14] USER-requeue test asserts coverage, not a direct Timer fire on an un-credited root**
- **Found during:** Task 1
- **Issue:** The plan asked to fire `__execute_auto_delete(root)` after the new attempt commits with no imports and assert no delete. With no `imported_children` entry, D-14 grandfathers the root and the Timer would delete it on HEAD and after the fix alike. That is a property of a Timer that is never armed in that state, not of the pending notice.
- **Fix:** The test first asserts that no Timer is armed and the root is not imported. Then the arr imports parts 1, 3 and 4 of the new copy, and the test fires the Timer and asserts no delete. This proves the stale part-2 notice did not satisfy coverage, which is the threat in T-119-50.
- **Commit:** 7a73d8b

**3. [Rule 3 - Blocking] test_controller.py `__new__` fixture**
- **Found during:** Task 2
- **Issue:** `TestCheckWebhookImportsSanitization._make_controller` builds a Controller via `__new__` and lists every private attribute `__check_webhook_imports` reads. The new pending-notice attributes were missing, which raised AttributeError.
- **Fix:** Added `__pending_child_notices`, `__root_lifecycle_generation` and `__persist_callback` to the fixture.
- **Commit:** 9309bab

**4. [Rule 1] Phase 116 phrase split across string fragments**
- **Found during:** Task 2 grep gate
- **Issue:** The ambiguity WARNING split "no import credit or automatic cleanup authorized" across two string literals.
- **Fix:** Moved the phrase onto one source line. The log output is unchanged.
- **Commit:** 2e53cbb

## Assumption Drift (advisory)

- **Found during:** Task 2
- **Planned:** "Otherwise keep/insert the pending notice" for any root that is not committed and has a remote size.
- **Actual:** A notice is kept only while the root is QUEUED or DOWNLOADING. A root in DEFAULT, STOPPED and so on gets the existing "no transfer evidence" drop.
- **Why:** `test_auto_delete.py::test_import_refused_for_remote_only_file_not_downloaded` and the incident-2026-08-21 contract expect an immediate refusal there. Holding such notices for 6 h would only end in an "expired" WARNING.

## Known Stubs

None.

## Threat Flags

None. The new persist-callback write path is the T-119-19 mitigation already in the plan. `to_str()` can still race a Timer-thread `imported_children.pop`, as the 30 s main-thread save already could. The callback catches and logs that, and the periodic save retries.

## Self-Check: PASSED
- FOUND: src/python/tests/unittests/test_controller/test_import_credit.py
- FOUND: commits 7a73d8b (test), 9309bab (fix), 2e53cbb (fix). The `test(119-05)` commit precedes `fix(119-05)`.
