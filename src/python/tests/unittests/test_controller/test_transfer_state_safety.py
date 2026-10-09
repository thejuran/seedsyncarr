"""
Composed downstream tests for transfer-state safety when the lftp status is
unavailable (XFER-02, XFER-03; decisions D-01, D-02).

A tolerated `jobs -v` parse failure, or a `jobs -v` that timed out, is an
incomplete observation of lftp's jobs. It must leave every transfer's last
known protection in place: a DOWNLOADING file stays DOWNLOADING, nothing is
committed to the downloaded list, no QUEUE/EXTRACT/DELETE is issued for it,
and the controller's active-downloading list (fed to the active scanner) is
not cleared. The same holds for a transfer that was submitted to lftp and has
not yet appeared in any successful status. A genuinely empty status, by
contrast, really means "no jobs" and must still clear active state.

These tests observe downstream behavior (model state, persist membership,
issued commands, the active list), not just the status return value. Every
failing path reaches the defect through the REAL Lftp.status and the REAL
Lftp.__run_command over a scripted pexpect process: malformed text, or a
scripted pexpect timeout. None is never injected at the LftpManager.
"""
import logging
import threading
import unittest
from datetime import datetime
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pexpect

from common import Config
from controller import AutoQueue, AutoQueuePersist, Controller, LftpManager
from controller.controller_persist import ControllerPersist
from controller.model_builder import ModelBuilder
from controller.model_pipeline import ModelPipeline
from controller.scan import ScannerResult
from model import Model, ModelFile
from system import SystemFile
from tests.unittests.test_controller.base import BaseControllerTestCase


# Malformed `jobs -v` block (final content line `bad string uh oh`); the real
# parser raises LftpJobStatusParserError on it.
_MALFORMED_JOBS_OUTPUT = """
        [0] queue (sftp://someone:@localhost)
        sftp://someone:@localhost/home/someone
        Now executing: [1] mirror -c /tmp/test_controllerw0sbqxe_/remote/ra /tmp/test_controllerw0sbqxe_/local/ -- 0/1.1k (0%)
        -[2] mirror -c /tmp/test_controllerw0sbqxe_/remote/rb /tmp/test_controllerw0sbqxe_/local/ -- 49/9.3k (0%)
        Commands queued:
        1.  pget -c "/tmp/test_controllerw0sbqxe_/remote/rc" -o "/tmp/test_controllerw0sbqxe_/local/"
        bad string uh oh
        """


def _running_pget_output(basename: str, job_id: int = 1) -> str:
    return """
        [0] queue (sftp://seedsyncarrtest:@localhost:22)
        sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
        Now executing: [{id}] pget -c /tmp/t/remote/{name} -o /tmp/t/local/
        [{id}] pget -c /tmp/t/remote/{name} -o /tmp/t/local/
        sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
        `/tmp/t/remote/{name}', got 500 of 1000 (50%)
        """.format(id=job_id, name=basename)


_RUNNING_PGET_OUTPUT = _running_pget_output("File.One.rar")
_RUNNING_PGET_OTHER_OUTPUT = _running_pget_output("Other.Job.rar")
_RUNNING_PGET_FILE_TWO_OUTPUT = _running_pget_output("File.Two.rar", job_id=1)


class _TimedOut:
    """Script item: the `jobs -v` expect times out with `buffer` captured so far."""

    def __init__(self, buffer: str):
        self.buffer = buffer


def _make_lftp_with_scripted_process(script: list, sent_commands: Optional[List[str]] = None):
    """
    Construct an Lftp over a mocked pexpect process that drives the REAL
    Lftp.__run_command. Every sendline is recorded in `sent_commands`. When the
    last sent command is `jobs -v`, expect pops the next item from `script`
    (the list is consumed in place, so callers may append to it between
    cycles): a str completes with that output; a _TimedOut sets `before` to
    its buffer and raises pexpect.exceptions.TIMEOUT. Every other command
    (setup, property setters, `queue ...`, `kill N`) completes with b"".
    """
    from lftp import Lftp
    if sent_commands is None:
        sent_commands = []

    mock_proc = MagicMock()
    mock_proc.isalive.return_value = True
    mock_proc.before = b""
    mock_proc.after = b""

    def _sendline(command):
        sent_commands.append(command)

    def _expect(pattern, timeout=None):
        if sent_commands and sent_commands[-1] == "jobs -v":
            item = script.pop(0)
            if isinstance(item, _TimedOut):
                mock_proc.before = item.buffer.encode()
                raise pexpect.exceptions.TIMEOUT("scripted")
            mock_proc.before = item.encode()
            return 0
        mock_proc.before = b""
        return 0

    mock_proc.sendline.side_effect = _sendline
    mock_proc.expect.side_effect = _expect

    with patch('pexpect.spawn') as mock_spawn:
        mock_spawn.return_value = mock_proc
        lftp = Lftp(
            address="localhost",
            port=22,
            user="testuser",
            password="testpass",
        )
    return lftp


