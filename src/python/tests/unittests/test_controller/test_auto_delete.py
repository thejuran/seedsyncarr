import unittest
from unittest.mock import MagicMock, patch
import threading

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile, ModelError


class BaseAutoDeleteTestCase(unittest.TestCase):
    """Base class with patched Controller dependencies for auto-delete tests."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.mock_context.config.autodelete.enabled = True
        self.mock_context.config.autodelete.dry_run = False
        self.mock_context.config.autodelete.delay_seconds = 10
        self.persist = ControllerPersist(max_tracked_files=100)

        # Start patches for all 6 internal dependencies
        self.patcher_mb = patch('controller.controller.ModelBuilder')
        self.patcher_lftp = patch('controller.controller.LftpManager')
        self.patcher_sm = patch('controller.controller.ScanManager')
        self.patcher_fom = patch('controller.controller.FileOperationManager')
        self.patcher_mpl = patch('controller.controller.MultiprocessingLogger')
        self.patcher_mm = patch('controller.controller.MemoryMonitor')

        self.mock_model_builder_cls = self.patcher_mb.start()
        self.mock_lftp_manager_cls = self.patcher_lftp.start()
        self.mock_scan_manager_cls = self.patcher_sm.start()
        self.mock_file_op_manager_cls = self.patcher_fom.start()
        self.mock_mp_logger_cls = self.patcher_mpl.start()
        self.mock_memory_monitor_cls = self.patcher_mm.start()

        # Get mock instances
        self.mock_model_builder = self.mock_model_builder_cls.return_value
        self.mock_lftp_manager = self.mock_lftp_manager_cls.return_value
        self.mock_scan_manager = self.mock_scan_manager_cls.return_value
        self.mock_file_op_manager = self.mock_file_op_manager_cls.return_value
        self.mock_mp_logger = self.mock_mp_logger_cls.return_value
        self.mock_memory_monitor = self.mock_memory_monitor_cls.return_value
        # Create mock WebhookManager (not patched, passed as parameter)
        self.mock_webhook_manager = MagicMock()
        self.mock_webhook_manager.process.return_value = []

        self.controller = Controller(context=self.mock_context, persist=self.persist, webhook_manager=self.mock_webhook_manager)

    def tearDown(self):
        # Cancel any pending timers to prevent thread leaks
        for timer in list(self.controller._Controller__pending_auto_deletes.values()):
            timer.cancel()
        self.controller._Controller__pending_auto_deletes.clear()

        self.patcher_mb.stop()
        self.patcher_lftp.stop()
        self.patcher_sm.stop()
        self.patcher_fom.stop()
        self.patcher_mpl.stop()
        self.patcher_mm.stop()


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

    def _make_child(self, name, state=ModelFile.State.DOWNLOADED, children=None):
        child = MagicMock(spec=ModelFile)
        child.name = name
        child.state = state
        child.get_children.return_value = children or []
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
