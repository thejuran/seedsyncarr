import threading
from unittest.mock import MagicMock

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile, ModelError
from tests.unittests.test_controller.base import BaseControllerTestCase


class BaseAutoDeleteTestCase(BaseControllerTestCase):
    """Extends BaseControllerTestCase with auto-delete defaults and timer cleanup."""

    def setUp(self):
        super().setUp()
        self.mock_context.config.autodelete.enabled = True
        self.mock_context.config.autodelete.dry_run = False
        self.mock_context.config.autodelete.delay_seconds = 10
        # Re-create controller with auto-delete enabled
        self.controller = Controller(
            context=self.mock_context,
            persist=self.persist,
            webhook_manager=self.mock_webhook_manager,
        )

    def tearDown(self):
        # Cancel pending timers before stopping patches
        for timer in list(self.controller._Controller__pending_auto_deletes.values()):
            timer.cancel()
        self.controller._Controller__pending_auto_deletes.clear()
        super().tearDown()


class TestAutoDeleteScheduling(BaseAutoDeleteTestCase):
    """Test auto-delete scheduling from __schedule_auto_delete."""

    def test_pending_auto_deletes_initialized_empty(self):
        """Verify __pending_auto_deletes dict exists and starts empty."""
        self.assertEqual({}, self.controller._Controller__pending_auto_deletes)

    def test_schedule_creates_timer(self):
        """Verify scheduling creates a timer entry."""
        self.controller._Controller__schedule_auto_delete("test_file.mkv")
        self.assertIn("test_file.mkv", self.controller._Controller__pending_auto_deletes)
        timer = self.controller._Controller__pending_auto_deletes["test_file.mkv"]
        self.assertIsInstance(timer, threading.Timer)

    def test_schedule_timer_is_daemon(self):
        """Verify timer is a daemon thread (won't prevent process exit)."""
        self.controller._Controller__schedule_auto_delete("test_file.mkv")
        timer = self.controller._Controller__pending_auto_deletes["test_file.mkv"]
        self.assertTrue(timer.daemon)

    def test_schedule_cancels_existing_timer(self):
        """Verify re-scheduling cancels the old timer and creates a new one."""
        self.controller._Controller__schedule_auto_delete("test_file.mkv")
        old_timer = self.controller._Controller__pending_auto_deletes["test_file.mkv"]
        self.controller._Controller__schedule_auto_delete("test_file.mkv")
        new_timer = self.controller._Controller__pending_auto_deletes["test_file.mkv"]
        self.assertIsNot(old_timer, new_timer)
        # Old timer should be canceled
        self.assertTrue(old_timer.finished.is_set() or not old_timer.is_alive())

    def test_schedule_multiple_files(self):
        """Verify multiple files can have independent timers."""
        self.controller._Controller__schedule_auto_delete("file1.mkv")
        self.controller._Controller__schedule_auto_delete("file2.mkv")
        self.assertEqual(2, len(self.controller._Controller__pending_auto_deletes))
        self.assertIn("file1.mkv", self.controller._Controller__pending_auto_deletes)
        self.assertIn("file2.mkv", self.controller._Controller__pending_auto_deletes)


