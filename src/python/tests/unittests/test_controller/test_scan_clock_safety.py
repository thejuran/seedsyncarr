"""
Composed scan-clock safety regressions (XFER-04, XFER-05).

These tests drive the production write path (Controller._update_controller_status)
and the production read path (AutoQueue.process) through one real Status object,
so they are agnostic to where the successful-scan clock is stored. A failed
scanner result must never make a file look stable: the model pipeline does not
apply failed results, so the model keeps the last successful (possibly stale)
sizes, and time spent failing is not an observation of those sizes.

The tests assert only on queued commands and on the existing user-facing status
fields (latest_remote_scan_time, latest_remote_scan_failed, latest_local_scan_time),
whose meaning -- "time of the latest scan attempt" -- must stay unchanged.
"""
import logging
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from common import Config, Status
from controller import AutoQueue, AutoQueuePersist, Controller, ScannerResult
from model import ModelFile


T0 = datetime(2026, 10, 8, 12, 0, 0)


class TestStabilityOnSuccessfulScanClock(unittest.TestCase):
    """
    Failed remote/local scans can neither advance the stability clock nor reset
    it. A size change seen by the first successful scan after an outage
    restarts the window; a matching size is stable once two successful
    observations are at least the window apart.
    """

    FILE = "File.One"
    REMOTE_WINDOW = 90
    LOCAL_WINDOW = 30

    def setUp(self):
        self.logger = logging.getLogger(TestStabilityOnSuccessfulScanClock.__name__)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.setLevel(logging.DEBUG)

        # Production status write path: Controller with a real Status.
        self.controller = Controller.__new__(Controller)
        self.ctx = MagicMock()
        self.ctx.status = Status()
        self.controller._Controller__context = self.ctx

        # Production status read path: AutoQueue sharing the same Status.
        self.aq_ctx = MagicMock()
        self.aq_ctx.status = self.ctx.status
        self.aq_ctx.config = Config()
        self.aq_ctx.config.autoqueue.enabled = True
        self.aq_ctx.config.autoqueue.patterns_only = False
        self.aq_ctx.config.autoqueue.auto_extract = False
        self.aq_ctx.logger = self.logger

        self.aq_controller = MagicMock()
        self.aq_controller.queue_command = MagicMock()
        self.model_files = []
        self.model_listener = None

        def add_listener_and_get(listener):
            self.model_listener = listener
            return list(self.model_files)

        self.aq_controller.get_model_files.side_effect = lambda: list(self.model_files)
        self.aq_controller.get_model_files_and_add_listener.side_effect = add_listener_and_get
        self.aq_controller.is_file_stopped.side_effect = lambda n: False
        self.aq_controller.is_file_downloaded.side_effect = lambda n: False

        self.auto_queue = None

    def tearDown(self):
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)

    # ------------------------------------------------------------------ helpers

    def _configure(self, remote_window, local_window):
        self.aq_ctx.config.autoqueue.remote_stability_seconds = remote_window
        self.aq_ctx.config.autoqueue.local_stability_seconds = local_window
        self.auto_queue = AutoQueue(self.aq_ctx, AutoQueuePersist(), self.aq_controller)

    def _apply_model(self, remote_size, local_size):
        """Model pipeline applies a successful scan: replace the model file."""
        f = ModelFile(self.FILE, False)
        f.remote_size = remote_size
        f.local_size = local_size
        f.state = ModelFile.State.DEFAULT
        old = self.model_files[0] if self.model_files else None
        self.model_files = [f]
        if self.model_listener is not None:
            if old is None:
                self.model_listener.file_added(f)
            elif old.remote_size != f.remote_size or old.local_size != f.local_size:
                self.model_listener.file_updated(old, f)

    def _remote(self, t_seconds, failed, size):
        """
        Remote scanner result at T0 + t_seconds. A successful result also lands
        in the model (remote size, no local copy); a failed one leaves the model
        stale, exactly as the model pipeline does.
        """
        result = ScannerResult(timestamp=T0 + timedelta(seconds=t_seconds),
                               files=[], failed=failed)
        if not failed:
            self._apply_model(remote_size=size, local_size=None)
        return result

    def _local(self, t_seconds, failed, size, remote_size=1000):
        """
        Local scanner result at T0 + t_seconds. A successful result also lands
        in the model (partial local copy of a larger remote); a failed one
        leaves the model stale.
        """
        result = ScannerResult(timestamp=T0 + timedelta(seconds=t_seconds),
                               files=[], failed=failed)
        if not failed:
            self._apply_model(remote_size=remote_size, local_size=size)
        return result

    def _queued(self):
        return self.aq_controller.queue_command.call_count

    def _assert_last_command_is_queue(self):
        command = self.aq_controller.queue_command.call_args[0][0]
        self.assertEqual(Controller.Command.Action.QUEUE, command.action)
        self.assertEqual(self.FILE, command.filename)

    # ------------------------------------------------------------ remote clock

    def test_failed_remote_scans_spanning_window_do_not_queue(self):
        """XFER-04 / D-03: failed remote scans must not establish stability."""
        self._configure(remote_window=self.REMOTE_WINDOW, local_window=0)

        self.controller._update_controller_status(self._remote(0, False, 100), None)
        self.auto_queue.process()
        self.assertEqual(0, self._queued(), "file must not queue on first sighting")

        for t in (30, 60, 90, 120, 300):
            self.controller._update_controller_status(self._remote(t, True, 100), None)
            self.auto_queue.process()
            self.assertEqual(0, self._queued(),
                             "failed remote scans must not advance the stability "
                             "clock (XFER-04, D-03) [t={}]".format(t))

        # D-06: the user-facing fields keep meaning "latest scan attempt".
        status = self.ctx.status.controller
        self.assertEqual(T0 + timedelta(seconds=300), status.latest_remote_scan_time)
        self.assertIs(True, status.latest_remote_scan_failed)

    def test_remote_recovery_with_matching_size_queues(self):
        """D-03 preservation: matching size across an outage is stable."""
        self._configure(remote_window=self.REMOTE_WINDOW, local_window=0)

        self.controller._update_controller_status(self._remote(0, False, 100), None)
        self.auto_queue.process()
        for t in (30, 60):
            self.controller._update_controller_status(self._remote(t, True, 100), None)
            self.auto_queue.process()
            self.assertEqual(0, self._queued(),
                             "nothing may queue inside the window [t={}]".format(t))

        self.controller._update_controller_status(self._remote(100, False, 100), None)
        self.auto_queue.process()
        self.assertEqual(1, self._queued(),
                         "matching size seen by two successful scans >= window apart "
                         "must queue")
        self._assert_last_command_is_queue()
        self.assertIs(False, self.ctx.status.controller.latest_remote_scan_failed)

    def test_remote_recovery_with_changed_size_restarts_window(self):
        """XFER-04 / D-04: a size change after an outage restarts the window."""
        self._configure(remote_window=self.REMOTE_WINDOW, local_window=0)

        self.controller._update_controller_status(self._remote(0, False, 100), None)
        self.auto_queue.process()
        for t in (30, 60, 90, 120, 150):
            self.controller._update_controller_status(self._remote(t, True, 100), None)
            self.auto_queue.process()
            self.assertEqual(0, self._queued(),
                             "failed remote scans must not establish stability during "
                             "the outage (XFER-04, D-03/D-04) [t={}]".format(t))

        self.controller._update_controller_status(self._remote(180, False, 150), None)
        self.auto_queue.process()
        self.assertEqual(0, self._queued(),
                         "a size change after the outage restarts the window (D-04)")

        self.controller._update_controller_status(self._remote(240, False, 150), None)
        self.auto_queue.process()
        self.assertEqual(0, self._queued(), "restarted window has not elapsed yet")

        self.controller._update_controller_status(self._remote(271, False, 150), None)
        self.auto_queue.process()
        self.assertEqual(1, self._queued(),
                         "file must queue once the restarted window elapses")
        self._assert_last_command_is_queue()

    # ------------------------------------------------------------- local clock
    #
    # No remote scan is ever written in these tests, so the remote clock stays
    # None and the sweep cooldown (which runs on the remote clock) is skipped.

    def test_failed_local_scans_spanning_window_do_not_queue(self):
        """XFER-05 / D-03 / D-05: failed local scans must not establish idleness."""
        self._configure(remote_window=0, local_window=self.LOCAL_WINDOW)

        self.controller._update_controller_status(None, self._local(0, False, 400))
        self.auto_queue.process()
        self.assertEqual(0, self._queued(), "partial must not be swept on first sighting")

        for t in (10, 20, 30, 40, 120):
            self.controller._update_controller_status(None, self._local(t, True, 400))
            self.auto_queue.process()
            self.assertEqual(0, self._queued(),
                             "failed local scans must not advance the local stability "
                             "clock (XFER-05, D-03/D-05) [t={}]".format(t))

        # D-06: the user-facing field keeps meaning "latest scan attempt".
        self.assertEqual(T0 + timedelta(seconds=120),
                         self.ctx.status.controller.latest_local_scan_time)

    def test_local_recovery_with_changed_size_restarts_window(self):
        """XFER-05 / D-04 / D-05: a local size change after an outage restarts the window."""
        self._configure(remote_window=0, local_window=self.LOCAL_WINDOW)

        self.controller._update_controller_status(None, self._local(0, False, 400))
        self.auto_queue.process()
        for t in (10, 20, 30, 40, 50, 60):
            self.controller._update_controller_status(None, self._local(t, True, 400))
            self.auto_queue.process()
            self.assertEqual(0, self._queued(),
                             "failed local scans must not establish idleness during the "
                             "outage (XFER-05, D-03/D-05) [t={}]".format(t))

        self.controller._update_controller_status(None, self._local(70, False, 600))
        self.auto_queue.process()
        self.assertEqual(0, self._queued(),
                         "a local size change after the outage restarts the window (D-04)")

        self.controller._update_controller_status(None, self._local(90, False, 600))
        self.auto_queue.process()
        self.assertEqual(0, self._queued(), "restarted local window has not elapsed yet")

        self.controller._update_controller_status(None, self._local(101, False, 600))
        self.auto_queue.process()
        self.assertEqual(1, self._queued(),
                         "partial must be swept once the restarted window elapses")
        self._assert_last_command_is_queue()

    def test_local_recovery_with_matching_size_queues(self):
        """D-03 / D-05 preservation: matching local size across an outage is idle."""
        self._configure(remote_window=0, local_window=self.LOCAL_WINDOW)

        self.controller._update_controller_status(None, self._local(0, False, 400))
        self.auto_queue.process()
        for t in (10, 20):
            self.controller._update_controller_status(None, self._local(t, True, 400))
            self.auto_queue.process()
            self.assertEqual(0, self._queued(),
                             "nothing may queue inside the window [t={}]".format(t))

        self.controller._update_controller_status(None, self._local(31, False, 400))
        self.auto_queue.process()
        self.assertEqual(1, self._queued(),
                         "matching local size seen by two successful scans >= window "
                         "apart must be swept")
        self._assert_last_command_is_queue()
        self.assertEqual(T0 + timedelta(seconds=31),
                         self.ctx.status.controller.latest_local_scan_time)


if __name__ == "__main__":
    unittest.main()
