import unittest
from unittest.mock import MagicMock
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
        c._update_controller_status(self._result(2_000_100_000_000, 1_015_000_000_000), None)
        self.assertEqual(2_000_100_000_000, c._Controller__context.status.storage.remote_total)
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


if __name__ == "__main__":
    unittest.main()