class TestAutoDeleteExecution(BaseAutoDeleteTestCase):
    """Test auto-delete execution (timer callback)."""

    def _make_safe_mock_file(self, state=ModelFile.State.DOWNLOADED, is_dir=False, children=None):
        """Helper: build a ModelFile mock that passes the state + pack guards."""
        mock_file = MagicMock(spec=ModelFile)
        mock_file.state = state
        mock_file.is_dir = is_dir
        mock_file.get_children.return_value = children or []
        return mock_file

    def test_execute_calls_delete_local(self):
        """Verify execution calls delete_local (not delete_remote)."""
        mock_file = self._make_safe_mock_file()
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)

        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    def test_execute_never_calls_delete_remote(self):
        """SAFETY: Verify execution NEVER calls delete_remote."""
        mock_file = self._make_safe_mock_file()
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)

        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.mock_file_op_manager.delete_remote.assert_not_called()

    def test_execute_dry_run_does_not_delete(self):
        """Verify dry-run mode logs but does not delete."""
        self.mock_context.config.autodelete.dry_run = True

        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.mock_file_op_manager.delete_local.assert_not_called()
        self.mock_file_op_manager.delete_remote.assert_not_called()

    def test_execute_disabled_skips_deletion(self):
        """Verify disabled config skips deletion even if timer fires."""
        self.mock_context.config.autodelete.enabled = False

        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_execute_handles_model_error(self):
        """Verify ModelError is caught gracefully when file no longer exists."""
        self.controller._Controller__model.get_file = MagicMock(
            side_effect=ModelError("not found")
        )

        # Should not raise
        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_execute_removes_from_pending_dict(self):
        """Verify execution removes file from pending dict."""
        mock_file = self._make_safe_mock_file()
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        # Pre-populate pending dict
        self.controller._Controller__pending_auto_deletes["test_file.mkv"] = MagicMock()

        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.assertNotIn("test_file.mkv", self.controller._Controller__pending_auto_deletes)

    def test_execute_removes_from_pending_dict_even_on_error(self):
        """Verify pending dict cleanup happens even if ModelError occurs."""
        self.controller._Controller__model.get_file = MagicMock(
            side_effect=ModelError("not found")
        )
        self.controller._Controller__pending_auto_deletes["test_file.mkv"] = MagicMock()

        self.controller._Controller__execute_auto_delete("test_file.mkv")

        self.assertNotIn("test_file.mkv", self.controller._Controller__pending_auto_deletes)

    def test_execute_acquires_model_lock(self):
        """Verify auto-delete callback acquires model lock before reading model."""
        lock_was_held = []

        def check_lock(name):
            lock_was_held.append(self.controller._Controller__model_lock.locked())
            return self._make_safe_mock_file()

        self.controller._Controller__model.get_file = MagicMock(side_effect=check_lock)
        self.controller._Controller__execute_auto_delete("test_file.mkv")
        self.assertTrue(lock_was_held[0], "Model lock must be held during get_file in auto-delete")

    def test_execute_releases_lock_before_delete_local(self):
        """Verify model lock is released before calling delete_local (avoid blocking)."""
        lock_held_during_delete = []
        mock_file = self._make_safe_mock_file()
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)

        def check_lock_on_delete(file):
            lock_held_during_delete.append(self.controller._Controller__model_lock.locked())

        self.mock_file_op_manager.delete_local.side_effect = check_lock_on_delete
        self.controller._Controller__execute_auto_delete("test_file.mkv")
        self.assertFalse(
            lock_held_during_delete[0],
            "Model lock must NOT be held during delete_local"
        )

    # --- State guard: skip deletion when root is in an active state -----------

    def _run_skip_on_root_state_test(self, state):
        """Helper: assert auto-delete is skipped when the root is in `state`."""
        mock_file = self._make_safe_mock_file(state=state)
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("test_file.mkv")
        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_execute_skips_when_root_is_downloading(self):
        self._run_skip_on_root_state_test(ModelFile.State.DOWNLOADING)

    def test_execute_skips_when_root_is_queued(self):
        self._run_skip_on_root_state_test(ModelFile.State.QUEUED)

    def test_execute_skips_when_root_is_extracting(self):
        self._run_skip_on_root_state_test(ModelFile.State.EXTRACTING)

    def test_execute_skips_when_root_is_deleted(self):
        self._run_skip_on_root_state_test(ModelFile.State.DELETED)

    def test_execute_proceeds_when_root_is_default(self):
        mock_file = self._make_safe_mock_file(state=ModelFile.State.DEFAULT)
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("test_file.mkv")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    def test_execute_proceeds_when_root_is_extracted(self):
        mock_file = self._make_safe_mock_file(state=ModelFile.State.EXTRACTED)
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("test_file.mkv")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    # --- Pack guard: skip deletion when any descendant is in an active state --

    def _make_child(self, name, state=ModelFile.State.DOWNLOADED, children=None, is_dir=None):
        child = MagicMock(spec=ModelFile)
        child.name = name
        child.state = state
        child.get_children.return_value = children or []
        # is_dir defaults to whether children were provided. MagicMock(spec=ModelFile)
        # would otherwise leave `is_dir` as a truthy MagicMock, breaking the coverage
        # guard's `not child.is_dir` leaf check.
        child.is_dir = is_dir if is_dir is not None else bool(children)
        return child

    def test_execute_skips_dir_when_direct_child_is_downloading(self):
        child = self._make_child("ep01.mkv", state=ModelFile.State.DOWNLOADING)
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_execute_skips_dir_when_direct_child_is_extracting(self):
        child = self._make_child("ep02.mkv", state=ModelFile.State.EXTRACTING)
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_execute_skips_dir_when_nested_child_is_queued(self):
        grandchild = self._make_child("sample.mkv", state=ModelFile.State.QUEUED)
        child = self._make_child("Samples", children=[grandchild])
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_execute_proceeds_dir_when_all_children_safe(self):
        child_a = self._make_child("ep01.mkv", state=ModelFile.State.DOWNLOADED)
        child_b = self._make_child("ep02.mkv", state=ModelFile.State.EXTRACTED)
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a, child_b])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.controller._Controller__execute_auto_delete("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)


class TestAutoDeleteCoverageGuard(TestAutoDeleteExecution):
    """Phase 75 (GH #19): per-child coverage guard in __execute_auto_delete.

    Reuses _make_safe_mock_file and _make_child from TestAutoDeleteExecution.
    Seeds self.persist.imported_children directly to simulate webhook-driven
    per-child state (the webhook path itself is exercised in
    TestAutoDeleteIntegration).
    """

    def test_execute_proceeds_single_file_root_when_root_imported(self):
        """D-11: non-dir root bypasses the coverage guard entirely (single-file
        pass-through -- pre-PR-18 behavior preserved)."""
        mock_file = self._make_safe_mock_file(is_dir=False)
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.persist.imported_file_names.add("single_file.mkv")
        # Intentionally NOT seeding imported_children -- single-file roots never
        # touch it (coverage check gated on file.is_dir == True).
        self.controller._Controller__execute_auto_delete("single_file.mkv")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    def test_execute_proceeds_dir_when_all_video_children_imported(self):
        """D-08 full-coverage path: every on-disk video basename covered -> delete."""
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a, child_b])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")
        self.persist.add_imported_child("Pack.S01", "ep02.mkv")
        self.controller._Controller__execute_auto_delete("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    def test_execute_skips_dir_when_one_video_child_missing(self):
        """D-08 partial-coverage path: one on-disk video missing from imported
        children -> skip + INFO log containing 'partial import' and the
        missing basename. This is the canonical GH #19 regression test."""
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a, child_b])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        # Seed only ep01 -- ep02 is on disk but not imported
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")

        self.controller._Controller__execute_auto_delete("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_not_called()
        # Verify the D-16 log phrasing
        logged_messages = [
            str(call) for call in self.controller.logger.info.call_args_list
        ]
        partial_hits = [m for m in logged_messages if "partial import" in m and "Pack.S01" in m]
        self.assertTrue(partial_hits, "Expected 'partial import' INFO log for 'Pack.S01'")
        missing_hits = [m for m in logged_messages if "ep02.mkv" in m]
        self.assertTrue(missing_hits, "Expected missing basename 'ep02.mkv' in log")

    def test_execute_proceeds_dir_when_non_video_files_uncovered(self):
        """D-10: non-allowlisted extensions (.nfo, .txt) are ignored by the
        coverage guard. Only .mkv must be covered for delete to proceed."""
        child_video = self._make_child("ep01.mkv")
        child_nfo = self._make_child("ep01.nfo")
        child_sample = self._make_child("sample.txt")
        mock_file = self._make_safe_mock_file(
            is_dir=True,
            children=[child_video, child_nfo, child_sample],
        )
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        # Only the video is covered -- .nfo and .txt are out of the allowlist
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")

        self.controller._Controller__execute_auto_delete("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    def test_execute_proceeds_dir_when_no_imported_children_entry_legacy(self):
        """D-14 grandfather: root tracked in imported_file_names but absent
        from imported_children (pre-upgrade state) -> delete proceeds."""
        child_a = self._make_child("ep01.mkv")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        # Populate imported_file_names (root tracked) but NOT imported_children
        self.persist.imported_file_names.add("Pack.S01")
        self.assertNotIn("Pack.S01", self.persist.imported_children)

        self.controller._Controller__execute_auto_delete("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)

    def test_execute_clears_imported_children_after_delete(self):
        """D-04: after successful delete, the per-root entry is removed from
        imported_children to keep persist small and avoid stale data."""
        child_a = self._make_child("ep01.mkv")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")
        self.assertIn("Pack.S01", self.persist.imported_children)

        self.controller._Controller__execute_auto_delete("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
        self.assertNotIn("Pack.S01", self.persist.imported_children)

    def test_execute_coverage_check_is_case_insensitive(self):
        """Case-insensitive matching: imported_children stored lowercase,
        on-disk basename may be mixed case -- delete still proceeds."""
        child_mixed_case = self._make_child("Ep01.MKV")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_mixed_case])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)
        # Stored as lowercase (what the controller writes via matched_name.lower())
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")

        self.controller._Controller__execute_auto_delete("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)


class TestAutoDeletePersistRehydration(TestAutoDeleteExecution):
    """D-20: partial-coverage state survives JSON round-trip (restart)."""

    def test_imported_children_partial_coverage_survives_restart(self):
        """Seed partial coverage, round-trip through to_str/from_str, replace
        the controller's persist with the rehydrated copy, and confirm
        Timer-fire still skips -- proving persist rehydration works."""
        # Seed the original persist
        self.persist.imported_file_names.add("Pack.S01")
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")
        # Round-trip
        serialized = self.persist.to_str()
        rehydrated = ControllerPersist.from_str(serialized, max_tracked_files=100)
        # Swap the controller's persist for the rehydrated copy
        self.controller._Controller__persist = rehydrated
        # Confirm the rehydrated persist contains the seeded state
        self.assertIn("Pack.S01", rehydrated.imported_children)
        self.assertIn("ep01.mkv", rehydrated.imported_children["Pack.S01"])
        # Now run Timer-fire with an on-disk pack containing BOTH ep01 and ep02
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_safe_mock_file(is_dir=True, children=[child_a, child_b])
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)

        self.controller._Controller__execute_auto_delete("Pack.S01")

        # ep02 was not in the persisted imported_children -> partial coverage -> skip
        self.mock_file_op_manager.delete_local.assert_not_called()


class TestAutoDeleteShutdown(BaseAutoDeleteTestCase):
    """Test timer cleanup on controller exit."""

    def test_exit_cancels_all_pending_timers(self):
        """Verify exit() cancels all pending auto-delete timers."""
        # Schedule some timers
        self.controller._Controller__schedule_auto_delete("file1.mkv")
        self.controller._Controller__schedule_auto_delete("file2.mkv")
        self.assertEqual(2, len(self.controller._Controller__pending_auto_deletes))

        # Mark as started so exit() runs cleanup
        self.controller._Controller__started = True

        self.controller.exit()

        self.assertEqual(0, len(self.controller._Controller__pending_auto_deletes))

    def test_exit_without_pending_timers(self):
        """Verify exit() works cleanly with no pending timers."""
        self.controller._Controller__started = True

        # Should not raise
        self.controller.exit()

        self.assertEqual(0, len(self.controller._Controller__pending_auto_deletes))


class TestAutoDeleteIntegration(BaseAutoDeleteTestCase):
    """Test auto-delete scheduling triggered from check_webhook_imports via process()."""

    def _make_controller_started(self):
        """Helper: set __started flag and configure no-op model update mocks."""
        self.controller._Controller__started = True
        self.mock_scan_manager.pop_latest_results.return_value = (None, None, None)
        self.mock_lftp_manager.status.return_value = None
        self.mock_file_op_manager.pop_extract_statuses.return_value = None
        self.mock_file_op_manager.pop_completed_extractions.return_value = []
        self.mock_model_builder.has_changes.return_value = False

    def test_webhook_import_triggers_auto_delete_schedule(self):
        """Verify webhook import detection schedules auto-delete when enabled."""
        self._make_controller_started()
        # Add file to model
        f = ModelFile("test_file.mkv", False)
        f.remote_size = 1000
        self.controller._Controller__model.add_file(f)
        # Webhook manager reports import
        self.mock_webhook_manager.process.return_value = [("test_file.mkv", "test_file.mkv")]

        self.controller.process()

        self.assertIn("test_file.mkv", self.controller._Controller__pending_auto_deletes)

    def test_webhook_import_no_schedule_when_disabled(self):
        """Verify webhook import does NOT schedule auto-delete when disabled."""
        self._make_controller_started()
        self.mock_context.config.autodelete.enabled = False
        # Add file to model
        f = ModelFile("test_file.mkv", False)
        f.remote_size = 1000
        self.controller._Controller__model.add_file(f)
        self.mock_webhook_manager.process.return_value = [("test_file.mkv", "test_file.mkv")]

        self.controller.process()

        self.assertEqual(0, len(self.controller._Controller__pending_auto_deletes))
