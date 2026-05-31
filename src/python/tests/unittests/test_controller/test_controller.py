import unittest
from queue import Queue
from threading import Lock
from unittest.mock import MagicMock, call

from datetime import datetime

from common import Status
from controller.controller import Controller
from controller.scan import ScannerResult


class TestShouldUpdateCapacity(unittest.TestCase):
    def test_new_is_none_returns_false(self):
        self.assertFalse(Controller._should_update_capacity(1000, None))
        self.assertFalse(Controller._should_update_capacity(None, None))

    def test_old_is_none_new_not_none_returns_true(self):
        self.assertTrue(Controller._should_update_capacity(None, 1000))

    def test_delta_above_one_percent_returns_true(self):
        self.assertTrue(Controller._should_update_capacity(1_000_000_000_000, 1_011_000_000_000))

    def test_delta_below_one_percent_returns_false(self):
        self.assertFalse(Controller._should_update_capacity(1_000_000_000_000, 1_005_000_000_000))

    def test_exact_one_percent_does_not_pass(self):
        self.assertFalse(Controller._should_update_capacity(1000, 1010))

    def test_just_above_one_percent_passes(self):
        self.assertTrue(Controller._should_update_capacity(1000, 1011))

    def test_old_zero_new_nonzero_returns_true(self):
        self.assertTrue(Controller._should_update_capacity(0, 100))

    def test_old_zero_new_zero_returns_false(self):
        self.assertFalse(Controller._should_update_capacity(0, 0))

    def test_negative_delta_above_one_percent_returns_true(self):
        self.assertTrue(Controller._should_update_capacity(1_000_000_000_000, 980_000_000_000))


