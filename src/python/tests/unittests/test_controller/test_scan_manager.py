import unittest
from unittest.mock import MagicMock, patch

from controller import ScanManager, ScannerProcessDiedError


class TestScanManager(unittest.TestCase):
    """Unit tests for ScanManager."""

    def setUp(self):
        """Set up mocked context and mp_logger for tests."""
        # Create mock context with required config attributes
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()

        # Mock config attributes
        self.mock_context.config.lftp.local_path = "/local/path"
        self.mock_context.config.lftp.use_temp_file = False
        self.mock_context.config.lftp.remote_address = "remote.server.com"
        self.mock_context.config.lftp.remote_username = "user"
        self.mock_context.config.lftp.remote_password = "password"
        self.mock_context.config.lftp.use_ssh_key = False
        self.mock_context.config.lftp.remote_port = 22
        self.mock_context.config.lftp.remote_path = "/remote/path"
        self.mock_context.config.lftp.remote_path_to_scan_script = "/usr/bin/scanfs"
        self.mock_context.args.local_path_to_scanfs = "/local/bin/scanfs"
        self.mock_context.config.controller.interval_ms_downloading_scan = 500
        self.mock_context.config.controller.interval_ms_local_scan = 30000
        self.mock_context.config.controller.interval_ms_remote_scan = 30000

        self.mock_mp_logger = MagicMock()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_init_creates_scanners_and_processes(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that __init__ creates all scanners and processes."""
        manager = ScanManager(self.mock_context, self.mock_mp_logger)  # noqa: F841

        # Verify scanners were created with correct arguments
        mock_active_scanner.assert_called_once_with(
            "/local/path", use_temp_file=True
        )
        mock_local_scanner.assert_called_once_with(
            local_path="/local/path",
            use_temp_file=True
        )
        mock_remote_scanner.assert_called_once()

        # Verify scanner processes were created (3 total)
        self.assertEqual(mock_scanner_process.call_count, 3)

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_scanners_constructed_with_temp_file_forced(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """IMP-01 / D-18: in-flight copies are always *.lftp, so both local
        scanners must map the suffix even though config says False."""
        self.assertFalse(self.mock_context.config.lftp.use_temp_file)
        ScanManager(self.mock_context, self.mock_mp_logger)
        self.assertIs(True, mock_active_scanner.call_args.kwargs["use_temp_file"])
        self.assertIs(True, mock_local_scanner.call_args.kwargs["use_temp_file"])

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_start_starts_all_processes(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that start() starts all scanner processes."""
        # Setup mock processes
        mock_process = MagicMock()
        mock_scanner_process.return_value = mock_process

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        # Verify start was called on each process (3 times)
        self.assertEqual(mock_process.start.call_count, 3)

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_stop_terminates_and_joins_all_processes(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that stop() terminates and joins all scanner processes."""
        # Setup mock processes
        mock_process = MagicMock()
        mock_scanner_process.return_value = mock_process

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()
        manager.stop()

        # Verify terminate and join were called on each process (3 times each)
        self.assertEqual(mock_process.terminate.call_count, 3)
        self.assertEqual(mock_process.join.call_count, 3)

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_stop_without_start_is_safe(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that stop() without start() doesn't raise errors."""
        mock_process = MagicMock()
        mock_scanner_process.return_value = mock_process

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        # Should not raise
        manager.stop()

        # Verify terminate was not called
        mock_process.terminate.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_pop_latest_results_returns_results_from_all_scanners(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that pop_latest_results() returns results from all scanners."""
        # Create distinct mock processes for each scanner
        mock_remote_process = MagicMock()
        mock_local_process = MagicMock()
        mock_active_process = MagicMock()

        # Set up return values for pop_latest_result
        mock_remote_result = MagicMock()
        mock_local_result = MagicMock()
        mock_active_result = MagicMock()

        mock_remote_process.pop_latest_result.return_value = mock_remote_result
        mock_local_process.pop_latest_result.return_value = mock_local_result
        mock_active_process.pop_latest_result.return_value = mock_active_result

        # Make ScannerProcess return different mocks for each call
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        result = manager.pop_latest_results()

        # Verify results are returned in correct order (remote, local, active)
        self.assertEqual(result, (mock_remote_result, mock_local_result, mock_active_result))

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_update_active_files_delegates_to_active_scanner(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that update_active_files() delegates to active scanner."""
        mock_active = MagicMock()
        mock_active_scanner.return_value = mock_active

        manager = ScanManager(self.mock_context, self.mock_mp_logger)

        file_names = ["file1", "file2", "file3"]
        manager.update_active_files(file_names)

        mock_active.set_active_files.assert_called_once_with(file_names)

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_propagate_exceptions_calls_all_processes(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that propagate_exceptions() calls propagate_exception on all processes."""
        mock_process = MagicMock()
        mock_scanner_process.return_value = mock_process

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.propagate_exceptions()

        # Verify propagate_exception was called on each process (3 times)
        self.assertEqual(mock_process.propagate_exception.call_count, 3)

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_force_local_scan_delegates_to_local_process(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that force_local_scan() calls force_scan on local process."""
        # Create distinct mock processes
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()

        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.force_local_scan()

        # Verify force_scan was called on local process only
        mock_local_process.force_scan.assert_called_once()
        mock_remote_process.force_scan.assert_not_called()
        mock_active_process.force_scan.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_force_remote_scan_delegates_to_remote_process(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that force_remote_scan() calls force_scan on remote process."""
        # Create distinct mock processes
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()

        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.force_remote_scan()

        # Verify force_scan was called on remote process only
        mock_remote_process.force_scan.assert_called_once()
        mock_local_process.force_scan.assert_not_called()
        mock_active_process.force_scan.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_ssh_key_mode_uses_none_password(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that SSH key mode uses None for password."""
        self.mock_context.config.lftp.use_ssh_key = True

        manager = ScanManager(self.mock_context, self.mock_mp_logger)  # noqa: F841

        # Verify remote scanner was called with password=None
        call_kwargs = mock_remote_scanner.call_args.kwargs
        self.assertIsNone(call_kwargs['remote_password'])

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_propagate_exceptions_raises_when_process_dies(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that propagate_exceptions raises when a scanner process dies."""
        # Create distinct mock processes
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()

        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        # Simulate remote scanner process dying
        mock_remote_process.is_alive.return_value = False
        mock_local_process.is_alive.return_value = True
        mock_active_process.is_alive.return_value = True

        with self.assertRaises(ScannerProcessDiedError):
            manager.propagate_exceptions()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_propagate_exceptions_no_error_when_all_alive(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that propagate_exceptions does not raise when all processes are alive."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()

        mock_active_process.is_alive.return_value = True
        mock_local_process.is_alive.return_value = True
        mock_remote_process.is_alive.return_value = True

        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        # Should not raise
        manager.propagate_exceptions()

        # Verify is_alive was checked on each distinct process
        mock_active_process.is_alive.assert_called_once()
        mock_local_process.is_alive.assert_called_once()
        mock_remote_process.is_alive.assert_called_once()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_propagate_exceptions_skips_health_check_when_not_started(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that health check is skipped when manager is not started."""
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        mock_scanner_process.return_value = mock_process

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        # NOT started

        # Should not raise because health check is skipped
        manager.propagate_exceptions()

    # --- Partial-start cleanup and per-process cleanup isolation (LIFE-01, LIFE-02) ---

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_partial_start_third_process_fails_stops_started(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """LIFE-01: remote.start() raising stops the already-started active
        and local processes; remote itself is never terminated/joined, and
        the original exception propagates unchanged."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        error = RuntimeError("remote start failed")
        mock_remote_process.start.side_effect = error

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        with self.assertRaises(RuntimeError) as ctx:
            manager.start()
        self.assertIs(error, ctx.exception)

        mock_active_process.terminate.assert_called_once()
        mock_active_process.join.assert_called_once()
        mock_local_process.terminate.assert_called_once()
        mock_local_process.join.assert_called_once()
        mock_remote_process.terminate.assert_not_called()
        mock_remote_process.join.assert_not_called()

        # __started never flipped true, so a later stop() adds no terminate calls
        mock_active_process.terminate.reset_mock()
        mock_local_process.terminate.reset_mock()
        manager.stop()
        mock_active_process.terminate.assert_not_called()
        mock_local_process.terminate.assert_not_called()
        mock_remote_process.terminate.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_partial_start_second_process_fails_stops_started(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """LIFE-01: local.start() raising stops the already-started active
        process; local/remote are never terminated/joined and remote.start()
        is never reached."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        error = RuntimeError("local start failed")
        mock_local_process.start.side_effect = error

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        with self.assertRaises(RuntimeError) as ctx:
            manager.start()
        self.assertIs(error, ctx.exception)

        mock_active_process.terminate.assert_called_once()
        mock_active_process.join.assert_called_once()
        mock_local_process.terminate.assert_not_called()
        mock_local_process.join.assert_not_called()
        mock_remote_process.terminate.assert_not_called()
        mock_remote_process.join.assert_not_called()
        mock_remote_process.start.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_partial_start_first_process_fails_touches_nothing(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Characterization of the existing start order: active.start()
        raising first touches nothing (nothing started yet to clean up),
        and local/remote start() are never reached."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        error = RuntimeError("active start failed")
        mock_active_process.start.side_effect = error

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        with self.assertRaises(RuntimeError) as ctx:
            manager.start()
        self.assertIs(error, ctx.exception)

        mock_active_process.terminate.assert_not_called()
        mock_active_process.join.assert_not_called()
        mock_local_process.start.assert_not_called()
        mock_remote_process.start.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_partial_start_cleanup_error_does_not_mask_original(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """D-06: a cleanup-time error during partial-start cleanup is
        logged and never replaces the original start exception."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]

        original_error = RuntimeError("remote start failed")
        cleanup_error = RuntimeError("active terminate failed")
        mock_remote_process.start.side_effect = original_error
        mock_active_process.terminate.side_effect = cleanup_error

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        with self.assertRaises(RuntimeError) as ctx:
            manager.start()
        self.assertIs(original_error, ctx.exception)

        mock_local_process.terminate.assert_called_once()
        mock_local_process.join.assert_called_once()
        manager.logger.exception.assert_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_cleanup_isolation_terminate_error_continues(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """LIFE-02: one process's terminate() raising does not skip the
        other two; the failed process is not joined because it may still
        be running and join() has no bound."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        mock_active_process.terminate.side_effect = RuntimeError("terminate failed")

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        manager.stop()  # must not raise

        mock_active_process.terminate.assert_called_once()
        mock_active_process.join.assert_not_called()
        mock_local_process.terminate.assert_called_once()
        mock_local_process.join.assert_called_once()
        mock_remote_process.terminate.assert_called_once()
        mock_remote_process.join.assert_called_once()
        manager.logger.exception.assert_called_once()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_cleanup_isolation_join_error_continues(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """LIFE-02: one process's join() raising does not skip the
        others."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        mock_local_process.join.side_effect = RuntimeError("join failed")

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        manager.stop()  # must not raise

        mock_active_process.terminate.assert_called_once()
        mock_local_process.terminate.assert_called_once()
        mock_remote_process.terminate.assert_called_once()
        mock_active_process.join.assert_called_once()
        mock_remote_process.join.assert_called_once()
        manager.logger.exception.assert_called_once()

    # --- D-01: shutdown-aware health check and SIGTERM one-cycle recheck ---

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_shutdown_aware_dead_scanners_after_request_do_not_raise(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """D-01: once note_shutdown_requested() has been called, dead
        scanners are reported as an expected stop (INFO, no raise), not an
        unexpected death (ERROR, ScannerProcessDiedError)."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        for process in (mock_active_process, mock_local_process, mock_remote_process):
            process.is_alive.return_value = False
            process.exitcode = -15

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()
        manager.note_shutdown_requested()

        manager.propagate_exceptions()  # must not raise

        manager.logger.error.assert_not_called()
        info_calls = [str(call) for call in manager.logger.info.call_args_list]
        self.assertTrue(
            any("stopped during shutdown" in c and "exitcode -15" in c for c in info_calls),
            msg="Expected an info log mentioning 'stopped during shutdown' and 'exitcode -15'"
        )
        mock_active_process.terminate.assert_called_once()
        mock_local_process.terminate.assert_called_once()
        mock_remote_process.terminate.assert_called_once()
        mock_active_process.join.assert_called_once()
        mock_local_process.join.assert_called_once()
        mock_remote_process.join.assert_called_once()

        # Already stopped (__started False) -- a second call skips the
        # health check entirely, so no new terminate calls happen.
        mock_active_process.terminate.reset_mock()
        mock_local_process.terminate.reset_mock()
        mock_remote_process.terminate.reset_mock()
        manager.propagate_exceptions()
        mock_active_process.terminate.assert_not_called()
        mock_local_process.terminate.assert_not_called()
        mock_remote_process.terminate.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_shutdown_aware_any_exitcode_after_request_does_not_raise(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """D-01: after a shutdown request, ANY exitcode on a dead process
        (not just SIGTERM) is reported as an expected stop, never an error."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        mock_active_process.is_alive.return_value = True
        mock_local_process.is_alive.return_value = True
        mock_remote_process.is_alive.return_value = False
        mock_remote_process.exitcode = -9

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()
        manager.note_shutdown_requested()

        manager.propagate_exceptions()  # must not raise

        manager.logger.error.assert_not_called()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_shutdown_aware_sigterm_death_rechecked_once_then_raises(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """D-01: without a shutdown request, an all-SIGTERM death is
        re-checked once (covers the few-millisecond gap before the main
        thread's handler runs) before raising on the next cycle."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        for process in (mock_active_process, mock_local_process, mock_remote_process):
            process.is_alive.return_value = False
            process.exitcode = -15

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        manager.propagate_exceptions()  # first call: re-checked, no raise
        manager.logger.error.assert_not_called()

        with self.assertRaises(ScannerProcessDiedError):
            manager.propagate_exceptions()  # second call: raises

        error_calls = [str(call) for call in manager.logger.error.call_args_list]
        self.assertTrue(
            any("Scanner process(es) died unexpectedly" in c for c in error_calls)
        )

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_shutdown_aware_sigterm_death_then_request_is_benign(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """D-01: a SIGTERM death seen before the request, followed by the
        request arriving before the recheck cycle, resolves benignly."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        for process in (mock_active_process, mock_local_process, mock_remote_process):
            process.is_alive.return_value = False
            process.exitcode = -15

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        manager.propagate_exceptions()  # first call: re-checked, no raise
        manager.logger.error.assert_not_called()

        manager.note_shutdown_requested()

        manager.propagate_exceptions()  # second call: now shutdown-aware
        manager.logger.error.assert_not_called()
        info_calls = [str(call) for call in manager.logger.info.call_args_list]
        self.assertTrue(any("stopped during shutdown" in c for c in info_calls))

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_shutdown_aware_mixed_exitcodes_raise_immediately(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Characterization (unchanged before and after this plan): a death
        where not every dead process was killed by SIGTERM raises
        immediately, with no shutdown request and no one-cycle recheck."""
        mock_active_process = MagicMock()
        mock_local_process = MagicMock()
        mock_remote_process = MagicMock()
        mock_scanner_process.side_effect = [
            mock_active_process, mock_local_process, mock_remote_process
        ]
        mock_active_process.is_alive.return_value = True
        mock_local_process.is_alive.return_value = False
        mock_local_process.exitcode = -9
        mock_remote_process.is_alive.return_value = False
        mock_remote_process.exitcode = -15

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        with self.assertRaises(ScannerProcessDiedError):
            manager.propagate_exceptions()
if __name__ == '__main__':
    unittest.main()


class TestScanManagerActiveScannerTempFile(unittest.TestCase):
    """ScanManager must pass use_temp_file to ActiveScanner so active scans
    resolve '<name>.lftp' files instead of warning once per second for the
    whole transfer (incident 2026-08-22)."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.mock_context.config.lftp.local_path = "/local/path"
        self.mock_context.config.lftp.use_temp_file = True
        self.mock_context.config.lftp.remote_address = "remote.server.com"
        self.mock_context.config.lftp.remote_username = "user"
        self.mock_context.config.lftp.remote_password = "password"
        self.mock_context.config.lftp.use_ssh_key = False
        self.mock_context.config.lftp.remote_port = 22
        self.mock_context.config.lftp.remote_path = "/remote/path"
        self.mock_context.config.lftp.remote_path_to_scan_script = "/usr/bin/scanfs"
        self.mock_context.args.local_path_to_scanfs = "/local/bin/scanfs"
        self.mock_context.config.controller.interval_ms_downloading_scan = 500
        self.mock_context.config.controller.interval_ms_local_scan = 30000
        self.mock_context.config.controller.interval_ms_remote_scan = 30000
        self.mock_mp_logger = MagicMock()

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_active_scanner_receives_use_temp_file(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        ScanManager(self.mock_context, self.mock_mp_logger)
        mock_active_scanner.assert_called_once_with(
            "/local/path", use_temp_file=True
        )