def _make_real_lftp_manager(script: list, sent_commands: Optional[List[str]] = None) -> LftpManager:
    """Build a real LftpManager around a real Lftp over the scripted process."""
    real_lftp = _make_lftp_with_scripted_process(script, sent_commands)
    context = MagicMock()
    context.logger = logging.getLogger("TestTransferStateSafety")
    context.config.lftp.remote_address = "localhost"
    context.config.lftp.remote_port = 22
    context.config.lftp.remote_username = "testuser"
    context.config.lftp.remote_password = "testpass"  # Test-only credential, mocked process
    context.config.lftp.use_ssh_key = False
    context.config.lftp.remote_path = "/tmp/t/remote"
    context.config.lftp.local_path = "/tmp/t/local"
    context.config.lftp.num_max_parallel_downloads = 2
    context.config.lftp.num_max_parallel_files_per_download = 3
    context.config.lftp.num_max_connections_per_root_file = 4
    context.config.lftp.num_max_connections_per_dir_file = 2
    context.config.lftp.num_max_total_connections = 8
    context.config.lftp.use_temp_file = True
    context.config.lftp.rate_limit = 0
    context.config.general.verbose = False
    with patch('controller.lftp_manager.Lftp', return_value=real_lftp):
        return LftpManager(context)


def _scan(files: Optional[List[SystemFile]]) -> Optional[ScannerResult]:
    if files is None:
        return None
    return ScannerResult(timestamp=datetime.now(), files=files)


