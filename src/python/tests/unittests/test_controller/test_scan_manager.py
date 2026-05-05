import unittest
from unittest.mock import MagicMock, patch

from controller import ScanManager


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
        mock_active_scanner.assert_called_once_with("/local/path")
        mock_local_scanner.assert_called_once_with(
            local_path="/local/path",
            use_temp_file=False
        )
        mock_remote_scanner.assert_called_once()

        # Verify scanner processes were created (3 total)
        self.assertEqual(mock_scanner_process.call_count, 3)

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
        from controller.scan_manager import ScannerProcessDiedError

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

        with self.assertRaises(ScannerProcessDiedError) as ctx:
            manager.propagate_exceptions()
        self.assertIn("RemoteScanner", str(ctx.exception))

    @patch('controller.scan_manager.ScannerProcess')
    @patch('controller.scan_manager.ActiveScanner')
    @patch('controller.scan_manager.LocalScanner')
    @patch('controller.scan_manager.RemoteScanner')
    def test_propagate_exceptions_no_error_when_all_alive(
            self, mock_remote_scanner, mock_local_scanner,
            mock_active_scanner, mock_scanner_process):
        """Test that propagate_exceptions does not raise when all processes are alive."""
        mock_process = MagicMock()
        mock_process.is_alive.return_value = True
        mock_scanner_process.return_value = mock_process

        manager = ScanManager(self.mock_context, self.mock_mp_logger)
        manager.start()

        # Should not raise
        manager.propagate_exceptions()

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
if __name__ == '__main__':
    unittest.main()
