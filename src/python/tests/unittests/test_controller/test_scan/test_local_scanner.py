import logging
import unittest
from unittest.mock import MagicMock, patch

from controller.scan import LocalScanner
from system import SystemFile


class TestLocalScannerCapacityCollection(unittest.TestCase):
    """
    Phase 74-02 — REQ-02.2: LocalScanner.scan() collects disk capacity via
    shutil.disk_usage() and silently falls back to (None, None) on failure.

    D-16: capacity failures never affect the scan file list.
    D-15: per-tile independence (tested here by confirming the file list is
          preserved verbatim across both fallback paths).
    """

    def setUp(self):
        self.scanner = LocalScanner(local_path="/mock/local/path", use_temp_file=False)

        # Stub out the internal SystemScanner so no real filesystem I/O occurs.
        self.stub_system_scanner = MagicMock()
        self.sample_files = [
            SystemFile("alpha", 100, True),
            SystemFile("beta", 200, False),
        ]
        self.stub_system_scanner.scan.return_value = self.sample_files
        # Name-mangled private attribute on LocalScanner.
        self.scanner._LocalScanner__scanner = self.stub_system_scanner

        # Silence warning logs emitted on fallback paths.
        self.scanner.logger = logging.getLogger("test_local_scanner_silent")
        self.scanner.logger.addHandler(logging.NullHandler())
        self.scanner.logger.propagate = False

    @patch("controller.scan.local_scanner.shutil.disk_usage")
    def test_returns_three_tuple_with_real_integers_on_happy_path(self, mock_disk_usage):
        # shutil.disk_usage returns a named tuple with total/used/free.
        usage = MagicMock()
        usage.total = 2_000_000_000_000
        usage.used = 1_300_000_000_000
        mock_disk_usage.return_value = usage

        result = self.scanner.scan()

        self.assertIsInstance(result, tuple)
        self.assertEqual(3, len(result))
        files, total_bytes, used_bytes = result
        self.assertEqual(self.sample_files, files)
        self.assertEqual(2_000_000_000_000, total_bytes)
        self.assertEqual(1_300_000_000_000, used_bytes)
        self.assertIsInstance(total_bytes, int)
        self.assertIsInstance(used_bytes, int)
        mock_disk_usage.assert_called_once_with("/mock/local/path")

    @patch("controller.scan.local_scanner.shutil.disk_usage")
    def test_returns_none_capacity_on_oserror_preserving_file_list(self, mock_disk_usage):
        mock_disk_usage.side_effect = OSError("[Errno 2] No such file or directory: '/mock/local/path'")

        # Bind a dedicated logger BEFORE assertLogs so the context manager
        # watches the same instance the implementation will call.
        self.scanner.logger = logging.getLogger("test_local_scanner_oserror")
        with self.assertLogs(self.scanner.logger, level="WARNING") as log_ctx:
            files, total_bytes, used_bytes = self.scanner.scan()

        self.assertEqual(self.sample_files, files)  # D-16: scan list preserved
        self.assertIsNone(total_bytes)
        self.assertIsNone(used_bytes)
        # At least one WARN-level log entry was emitted by the fallback branch.
        self.assertTrue(any("disk_usage" in msg.lower() or "No such file" in msg
                            for msg in log_ctx.output))

    @patch("controller.scan.local_scanner.shutil.disk_usage")
    def test_returns_none_capacity_on_valueerror_preserving_file_list(self, mock_disk_usage):
        mock_disk_usage.side_effect = ValueError("invalid path argument")

        # Use a logger we know assertLogs can grab.
        self.scanner.logger = logging.getLogger("test_local_scanner_valueerror")
        with self.assertLogs(self.scanner.logger, level="WARNING") as log_ctx:
            files, total_bytes, used_bytes = self.scanner.scan()

        self.assertEqual(self.sample_files, files)  # D-16: scan list preserved
        self.assertIsNone(total_bytes)
        self.assertIsNone(used_bytes)
        self.assertTrue(any("invalid path argument" in msg or "disk_usage" in msg.lower()
                            for msg in log_ctx.output))

    @patch("controller.scan.local_scanner.shutil.disk_usage")
    def test_scan_file_list_identity_preserved_across_fallback(self, mock_disk_usage):
        """Regression guard: the files list returned by SystemScanner is passed
        through unchanged by both success and failure capacity paths."""
        mock_disk_usage.side_effect = OSError("unmounted")
        files_fail, _, _ = self.scanner.scan()

        # Reset for success path.
        usage = MagicMock()
        usage.total = 500
        usage.used = 250
        mock_disk_usage.side_effect = None
        mock_disk_usage.return_value = usage
        files_ok, _, _ = self.scanner.scan()

        # Same object returned by the stubbed SystemScanner both times.
        self.assertIs(self.sample_files, files_fail)
        self.assertIs(self.sample_files, files_ok)


if __name__ == "__main__":
    unittest.main()