class TestUpdateControllerStatusCapacity(unittest.TestCase):
    """Capacity assignment with >1% gate, per-side independence (D-12/D-13/D-15)."""

    def _make_controller_with_status(self):
        controller = Controller.__new__(Controller)
        ctx = MagicMock()
        ctx.status = Status()
        controller._Controller__context = ctx
        return controller

    def _result(self, total=None, used=None):
        return ScannerResult(
            timestamp=datetime.now(),
            files=[],
            total_bytes=total,
            used_bytes=used,
        )

    def test_first_write_populates_remote(self):
        c = self._make_controller_with_status()
        c._update_controller_status(self._result(2_000_000_000_000, 1_300_000_000_000), None)
        self.assertEqual(2_000_000_000_000, c._Controller__context.status.storage.remote_total)
        self.assertEqual(1_300_000_000_000, c._Controller__context.status.storage.remote_used)

    def test_first_write_populates_local(self):
        c = self._make_controller_with_status()
        c._update_controller_status(None, self._result(500_000_000_000, 100_000_000_000))
        self.assertEqual(500_000_000_000, c._Controller__context.status.storage.local_total)
        self.assertEqual(100_000_000_000, c._Controller__context.status.storage.local_used)

    def test_sub_one_percent_delta_is_skipped(self):
        c = self._make_controller_with_status()
        c._update_controller_status(self._result(2_000_000_000_000, 1_000_000_000_000), None)
        c._update_controller_status(self._result(2_008_000_000_000, 1_004_000_000_000), None)
        self.assertEqual(2_000_000_000_000, c._Controller__context.status.storage.remote_total)
        self.assertEqual(1_000_000_000_000, c._Controller__context.status.storage.remote_used)

    def test_above_one_percent_delta_writes_both(self):
        c = self._make_controller_with_status()
        c._update_controller_status(self._result(2_000_000_000_000, 1_000_000_000_000), None)
        # Both fields move +1.5% — each crosses its own per-field gate (D-12/D-15).
        c._update_controller_status(self._result(2_030_000_000_000, 1_015_000_000_000), None)
        self.assertEqual(2_030_000_000_000, c._Controller__context.status.storage.remote_total)
        self.assertEqual(1_015_000_000_000, c._Controller__context.status.storage.remote_used)

    def test_none_capacity_leaves_existing_values(self):
        c = self._make_controller_with_status()
        c._update_controller_status(self._result(2_000_000_000_000, 1_300_000_000_000), None)
        c._update_controller_status(self._result(None, None), None)
        self.assertEqual(2_000_000_000_000, c._Controller__context.status.storage.remote_total)
        self.assertEqual(1_300_000_000_000, c._Controller__context.status.storage.remote_used)

    def test_per_side_independence_remote_none_local_populated(self):
        c = self._make_controller_with_status()
        c._update_controller_status(
            self._result(None, None),
            self._result(500_000_000_000, 100_000_000_000),
        )
        self.assertIsNone(c._Controller__context.status.storage.remote_total)
        self.assertIsNone(c._Controller__context.status.storage.remote_used)
        self.assertEqual(500_000_000_000, c._Controller__context.status.storage.local_total)
        self.assertEqual(100_000_000_000, c._Controller__context.status.storage.local_used)

    def test_per_side_independence_local_none_remote_populated(self):
        c = self._make_controller_with_status()
        c._update_controller_status(
            self._result(2_000_000_000_000, 1_300_000_000_000),
            self._result(None, None),
        )
        self.assertEqual(2_000_000_000_000, c._Controller__context.status.storage.remote_total)
        self.assertEqual(1_300_000_000_000, c._Controller__context.status.storage.remote_used)
        self.assertIsNone(c._Controller__context.status.storage.local_total)
        self.assertIsNone(c._Controller__context.status.storage.local_used)

    def test_none_scan_result_is_noop(self):
        c = self._make_controller_with_status()
        c._update_controller_status(None, None)
        self.assertIsNone(c._Controller__context.status.storage.remote_total)
        self.assertIsNone(c._Controller__context.status.storage.local_total)

    def test_existing_scan_time_fields_still_updated(self):
        c = self._make_controller_with_status()
        ts = datetime.now()
        scan = ScannerResult(timestamp=ts, files=[], failed=False,
                             total_bytes=2_000_000_000_000, used_bytes=1_300_000_000_000)
        c._update_controller_status(scan, None)
        self.assertEqual(ts, c._Controller__context.status.controller.latest_remote_scan_time)
        self.assertEqual(False, c._Controller__context.status.controller.latest_remote_scan_failed)

    def test_used_crosses_threshold_total_does_not_writes_only_used(self):
        """Per-field independence: a sub-1% delta on total must not bypass its own gate
        when used crosses the threshold (and vice versa)."""
        c = self._make_controller_with_status()
        c._update_controller_status(
            self._result(2_000_000_000_000, 1_000_000_000_000), None
        )
        # total: +0.0005% (well below gate); used: +1.5% (above gate)
        c._update_controller_status(
            self._result(2_000_010_000_000, 1_015_000_000_000), None
        )
        self.assertEqual(
            2_000_000_000_000,
            c._Controller__context.status.storage.remote_total,
            "remote_total must NOT be overwritten when its own delta is sub-1%",
        )
        self.assertEqual(
            1_015_000_000_000,
            c._Controller__context.status.storage.remote_used,
            "remote_used must be written when it crosses the gate",
        )

    def test_total_crosses_threshold_used_does_not_writes_only_total(self):
        c = self._make_controller_with_status()
        c._update_controller_status(
            self._result(2_000_000_000_000, 1_000_000_000_000), None
        )
        # total: +5% (above gate); used: +0.0005% (below gate)
        c._update_controller_status(
            self._result(2_100_000_000_000, 1_000_005_000_000), None
        )
        self.assertEqual(2_100_000_000_000, c._Controller__context.status.storage.remote_total)
        self.assertEqual(
            1_000_000_000_000,
            c._Controller__context.status.storage.remote_used,
            "remote_used must NOT be overwritten when its own delta is sub-1%",
        )


class TestCheckWebhookImportsSanitization(unittest.TestCase):
    """CWE-117 log-injection sanitization for __check_webhook_imports (Plan 101-04)."""

    def _make_controller(self):
        """Build a minimal Controller instance with all private attrs needed by __check_webhook_imports."""
        c = Controller.__new__(Controller)
        ctx = MagicMock()
        ctx.config.autodelete.enabled = False  # disable auto-delete path for simplicity
        c._Controller__context = ctx
        c.logger = MagicMock()

        # Model: returns no file names by default — tests override as needed
        c._Controller__model = MagicMock()
        c._Controller__model.get_file_names.return_value = []
        c._Controller__model_lock = Lock()

        # Persist: needs add_imported_child + imported_file_names (a set-like)
        mock_persist = MagicMock()
        mock_persist.imported_file_names = set()
        mock_persist.imported_children = {}
        c._Controller__persist = mock_persist

        # Webhook manager: returns our crafted tuple
        c._Controller__webhook_manager = MagicMock()

        return c

    def test_recorded_import_log_is_sanitized(self):
        """CRLF-bearing root_name must be escaped in the 'Recorded webhook import' log (site 792).

        Site 790 already used an inline escape for matched_name (REPLACED by sanitize_log_value);
        site 792 logs root_name which is NEWLY wrapped in this plan.  We inject CRLF into root_name
        so this test fails RED (the current code logs it raw) and passes GREEN (after the wrap).
        """
        crlf_root = "Root\r\ninjected"
        matched_name = "child.file.mkv"

        c = self._make_controller()
        # Return an import whose root_name contains CRLF (remote-scanner-sourced)
        c._Controller__webhook_manager.process.return_value = [(crlf_root, matched_name)]
        c._Controller__persist.imported_file_names = set()
        c._set_import_status = MagicMock()

        c._Controller__check_webhook_imports()

        # Find any logger.info call whose message starts with "Recorded webhook import"
        recorded_calls = [
            args[0][0]
            for args in c.logger.info.call_args_list
            if args[0] and "Recorded webhook import" in str(args[0][0])
        ]
        self.assertTrue(recorded_calls, "Expected a 'Recorded webhook import' info log call")
        logged_msg = recorded_calls[0]

        # Must not contain a literal newline or carriage-return
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in log output")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in log output")
        # Must contain escaped tokens
        self.assertIn("\\r", logged_msg)
        self.assertIn("\\n", logged_msg)

    def test_recorded_import_persist_value_is_raw(self):
        """Control-flow persist/add_imported_child uses the RAW matched_name — not the sanitized log value."""
        crlf_matched = "child\r\ninjected"
        root_name = "Root"

        c = self._make_controller()
        c._Controller__webhook_manager.process.return_value = [(root_name, crlf_matched)]
        c._Controller__persist.imported_file_names = set()
        c._set_import_status = MagicMock()

        c._Controller__check_webhook_imports()

        # add_imported_child receives the RAW lowercased matched_name (D-01)
        c._Controller__persist.add_imported_child.assert_called_once_with(
            root_name, crlf_matched.lower()
        )


