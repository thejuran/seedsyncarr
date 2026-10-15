import threading
from unittest.mock import MagicMock, patch

import pytest

from controller import Controller
from controller.controller import _AUTO_DELETE_MAX_REARMS
from model import ModelFile, ModelError
from tests.unittests.test_controller.test_auto_delete import BaseAutoDeleteTestCase


INCIDENT_ROOT = "The.Burbs.1989.2160p.UHD.BluRay.x265-B0MBARDiERS"


class BaseAutoDeleteRearmTestCase(BaseAutoDeleteTestCase):
    """
    Incident 2026-09-16: the auto-delete Timer fired while the root was still
    EXTRACTING, logged a skip, and was never re-armed -- the 77 GB local copy
    stayed forever. A skip for a retriable reason must now re-arm the Timer,
    bounded by _AUTO_DELETE_MAX_REARMS.
    """

    def setUp(self):
        super().setUp()
        self.persist.downloaded_file_names.add(INCIDENT_ROOT)

    def _make_file(self, state=ModelFile.State.DOWNLOADED, is_dir=False, children=None):
        mock_file = MagicMock(spec=ModelFile)
        mock_file.state = state
        mock_file.is_dir = is_dir
        mock_file.get_children.return_value = children or []
        return mock_file

    def _make_child(self, name, state=ModelFile.State.DOWNLOADED, children=None, is_dir=None):
        child = MagicMock(spec=ModelFile)
        child.name = name
        child.state = state
        child.get_children.return_value = children or []
        child.is_dir = is_dir if is_dir is not None else bool(children)
        return child

    def _set_model_file(self, mock_file):
        self.controller._Controller__model.get_file = MagicMock(return_value=mock_file)

    def _fire(self, file_name):
        self.controller._Controller__execute_auto_delete(file_name)

    def _pending(self):
        return self.controller._Controller__pending_auto_deletes

    def _rearms(self):
        return self.controller._Controller__auto_delete_rearms

    def _info_messages(self):
        return [str(c.args[0]) for c in self.controller.logger.info.call_args_list if c.args]

    def _warning_messages(self):
        return [str(c.args[0]) for c in self.controller.logger.warning.call_args_list if c.args]

    @staticmethod
    def _deferred_line(file_name, attempt, reason, delay=10, limit=_AUTO_DELETE_MAX_REARMS):
        return "Auto-delete deferred for '{}' (attempt {}/{}): {}; retrying in {} s".format(
            file_name, attempt, limit, reason, delay
        )

    @staticmethod
    def _given_up_line(file_name, reason, limit=_AUTO_DELETE_MAX_REARMS):
        return "Auto-delete given up for '{}' after {} deferrals; last reason: {}. " \
               "Local copy left in place".format(file_name, limit, reason)


