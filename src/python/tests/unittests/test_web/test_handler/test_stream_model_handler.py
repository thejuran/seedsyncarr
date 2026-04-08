# Copyright 2017, Inderpreet Singh, All rights reserved.

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

    def test_initial_files_sent_one_at_a_time(self):
        file1 = ModelFile("alpha.txt", False)
        file2 = ModelFile("beta.txt", False)
        self.mock_controller.get_model_files_and_add_listener.return_value = [file1, file2]
        self.handler.setup()
        result1 = self.handler.get_value()
        self.assertIsNotNone(result1)
        self.assertIn("model-added", result1)
        result2 = self.handler.get_value()
        self.assertIsNotNone(result2)
        self.assertIn("model-added", result2)
        result3 = self.handler.get_value()
        self.assertIsNone(result3)

    def test_empty_initial_model(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        result = self.handler.get_value()
        self.assertIsNone(result)

    def test_initial_files_contain_file_data(self):
        file = ModelFile("test.txt", False)
        self.mock_controller.get_model_files_and_add_listener.return_value = [file]
        self.handler.setup()
        result = self.handler.get_value()
        self.assertIn("test.txt", result)

    def test_realtime_events_after_initial_files(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        new_file = ModelFile("new.txt", False)
        self.handler.model_listener.file_added(new_file)
        result = self.handler.get_value()
        self.assertIsNotNone(result)
        self.assertIn("model-added", result)
        self.assertIn("new.txt", result)

    def test_realtime_removed_event(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        old_file = ModelFile("removed.txt", False)
        self.handler.model_listener.file_removed(old_file)
        result = self.handler.get_value()
        self.assertIn("model-removed", result)

    def test_realtime_updated_event(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
        old_file = ModelFile("updated.txt", False)
        new_file = ModelFile("updated.txt", False)
        self.handler.model_listener.file_updated(old_file, new_file)
        result = self.handler.get_value()
        self.assertIn("model-updated", result)

    def test_no_events_returns_none(self):
        self.mock_controller.get_model_files_and_add_listener.return_value = []
        self.handler.setup()
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
