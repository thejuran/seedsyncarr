# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
from unittest.mock import MagicMock

from web.handler.stream_status import StatusStreamHandler, StatusListener


class TestStatusListener(unittest.TestCase):
    def test_notify_copies_status_and_queues(self):
        mock_status = MagicMock()
        mock_copy = MagicMock()
        mock_status.copy.return_value = mock_copy
        listener = StatusListener(mock_status)
        listener.notify()
        mock_status.copy.assert_called_once()
        event = listener.get_next_event()
        self.assertIs(mock_copy, event)

    def test_multiple_notifications_queued(self):
        mock_status = MagicMock()
        mock_status.copy.side_effect = [MagicMock(), MagicMock()]
        listener = StatusListener(mock_status)
        listener.notify()
        listener.notify()
        event1 = listener.get_next_event()
        event2 = listener.get_next_event()
        self.assertIsNotNone(event1)
        self.assertIsNotNone(event2)
        self.assertIsNot(event1, event2)

    def test_empty_queue_returns_none(self):
        mock_status = MagicMock()
        listener = StatusListener(mock_status)
        event = listener.get_next_event()
        self.assertIsNone(event)


class TestStatusStreamHandler(unittest.TestCase):
    def setUp(self):
        self.mock_status = MagicMock()
        self.handler = StatusStreamHandler(self.mock_status)
        # Replace real SerializeStatus with mock to avoid json.dumps failure on MagicMock
        self.handler.serialize = MagicMock()
        self.handler.serialize.status.return_value = "event: status\ndata: {}\n\n"

    def test_setup_registers_listener(self):
        self.handler.setup()
        self.mock_status.add_listener.assert_called_once_with(
            self.handler.status_listener
        )

    def test_first_get_value_returns_current_status(self):
        mock_status_copy = MagicMock()
        self.mock_status.copy.return_value = mock_status_copy
        self.handler.setup()
        result = self.handler.get_value()
        self.assertIsNotNone(result)
        self.mock_status.copy.assert_called_once()
        self.assertIn("event: status", result)

    def test_first_get_value_sets_first_run_false(self):
        self.mock_status.copy.return_value = MagicMock()
        self.handler.setup()
        self.assertTrue(self.handler.first_run)
        self.handler.get_value()
        self.assertFalse(self.handler.first_run)

    def test_second_get_value_reads_from_queue(self):
        self.mock_status.copy.return_value = MagicMock()
        self.handler.setup()
        self.handler.get_value()  # consume first run
        result = self.handler.get_value()
        self.assertIsNone(result)

    def test_second_get_value_returns_queued_status(self):
        self.mock_status.copy.return_value = MagicMock()
        self.handler.setup()
        self.handler.get_value()  # consume first run
        # Simulate a status update via the listener
        queued_status = MagicMock()
        self.mock_status.copy.return_value = queued_status
        self.handler.status_listener.notify()
        result = self.handler.get_value()
        self.assertIsNotNone(result)
        self.assertIn("event: status", result)

    def test_cleanup_removes_listener(self):
        self.handler.setup()
        self.handler.cleanup()
        self.mock_status.remove_listener.assert_called_once_with(
            self.handler.status_listener
        )

    def test_cleanup_with_no_setup(self):
        self.handler.cleanup()
        self.mock_status.remove_listener.assert_called_once()
