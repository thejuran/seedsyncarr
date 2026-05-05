from unittest.mock import MagicMock

from controller import Controller
from controller.controller import ControllerError
from model import ModelFile, IModelListener, ModelDiff, Model
from lftp import LftpError, LftpJobStatus, LftpJobStatusParserError
from tests.unittests.test_controller.base import BaseControllerTestCase


class TestControllerInit(BaseControllerTestCase):
    """Tests for Controller.__init__ constructor."""

    def test_init_creates_model_builder(self):
        self.mock_model_builder_cls.assert_called_once()
        self.mock_model_builder.set_base_logger.assert_called_once()
        self.mock_model_builder.set_downloaded_files.assert_called_once_with(
            self.persist.downloaded_file_names
        )
        self.mock_model_builder.set_extracted_files.assert_called_once_with(
            self.persist.extracted_file_names
        )

    def test_init_creates_lftp_manager(self):
        self.mock_lftp_manager_cls.assert_called_once()

    def test_init_creates_scan_manager(self):
        self.mock_scan_manager_cls.assert_called_once()

    def test_init_creates_file_operation_manager(self):
        self.mock_file_op_manager_cls.assert_called_once()

    def test_init_creates_memory_monitor(self):
        self.mock_memory_monitor_cls.assert_called_once()
        self.mock_memory_monitor.set_base_logger.assert_called_once()
        # 9 data sources: downloaded_files, extracted_files, stopped_files, model_files,
        # downloaded_evictions, extracted_evictions, stopped_evictions,
        # imported_files, imported_evictions
        self.assertEqual(9, self.mock_memory_monitor.register_data_source.call_count)

    def test_init_creates_multiprocessing_logger(self):
        self.mock_mp_logger_cls.assert_called_once()

    def test_init_creates_logger_as_child(self):
        self.mock_context.logger.getChild.assert_called_with("Controller")
        self.assertEqual(
            self.mock_context.logger.getChild.return_value,
            self.controller.logger
        )


class TestControllerLifecycle(BaseControllerTestCase):
    """Tests for Controller start/exit/process lifecycle."""

    def test_start_starts_scan_manager(self):
        self.controller.start()
        self.mock_scan_manager.start.assert_called_once()

    def test_start_starts_file_op_manager(self):
        self.controller.start()
        self.mock_file_op_manager.start.assert_called_once()

    def test_start_starts_mp_logger(self):
        self.controller.start()
        self.mock_mp_logger.start.assert_called_once()

    def test_exit_stops_all_managers(self):
        self.controller.start()
        self.controller.exit()
        self.mock_lftp_manager.exit.assert_called_once()
        self.mock_scan_manager.stop.assert_called_once()
        self.mock_file_op_manager.stop.assert_called_once()
        self.mock_mp_logger.stop.assert_called_once()

    def test_exit_without_start_is_safe(self):
        self.controller.exit()  # should not raise
        self.mock_scan_manager.stop.assert_not_called()

    def test_process_without_start_raises_error(self):
        with self.assertRaises(ControllerError):
            self.controller.process()


class TestControllerPublicAPI(BaseControllerTestCase):
    """Tests for Controller public API methods."""

    def test_get_model_files_returns_empty_list(self):
        result = self.controller.get_model_files()
        self.assertEqual([], result)

    def test_get_model_files_returns_added_files(self):
        self._add_file_to_model("file1", remote_size=100)
        self._add_file_to_model("file2", remote_size=200)
        result = self.controller.get_model_files()
        self.assertEqual(2, len(result))
        names = {f.name for f in result}
        self.assertEqual({"file1", "file2"}, names)

    def test_is_file_stopped_false_initially(self):
        self.assertFalse(self.controller.is_file_stopped("file"))

    def test_is_file_stopped_true_after_adding(self):
        self.persist.stopped_file_names.add("stopped_file")
        self.assertTrue(self.controller.is_file_stopped("stopped_file"))

    def test_is_file_downloaded_false_initially(self):
        self.assertFalse(self.controller.is_file_downloaded("file"))

    def test_is_file_downloaded_true_after_adding(self):
        self.persist.downloaded_file_names.add("dl_file")
        self.assertTrue(self.controller.is_file_downloaded("dl_file"))

    def test_add_model_listener(self):
        mock_listener = MagicMock(spec=IModelListener)
        self.controller.add_model_listener(mock_listener)
        # Adding a file should trigger the listener
        self._add_file_to_model("new_file", remote_size=100)
        mock_listener.file_added.assert_called_once()

    def test_remove_model_listener(self):
        mock_listener = MagicMock(spec=IModelListener)
        self.controller.add_model_listener(mock_listener)
        self.controller.remove_model_listener(mock_listener)
        # Adding a file should NOT trigger the removed listener
        self._add_file_to_model("new_file", remote_size=100)
        mock_listener.file_added.assert_not_called()

    def test_get_model_files_and_add_listener_returns_files(self):
        self._add_file_to_model("existing_file", remote_size=100)
        mock_listener = MagicMock(spec=IModelListener)
        result = self.controller.get_model_files_and_add_listener(mock_listener)
        self.assertEqual(1, len(result))
        self.assertEqual("existing_file", result[0].name)
        # Listener should be active - adding another file triggers it
        self._add_file_to_model("another_file", remote_size=200)
        mock_listener.file_added.assert_called_once()

    def test_queue_command_adds_to_queue(self):
        cmd = Controller.Command(Controller.Command.Action.QUEUE, "file")
        self.controller.queue_command(cmd)
        self.assertEqual(1, self.controller._Controller__command_queue.qsize())


