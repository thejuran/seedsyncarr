import unittest
from unittest.mock import MagicMock

from controller import Controller
from model import ModelFile
from web.handler.stream_model import ModelStreamHandler, WebResponseModelListener
from web.serialize import SerializeModel


class TestWebResponseModelListener(unittest.TestCase):
    def test_file_added_puts_added_event(self):
        listener = WebResponseModelListener()
        file = ModelFile("test.txt", False)
        listener.file_added(file)
        event = listener.get_next_event()
        self.assertIsNotNone(event)
        self.assertEqual(SerializeModel.UpdateEvent.Change.ADDED, event.change)
        self.assertIsNone(event.old_file)
        self.assertIs(file, event.new_file)

    def test_file_removed_puts_removed_event(self):
        listener = WebResponseModelListener()
        file = ModelFile("test.txt", False)
        listener.file_removed(file)
        event = listener.get_next_event()
        self.assertIsNotNone(event)
        self.assertEqual(SerializeModel.UpdateEvent.Change.REMOVED, event.change)
        self.assertIs(file, event.old_file)
        self.assertIsNone(event.new_file)

    def test_file_updated_puts_updated_event(self):
        listener = WebResponseModelListener()
        old_file = ModelFile("test.txt", False)
        new_file = ModelFile("test.txt", False)
        listener.file_updated(old_file, new_file)
        event = listener.get_next_event()
        self.assertIsNotNone(event)
        self.assertEqual(SerializeModel.UpdateEvent.Change.UPDATED, event.change)
        self.assertIs(old_file, event.old_file)
        self.assertIs(new_file, event.new_file)

    def test_empty_queue_returns_none(self):
        listener = WebResponseModelListener()
        event = listener.get_next_event()
        self.assertIsNone(event)