class TestProcessCommandsSanitization(unittest.TestCase):
    """CWE-117 log-injection sanitization for _notify_failure / __process_commands (Plan 101-04)."""

    def _make_controller(self):
        """Build a minimal Controller instance with private attrs needed by __process_commands."""
        c = Controller.__new__(Controller)
        ctx = MagicMock()
        c._Controller__context = ctx
        c.logger = MagicMock()

        c._Controller__command_queue = Queue()
        c._Controller__model = MagicMock()
        c._Controller__model_lock = Lock()

        return c

    def test_notify_failure_log_is_sanitized(self):
        """CRLF-bearing command.filename -> 'Command failed.' warning log is sanitized (site 1069)."""
        crlf_filename = "file\r\ninjected.mkv"
        # Build a command with the CRLF filename; no matching model file -> ModelError path
        from model import ModelError
        c = self._make_controller()
        c._Controller__model.get_file.side_effect = ModelError("not found")

        cmd = Controller.Command(Controller.Command.Action.QUEUE, crlf_filename)
        mock_callback = MagicMock()
        cmd.add_callback(mock_callback)
        c._Controller__command_queue.put(cmd)

        c._Controller__process_commands()

        # Find the "Command failed." warning log call
        failed_calls = [
            args[0][0]
            for args in c.logger.warning.call_args_list
            if args[0] and "Command failed." in str(args[0][0])
        ]
        self.assertTrue(failed_calls, "Expected a 'Command failed.' warning log call")
        logged_msg = failed_calls[0]

        # Log must not contain a raw newline or CR
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in the warning log")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in the warning log")
        # Log must contain the escaped tokens
        self.assertIn("\\r", logged_msg)
        self.assertIn("\\n", logged_msg)

    def test_notify_failure_callback_receives_raw_msg(self):
        """on_failure callback receives the RAW _msg — sanitization is log-output-only (site 1071)."""
        crlf_filename = "file\r\ninjected.mkv"
        expected_raw_msg = "File '{}' not found".format(crlf_filename)

        from model import ModelError
        c = self._make_controller()
        c._Controller__model.get_file.side_effect = ModelError("not found")

        cmd = Controller.Command(Controller.Command.Action.QUEUE, crlf_filename)
        mock_callback = MagicMock()
        cmd.add_callback(mock_callback)
        c._Controller__command_queue.put(cmd)

        c._Controller__process_commands()

        # The on_failure callback must receive the RAW (un-sanitized) message
        mock_callback.on_failure.assert_called_once()
        actual_msg = mock_callback.on_failure.call_args[0][0]
        self.assertEqual(expected_raw_msg, actual_msg,
                         "on_failure callback must receive the raw (unsanitized) message")
        # Verify the raw msg does contain the literal newline (confirming it's truly raw)
        self.assertIn("\r\n", actual_msg)


