import logging
import shlex
import threading
import unittest
from unittest.mock import MagicMock, patch

from controller import FileOperationManager
from controller.command_processor import CommandProcessor
from controller.controller import Controller
from controller.root_reservation import RootReservations
from controller.delete.delete_process import DeleteRemoteProcess
from controller.extract import ExtractStatus


class TestFileOperationManager(unittest.TestCase):
    """Unit tests for FileOperationManager."""

    def setUp(self):
        """Set up mocked dependencies for tests."""
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()

        # Mock config attributes
        self.mock_context.config.lftp.local_path = "/local/path"
        self.mock_context.config.lftp.remote_address = "remote.server.com"
        self.mock_context.config.lftp.remote_username = "user"
        self.mock_context.config.lftp.remote_password = "password"  # Test-only credential — not a real secret (mock, no real connection)
        self.mock_context.config.lftp.use_ssh_key = False
        self.mock_context.config.lftp.remote_port = 22
        self.mock_context.config.lftp.remote_path = "/remote/path"
        self.mock_context.config.controller.use_local_path_as_extract_path = True
        self.mock_context.config.controller.extract_path = "/extract/path"

        self.mock_mp_logger = MagicMock()
        self.mock_force_local_scan = MagicMock()
        self.mock_force_remote_scan = MagicMock()

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_init_creates_extract_process_with_local_path(self, mock_extract_class):
        """Test that __init__ creates ExtractProcess with local_path when configured."""
        self.mock_context.config.controller.use_local_path_as_extract_path = True

        manager = FileOperationManager(  # noqa: F841
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )

        mock_extract_class.assert_called_once_with(
            out_dir_path="/local/path",
            local_path="/local/path"
        )

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_init_creates_extract_process_with_extract_path(self, mock_extract_class):
        """Test that __init__ creates ExtractProcess with extract_path when configured."""
        self.mock_context.config.controller.use_local_path_as_extract_path = False

        manager = FileOperationManager(  # noqa: F841
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )

        mock_extract_class.assert_called_once_with(
            out_dir_path="/extract/path",
            local_path="/local/path"
        )

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_start_starts_extract_process(self, mock_extract_class):
        """Test that start() starts the extract process."""
        mock_extract = MagicMock()
        mock_extract_class.return_value = mock_extract

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.start()

        mock_extract.start.assert_called_once()

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_stop_terminates_and_joins_extract_process(self, mock_extract_class):
        """Test that stop() terminates and joins the extract process."""
        mock_extract = MagicMock()
        mock_extract_class.return_value = mock_extract

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.start()
        manager.stop()

        mock_extract.terminate.assert_called_once()
        mock_extract.join.assert_called_once()

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_stop_without_start_is_safe(self, mock_extract_class):
        """Test that stop() without start() doesn't raise errors."""
        mock_extract = MagicMock()
        mock_extract_class.return_value = mock_extract

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        # Should not raise
        manager.stop()

        mock_extract.terminate.assert_not_called()

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_extract_delegates_to_extract_process(self, mock_extract_class):
        """Test that extract() delegates to ExtractProcess.extract()."""
        mock_extract = MagicMock()
        mock_extract_class.return_value = mock_extract
        mock_file = MagicMock()

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.extract(mock_file)

        mock_extract.extract.assert_called_once_with(mock_file)

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_pop_extract_statuses_delegates_to_extract_process(self, mock_extract_class):
        """Test that pop_extract_statuses() delegates to ExtractProcess."""
        mock_extract = MagicMock()
        mock_statuses = MagicMock()
        mock_extract.pop_latest_statuses.return_value = mock_statuses
        mock_extract_class.return_value = mock_extract

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        result = manager.pop_extract_statuses()

        self.assertEqual(result, mock_statuses)

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_pop_completed_extractions_delegates_to_extract_process(self, mock_extract_class):
        """Test that pop_completed_extractions() delegates to ExtractProcess."""
        mock_extract = MagicMock()
        mock_completed = [MagicMock(), MagicMock()]
        mock_extract.pop_completed.return_value = mock_completed
        mock_extract_class.return_value = mock_extract

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        result = manager.pop_completed_extractions()

        self.assertEqual(result, mock_completed)

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_get_active_extracting_file_names_returns_empty_initially(self, mock_extract_class):
        """Test that get_active_extracting_file_names() returns empty list initially."""
        mock_extract_class.return_value = MagicMock()

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        result = manager.get_active_extracting_file_names()

        self.assertEqual(result, [])

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_update_active_extracting_files_updates_list(self, mock_extract_class):
        """Test that update_active_extracting_files() updates the active list."""
        mock_extract_class.return_value = MagicMock()

        # Create mock extract statuses
        mock_status1 = MagicMock()
        mock_status1.name = "file1"
        mock_status1.state = ExtractStatus.State.EXTRACTING

        mock_status2 = MagicMock()
        mock_status2.name = "file2"
        mock_status2.state = ExtractStatus.State.EXTRACTING

        # Third status with a different state (not EXTRACTING)
        # ExtractStatus.State only has EXTRACTING, so we use a mock state
        mock_status3 = MagicMock()
        mock_status3.name = "file3"
        mock_status3.state = MagicMock()  # Any state that isn't EXTRACTING

        mock_statuses = MagicMock()
        mock_statuses.statuses = [mock_status1, mock_status2, mock_status3]

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.update_active_extracting_files(mock_statuses)
        result = manager.get_active_extracting_file_names()

        self.assertEqual(result, ["file1", "file2"])

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_update_active_extracting_files_handles_none(self, mock_extract_class):
        """Test that update_active_extracting_files() handles None input."""
        mock_extract_class.return_value = MagicMock()

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        # Should not raise
        manager.update_active_extracting_files(None)
        result = manager.get_active_extracting_file_names()

        self.assertEqual(result, [])

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_local_starts_delete_process(self, mock_extract_class, mock_delete_class):
        """Test that delete_local() starts a DeleteLocalProcess."""
        mock_extract_class.return_value = MagicMock()
        mock_delete = MagicMock()
        mock_delete_class.return_value = mock_delete
        mock_file = MagicMock()
        mock_file.name = "test_file"

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        result = manager.delete_local(mock_file)

        self.assertTrue(result)
        mock_delete_class.assert_called_once_with(
            local_path="/local/path",
            file_name="test_file"
        )
        mock_delete.start.assert_called_once()

    @patch('controller.file_operation_manager.DeleteRemoteProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_remote_starts_delete_process(self, mock_extract_class, mock_delete_class):
        """Test that delete_remote() starts a DeleteRemoteProcess."""
        mock_extract_class.return_value = MagicMock()
        mock_delete = MagicMock()
        mock_delete_class.return_value = mock_delete
        mock_file = MagicMock()
        mock_file.name = "test_file"

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        result = manager.delete_remote(mock_file)

        self.assertTrue(result)
        mock_delete_class.assert_called_once_with(
            remote_address="remote.server.com",
            remote_username="user",
            remote_password="password",
            remote_port=22,
            remote_path="/remote/path",
            file_name="test_file"
        )
        mock_delete.start.assert_called_once()

    @patch('controller.file_operation_manager.DeleteRemoteProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_remote_uses_none_password_with_ssh_key(self, mock_extract_class, mock_delete_class):
        """Test that delete_remote() uses None password with SSH key mode."""
        self.mock_context.config.lftp.use_ssh_key = True
        mock_extract_class.return_value = MagicMock()
        mock_delete = MagicMock()
        mock_delete_class.return_value = mock_delete
        mock_file = MagicMock()
        mock_file.name = "test_file"

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.delete_remote(mock_file)

        call_kwargs = mock_delete_class.call_args.kwargs
        self.assertIsNone(call_kwargs['remote_password'])

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_cleanup_completed_processes_calls_callbacks(self, mock_extract_class, mock_delete_class):
        """Test that cleanup_completed_processes() calls post callbacks for completed processes."""
        mock_extract_class.return_value = MagicMock()
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = False
        mock_delete_class.return_value = mock_delete
        mock_file = MagicMock()
        mock_file.name = "test_file"

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.delete_local(mock_file)
        manager.cleanup_completed_processes()

        self.mock_force_local_scan.assert_called_once()
        mock_delete.propagate_exception.assert_called_once()

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_cleanup_completed_processes_keeps_active(self, mock_extract_class, mock_delete_class):
        """Test that cleanup_completed_processes() keeps active processes."""
        mock_extract_class.return_value = MagicMock()
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = True  # Still running
        mock_delete_class.return_value = mock_delete
        mock_file = MagicMock()
        mock_file.name = "test_file"

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.delete_local(mock_file)
        manager.cleanup_completed_processes()

        # Callback should not be called for active processes
        self.mock_force_local_scan.assert_not_called()

    # --- Root reservation lifetime (DEL-01) --------------------------------
    # delete_local only STARTS a DeleteLocalProcess and returns at once; the
    # child deletes for seconds to minutes afterwards. A reservation handed to
    # delete_local must therefore be held until cleanup_completed_processes
    # observes the child dead, and never released for a child that has not
    # been started yet.

    def _make_manager(self):
        return FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )

    @staticmethod
    def _named_file(name="f"):
        mock_file = MagicMock()
        mock_file.name = name
        return mock_file

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_local_holds_reservation_until_process_exit(self, mock_extract_class, mock_delete_class):
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = True
        mock_delete_class.return_value = mock_delete
        reservations = RootReservations()
        token = reservations.acquire("f", "delete")
        try:
            manager = self._make_manager()
            self.assertTrue(manager.delete_local(self._named_file(), reservation=token))
            # delete_local returned, but the child is still deleting
            self.assertEqual("delete", reservations.holder_of("f"))

            manager.cleanup_completed_processes()
            self.assertEqual("delete", reservations.holder_of("f"))
            self.mock_force_local_scan.assert_not_called()

            mock_delete.is_alive.return_value = False
            manager.cleanup_completed_processes()
            self.assertIsNone(reservations.holder_of("f"))
            self.mock_force_local_scan.assert_called_once()
            mock_delete.propagate_exception.assert_called_once()
        finally:
            token.release()

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_local_releases_reservation_on_launch_failure(self, mock_extract_class, mock_delete_class):
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = False
        mock_delete.start.side_effect = RuntimeError("fork failed")
        mock_delete_class.return_value = mock_delete
        reservations = RootReservations()
        token = reservations.acquire("f", "delete")
        try:
            manager = self._make_manager()
            with self.assertRaises(RuntimeError):
                manager.delete_local(self._named_file(), reservation=token)
            self.assertIsNone(reservations.holder_of("f"))

            # The failed wrapper was never tracked: nothing to clean up
            manager.cleanup_completed_processes()
            self.mock_force_local_scan.assert_not_called()
            mock_delete.propagate_exception.assert_not_called()
        finally:
            token.release()

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_cleanup_releases_reservation_even_when_propagate_exception_raises(
            self, mock_extract_class, mock_delete_class):
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = False
        mock_delete.propagate_exception.side_effect = RuntimeError("child died")
        mock_delete_class.return_value = mock_delete
        reservations = RootReservations()
        token = reservations.acquire("f", "delete")
        try:
            manager = self._make_manager()
            manager.delete_local(self._named_file(), reservation=token)
            with self.assertRaises(RuntimeError):
                manager.cleanup_completed_processes()
            # A crashed child can never pin the root
            self.assertIsNone(reservations.holder_of("f"))
        finally:
            token.release()

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_stop_releases_outstanding_reservations(self, mock_extract_class, mock_delete_class):
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = True
        mock_delete_class.return_value = mock_delete
        reservations = RootReservations()

        # Started manager
        token = reservations.acquire("f", "delete")
        try:
            manager = self._make_manager()
            manager.start()
            manager.delete_local(self._named_file(), reservation=token)
            self.assertEqual("delete", reservations.holder_of("f"))
            manager.stop()
            self.assertIsNone(reservations.holder_of("f"))
        finally:
            token.release()

        # Never-started manager: the sweep runs before the early return
        token = reservations.acquire("g", "delete")
        try:
            manager = self._make_manager()
            manager.delete_local(self._named_file("g"), reservation=token)
            self.assertEqual("delete", reservations.holder_of("g"))
            manager.stop()
            self.assertIsNone(reservations.holder_of("g"))
        finally:
            token.release()

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_local_without_reservation_keeps_legacy_behavior(self, mock_extract_class, mock_delete_class):
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = False
        mock_delete_class.return_value = mock_delete

        manager = self._make_manager()
        self.assertTrue(manager.delete_local(self._named_file("test_file")))
        mock_delete_class.assert_called_once_with(local_path="/local/path", file_name="test_file")
        mock_delete.start.assert_called_once()

        manager.cleanup_completed_processes()
        self.mock_force_local_scan.assert_called_once()
        mock_delete.propagate_exception.assert_called_once()

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_delete_local_and_cleanup_from_two_threads_do_not_lose_wrappers(
            self, mock_extract_class, mock_delete_class):
        """The auto-delete Timer thread appends wrappers while the controller
        thread sweeps them; no wrapper may be lost in between."""
        mock_delete = MagicMock()
        mock_delete.is_alive.return_value = False
        mock_delete_class.return_value = mock_delete
        manager = self._make_manager()
        mock_file = self._named_file()
        errors = []

        def _appender():
            try:
                for _ in range(200):
                    manager.delete_local(mock_file)
            except Exception as e:  # pragma: no cover - surfaced via errors
                errors.append(e)

        appender = threading.Thread(target=_appender, daemon=True)
        appender.start()
        while appender.is_alive():
            manager.cleanup_completed_processes()
        appender.join(timeout=5)
        self.assertFalse(appender.is_alive())
        manager.cleanup_completed_processes()

        self.assertEqual([], errors)
        self.assertEqual(200, self.mock_force_local_scan.call_count)

    @patch('controller.file_operation_manager.DeleteLocalProcess')
    @patch('controller.file_operation_manager.ExtractProcess')
    def test_reservation_held_across_register_start_window(self, mock_extract_class, mock_delete_class):
        """Launch window: a multiprocessing.Process reports is_alive() False
        until start() has run. A cleanup sweep that runs while the launching
        thread is inside start() must neither reap the wrapper nor release
        the reservation, and a USER QUEUE must stay refused."""
        in_launch = threading.Event()
        proceed = threading.Event()
        started = threading.Event()
        child_alive = [True]
        proceed_waits = []

        def _start():
            in_launch.set()
            proceed_waits.append(proceed.wait(timeout=5))
            started.set()

        mock_delete = MagicMock()
        mock_delete.is_alive.side_effect = lambda: started.is_set() and child_alive[0]
        mock_delete.start.side_effect = _start
        mock_delete_class.return_value = mock_delete

        manager = self._make_manager()
        reservations = RootReservations()
        mock_lftp = MagicMock()
        mock_lftp.submitted_unobserved_file_names.return_value = []
        processor = CommandProcessor(
            lftp_manager=mock_lftp,
            file_op_manager=manager,
            persist=MagicMock(),
            logger=logging.getLogger("test_launch_window"),
            root_reservations=reservations,
        )
        mock_file = self._named_file()
        mock_file.remote_size = 1234
        mock_file.is_dir = False

        token = reservations.acquire("f", "delete")
        results = []
        launcher = threading.Thread(
            target=lambda: results.append(manager.delete_local(mock_file, reservation=token)),
            daemon=True,
        )
        try:
            launcher.start()
            self.assertTrue(in_launch.wait(timeout=5), "launcher never reached start()")

            # Controller.process() runs a sweep while the child is unstarted
            manager.cleanup_completed_processes()
            self.assertEqual("delete", reservations.holder_of("f"))
            self.mock_force_local_scan.assert_not_called()
            mock_delete.propagate_exception.assert_not_called()

            ok, msg, code = processor.handle(
                mock_file, Controller.Command(Controller.Command.Action.QUEUE, "f")
            )
            self.assertFalse(ok)
            self.assertEqual(409, code)
            self.assertIn("operation in progress", msg)
            mock_lftp.queue.assert_not_called()

            proceed.set()
            launcher.join(timeout=5)
            self.assertFalse(launcher.is_alive())
            self.assertEqual([True], proceed_waits)
            self.assertEqual([True], results)
            self.assertEqual("delete", reservations.holder_of("f"))

            # Started child still running
            manager.cleanup_completed_processes()
            self.assertEqual("delete", reservations.holder_of("f"))

            # Child exits -> next sweep releases the root
            child_alive[0] = False
            manager.cleanup_completed_processes()
            self.assertIsNone(reservations.holder_of("f"))
            self.mock_force_local_scan.assert_called_once()
            mock_delete.propagate_exception.assert_called_once()

            ok, msg, code = processor.handle(
                mock_file, Controller.Command(Controller.Command.Action.QUEUE, "f")
            )
            self.assertTrue(ok)
            mock_lftp.queue.assert_called_once_with("f", False)
        finally:
            proceed.set()
            launcher.join(timeout=5)
            token.release()

    @patch('controller.file_operation_manager.ExtractProcess')
    def test_propagate_exception_delegates_to_extract_process(self, mock_extract_class):
        """Test that propagate_exception() delegates to ExtractProcess."""
        mock_extract = MagicMock()
        mock_extract_class.return_value = mock_extract

        manager = FileOperationManager(
            self.mock_context,
            self.mock_mp_logger,
            self.mock_force_local_scan,
            self.mock_force_remote_scan
        )
        manager.propagate_exception()

        mock_extract.propagate_exception.assert_called_once()


class TestDeleteRemoteProcessShellEscaping(unittest.TestCase):
    """Tests that DeleteRemoteProcess uses shlex.quote to escape shell metacharacters."""

    def _make_process(self, file_name: str) -> DeleteRemoteProcess:
        return DeleteRemoteProcess(
            remote_address="remote.server.com",
            remote_username="user",
            remote_password="password",
            remote_port=22,
            remote_path="/remote/path",
            file_name=file_name
        )

    @patch('controller.delete.delete_process.Sshcp')
    def test_delete_remote_escapes_single_quotes_in_filename(self, mock_sshcp_cls):
        """File names containing single quotes are properly escaped."""
        mock_ssh = MagicMock()
        mock_ssh.shell.return_value = b""
        mock_sshcp_cls.return_value = mock_ssh

        process = self._make_process("it's a file")
        process.run_once()

        file_path = "/remote/path/it's a file"
        expected_cmd = "rm -rf {}".format(shlex.quote(file_path))
        mock_ssh.shell.assert_called_once_with(expected_cmd)
        # Verify the single quote in the filename is properly escaped by shlex.quote
        # shlex.quote converts: /remote/path/it's a file -> '/remote/path/it'"'"'s a file'
        # The embedded single quote becomes '"'"' (end quote, literal ', re-open quote)
        self.assertIn("'\"'\"'", expected_cmd)

    @patch('controller.delete.delete_process.Sshcp')
    def test_delete_remote_escapes_semicolons_in_filename(self, mock_sshcp_cls):
        """File names containing semicolons are properly escaped so metacharacter is not interpreted."""
        mock_ssh = MagicMock()
        mock_ssh.shell.return_value = b""
        mock_sshcp_cls.return_value = mock_ssh

        process = self._make_process("file; rm -rf /")
        process.run_once()

        file_path = "/remote/path/file; rm -rf /"
        expected_cmd = "rm -rf {}".format(shlex.quote(file_path))
        mock_ssh.shell.assert_called_once_with(expected_cmd)
        # The entire path (including semicolon) must be wrapped in a single quoted token
        # shlex.quote produces: '/remote/path/file; rm -rf /'
        # The semicolon appears inside single quotes — safe for the shell
        self.assertTrue(expected_cmd.startswith("rm -rf '"))

    @patch('controller.delete.delete_process.Sshcp')
    def test_delete_remote_normal_filename(self, mock_sshcp_cls):
        """Normal file names are safely quoted by shlex.quote (no injection possible)."""
        mock_ssh = MagicMock()
        mock_ssh.shell.return_value = b""
        mock_sshcp_cls.return_value = mock_ssh

        process = self._make_process("normal_file.txt")
        process.run_once()

        file_path = "/remote/path/normal_file.txt"
        expected_cmd = "rm -rf {}".format(shlex.quote(file_path))
        mock_ssh.shell.assert_called_once_with(expected_cmd)


if __name__ == '__main__':
    unittest.main()