class TestModelStreamHandler(unittest.TestCase):
    def setUp(self):
        self.mock_controller = MagicMock(spec=Controller)
        self.handler = ModelStreamHandler(self.mock_controller)

    def test_setup_registers_listener(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.mock_controller.get_model_files_and_add_listener.assert_called_once()
        call_args = self.mock_controller.get_model_files_and_add_listener.call_args[0][0]
        self.assertIs(call_args, self.handler.model_listener)

    def test_initial_files_sent_as_single_init_event(self):
        file1 = ModelFile("alpha.txt", False)
        file2 = ModelFile("beta.txt", False)
        self.mock_controller.get_model_files_and_add_listener.return_value = [file1, file2]
        self.handler.setup()
        result1 = self.handler.get_value()
        self.assertIsNotNone(result1)
        self.assertIn("model-init", result1)
        self.assertIn("alpha.txt", result1)
        self.assertIn("beta.txt", result1)
        result2 = self.handler.get_value()
        self.assertIsNone(result2)

    def test_empty_initial_model_sends_empty_init_event(self):
        # An empty model still sends model-init so the frontend knows the
        # initial state has loaded
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        result = self.handler.get_value()
        self.assertIsNotNone(result)
        self.assertIn("model-init", result)
        result2 = self.handler.get_value()
        self.assertIsNone(result2)

    def test_initial_files_contain_file_data(self):
        file = ModelFile("test.txt", False)
        self.mock_controller.get_model_files_and_add_listener.return_value = [file]
        self.handler.setup()
        result = self.handler.get_value()
        self.assertIn("test.txt", result)

    def test_realtime_events_after_initial_files(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.handler.get_value()  # consume model-init
        new_file = ModelFile("new.txt", False)
        self.handler.model_listener.file_added(new_file)
        result = self.handler.get_value()
        self.assertIsNotNone(result)
        self.assertIn("model-added", result)
        self.assertIn("new.txt", result)

    def test_realtime_removed_event(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.handler.get_value()  # consume model-init
        old_file = ModelFile("removed.txt", False)
        self.handler.model_listener.file_removed(old_file)
        result = self.handler.get_value()
        self.assertIn("model-removed", result)

    def test_realtime_updated_event(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.handler.get_value()  # consume model-init
        old_file = ModelFile("updated.txt", False)
        new_file = ModelFile("updated.txt", False)
        self.handler.model_listener.file_updated(old_file, new_file)
        result = self.handler.get_value()
        self.assertIn("model-updated", result)

    def test_no_events_returns_none(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.handler.get_value()  # consume model-init
        result = self.handler.get_value()
        self.assertIsNone(result)

    def test_cleanup_removes_listener(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        self.handler.cleanup()
        self.mock_controller.remove_model_listener.assert_called_once_with(
            self.handler.model_listener
        )

    def test_cleanup_with_no_setup(self):
        self.handler.cleanup()
        self.mock_controller.remove_model_listener.assert_called_once()

    def test_mixed_initial_and_realtime(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = [
            ModelFile("init.txt", False)
        ]
        self.handler.setup()
        # Add realtime event before consuming initial
        self.handler.model_listener.file_added(ModelFile("realtime.txt", False))
        result1 = self.handler.get_value()
        self.assertIn("init.txt", result1)
        result2 = self.handler.get_value()
        self.assertIn("realtime.txt", result2)
        result3 = self.handler.get_value()
        self.assertIsNone(result3)


class TestModelStreamHandlerResync(unittest.TestCase):
    """STRM-02 (D-02..D-05, D-08): a mocked Controller proving the resync
    gate's coalescing, bounded state, and rate-limited warning in isolation
    from the real lock (covered separately by TestModelStreamConvergence)."""

    def setUp(self):
        self.mock_controller = MagicMock(spec=Controller)
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.mock_controller.resync_model_files.side_effect = \
            lambda discard: (discard(), [ModelFile("snap.txt", False)])[1]
        self.handler = ModelStreamHandler(self.mock_controller)
        self.handler.setup()
        self.handler.get_value()  # consume initial model-init
        self._overflow_offset = 0

    def _overflow(self, n=1001):
        """Floods the listener's queue past maxsize without draining it,
        using a unique name offset per call so repeated bursts never collide."""
        for i in range(n):
            self.handler.model_listener.file_added(
                ModelFile("f%d" % (self._overflow_offset + i), False)
            )
        self._overflow_offset += n

    def test_no_resync_without_drops(self):
        self.handler.model_listener.file_added(ModelFile("one.txt", False))
        result = self.handler.get_value()
        self.assertIn("model-added", result)
        self.mock_controller.resync_model_files.assert_not_called()

    def test_drop_triggers_single_model_init_resync(self):
        self._overflow()

        result = self.handler.get_value()
        self.assertIn("model-init", result)
        self.assertIn("snap.txt", result)

        self.mock_controller.resync_model_files.assert_called_once()
        call_args = self.mock_controller.resync_model_files.call_args[0]
        self.assertEqual(1, len(call_args))
        self.assertTrue(callable(call_args[0]))

        self.assertIsNone(self.handler.get_value())

    def test_multiple_drops_coalesce_into_one_resync(self):
        self._overflow()
        self._overflow()
        self._overflow()

        self.handler.get_value()
        result2 = self.handler.get_value()

        self.mock_controller.resync_model_files.assert_called_once()
        self.assertIsNone(result2)

    def test_resync_pending_state_is_bounded(self):
        self._overflow()
        self._overflow()
        self._overflow()

        self.assertLessEqual(
            self.handler.model_listener.get_queue_size(),
            self.handler.model_listener.get_maxsize(),
        )

        self.handler.get_value()

        self.assertEqual(0, self.handler.model_listener.get_queue_size())
        # No handler attribute holds a list of snapshots -- a single bool.
        self.assertIsNone(self.handler.initial_model_files)

    def test_resync_warning_rate_limited_by_resync_count(self):
        with self.assertLogs("ModelStreamHandler", level="WARNING") as cm:
            for _ in range(101):
                self._overflow(1001)
                self.handler.get_value()

        self.assertEqual(2, len(cm.records))
        for record in cm.records:
            message = record.getMessage()
            self.assertNotIn("f1", message)

    def test_drop_during_resync_is_absorbed(self):
        def resync_with_concurrent_drop(discard):
            # Simulate drops that land before the discard runs inside the
            # lock (D-04): they must be absorbed by this same resync, not
            # trigger a second one.
            for i in range(1001):
                self.handler.model_listener.file_added(
                    ModelFile("concurrent-%d" % i, False)
                )
            discard()
            return [ModelFile("snap.txt", False)]

        self.mock_controller.resync_model_files.side_effect = resync_with_concurrent_drop

        self._overflow()
        self.handler.get_value()  # triggers the resync above

        result = self.handler.get_value()
        self.assertIsNone(result)
        self.mock_controller.resync_model_files.assert_called_once()