class TestControllerCommandQueue(BaseControllerTestCase):
    """Tests for QUEUE command processing."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_queue_success_calls_lftp_queue(self):
        self._add_file_to_model("file", remote_size=5000)
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "file", [mock_cb]
        )
        self.mock_lftp_manager.queue.assert_called_once_with("file", False)
        mock_cb.on_success.assert_called_once()

    def test_queue_directory_calls_lftp_with_is_dir_true(self):
        self._add_file_to_model("dir", is_dir=True, remote_size=5000)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "dir"
        )
        self.mock_lftp_manager.queue.assert_called_once_with("dir", True)

    def test_queue_no_remote_size_returns_404(self):
        self._add_file_to_model("file", remote_size=None)
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertIn("does not exist remotely", args[0][0])
        self.assertEqual(404, args[0][1])

    def test_queue_lftp_error_returns_500(self):
        self._add_file_to_model("file", remote_size=5000)
        self.mock_lftp_manager.queue.side_effect = LftpError("connection failed")
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(500, args[0][1])

    def test_queue_removes_from_stopped_files(self):
        self.persist.stopped_file_names.add("file")
        self._add_file_to_model("file", remote_size=5000)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "file"
        )
        self.assertNotIn("file", self.persist.stopped_file_names)


class TestControllerCommandStop(BaseControllerTestCase):
    """Tests for STOP command processing."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_stop_downloading_file_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.STOP, "file", [mock_cb]
        )
        self.mock_lftp_manager.kill.assert_called_once_with("file")
        mock_cb.on_success.assert_called_once()

    def test_stop_queued_file_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.QUEUED, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.STOP, "file", [mock_cb]
        )
        mock_cb.on_success.assert_called_once()

    def test_stop_default_state_returns_409(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DEFAULT, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.STOP, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertIn("not Queued or Downloading", args[0][0])
        self.assertEqual(409, args[0][1])

    def test_stop_lftp_error_returns_500(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000
        )
        self.mock_lftp_manager.kill.side_effect = LftpError("error")
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.STOP, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(500, args[0][1])

    def test_stop_lftp_parser_error_returns_500(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000
        )
        self.mock_lftp_manager.kill.side_effect = LftpJobStatusParserError("parse error")
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.STOP, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(500, args[0][1])

    def test_stop_adds_to_stopped_files(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000
        )
        self._queue_and_process_command(
            Controller.Command.Action.STOP, "file"
        )
        self.assertIn("file", self.persist.stopped_file_names)


class TestControllerCommandExtract(BaseControllerTestCase):
    """Tests for EXTRACT command processing."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_extract_downloaded_file_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADED, local_size=5000, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.EXTRACT, "file", [mock_cb]
        )
        self.mock_file_op_manager.extract.assert_called_once()
        mock_cb.on_success.assert_called_once()

    def test_extract_default_state_with_local_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DEFAULT, local_size=5000, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.EXTRACT, "file", [mock_cb]
        )
        mock_cb.on_success.assert_called_once()

    def test_extract_extracted_state_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.EXTRACTED, local_size=5000, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.EXTRACT, "file", [mock_cb]
        )
        mock_cb.on_success.assert_called_once()

    def test_extract_downloading_state_returns_409(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000, local_size=1000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.EXTRACT, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(409, args[0][1])

    def test_extract_no_local_size_returns_404(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADED, remote_size=5000, local_size=None
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.EXTRACT, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertIn("does not exist locally", args[0][0])
        self.assertEqual(404, args[0][1])


class TestControllerCommandDelete(BaseControllerTestCase):
    """Tests for DELETE_LOCAL and DELETE_REMOTE command processing."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_delete_local_downloaded_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADED, local_size=5000, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_LOCAL, "file", [mock_cb]
        )
        self.mock_file_op_manager.delete_local.assert_called_once()
        mock_cb.on_success.assert_called_once()

    def test_delete_local_downloading_returns_409(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000, local_size=1000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_LOCAL, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(409, args[0][1])

    def test_delete_local_no_local_returns_404(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DEFAULT, remote_size=5000, local_size=None
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_LOCAL, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(404, args[0][1])

    def test_delete_local_adds_to_stopped(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADED, local_size=5000, remote_size=5000
        )
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_LOCAL, "file"
        )
        self.assertIn("file", self.persist.stopped_file_names)

    def test_delete_remote_default_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DEFAULT, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_REMOTE, "file", [mock_cb]
        )
        self.mock_file_op_manager.delete_remote.assert_called_once()
        mock_cb.on_success.assert_called_once()

    def test_delete_remote_deleted_state_succeeds(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DELETED, remote_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_REMOTE, "file", [mock_cb]
        )
        mock_cb.on_success.assert_called_once()

    def test_delete_remote_downloading_returns_409(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DOWNLOADING, remote_size=5000, local_size=1000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_REMOTE, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(409, args[0][1])

    def test_delete_remote_no_remote_returns_404(self):
        self._add_file_to_model(
            "file", state=ModelFile.State.DEFAULT, remote_size=None, local_size=5000
        )
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.DELETE_REMOTE, "file", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertEqual(404, args[0][1])


class TestControllerCommandCommon(BaseControllerTestCase):
    """Tests for common command processing paths."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_command_file_not_found_returns_404(self):
        mock_cb = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "nonexistent", [mock_cb]
        )
        mock_cb.on_failure.assert_called_once()
        args = mock_cb.on_failure.call_args
        self.assertIn("not found", args[0][0])
        self.assertEqual(404, args[0][1])

    def test_command_success_notifies_all_callbacks(self):
        self._add_file_to_model("file", remote_size=5000)
        mock_cb1 = MagicMock(spec=Controller.Command.ICallback)
        mock_cb2 = MagicMock(spec=Controller.Command.ICallback)
        mock_cb3 = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "file", [mock_cb1, mock_cb2, mock_cb3]
        )
        mock_cb1.on_success.assert_called_once()
        mock_cb2.on_success.assert_called_once()
        mock_cb3.on_success.assert_called_once()

    def test_command_failure_notifies_all_callbacks(self):
        mock_cb1 = MagicMock(spec=Controller.Command.ICallback)
        mock_cb2 = MagicMock(spec=Controller.Command.ICallback)
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "nonexistent", [mock_cb1, mock_cb2]
        )
        mock_cb1.on_failure.assert_called_once()
        mock_cb2.on_failure.assert_called_once()

    def test_command_no_callbacks_no_crash(self):
        self._add_file_to_model("file", remote_size=5000)
        # Should not raise even with no callbacks
        self._queue_and_process_command(
            Controller.Command.Action.QUEUE, "file"
        )

    def test_multiple_commands_in_single_process(self):
        self._add_file_to_model("file1", remote_size=5000)
        self._add_file_to_model("file2", remote_size=3000)
        mock_cb1 = MagicMock(spec=Controller.Command.ICallback)
        mock_cb2 = MagicMock(spec=Controller.Command.ICallback)
        cmd1 = Controller.Command(Controller.Command.Action.QUEUE, "file1")
        cmd1.add_callback(mock_cb1)
        cmd2 = Controller.Command(Controller.Command.Action.QUEUE, "file2")
        cmd2.add_callback(mock_cb2)
        self.controller.queue_command(cmd1)
        self.controller.queue_command(cmd2)
        self.controller.process()
        mock_cb1.on_success.assert_called_once()
        mock_cb2.on_success.assert_called_once()
        self.assertEqual(2, self.mock_lftp_manager.queue.call_count)


class TestControllerCollect(BaseControllerTestCase):
    """Tests for Controller._collect_* data collection methods."""

    def test_collect_scan_results_delegates_to_scan_manager(self):
        expected = (MagicMock(), MagicMock(), MagicMock())
        self.mock_scan_manager.pop_latest_results.return_value = expected
        result = self.controller._collect_scan_results()
        self.mock_scan_manager.pop_latest_results.assert_called_once()
        self.assertEqual(expected, result)

    def test_collect_lftp_status_delegates_to_lftp_manager(self):
        expected = [MagicMock()]
        self.mock_lftp_manager.status.return_value = expected
        result = self.controller._collect_lftp_status()
        self.mock_lftp_manager.status.assert_called_once()
        self.assertEqual(expected, result)

    def test_collect_extract_results_delegates_to_file_op_manager(self):
        mock_statuses = MagicMock()
        mock_completed = [MagicMock()]
        self.mock_file_op_manager.pop_extract_statuses.return_value = mock_statuses
        self.mock_file_op_manager.pop_completed_extractions.return_value = mock_completed
        statuses, completed = self.controller._collect_extract_results()
        self.mock_file_op_manager.pop_extract_statuses.assert_called_once()
        self.mock_file_op_manager.pop_completed_extractions.assert_called_once()
        self.assertEqual(mock_statuses, statuses)
        self.assertEqual(mock_completed, completed)


class TestControllerFeedModelBuilder(BaseControllerTestCase):
    """Tests for Controller._feed_model_builder()."""

    def test_remote_scan_sets_remote_files(self):
        remote_scan = MagicMock(failed=False)
        self.controller._feed_model_builder(
            remote_scan, None, None, None, None, []
        )
        self.mock_model_builder.set_remote_files.assert_called_once_with(remote_scan.files)

    def test_local_scan_sets_local_files(self):
        local_scan = MagicMock(failed=False)
        self.controller._feed_model_builder(
            None, local_scan, None, None, None, []
        )
        self.mock_model_builder.set_local_files.assert_called_once_with(local_scan.files)

    def test_active_scan_sets_active_files(self):
        active_scan = MagicMock(failed=False)
        self.controller._feed_model_builder(
            None, None, active_scan, None, None, []
        )
        self.mock_model_builder.set_active_files.assert_called_once_with(active_scan.files)

    def test_lftp_statuses_sets_lftp_statuses(self):
        lftp_statuses = [MagicMock()]
        self.controller._feed_model_builder(
            None, None, None, lftp_statuses, None, []
        )
        self.mock_model_builder.set_lftp_statuses.assert_called_once_with(lftp_statuses)

    def test_extract_statuses_sets_extract_statuses(self):
        extract_statuses = MagicMock()
        extract_statuses.statuses = [MagicMock()]
        self.controller._feed_model_builder(
            None, None, None, None, extract_statuses, []
        )
        self.mock_model_builder.set_extract_statuses.assert_called_once_with(
            extract_statuses.statuses
        )

    def test_extracted_results_adds_to_persist_and_sets_extracted_files(self):
        result = MagicMock()
        result.name = "extracted_file"
        # Reset mock since __init__ already called set_extracted_files once
        self.mock_model_builder.set_extracted_files.reset_mock()
        self.controller._feed_model_builder(
            None, None, None, None, None, [result]
        )
        self.assertIn("extracted_file", self.persist.extracted_file_names)
        self.mock_model_builder.set_extracted_files.assert_called_once_with(
            self.persist.extracted_file_names
        )

    def test_all_none_no_set_methods_called(self):
        # Reset mocks since __init__ already called set_extracted_files and set_downloaded_files
        self.mock_model_builder.set_extracted_files.reset_mock()
        self.mock_model_builder.set_downloaded_files.reset_mock()
        self.controller._feed_model_builder(
            None, None, None, None, None, []
        )
        self.mock_model_builder.set_remote_files.assert_not_called()
        self.mock_model_builder.set_local_files.assert_not_called()
        self.mock_model_builder.set_active_files.assert_not_called()
        self.mock_model_builder.set_lftp_statuses.assert_not_called()
        self.mock_model_builder.set_extract_statuses.assert_not_called()
        self.mock_model_builder.set_extracted_files.assert_not_called()

    def test_multiple_extracted_results(self):
        result1 = MagicMock()
        result1.name = "file_a"
        result2 = MagicMock()
        result2.name = "file_b"
        # Reset mock since __init__ already called set_extracted_files once
        self.mock_model_builder.set_extracted_files.reset_mock()
        self.controller._feed_model_builder(
            None, None, None, None, None, [result1, result2]
        )
        self.assertIn("file_a", self.persist.extracted_file_names)
        self.assertIn("file_b", self.persist.extracted_file_names)
        self.mock_model_builder.set_extracted_files.assert_called_once()


    def test_failed_remote_scan_does_not_set_remote_files(self):
        remote_scan = MagicMock(failed=True)
        self.controller._feed_model_builder(
            remote_scan, None, None, None, None, []
        )
        self.mock_model_builder.set_remote_files.assert_not_called()

    def test_failed_local_scan_does_not_set_local_files(self):
        local_scan = MagicMock(failed=True)
        self.controller._feed_model_builder(
            None, local_scan, None, None, None, []
        )
        self.mock_model_builder.set_local_files.assert_not_called()

    def test_failed_active_scan_does_not_set_active_files(self):
        active_scan = MagicMock(failed=True)
        self.controller._feed_model_builder(
            None, None, active_scan, None, None, []
        )
        self.mock_model_builder.set_active_files.assert_not_called()

class TestControllerDetectAndTrackQueued(BaseControllerTestCase):
    """Tests for Controller._detect_and_track_queued()."""

    def test_added_downloading_with_local_size_tracked(self):
        f = ModelFile("file", False)
        f.state = ModelFile.State.DOWNLOADING
        f.local_size = 100
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._detect_and_track_queued(diff)
        self.assertIn("file", self.persist.downloaded_file_names)

    def test_added_queued_not_tracked(self):
        f = ModelFile("file", False)
        f.state = ModelFile.State.QUEUED
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._detect_and_track_queued(diff)
        self.assertNotIn("file", self.persist.downloaded_file_names)

    def test_downloading_with_local_size_zero_not_tracked(self):
        f = ModelFile("file", False)
        f.state = ModelFile.State.DOWNLOADING
        f.local_size = 0
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._detect_and_track_queued(diff)
        self.assertNotIn("file", self.persist.downloaded_file_names)

    def test_downloading_with_local_size_none_not_tracked(self):
        f = ModelFile("file", False)
        f.state = ModelFile.State.DOWNLOADING
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._detect_and_track_queued(diff)
        self.assertNotIn("file", self.persist.downloaded_file_names)

    def test_already_tracked_not_readded(self):
        self.persist.downloaded_file_names.add("file")
        f = ModelFile("file", False)
        f.state = ModelFile.State.DOWNLOADING
        f.local_size = 100
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        # Reset mock to detect if set_downloaded_files is called again
        self.mock_model_builder.set_downloaded_files.reset_mock()
        self.controller._detect_and_track_queued(diff)
        # Should NOT call set_downloaded_files again since already tracked
        self.mock_model_builder.set_downloaded_files.assert_not_called()

    def test_updated_default_to_downloading_with_content_tracked(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DEFAULT
        new_f = ModelFile("file", False)
        new_f.state = ModelFile.State.DOWNLOADING
        new_f.local_size = 500
        diff = ModelDiff(ModelDiff.Change.UPDATED, old_f, new_f)
        self.controller._detect_and_track_queued(diff)
        self.assertIn("file", self.persist.downloaded_file_names)

    def test_updated_downloading_no_content_to_content_tracked(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DOWNLOADING
        old_f.local_size = 0
        new_f = ModelFile("file", False)
        new_f.state = ModelFile.State.DOWNLOADING
        new_f.local_size = 500
        diff = ModelDiff(ModelDiff.Change.UPDATED, old_f, new_f)
        self.controller._detect_and_track_queued(diff)
        self.assertIn("file", self.persist.downloaded_file_names)

    def test_removed_diff_no_change(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DOWNLOADING
        old_f.local_size = 100
        diff = ModelDiff(ModelDiff.Change.REMOVED, old_f, None)
        self.controller._detect_and_track_queued(diff)
        self.assertNotIn("file", self.persist.downloaded_file_names)


class TestControllerDetectAndTrackDownload(BaseControllerTestCase):
    """Tests for Controller._detect_and_track_download()."""

    def test_added_downloaded_tracked(self):
        f = ModelFile("file", False)
        f.state = ModelFile.State.DOWNLOADED
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._detect_and_track_download(diff)
        self.assertIn("file", self.persist.downloaded_file_names)

    def test_updated_downloading_to_downloaded_tracked(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DOWNLOADING
        new_f = ModelFile("file", False)
        new_f.state = ModelFile.State.DOWNLOADED
        diff = ModelDiff(ModelDiff.Change.UPDATED, old_f, new_f)
        self.controller._detect_and_track_download(diff)
        self.assertIn("file", self.persist.downloaded_file_names)

    def test_updated_downloaded_to_downloaded_not_retracked(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DOWNLOADED
        new_f = ModelFile("file", False)
        new_f.state = ModelFile.State.DOWNLOADED
        diff = ModelDiff(ModelDiff.Change.UPDATED, old_f, new_f)
        self.mock_model_builder.set_downloaded_files.reset_mock()
        self.controller._detect_and_track_download(diff)
        # Should NOT track because old_file.state was already DOWNLOADED
        self.mock_model_builder.set_downloaded_files.assert_not_called()

    def test_added_queued_not_tracked(self):
        f = ModelFile("file", False)
        f.state = ModelFile.State.QUEUED
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._detect_and_track_download(diff)
        self.assertNotIn("file", self.persist.downloaded_file_names)

    def test_removed_not_tracked(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DOWNLOADED
        diff = ModelDiff(ModelDiff.Change.REMOVED, old_f, None)
        self.mock_model_builder.set_downloaded_files.reset_mock()
        self.controller._detect_and_track_download(diff)
        self.mock_model_builder.set_downloaded_files.assert_not_called()

    def test_updated_to_non_downloaded_not_tracked(self):
        old_f = ModelFile("file", False)
        old_f.state = ModelFile.State.DOWNLOADING
        new_f = ModelFile("file", False)
        new_f.state = ModelFile.State.QUEUED
        diff = ModelDiff(ModelDiff.Change.UPDATED, old_f, new_f)
        self.mock_model_builder.set_downloaded_files.reset_mock()
        self.controller._detect_and_track_download(diff)
        self.mock_model_builder.set_downloaded_files.assert_not_called()


class TestControllerPruneExtracted(BaseControllerTestCase):
    """Tests for Controller._prune_extracted_files()."""

    def test_file_in_persist_and_model_with_deleted_state_removed(self):
        self.persist.extracted_file_names.add("file")
        self._add_file_to_model("file", state=ModelFile.State.DELETED)
        self.controller._prune_extracted_files()
        self.assertNotIn("file", self.persist.extracted_file_names)

    def test_file_in_persist_and_model_with_downloaded_state_kept(self):
        self.persist.extracted_file_names.add("file")
        self._add_file_to_model("file", state=ModelFile.State.DOWNLOADED, local_size=100)
        self.controller._prune_extracted_files()
        self.assertIn("file", self.persist.extracted_file_names)

    def test_file_in_persist_but_not_in_model_kept(self):
        self.persist.extracted_file_names.add("missing_file")
        # Do NOT add file to model -- scans may not be available
        self.controller._prune_extracted_files()
        self.assertIn("missing_file", self.persist.extracted_file_names)

    def test_empty_persist_no_crash(self):
        # persist.extracted_file_names is empty by default
        self.controller._prune_extracted_files()  # should not raise


class TestControllerApplyModelDiff(BaseControllerTestCase):
    """Tests for Controller._apply_model_diff()."""

    def test_added_file_appears_in_model(self):
        f = ModelFile("new_file", False)
        f.remote_size = 1000
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._apply_model_diff([diff])
        result = self.controller._Controller__model.get_file("new_file")
        self.assertEqual("new_file", result.name)

    def test_removed_file_gone_from_model(self):
        self._add_file_to_model("old_file", remote_size=1000)
        old_f = self.controller._Controller__model.get_file("old_file")
        diff = ModelDiff(ModelDiff.Change.REMOVED, old_f, None)
        self.controller._apply_model_diff([diff])
        self.assertNotIn("old_file", self.controller._Controller__model.get_file_names())

    def test_updated_file_updated_in_model(self):
        self._add_file_to_model("file", remote_size=1000)
        new_f = ModelFile("file", False)
        new_f.remote_size = 2000
        old_f = self.controller._Controller__model.get_file("file")
        diff = ModelDiff(ModelDiff.Change.UPDATED, old_f, new_f)
        self.controller._apply_model_diff([diff])
        result = self.controller._Controller__model.get_file("file")
        self.assertEqual(2000, result.remote_size)

    def test_mixed_diffs_correct_final_state(self):
        self._add_file_to_model("remove_me", remote_size=100)
        old_f = self.controller._Controller__model.get_file("remove_me")
        f_add_b = ModelFile("add_b", False)
        f_add_b.remote_size = 200
        f_add_c = ModelFile("add_c", False)
        f_add_c.remote_size = 300
        diffs = [
            ModelDiff(ModelDiff.Change.REMOVED, old_f, None),
            ModelDiff(ModelDiff.Change.ADDED, None, f_add_b),
            ModelDiff(ModelDiff.Change.ADDED, None, f_add_c),
        ]
        self.controller._apply_model_diff(diffs)
        file_names = self.controller._Controller__model.get_file_names()
        self.assertNotIn("remove_me", file_names)
        self.assertIn("add_b", file_names)
        self.assertIn("add_c", file_names)

    def test_empty_diff_no_crash(self):
        self.controller._apply_model_diff([])  # should not raise

    def test_added_downloaded_state_triggers_tracking(self):
        f = ModelFile("dl_file", False)
        f.state = ModelFile.State.DOWNLOADED
        diff = ModelDiff(ModelDiff.Change.ADDED, None, f)
        self.controller._apply_model_diff([diff])
        self.assertIn("dl_file", self.persist.downloaded_file_names)


class TestControllerActiveFileTracking(BaseControllerTestCase):
    """Tests for Controller._update_active_file_tracking()."""

    def test_running_lftp_statuses_updates_active_list(self):
        mock_status = MagicMock()
        mock_status.state = LftpJobStatus.State.RUNNING
        mock_status.name = "file_a"
        self.controller._update_active_file_tracking([mock_status], None)
        self.assertEqual(["file_a"],
                         self.controller._Controller__active_downloading_file_names)

    def test_queued_lftp_status_empty_list(self):
        mock_status = MagicMock()
        mock_status.state = LftpJobStatus.State.QUEUED
        mock_status.name = "file_a"
        self.controller._update_active_file_tracking([mock_status], None)
        self.assertEqual([],
                         self.controller._Controller__active_downloading_file_names)

    def test_none_lftp_statuses_preserves_existing_list(self):
        self.controller._Controller__active_downloading_file_names = ["existing"]
        self.controller._update_active_file_tracking(None, None)
        self.assertEqual(["existing"],
                         self.controller._Controller__active_downloading_file_names)

    def test_calls_scan_manager_update_active_files(self):
        mock_status = MagicMock()
        mock_status.state = LftpJobStatus.State.RUNNING
        mock_status.name = "file_a"
        self.mock_file_op_manager.get_active_extracting_file_names.return_value = ["extract_b"]
        self.controller._update_active_file_tracking([mock_status], None)
        self.mock_scan_manager.update_active_files.assert_called_once_with(
            ["file_a", "extract_b"]
        )


class TestControllerBuildAndApplyModel(BaseControllerTestCase):
    """Tests for Controller._build_and_apply_model()."""

    def test_no_changes_build_model_not_called(self):
        self.mock_model_builder.has_changes.return_value = False
        self.controller._build_and_apply_model(None)
        self.mock_model_builder.build_model.assert_not_called()

    def test_has_changes_build_model_called(self):
        self.mock_model_builder.has_changes.return_value = True
        new_model = Model()
        self.mock_model_builder.build_model.return_value = new_model
        self.controller._build_and_apply_model(None)
        self.mock_model_builder.build_model.assert_called_once()

    def test_has_changes_new_file_appears_in_controller_model(self):
        self.mock_model_builder.has_changes.return_value = True
        new_model = Model()
        f = ModelFile("brand_new", False)
        f.remote_size = 999
        new_model.add_file(f)
        self.mock_model_builder.build_model.return_value = new_model
        self.controller._build_and_apply_model(None)
        result = self.controller._Controller__model.get_file("brand_new")
        self.assertEqual("brand_new", result.name)

    def test_has_changes_empty_model_no_change(self):
        self.mock_model_builder.has_changes.return_value = True
        new_model = Model()
        self.mock_model_builder.build_model.return_value = new_model
        self.controller._build_and_apply_model(None)
        self.assertEqual(set(), self.controller._Controller__model.get_file_names())


class TestControllerUpdateStatus(BaseControllerTestCase):
    """Tests for Controller._update_controller_status()."""

    def test_remote_scan_updates_status(self):
        remote_scan = MagicMock()
        remote_scan.timestamp = 12345
        remote_scan.failed = False
        remote_scan.error_message = None
        # Phase 74-02: capacity fields default to None on the mock so the
        # capacity-write block is skipped (this test covers scan-time fields only).
        remote_scan.total_bytes = None
        remote_scan.used_bytes = None
        self.controller._update_controller_status(remote_scan, None)
        self.assertEqual(12345,
                         self.mock_context.status.controller.latest_remote_scan_time)
        self.assertEqual(False,
                         self.mock_context.status.controller.latest_remote_scan_failed)
        self.assertIsNone(
            self.mock_context.status.controller.latest_remote_scan_error)

    def test_local_scan_updates_status(self):
        local_scan = MagicMock()
        local_scan.timestamp = 67890
        # Phase 74-02: see above — skip capacity-write block in this test.
        local_scan.total_bytes = None
        local_scan.used_bytes = None
        self.controller._update_controller_status(None, local_scan)
        self.assertEqual(67890,
                         self.mock_context.status.controller.latest_local_scan_time)

    def test_both_none_no_crash(self):
        self.controller._update_controller_status(None, None)  # should not raise


class TestControllerPropagateExceptions(BaseControllerTestCase):
    """Tests for Controller.__propagate_exceptions and process()."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_process_calls_all_propagation_methods(self):
        self.controller.process()
        self.mock_lftp_manager.raise_pending_error.assert_called_once()
        self.mock_scan_manager.propagate_exceptions.assert_called_once()
        self.mock_mp_logger.propagate_exception.assert_called_once()
        self.mock_file_op_manager.propagate_exception.assert_called_once()

    def test_lftp_error_from_raise_pending_error_propagates(self):
        self.mock_lftp_manager.raise_pending_error.side_effect = LftpError("lftp broke")
        with self.assertRaises(LftpError):
            self.controller.process()

    def test_process_calls_cleanup_completed_processes(self):
        self.controller.process()
        self.mock_file_op_manager.cleanup_completed_processes.assert_called_once()


class TestControllerWebhookIntegration(BaseControllerTestCase):
    """Tests for Controller webhook integration."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_process_calls_webhook_manager(self):
        self.controller.process()
        self.assertTrue(self.mock_webhook_manager.process.called)

    def test_webhook_imports_added_to_persist(self):
        self._add_file_to_model("File.A", remote_size=5000)
        self._add_file_to_model("File.B", remote_size=3000)
        self.mock_webhook_manager.process.return_value = [("File.A", "File.A"), ("File.B", "File.B")]
        self.controller.process()
        self.assertIn("File.A", self.persist.imported_file_names)
        self.assertIn("File.B", self.persist.imported_file_names)

    def test_webhook_no_imports_when_empty(self):
        self.mock_webhook_manager.process.return_value = []
        self.controller.process()
        self.assertEqual(0, len(self.persist.imported_file_names))

    def test_webhook_name_lookup_includes_root_names(self):
        """Verify name_to_root dict passed to webhook_manager includes root file names."""
        self._add_file_to_model("File.A", remote_size=5000)
        self._add_file_to_model("File.B", remote_size=3000)
        self.controller.process()
        call_args = self.mock_webhook_manager.process.call_args[0][0]
        self.assertIn("file.a", call_args)
        self.assertEqual("File.A", call_args["file.a"])
        self.assertIn("file.b", call_args)
        self.assertEqual("File.B", call_args["file.b"])

    def test_webhook_name_lookup_includes_child_names(self):
        """Verify name_to_root dict includes child file names mapped to root."""
        # Create a directory with children
        root_dir = ModelFile("ShowDir", True)
        root_dir.remote_size = 5000
        child1 = ModelFile("Episode.S01E01.mkv", False)
        child1.remote_size = 2000
        child2 = ModelFile("Episode.S01E02.mkv", False)
        child2.remote_size = 3000
        root_dir.add_child(child1)
        root_dir.add_child(child2)
        self.controller._Controller__model.add_file(root_dir)
        self.controller.process()
        call_args = self.mock_webhook_manager.process.call_args[0][0]
        # Root name should be in the lookup
        self.assertIn("showdir", call_args)
        self.assertEqual("ShowDir", call_args["showdir"])
        # Child names should map back to root name
        self.assertIn("episode.s01e01.mkv", call_args)
        self.assertEqual("ShowDir", call_args["episode.s01e01.mkv"])
        self.assertIn("episode.s01e02.mkv", call_args)
        self.assertEqual("ShowDir", call_args["episode.s01e02.mkv"])

    def test_webhook_name_lookup_includes_nested_child_names(self):
        """Verify name_to_root dict includes deeply nested child names."""
        root_dir = ModelFile("ShowDir", True)
        root_dir.remote_size = 5000
        sub_dir = ModelFile("Season 1", True)
        root_dir.add_child(sub_dir)
        child = ModelFile("Episode.S01E01.mkv", False)
        child.remote_size = 2000
        sub_dir.add_child(child)
        self.controller._Controller__model.add_file(root_dir)
        self.controller.process()
        call_args = self.mock_webhook_manager.process.call_args[0][0]
        self.assertIn("showdir", call_args)
        self.assertIn("season 1", call_args)
        self.assertEqual("ShowDir", call_args["season 1"])
        self.assertIn("episode.s01e01.mkv", call_args)
        self.assertEqual("ShowDir", call_args["episode.s01e01.mkv"])


class TestControllerWebhookThreadSafety(BaseControllerTestCase):
    """Tests verifying model lock is acquired during webhook import processing."""

    def setUp(self):
        super().setUp()
        self._make_controller_started()

    def test_check_webhook_imports_acquires_model_lock_for_name_lookup(self):
        """Verify model lock is held when iterating model file names for name_to_root."""
        lock_was_held = []
        original_get_file_names = self.controller._Controller__model.get_file_names

        def check_lock_on_get_file_names():
            lock_was_held.append(self.controller._Controller__model_lock.locked())
            return original_get_file_names()

        self.controller._Controller__model.get_file_names = check_lock_on_get_file_names
        self.controller.process()
        self.assertTrue(
            any(lock_was_held),
            "Model lock must be held during get_file_names in webhook import name lookup"
        )

    def test_check_webhook_imports_acquires_model_lock_for_model_mutation(self):
        """Verify model lock is held when calling update_file for import status."""
        lock_held_during_update = []
        # Add a file to the model so an import can be processed
        f = ModelFile("test_file.mkv", False)
        f.remote_size = 1000
        self.controller._Controller__model.add_file(f)
        # Webhook manager reports this file was imported
        self.mock_webhook_manager.process.return_value = [("test_file.mkv", "test_file.mkv")]
        # Intercept update_file to check lock state
        original_update_file = self.controller._Controller__model.update_file

        def check_lock_on_update(new_file):
            lock_held_during_update.append(self.controller._Controller__model_lock.locked())
            return original_update_file(new_file)

        self.controller._Controller__model.update_file = check_lock_on_update
        self.controller.process()
        self.assertTrue(
            len(lock_held_during_update) > 0,
            "update_file must be called during webhook import"
        )
        self.assertTrue(
            lock_held_during_update[0],
            "Model lock must be held during update_file in webhook import"
        )