class TestAutoDeleteDeferral(BaseAutoDeleteRearmTestCase):
    """Retriable skips re-arm; terminal skips do not."""

    def test_incident_replay_webhook_during_extracting_defers_then_deletes(self):
        """21:29 webhook accepted while EXTRACTING -> ~21:34 fire defers ->
        21:39 extraction done -> next fire deletes."""
        self._make_controller_started()
        f = ModelFile(INCIDENT_ROOT, True)
        f.state = ModelFile.State.EXTRACTING
        f.remote_size = 38_482_836_588
        f.local_size = 44_000_000_000  # rars + partial mkv: passes the evidence gate
        self.controller._Controller__model.add_file(f)
        self.mock_webhook_manager.process.return_value = [(INCIDENT_ROOT, "The.Burbs.1989.mkv")]

        # Webhook accepted -> Timer armed
        self.controller.process()
        self.assertIn(INCIDENT_ROOT, self._pending())
        first_timer = self._pending()[INCIDENT_ROOT]
        self.assertNotIn(INCIDENT_ROOT, self._rearms())

        # Timer fires while the root is still EXTRACTING -> deferred, re-armed
        mock_file = self._make_file(state=ModelFile.State.EXTRACTING, is_dir=True)
        self._set_model_file(mock_file)
        self._fire(INCIDENT_ROOT)
        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertIn(INCIDENT_ROOT, self._pending())
        self.assertIsNot(first_timer, self._pending()[INCIDENT_ROOT])
        self.assertTrue(self._pending()[INCIDENT_ROOT].is_alive())
        self.assertEqual(1, self._rearms()[INCIDENT_ROOT])
        self.assertIn(
            self._deferred_line(INCIDENT_ROOT, 1, "file is in state {}".format(ModelFile.State.EXTRACTING)),
            self._info_messages()
        )
        # The old one-shot wording is gone: it is a deferral, not a skip
        self.assertFalse([m for m in self._info_messages() if m.startswith("Auto-delete skipped")])

        # Extraction finished -> next fire deletes and clears the counter
        mock_file.state = ModelFile.State.EXTRACTED
        self._fire(INCIDENT_ROOT)
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
        self.assertNotIn(INCIDENT_ROOT, self._pending())
        self.assertNotIn(INCIDENT_ROOT, self._rearms())
        self.assertNotIn(INCIDENT_ROOT, self.persist.imported_children)

    def test_unsafe_child_defers_then_succeeds(self):
        child = self._make_child("ep02.mkv", state=ModelFile.State.EXTRACTING)
        mock_file = self._make_file(is_dir=True, children=[child])
        self._set_model_file(mock_file)

        self._fire("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertIn("Pack.S01", self._pending())
        self.assertEqual(1, self._rearms()["Pack.S01"])
        self.assertIn(
            self._deferred_line("Pack.S01", 1, "a child is still in an active state"),
            self._info_messages()
        )

        child.state = ModelFile.State.EXTRACTED
        self._fire("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
        self.assertNotIn("Pack.S01", self._pending())
        self.assertNotIn("Pack.S01", self._rearms())

    def test_partial_coverage_defers_then_succeeds(self):
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_file(is_dir=True, children=[child_a, child_b])
        self._set_model_file(mock_file)
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")

        self._fire("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertIn("Pack.S01", self._pending())
        self.assertEqual(1, self._rearms()["Pack.S01"])
        self.assertIn(
            self._deferred_line("Pack.S01", 1, "not every on-disk video child has been imported yet"),
            self._info_messages()
        )
        # The per-child entry is left intact for the retry
        self.assertIn("Pack.S01", self.persist.imported_children)

        # Sonarr imports the second episode
        self.persist.add_imported_child("Pack.S01", "ep02.mkv")
        self._fire("Pack.S01")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
        self.assertNotIn("Pack.S01", self._pending())
        self.assertNotIn("Pack.S01", self._rearms())

    def test_bfs_limit_is_terminal_and_does_not_rearm(self):
        child_a = self._make_child("ep01.mkv")
        child_b = self._make_child("ep02.mkv")
        mock_file = self._make_file(is_dir=True, children=[child_a, child_b])
        self._set_model_file(mock_file)
        self.persist.add_imported_child("Pack.S01", "ep01.mkv")
        self._rearms()["Pack.S01"] = 3

        with patch("controller.auto_delete_manager._AUTO_DELETE_BFS_NODE_LIMIT", 1):
            self._fire("Pack.S01")

        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertNotIn("Pack.S01", self._pending())
        self.assertNotIn("Pack.S01", self._rearms())
        self.assertNotIn("Pack.S01", self.persist.imported_children)
        self.assertFalse([m for m in self._info_messages() if m.startswith("Auto-delete deferred")])

    def test_gives_up_after_max_rearms_with_one_warning(self):
        self._rearms()["test_file.mkv"] = _AUTO_DELETE_MAX_REARMS
        self._set_model_file(self._make_file(state=ModelFile.State.EXTRACTING))

        self._fire("test_file.mkv")

        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertNotIn("test_file.mkv", self._pending())
        self.assertNotIn("test_file.mkv", self._rearms())
        self.assertEqual(
            [self._given_up_line("test_file.mkv", "file is in state {}".format(ModelFile.State.EXTRACTING))],
            self._warning_messages()
        )
        self.assertFalse([m for m in self._info_messages() if m.startswith("Auto-delete deferred")])

    def test_deferrals_accumulate_then_give_up(self):
        mock_file = self._make_file(state=ModelFile.State.EXTRACTING)
        self._set_model_file(mock_file)
        reason = "file is in state {}".format(ModelFile.State.EXTRACTING)

        with patch("controller.controller._AUTO_DELETE_MAX_REARMS", 2):
            self._fire("test_file.mkv")
            self.assertEqual(1, self._rearms()["test_file.mkv"])
            self.assertIn("test_file.mkv", self._pending())
            self._fire("test_file.mkv")
            self.assertEqual(2, self._rearms()["test_file.mkv"])
            self.assertIn("test_file.mkv", self._pending())
            self._fire("test_file.mkv")

        self.assertNotIn("test_file.mkv", self._pending())
        self.assertNotIn("test_file.mkv", self._rearms())
        self.mock_file_op_manager.delete_local.assert_not_called()
        deferred = [m for m in self._info_messages() if m.startswith("Auto-delete deferred")]
        self.assertEqual(
            [
                self._deferred_line("test_file.mkv", 1, reason, limit=2),
                self._deferred_line("test_file.mkv", 2, reason, limit=2),
            ],
            deferred
        )
        self.assertEqual([self._given_up_line("test_file.mkv", reason, limit=2)], self._warning_messages())

    def test_successful_delete_clears_counter(self):
        self._rearms()["test_file.mkv"] = 3
        mock_file = self._make_file()
        self._set_model_file(mock_file)

        self._fire("test_file.mkv")

        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
        self.assertNotIn("test_file.mkv", self._rearms())
        self.assertNotIn("test_file.mkv", self._pending())

    def test_fresh_webhook_arm_resets_counter(self):
        self._rearms()["test_file.mkv"] = 5

        self.controller._Controller__schedule_auto_delete("test_file.mkv")

        self.assertNotIn("test_file.mkv", self._rearms())
        self.assertIn("test_file.mkv", self._pending())


class TestAutoDeleteTerminalSkipsDoNotRearm(BaseAutoDeleteRearmTestCase):
    """Each terminal skip leaves no Timer armed and clears the deferral counter."""

    def _assert_terminal(self, file_name):
        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertNotIn(file_name, self._pending())
        self.assertNotIn(file_name, self._rearms())
        self.assertFalse([m for m in self._info_messages() if m.startswith("Auto-delete deferred")])

    def test_feature_disabled(self):
        self._rearms()["test_file.mkv"] = 3
        self.mock_context.config.autodelete.enabled = False
        self._fire("test_file.mkv")
        self._assert_terminal("test_file.mkv")

    def test_dry_run(self):
        self._rearms()["test_file.mkv"] = 3
        self.mock_context.config.autodelete.dry_run = True
        self._set_model_file(self._make_file(state=ModelFile.State.EXTRACTING))
        self._fire("test_file.mkv")
        self._assert_terminal("test_file.mkv")

    def test_file_gone_from_model(self):
        self._rearms()["test_file.mkv"] = 3
        self.controller._Controller__model.get_file = MagicMock(side_effect=ModelError("not found"))
        self._fire("test_file.mkv")
        self._assert_terminal("test_file.mkv")

    def test_no_download_evidence(self):
        self._rearms()["foreign.mkv"] = 3
        self._set_model_file(self._make_file(state=ModelFile.State.EXTRACTING))
        self._fire("foreign.mkv")  # never added to downloaded_file_names
        self._assert_terminal("foreign.mkv")

    def test_duplicate_basename_is_terminal_and_does_not_rearm(self):
        """Duplicate video basenames (Disc1/movie.mkv + Disc2/movie.mkv) are a
        structural property of a settled pack and do not clear with time, so
        re-arming the Timer up to the deferral budget would only add log noise.
        The skip is terminal: no re-arm, counter cleared, per-child entry
        popped, one WARNING. A later webhook still re-arms and the guard runs
        again on that firing."""
        disc1 = self._make_child("Disc1", children=[self._make_child("movie.mkv")])
        disc2 = self._make_child("Disc2", children=[self._make_child("movie.mkv")])
        self._set_model_file(self._make_file(is_dir=True, children=[disc1, disc2]))
        self.persist.add_imported_child("Pack.S01", "movie.mkv")
        self._rearms()["Pack.S01"] = 3

        self._fire("Pack.S01")

        self._assert_terminal("Pack.S01")
        self.assertNotIn("Pack.S01", self.persist.imported_children)
        skipped = [
            m for m in self._warning_messages()
            if m.startswith("Auto-delete skipped for 'Pack.S01'") and "more than one path" in m
        ]
        self.assertEqual(1, len(skipped), "expected one duplicate-basename WARNING, got {}".format(
            self._warning_messages()))


class TestAutoDeleteDeferralShutdown(BaseAutoDeleteRearmTestCase):
    """BUG-03 criteria hold for re-armed timers: exit() cancels them and
    nothing arms a Timer once shutdown has begun."""

    def test_exit_cancels_rearmed_timer(self):
        self.mock_context.config.autodelete.delay_seconds = 300
        self._set_model_file(self._make_file(state=ModelFile.State.EXTRACTING))

        self._fire("test_file.mkv")
        timer = self._pending()["test_file.mkv"]
        self.assertTrue(timer.is_alive())
        self.assertEqual(1, self._rearms()["test_file.mkv"])

        self.controller._Controller__started = True
        self.controller.exit()

        self.assertEqual({}, self._pending())
        self.assertEqual({}, self._rearms())
        self.assertTrue(timer.finished.is_set())

    def test_no_rearm_when_shutdown_begins_mid_callback(self):
        """Shutdown is signalled after the entry guard but before the deferral
        step: the retriable skip must NOT arm a new Timer."""
        mock_file = self._make_file(state=ModelFile.State.EXTRACTING)

        def _get_file_then_shutdown(name):
            self.controller._Controller__shutdown_event.set()
            return mock_file
        self.controller._Controller__model.get_file = MagicMock(side_effect=_get_file_then_shutdown)

        self._fire("test_file.mkv")

        self.assertEqual({}, self._pending())
        self.assertEqual({}, self._rearms())
        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_fire_after_exit_is_noop(self):
        self._set_model_file(self._make_file(state=ModelFile.State.EXTRACTING))
        self.controller._Controller__started = True
        self.controller.exit()

        self._fire("test_file.mkv")

        self.assertEqual({}, self._pending())
        self.assertEqual({}, self._rearms())


class TestAutoDeleteDeferralTimerIntegration(BaseAutoDeleteRearmTestCase):
    """A re-armed Timer really fires __execute_auto_delete again."""

    @pytest.mark.timeout(10)
    def test_rearmed_timer_fires_and_deletes_once_root_is_deletable(self):
        self.mock_context.config.autodelete.delay_seconds = 0.05
        mock_file = self._make_file(state=ModelFile.State.EXTRACTING)
        self._set_model_file(mock_file)
        deleted = threading.Event()
        self.mock_file_op_manager.delete_local.side_effect = lambda _file: deleted.set()

        # First firing defers and arms a real 50 ms Timer
        self._fire("test_file.mkv")
        self.assertIn("test_file.mkv", self._pending())
        # The root becomes deletable before the re-armed Timer fires
        mock_file.state = ModelFile.State.EXTRACTED

        self.assertTrue(deleted.wait(5), "re-armed Timer never fired")
        self.mock_file_op_manager.delete_local.assert_called_once_with(mock_file)
        self.assertNotIn("test_file.mkv", self._rearms())


class TestAutoDeleteSubmittedUnobserved(BaseAutoDeleteRearmTestCase):
    """DEL-01: a QUEUE lftp accepted but no successful status has observed
    yet leaves the model on its stale-retained state (XFER-02). The Timer must
    defer instead of deleting the copy lftp is about to rewrite."""

    SUBMITTED_REASON = "transfer submitted, awaiting lftp status"

    def setUp(self):
        super().setUp()
        self.mock_lftp_manager.status.return_value = None
        self.mock_lftp_manager.submitted_unobserved_file_names.return_value = [INCIDENT_ROOT]
        self.mock_file = self._make_file(state=ModelFile.State.DOWNLOADED, is_dir=False)
        self.mock_file.name = INCIDENT_ROOT
        self._set_model_file(self.mock_file)

    def test_timer_defers_when_root_submitted_unobserved_and_status_unavailable(self):
        self._fire(INCIDENT_ROOT)

        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertIn(INCIDENT_ROOT, self._pending())
        self.assertEqual(1, self._rearms()[INCIDENT_ROOT])
        self.assertIn(
            self._deferred_line(INCIDENT_ROOT, 1, self.SUBMITTED_REASON),
            self._info_messages()
        )

    def test_timer_deletes_after_status_observed_clears_submitted_set(self):
        self.persist.add_imported_child(INCIDENT_ROOT, "The.Burbs.1989.mkv")
        self._fire(INCIDENT_ROOT)
        self.mock_file_op_manager.delete_local.assert_not_called()

        # A successful status (the job need not appear active) clears the set
        self.mock_lftp_manager.submitted_unobserved_file_names.return_value = []
        self._fire(INCIDENT_ROOT)

        self.mock_file_op_manager.delete_local.assert_called_once()
        self.assertIs(self.mock_file, self.mock_file_op_manager.delete_local.call_args[0][0])
        self.assertNotIn(INCIDENT_ROOT, self._pending())
        self.assertNotIn(INCIDENT_ROOT, self._rearms())
        self.assertNotIn(INCIDENT_ROOT, self.persist.imported_children)

    def test_submitted_guard_runs_after_state_guard_and_respects_rearm_budget(self):
        # State guard wins when the root is mid-lifecycle
        self.mock_file.state = ModelFile.State.DOWNLOADING
        self._fire(INCIDENT_ROOT)
        self.assertIn(
            self._deferred_line(INCIDENT_ROOT, 1, "file is in state {}".format(ModelFile.State.DOWNLOADING)),
            self._info_messages()
        )

        # Submitted guard holds across the whole re-arm budget, then gives up
        self.mock_file.state = ModelFile.State.DOWNLOADED
        for _ in range(_AUTO_DELETE_MAX_REARMS):
            self._fire(INCIDENT_ROOT)

        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertNotIn(INCIDENT_ROOT, self._pending())
        self.assertNotIn(INCIDENT_ROOT, self._rearms())
        self.assertEqual(
            [self._given_up_line(INCIDENT_ROOT, self.SUBMITTED_REASON)],
            self._warning_messages()
        )


class TestAutoDeleteRootReservation(BaseAutoDeleteRearmTestCase):
    """DEL-01 / codex findings: the Timer releases __model_lock before
    delete_local and __process_commands releases it before
    CommandProcessor.handle, so a per-root reservation serializes deletion
    against queue submission. delete_local only STARTS the deletion child, so
    the reservation outlives it; here the captured token's release() stands
    in for cleanup_completed_processes observing the child's exit."""

    WAIT = 5

    def setUp(self):
        super().setUp()
        self._make_controller_started()
        self.mock_lftp_manager.submitted_unobserved_file_names.return_value = []
        self.mock_file = self._make_file(state=ModelFile.State.DOWNLOADED, is_dir=False)
        self.mock_file.name = INCIDENT_ROOT
        self.mock_file.remote_size = 1234
        self.mock_file.local_size = 1234
        self._set_model_file(self.mock_file)
        self._captured = []

    def tearDown(self):
        for token in self._captured:
            if token is not None:
                token.release()
        super().tearDown()

    def _reservations(self):
        return self.controller._Controller__root_reservations

    def _capturing_delete_local(self, block_on=None, signal=None):
        captured = self._captured

        def _se(_file, reservation=None):
            captured.append(reservation)
            if signal is not None:
                signal.set()
            if block_on is not None:
                block_on.wait(timeout=self.WAIT)
            return True
        return _se, captured

    def _start_thread(self, target):
        errors = []

        def _run():
            try:
                target()
            except Exception as e:  # pragma: no cover - surfaced via errors
                errors.append(e)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t, errors

    def _assert_refused_409(self, cb):
        cb.on_success.assert_not_called()
        cb.on_failure.assert_called_once()
        msg, code = cb.on_failure.call_args[0]
        self.assertEqual(409, code)
        self.assertIn("operation in progress", msg)

    def test_queue_refused_while_auto_delete_holds_root(self):
        deleting = threading.Event()
        proceed = threading.Event()
        se, captured = self._capturing_delete_local(block_on=proceed, signal=deleting)
        self.mock_file_op_manager.delete_local.side_effect = se
        t, errors = self._start_thread(lambda: self._fire(INCIDENT_ROOT))
        try:
            self.assertTrue(deleting.wait(timeout=self.WAIT), "Timer never reached delete_local")
            cb = MagicMock()
            self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT, callbacks=[cb])
            self._assert_refused_409(cb)
            self.mock_lftp_manager.queue.assert_not_called()
        finally:
            proceed.set()
            t.join(timeout=self.WAIT)
        self.assertFalse(t.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(1, self.mock_file_op_manager.delete_local.call_count)
        # delete_local returned but the child is still deleting
        self.assertEqual("auto-delete", self._reservations().holder_of(INCIDENT_ROOT))

        captured[0].release()
        self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT)
        self.mock_lftp_manager.queue.assert_called_once_with(INCIDENT_ROOT, False)

    def test_queue_stays_refused_after_delete_local_returns_until_subprocess_exits(self):
        se, captured = self._capturing_delete_local()
        self.mock_file_op_manager.delete_local.side_effect = se

        self._fire(INCIDENT_ROOT)  # Timer callback has fully returned

        self.assertEqual(1, self.mock_file_op_manager.delete_local.call_count)
        self.assertIsNotNone(captured[0], "reservation must be handed to delete_local")
        self.assertEqual("auto-delete", captured[0].holder)
        self.assertEqual("auto-delete", self._reservations().holder_of(INCIDENT_ROOT))

        cb = MagicMock()
        self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT, callbacks=[cb])
        self._assert_refused_409(cb)
        self.mock_lftp_manager.queue.assert_not_called()

        captured[0].release()
        self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT)
        self.mock_lftp_manager.queue.assert_called_once_with(INCIDENT_ROOT, False)

    def test_manual_delete_local_keeps_root_reserved_until_subprocess_exits(self):
        se, captured = self._capturing_delete_local()
        self.mock_file_op_manager.delete_local.side_effect = se

        cb = MagicMock()
        self._queue_and_process_command(Controller.Command.Action.DELETE_LOCAL, INCIDENT_ROOT, callbacks=[cb])
        cb.on_success.assert_called_once()
        self.assertIsNotNone(captured[0], "reservation must be handed to delete_local")
        self.assertEqual("delete", captured[0].holder)
        self.assertEqual("delete", self._reservations().holder_of(INCIDENT_ROOT))

        cb_queue = MagicMock()
        self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT, callbacks=[cb_queue])
        self._assert_refused_409(cb_queue)
        self.mock_lftp_manager.queue.assert_not_called()

        captured[0].release()
        self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT)
        self.mock_lftp_manager.queue.assert_called_once_with(INCIDENT_ROOT, False)

    def test_auto_delete_defers_while_queue_submission_holds_root(self):
        submitting = threading.Event()
        proceed = threading.Event()

        def _queue(_name, _is_dir):
            submitting.set()
            proceed.wait(timeout=self.WAIT)
        self.mock_lftp_manager.queue.side_effect = _queue

        t, errors = self._start_thread(
            lambda: self._queue_and_process_command(Controller.Command.Action.QUEUE, INCIDENT_ROOT)
        )
        try:
            self.assertTrue(submitting.wait(timeout=self.WAIT), "QUEUE never reached lftp.queue")
            self._fire(INCIDENT_ROOT)
            self.mock_file_op_manager.delete_local.assert_not_called()
            self.assertEqual(1, self._rearms()[INCIDENT_ROOT])
            self.assertIn(
                self._deferred_line(INCIDENT_ROOT, 1, "root operation in progress"),
                self._info_messages()
            )
        finally:
            proceed.set()
            t.join(timeout=self.WAIT)
        self.assertFalse(t.is_alive())
        self.assertEqual([], errors)

    def test_manual_delete_local_refused_while_auto_delete_holds_root(self):
        deleting = threading.Event()
        proceed = threading.Event()
        se, captured = self._capturing_delete_local(block_on=proceed, signal=deleting)
        self.mock_file_op_manager.delete_local.side_effect = se
        t, errors = self._start_thread(lambda: self._fire(INCIDENT_ROOT))
        try:
            self.assertTrue(deleting.wait(timeout=self.WAIT), "Timer never reached delete_local")
            cb = MagicMock()
            self._queue_and_process_command(Controller.Command.Action.DELETE_LOCAL, INCIDENT_ROOT, callbacks=[cb])
            self._assert_refused_409(cb)
        finally:
            proceed.set()
            t.join(timeout=self.WAIT)
        self.assertFalse(t.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(1, self.mock_file_op_manager.delete_local.call_count)

    def test_reservation_released_on_every_non_delete_timer_path(self):
        reservations = self._reservations()

        # Defer path
        self.mock_file.state = ModelFile.State.EXTRACTING
        self._fire(INCIDENT_ROOT)
        self.assertIsNone(reservations.holder_of(INCIDENT_ROOT))
        self.mock_file.state = ModelFile.State.DOWNLOADED

        # Evidence-gate terminal path
        self.persist.downloaded_file_names.discard(INCIDENT_ROOT)
        self._fire(INCIDENT_ROOT)
        self.assertIsNone(reservations.holder_of(INCIDENT_ROOT))
        self.persist.downloaded_file_names.add(INCIDENT_ROOT)

        # Shutdown begins mid-callback: the final-commit early return
        shutdown_event = self.controller._Controller__shutdown_event

        def _get_file_then_shutdown(_name):
            shutdown_event.set()
            return self.mock_file
        self.controller._Controller__model.get_file = MagicMock(side_effect=_get_file_then_shutdown)
        self._fire(INCIDENT_ROOT)
        self.assertIsNone(reservations.holder_of(INCIDENT_ROOT))
        shutdown_event.clear()
        self._set_model_file(self.mock_file)

        self.mock_file_op_manager.delete_local.assert_not_called()

        # Delete path: the token outlives the Timer until the child exits
        se, captured = self._capturing_delete_local()
        self.mock_file_op_manager.delete_local.side_effect = se
        self._fire(INCIDENT_ROOT)
        self.assertEqual(1, self.mock_file_op_manager.delete_local.call_count)
        self.assertEqual("auto-delete", reservations.holder_of(INCIDENT_ROOT))
        captured[0].release()
        self.assertIsNone(reservations.holder_of(INCIDENT_ROOT))