class TestStatusUnavailableKeepsTransferProtection(unittest.TestCase):
    """
    Real LftpManager -> real ModelPipeline / ModelBuilder / Model -> AutoQueue.
    Cycle 1 (baseline) observes File.One.rar running and lets the sweep submit
    File.Two.rar to lftp; each test then drives one or more further cycles.
    """

    T0 = 1_000_000

    def setUp(self):
        self.logger = logging.getLogger(TestStatusUnavailableKeepsTransferProtection.__name__)
        self.logger.setLevel(logging.DEBUG)

        # jobs -v script, consumed in place; _cycle appends one item per cycle
        self.script = []
        self.sent_commands = []
        self.real_lftp_manager = _make_real_lftp_manager(self.script, self.sent_commands)

        self.context = MagicMock()
        self.context.config = Config()
        self.context.config.autoqueue.enabled = True
        self.context.config.autoqueue.patterns_only = False
        self.context.config.autoqueue.auto_extract = True
        self.context.config.autoqueue.remote_stability_seconds = 0
        self.context.config.autoqueue.local_stability_seconds = 0
        self.context.logger = self.logger
        self.context.status.controller.latest_remote_scan_time = None
        self.context.status.controller.latest_local_scan_time = None
        self.context.status.controller.latest_successful_remote_scan_time = None
        self.context.status.controller.latest_successful_local_scan_time = None

        self.model = Model()
        self.model.set_base_logger(self.logger)
        self.builder = ModelBuilder()
        self.builder.set_base_logger(self.logger)
        self.builder.set_downloaded_files(set())
        self.persist = ControllerPersist(max_tracked_files=100)

        self.scan_manager = MagicMock()
        self.scan_manager.pop_latest_results.return_value = (None, None, None)
        self.file_op_manager = MagicMock()
        self.file_op_manager.pop_extract_statuses.return_value = None
        self.file_op_manager.pop_completed_extractions.return_value = []
        self.file_op_manager.get_active_extracting_file_names.return_value = []

        self.pipeline = ModelPipeline(
            context=self.context,
            persist=self.persist,
            model=self.model,
            model_lock=threading.Lock(),
            model_builder=self.builder,
            scan_manager=self.scan_manager,
            lftp_manager=self.real_lftp_manager,
            file_op_manager=self.file_op_manager,
            logger=self.logger,
        )

        self.controller = MagicMock()

        def _queue_command(cmd):
            # What CommandProcessor._handle_queue does for an accepted QUEUE
            if cmd.action == Controller.Command.Action.QUEUE:
                self.real_lftp_manager.queue(cmd.filename, False)

        self.controller.queue_command = MagicMock(side_effect=_queue_command)
        self.controller.is_file_stopped.side_effect = lambda name: False
        self.controller.is_file_downloaded.side_effect = lambda name: False

        def add_listener_and_get(listener):
            self.model.add_listener(listener)
            return self._model_files()

        self.controller.get_model_files_and_add_listener.side_effect = add_listener_and_get
        self.controller.get_model_files.side_effect = self._model_files

        self.auto_queue = AutoQueue(self.context, AutoQueuePersist(), self.controller)

        # Cycle 1: baseline
        self._cycle(
            t=self.T0,
            remote=[SystemFile("File.One.rar", 1000), SystemFile("File.Two.rar", 1000)],
            local=[SystemFile("File.One.rar", 1000), SystemFile("File.Two.rar", 400)],
            lftp_output=_RUNNING_PGET_OUTPUT,
        )
        self.assertEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"),
                         "precondition: cycle 1 must observe File.One.rar as DOWNLOADING")
        self.assertEqual(1, self.controller.queue_command.call_count,
                         "precondition: cycle 1 must sweep exactly one command")
        first_cmd = self.controller.queue_command.call_args_list[0][0][0]
        self.assertEqual("File.Two.rar", first_cmd.filename,
                         "precondition: the swept file must be File.Two.rar")
        self.assertEqual(Controller.Command.Action.QUEUE, first_cmd.action,
                         "precondition: the swept command must be QUEUE")
        self.assertEqual(1, len([c for c in self.sent_commands if c.startswith("queue '")]),
                         "precondition: File.Two.rar must have been submitted to lftp")

    def _model_files(self):
        return [self.model.get_file(n) for n in self.model.get_file_names()]

    def _state(self, name: str) -> ModelFile.State:
        return self.model.get_file(name).state

    def _cycle(self, t, remote, local, lftp_output):
        self.context.status.controller.latest_remote_scan_time = t
        self.scan_manager.pop_latest_results.return_value = (_scan(remote), _scan(local), None)
        self.script.append(lftp_output)
        self.pipeline.update_model()
        self.auto_queue.process()

    def _commands(self):
        return [c[0][0] for c in self.controller.queue_command.call_args_list]

    def test_isolated_parse_failure_keeps_downloading_state_and_issues_no_commands(self):
        """
        XFER-02, D-01: one tolerated parse failure must not demote the running
        transfer. Pre-fix: AssertionError, File.One.rar is demoted to
        DOWNLOADED (local >= remote) because the failure was reported as [].
        """
        self._cycle(t=self.T0 + 10, remote=None, local=None, lftp_output=_MALFORMED_JOBS_OUTPUT)

        self.assertEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"))
        self.assertNotIn("File.One.rar", self.persist.downloaded_file_names)
        self.assertEqual(1, self.controller.queue_command.call_count)

    def test_submitted_but_unobserved_file_is_not_requeued_after_cooldown_expiry(self):
        """
        XFER-02, D-01: a file submitted to lftp but not yet seen in a
        successful status must stay QUEUED while the status is unavailable,
        so the sweep does not submit it again once the requeue cooldown has
        expired. Pre-fix: AssertionError, File.Two.rar is DEFAULT.
        """
        self._cycle(t=self.T0 + 10, remote=None, local=None, lftp_output=_MALFORMED_JOBS_OUTPUT)
        self._cycle(t=self.T0 + AutoQueue.REQUEUE_COOLDOWN_SECONDS + 1, remote=None, local=None,
                    lftp_output=_MALFORMED_JOBS_OUTPUT)

        self.assertEqual(ModelFile.State.QUEUED, self._state("File.Two.rar"))
        self.assertEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"))
        self.assertEqual(1, self.controller.queue_command.call_count)
        self.assertEqual(0, len(self.persist.downloaded_file_names))

    def test_submitted_but_unobserved_file_is_not_marked_downloaded_by_preallocated_local_size(self):
        """
        XFER-02, D-01: a preallocated/sparse local file reads as full size as
        soon as lftp starts writing. A submitted-but-unobserved file must not
        be marked DOWNLOADED (and then committed / auto-extracted) on that
        evidence. Pre-fix: AssertionError, File.Two.rar is DOWNLOADED.
        """
        self._cycle(
            t=self.T0 + 10,
            remote=None,
            local=[SystemFile("File.One.rar", 1000), SystemFile("File.Two.rar", 1000)],
            lftp_output=_MALFORMED_JOBS_OUTPUT,
        )

        self.assertEqual(ModelFile.State.QUEUED, self._state("File.Two.rar"))
        self.assertNotIn("File.Two.rar", self.persist.downloaded_file_names)
        self.assertEqual(1, self.controller.queue_command.call_count)
        self.assertFalse(any(c.action == Controller.Command.Action.EXTRACT for c in self._commands()))
        self.file_op_manager.extract.assert_not_called()
        self.file_op_manager.delete_local.assert_not_called()
        self.assertEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"))

    def test_timed_out_status_with_empty_buffer_keeps_protection(self):
        """
        XFER-02, D-01: a timed-out `jobs -v` with an empty buffer is an
        incomplete observation. Pre-fix: AssertionError, File.One.rar is
        demoted because the empty buffer parsed as a genuine empty list.
        """
        self._cycle(t=self.T0 + 10, remote=None, local=None, lftp_output=_TimedOut(""))

        self.assertEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"))
        self.assertNotIn("File.One.rar", self.persist.downloaded_file_names)
        self.assertEqual(1, self.controller.queue_command.call_count)
        self.assertEqual(ModelFile.State.QUEUED, self._state("File.Two.rar"))
        self.file_op_manager.extract.assert_not_called()

    def test_timed_out_status_with_partial_parseable_buffer_keeps_protection(self):
        """
        XFER-02, D-01: a timed-out `jobs -v` whose partial buffer happens to
        parse (here a listing cut off before File.One.rar's job) must not be
        applied. Pre-fix: AssertionError, File.One.rar is demoted.
        """
        self._cycle(t=self.T0 + 10, remote=None, local=None,
                    lftp_output=_TimedOut(_RUNNING_PGET_OTHER_OUTPUT))

        self.assertEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"))
        self.assertNotIn("File.One.rar", self.persist.downloaded_file_names)
        self.assertEqual(1, self.controller.queue_command.call_count)
        self.assertEqual(ModelFile.State.QUEUED, self._state("File.Two.rar"))
        self.file_op_manager.extract.assert_not_called()
        self.assertNotIn("Other.Job.rar", self.model.get_file_names())

    def test_genuinely_empty_status_clears_downloading_state(self):
        """
        XFER-03 preservation: an empty `jobs -v` really means no jobs. The
        finished transfer is reconciled to DOWNLOADED and committed, and the
        submitted job is gone, so File.Two.rar falls back to its observed
        DEFAULT state (the sweep may retry it after the cooldown). Auto-extract
        of the genuinely completed archive is the expected follow-up.
        """
        self._cycle(t=self.T0 + 10, remote=None, local=None, lftp_output="")

        self.assertNotEqual(ModelFile.State.DOWNLOADING, self._state("File.One.rar"))
        self.assertEqual(ModelFile.State.DOWNLOADED, self._state("File.One.rar"))
        self.assertIn("File.One.rar", self.persist.downloaded_file_names)
        self.assertEqual(ModelFile.State.DEFAULT, self._state("File.Two.rar"))
        queue_cmds = [c for c in self._commands() if c.action == Controller.Command.Action.QUEUE]
        self.assertEqual(1, len(queue_cmds), "no re-queue inside the cooldown")
        extract_cmds = [c.filename for c in self._commands()
                        if c.action == Controller.Command.Action.EXTRACT]
        self.assertEqual(["File.One.rar"], extract_cmds)


