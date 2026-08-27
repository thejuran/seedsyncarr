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


class TestActiveScannerTempFileAndBackoff(unittest.TestCase):
    """Tests for ActiveScanner temp-file resolution and log backoff, using the
    real SystemScanner against a temp directory.

    Incident 2026-08-22: with use_temp_file enabled the active scanner looked
    up the final file name while lftp was still writing '<name>.lftp', logging
    'Path does not exist' once per second for the entire transfer (~172k
    lines/day measured). The scanner must resolve temp files like the local
    scanner does, and repeated misses for the same name must back off to
    debug level after the first warning.
    """

    def setUp(self):
        import tempfile
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir_obj.cleanup)
        self.tmpdir = self.tmpdir_obj.name
        from unittest.mock import MagicMock
        import logging
        self.logger = MagicMock(spec=logging.Logger)

    def _make_scanner(self, use_temp_file):
        scanner = ActiveScanner(self.tmpdir, use_temp_file=use_temp_file)
        scanner.logger = self.logger
        return scanner

    def _set_active(self, scanner, names):
        # Direct assignment: the multiprocessing queue's feeder thread makes
        # queue-based delivery timing-dependent in-process; queue plumbing is
        # covered by TestActiveScanner above.
        scanner._ActiveScanner__active_files = list(names)

    def test_resolves_lftp_temp_file_when_enabled(self):
        import os
        with open(os.path.join(self.tmpdir, "a.mkv.lftp"), "w") as f:
            f.write("partial")
        scanner = self._make_scanner(use_temp_file=True)
        self._set_active(scanner, ["a.mkv"])

        files, _, _ = scanner.scan()

        self.assertEqual(1, len(files))
        self.assertEqual("a.mkv", files[0].name)
        self.logger.warning.assert_not_called()

    def test_does_not_resolve_temp_file_when_disabled(self):
        import os
        with open(os.path.join(self.tmpdir, "a.mkv.lftp"), "w") as f:
            f.write("partial")
        scanner = self._make_scanner(use_temp_file=False)
        self._set_active(scanner, ["a.mkv"])

        files, _, _ = scanner.scan()

        self.assertEqual(0, len(files))

    def test_missing_path_warns_only_once_then_debug(self):
        scanner = self._make_scanner(use_temp_file=True)
        self._set_active(scanner, ["missing.mkv"])

        scanner.scan()
        scanner.scan()
        scanner.scan()

        self.assertEqual(1, self.logger.warning.call_count)
        self.assertGreaterEqual(self.logger.debug.call_count, 2)

    def test_miss_counter_resets_when_file_appears(self):
        import os
        scanner = self._make_scanner(use_temp_file=True)
        self._set_active(scanner, ["late.mkv"])
        scanner.scan()  # miss -> warning

        with open(os.path.join(self.tmpdir, "late.mkv"), "w") as f:
            f.write("data")
        scanner.scan()  # hit -> counter reset

        os.remove(os.path.join(self.tmpdir, "late.mkv"))
        scanner.scan()  # miss again -> warns again

        self.assertEqual(2, self.logger.warning.call_count)
