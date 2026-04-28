import queue
import unittest
from unittest.mock import patch

from controller.scan.active_scanner import ActiveScanner
from system import SystemScannerError, SystemFile


class TestActiveScanner(unittest.TestCase):
    """
    Unit tests for ActiveScanner.

    Mocks multiprocessing.Queue (replaced with stdlib queue.Queue to avoid
    pickle issues with MagicMock) and SystemScanner at the module level.

    Does NOT duplicate the 3-tuple contract test already in
    test_scanner_process.py::TestIScannerContract.

    Test paths (per D-12):
    - Empty queue on first scan
    - Single set_active_files then scan
    - Multiple set_active_files calls (drain loop -- last list wins)
    - SystemScannerError suppression
    """

    def setUp(self):
        # Patch multiprocessing.Queue to use stdlib queue.Queue (no pickle needed)
        queue_patcher = patch(
            'controller.scan.active_scanner.multiprocessing.Queue',
            side_effect=lambda: queue.Queue()
        )
        self.addCleanup(queue_patcher.stop)
        queue_patcher.start()

        scanner_patcher = patch('controller.scan.active_scanner.SystemScanner')
        self.addCleanup(scanner_patcher.stop)
        self.mock_scanner_cls = scanner_patcher.start()
        self.mock_scanner = self.mock_scanner_cls.return_value

    def test_scan_returns_empty_on_first_call(self):
        scanner = ActiveScanner("/local/path")
        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_set_active_files_then_scan_returns_scanned_file(self):
        scanner = ActiveScanner("/local/path")
        f = SystemFile("a.mkv", 100, False)
        self.mock_scanner.scan_single.return_value = f
        scanner.set_active_files(["a.mkv"])
        files, total, used = scanner.scan()
        self.assertEqual([f], files)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_scan_drains_all_queued_puts_uses_last(self):
        """Multiple set_active_files calls -- queue drains; last list is used."""
        scanner = ActiveScanner("/local/path")
        f_new = SystemFile("new.mkv", 20, False)
        self.mock_scanner.scan_single.return_value = f_new
        scanner.set_active_files(["old.mkv"])
        scanner.set_active_files(["new.mkv"])
        files, _, _ = scanner.scan()
        # Drain loop consumes both puts; last list ("new.mkv") wins
        self.assertEqual(1, len(files))
        self.assertEqual("new.mkv", files[0].name)

    def test_scan_suppresses_system_scanner_error(self):
        scanner = ActiveScanner("/local/path")
        scanner.set_active_files(["missing.mkv"])
        self.mock_scanner.scan_single.side_effect = SystemScannerError("not found")
        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertIsNone(total)
        self.assertIsNone(used)