class TestControllerActiveListFrozenWhileStatusUnavailable(BaseControllerTestCase):
    """
    The controller's active-downloading list (fed to the active scanner) must
    survive a status that is unavailable, and must clear on a genuinely empty
    status (XFER-02, XFER-03).
    """

    def setUp(self):
        super().setUp()
        self._make_controller_started()
        self.script = []
        self.real_manager = _make_real_lftp_manager(self.script)
        self.mock_lftp_manager.status.side_effect = self.real_manager.status
        self.mock_file_op_manager.get_active_extracting_file_names.return_value = []
        self.mock_model_builder.has_changes.return_value = False

    def test_active_downloading_list_and_scanner_feed_unchanged_on_parse_failure(self):
        """
        XFER-02: pre-fix AssertionError, the active list is emptied because the
        tolerated parse failure was reported as [].
        """
        self.script.extend([_RUNNING_PGET_OUTPUT, _MALFORMED_JOBS_OUTPUT])
        self.controller.process()
        self.controller.process()

        self.assertEqual(["File.One.rar"], self.controller._Controller__active_downloading_file_names)
        last_active = self.mock_scan_manager.update_active_files.call_args[0][0]
        self.assertIn("File.One.rar", last_active)
        self.assertEqual(1, self.mock_model_builder.set_lftp_statuses.call_count)

    def test_genuinely_empty_status_clears_active_list(self):
        """XFER-03 preservation: an empty status clears the active list."""
        self.script.extend([_RUNNING_PGET_OUTPUT, ""])
        self.controller.process()
        self.controller.process()

        self.assertEqual([], self.controller._Controller__active_downloading_file_names)
        self.assertEqual(2, self.mock_model_builder.set_lftp_statuses.call_count)
        self.assertEqual([], self.mock_model_builder.set_lftp_statuses.call_args[0][0])