class TestAutoDeleteLogSanitization(unittest.TestCase):
    """CWE-117 log-injection sanitization for auto-delete timer + exit-cancel log sites (Plan 101-05).

    Site coverage:
      - controller.py:820  __schedule_auto_delete "Scheduled auto-delete of '{}'"
      - controller.py:841  __execute_auto_delete  "Auto-delete skipped for '{}': feature was disabled"
      - controller.py:229  exit()                 "Canceled pending auto-delete for '{}'"
    """

    def _make_controller_for_auto_delete(self):
        """Build a minimal Controller instance with the attrs needed by schedule/execute/exit."""
        import threading
        c = Controller.__new__(Controller)

        ctx = MagicMock()
        ctx.config.autodelete.enabled = True
        ctx.config.autodelete.dry_run = False
        ctx.config.autodelete.delay_seconds = 3600  # long delay so timer never fires in test
        c._Controller__context = ctx
        c.logger = MagicMock()

        c._Controller__auto_delete_lock = threading.Lock()
        c._Controller__pending_auto_deletes = {}
        c._Controller__started = True

        # model + lock (needed by __execute_auto_delete)
        c._Controller__model = MagicMock()
        c._Controller__model_lock = threading.Lock()
        c._Controller__persist = MagicMock()
        c._Controller__file_op_manager = MagicMock()

        return c

    def test_schedule_auto_delete_log_sanitized(self):
        """__schedule_auto_delete with a CRLF-bearing file_name: 'Scheduled auto-delete' log
        must have no literal newline; __pending_auto_deletes still keyed by the RAW name."""
        crlf_name = "file\r\ninjected.mkv"

        c = self._make_controller_for_auto_delete()

        # Call the name-mangled method directly
        c._Controller__schedule_auto_delete(crlf_name)

        # Cancel the timer so it doesn't fire
        timer = c._Controller__pending_auto_deletes.get(crlf_name)
        if timer:
            timer.cancel()

        # Check that a "Scheduled auto-delete" info call exists
        sched_calls = [
            args[0][0]
            for args in c.logger.info.call_args_list
            if args[0] and "Scheduled auto-delete" in str(args[0][0])
        ]
        self.assertTrue(sched_calls, "Expected a 'Scheduled auto-delete' info log call")
        logged_msg = sched_calls[0]

        # Log must not contain raw CR or LF
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in schedule log")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in schedule log")
        # Must contain escaped tokens
        self.assertIn("\\r", logged_msg)
        self.assertIn("\\n", logged_msg)

        # The scheduling dict key must still be the RAW name (for timer cancellation by lookup)
        self.assertIn(crlf_name, c._Controller__pending_auto_deletes,
                      "__pending_auto_deletes must be keyed by the raw file name")

    def test_execute_auto_delete_skip_log_sanitized(self):
        """__execute_auto_delete skip branch (feature disabled): log is escaped, raw name not needed
        for dict lookup since the timer already fired and the entry was popped."""
        crlf_name = "file\r\nskip.mkv"

        c = self._make_controller_for_auto_delete()
        # Disable auto-delete so execution takes the first skip branch (feature disabled)
        c._Controller__context.config.autodelete.enabled = False

        c._Controller__execute_auto_delete(crlf_name)

        # Check that a "feature was disabled" info call exists
        skip_calls = [
            args[0][0]
            for args in c.logger.info.call_args_list
            if args[0] and "feature was disabled" in str(args[0][0])
        ]
        self.assertTrue(skip_calls, "Expected a 'feature was disabled' info log call")
        logged_msg = skip_calls[0]

        # Log must not contain raw CR or LF
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in skip log")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in skip log")
        self.assertIn("\\r", logged_msg)
        self.assertIn("\\n", logged_msg)

    def test_exit_cancel_log_sanitized(self):
        """exit() 'Canceled pending auto-delete' log (line 229) must escape CRLF-bearing file name;
        dict must be cleared."""
        import threading
        crlf_name = "file\r\nexit.mkv"

        c = self._make_controller_for_auto_delete()

        # Plant a fake timer in the pending dict (cancel-safe mock)
        fake_timer = MagicMock(spec=threading.Timer)
        c._Controller__pending_auto_deletes[crlf_name] = fake_timer

        c.exit()

        # The fake timer must have been canceled
        fake_timer.cancel.assert_called_once()
        # Dict must be cleared
        self.assertEqual({}, c._Controller__pending_auto_deletes)

        # Check that a "Canceled pending auto-delete" debug call exists
        cancel_calls = [
            args[0][0]
            for args in c.logger.debug.call_args_list
            if args[0] and "Canceled pending auto-delete" in str(args[0][0])
        ]
        self.assertTrue(cancel_calls, "Expected a 'Canceled pending auto-delete' debug log call")
        logged_msg = cancel_calls[0]

        # Log must not contain raw CR or LF
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in exit cancel log")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in exit cancel log")
        self.assertIn("\\r", logged_msg)
        self.assertIn("\\n", logged_msg)


if __name__ == "__main__":
    unittest.main()