class TestSameCycleCommandOrderingProtectsSubmittedTransfers(unittest.TestCase):
    """
    Controller.process() drains every queued command before it updates the
    model, so each command is handled against the previous cycle's frozen
    ModelFile. A QUEUE followed by EXTRACT / DELETE_LOCAL / DELETE_REMOTE for
    the same file in one process() must not dispatch the file operation once
    lftp has accepted the transfer (XFER-02, D-01). The Controller's
    CommandProcessor holds the REAL LftpManager here.
    """

    def _build_controller(self, script: list, sent_commands: Optional[List[str]] = None):
        self.real_lftp_manager = _make_real_lftp_manager(list(script), sent_commands)

        patchers = {
            "mb": patch('controller.controller.ModelBuilder'),
            "lftp": patch('controller.controller.LftpManager', return_value=self.real_lftp_manager),
            "sm": patch('controller.controller.ScanManager'),
            "fom": patch('controller.controller.FileOperationManager'),
            "mpl": patch('controller.controller.MultiprocessingLogger'),
            "mm": patch('controller.controller.MemoryMonitor'),
        }
        mocks = {}
        for key, p in patchers.items():
            mocks[key] = p.start()
            self.addCleanup(p.stop)

        self.mock_model_builder = mocks["mb"].return_value
        self.mock_scan_manager = mocks["sm"].return_value
        self.mock_file_op_manager = mocks["fom"].return_value

        mock_context = MagicMock()
        mock_context.logger = logging.getLogger("TestSameCycleCommandOrdering")
        mock_context.config.autodelete.enabled = False
        self.persist = ControllerPersist(max_tracked_files=100)
        self.controller = Controller(
            context=mock_context,
            persist=self.persist,
            webhook_manager=MagicMock(process=MagicMock(return_value=[])),
        )

        self.controller._Controller__started = True
        self.mock_scan_manager.pop_latest_results.return_value = (None, None, None)
        self.mock_file_op_manager.pop_extract_statuses.return_value = None
        self.mock_file_op_manager.pop_completed_extractions.return_value = []
        self.mock_file_op_manager.get_active_extracting_file_names.return_value = []
        self.mock_model_builder.has_changes.return_value = False

    def _add_file(self, name: str, remote_size: int, local_size: int,
                  state: ModelFile.State = ModelFile.State.DEFAULT) -> ModelFile:
        f = ModelFile(name, False)
        if state != ModelFile.State.DEFAULT:
            f.state = state
        f.remote_size = remote_size
        f.local_size = local_size
        self.controller._Controller__model.add_file(f)
        return f

    def _enqueue(self, action: Controller.Command.Action, name: str):
        cmd = Controller.Command(action, name)
        callback = MagicMock(spec=Controller.Command.ICallback)
        cmd.add_callback(callback)
        self.controller.queue_command(cmd)
        return callback

    def test_queue_then_extract_in_one_process_does_not_extract(self):
        """Pre-fix: AssertionError, extract is dispatched against the frozen DEFAULT file."""
        self._build_controller([_MALFORMED_JOBS_OUTPUT] * 4)
        self._add_file("File.Two.rar", remote_size=1000, local_size=400)
        queue_cb = self._enqueue(Controller.Command.Action.QUEUE, "File.Two.rar")
        extract_cb = self._enqueue(Controller.Command.Action.EXTRACT, "File.Two.rar")
        self.controller.process()

        self.mock_file_op_manager.extract.assert_not_called()
        extract_cb.on_failure.assert_called_once()
        self.assertEqual(409, extract_cb.on_failure.call_args[0][1])
        queue_cb.on_success.assert_called_once()

    def test_queue_then_delete_local_in_one_process_does_not_delete(self):
        """Pre-fix: AssertionError, delete_local is dispatched against the frozen DEFAULT file."""
        self._build_controller([_MALFORMED_JOBS_OUTPUT] * 4)
        self._add_file("File.Two.rar", remote_size=1000, local_size=400)
        queue_cb = self._enqueue(Controller.Command.Action.QUEUE, "File.Two.rar")
        delete_cb = self._enqueue(Controller.Command.Action.DELETE_LOCAL, "File.Two.rar")
        self.controller.process()

        self.mock_file_op_manager.delete_local.assert_not_called()
        delete_cb.on_failure.assert_called_once()
        self.assertEqual(409, delete_cb.on_failure.call_args[0][1])
        self.assertNotIn("File.Two.rar", self.persist.stopped_file_names)
        self.assertNotIn("File.Two.rar", self.persist.downloaded_file_names)
        queue_cb.on_success.assert_called_once()

    def test_queue_then_delete_remote_in_one_process_does_not_delete(self):
        """Pre-fix: AssertionError, delete_remote is dispatched against the frozen DEFAULT file."""
        self._build_controller([_MALFORMED_JOBS_OUTPUT] * 4)
        self._add_file("File.Two.rar", remote_size=1000, local_size=400)
        queue_cb = self._enqueue(Controller.Command.Action.QUEUE, "File.Two.rar")
        delete_cb = self._enqueue(Controller.Command.Action.DELETE_REMOTE, "File.Two.rar")
        self.controller.process()

        self.mock_file_op_manager.delete_remote.assert_not_called()
        delete_cb.on_failure.assert_called_once()
        self.assertEqual(409, delete_cb.on_failure.call_args[0][1])
        queue_cb.on_success.assert_called_once()

    def test_delete_local_of_unsubmitted_file_in_same_process_still_dispatches(self):
        """
        Preservation: the protection is keyed by file name, not a batch-wide
        freeze. A DELETE_LOCAL for a different, never-submitted file in the
        same batch is still dispatched.
        """
        self._build_controller([_MALFORMED_JOBS_OUTPUT] * 4)
        self._add_file("File.Two.rar", remote_size=1000, local_size=400)
        self._add_file("Other.rar", remote_size=1000, local_size=1000)
        self._enqueue(Controller.Command.Action.QUEUE, "File.Two.rar")
        delete_cb = self._enqueue(Controller.Command.Action.DELETE_LOCAL, "Other.rar")
        self.controller.process()

        self.mock_file_op_manager.delete_local.assert_called_once()
        self.assertEqual("Other.rar", self.mock_file_op_manager.delete_local.call_args[0][0].name)
        delete_cb.on_success.assert_called_once()

    def test_stop_then_user_queue_after_unavailable_status_resubmits_to_lftp(self):
        """
        Preservation: submitted -> status unavailable -> STOP (kill against a
        valid status) -> USER QUEUE in the next process() must really send a
        second `queue` command to lftp; a stale "submitted" record must not
        block the user's restart.
        """
        sent = []
        self._build_controller(
            [_MALFORMED_JOBS_OUTPUT, _RUNNING_PGET_FILE_TWO_OUTPUT, _MALFORMED_JOBS_OUTPUT], sent)
        self._add_file("File.Two.rar", remote_size=1000, local_size=400, state=ModelFile.State.QUEUED)

        # Process 1: submit; the status poll fails, so nothing reconciles it
        self._enqueue(Controller.Command.Action.QUEUE, "File.Two.rar")
        self.controller.process()

        # Process 2: stop (kill polls a valid status), then the user re-queues
        stop_cb = self._enqueue(Controller.Command.Action.STOP, "File.Two.rar")
        requeue_cb = self._enqueue(Controller.Command.Action.QUEUE, "File.Two.rar")
        self.controller.process()

        queue_idx = [i for i, c in enumerate(sent) if c.startswith("queue '")]
        self.assertEqual(2, len(queue_idx), "the user re-queue must be sent to lftp")
        self.assertIn("kill 1", sent)
        self.assertGreater(queue_idx[1], sent.index("kill 1"))
        stop_cb.on_success.assert_called_once()
        requeue_cb.on_success.assert_called_once()
        self.assertNotIn("File.Two.rar", self.persist.stopped_file_names)
