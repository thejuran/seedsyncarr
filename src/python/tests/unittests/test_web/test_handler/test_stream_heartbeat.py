# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
from unittest.mock import patch

from web.handler.stream_heartbeat import HeartbeatStreamHandler, SerializeHeartbeat


class TestSerializeHeartbeat(unittest.TestCase):
    def test_ping_returns_sse_format(self):
        s = SerializeHeartbeat()
        result = s.ping(1000.0)
        self.assertIn("event: ping", result)
        self.assertIn("data: 1000.0", result)
        self.assertTrue(result.endswith("\n\n"))

    def test_ping_contains_timestamp(self):
        s = SerializeHeartbeat()
        result = s.ping(1234567890.5)
        self.assertIn("1234567890.5", result)


class TestHeartbeatStreamHandler(unittest.TestCase):
    @patch("web.handler.stream_heartbeat.time")
    def test_setup_resets_state(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        result = handler.get_value()
        self.assertIsNotNone(result)

    @patch("web.handler.stream_heartbeat.time")
    def test_initial_heartbeat_sent_immediately(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        result = handler.get_value()
        self.assertIsNotNone(result)
        self.assertIn("event: ping", result)
        self.assertIn("1000.0", result)

    @patch("web.handler.stream_heartbeat.time")
    def test_no_heartbeat_before_interval(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        handler.get_value()  # consume initial
        mock_time_module.time.return_value = 1005.0
        result = handler.get_value()
        self.assertIsNone(result)

    @patch("web.handler.stream_heartbeat.time")
    def test_heartbeat_after_interval(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        handler.get_value()  # consume initial
        mock_time_module.time.return_value = 1015.0
        result = handler.get_value()
        self.assertIsNotNone(result)
        self.assertIn("event: ping", result)
        self.assertIn("1015.0", result)

    @patch("web.handler.stream_heartbeat.time")
    def test_heartbeat_after_interval_exceeded(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        handler.get_value()  # consume initial
        mock_time_module.time.return_value = 1020.0
        result = handler.get_value()
        self.assertIsNotNone(result)

    @patch("web.handler.stream_heartbeat.time")
    def test_multiple_heartbeat_cycles(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        handler.get_value()  # initial heartbeat at 1000.0

        mock_time_module.time.return_value = 1015.0
        result = handler.get_value()  # second heartbeat at 1015.0
        self.assertIsNotNone(result)

        mock_time_module.time.return_value = 1025.0
        result = handler.get_value()  # only 10s since last
        self.assertIsNone(result)

        mock_time_module.time.return_value = 1030.0
        result = handler.get_value()  # 15s since 1015.0
        self.assertIsNotNone(result)

    @patch("web.handler.stream_heartbeat.time")
    def test_cleanup_is_noop(self, mock_time_module):
        mock_time_module.time.return_value = 1000.0
        handler = HeartbeatStreamHandler()
        handler.setup()
        handler.cleanup()  # should not raise

    def test_heartbeat_interval_constant(self):
        self.assertEqual(15, HeartbeatStreamHandler.HEARTBEAT_INTERVAL_S)

    @patch("web.handler.stream_heartbeat.time")
    def test_setup_can_be_called_again(self, mock_time_module):
        handler = HeartbeatStreamHandler()
        mock_time_module.time.return_value = 1000.0
        handler.setup()
        handler.get_value()  # consume initial at 1000.0

        mock_time_module.time.return_value = 1005.0
        result = handler.get_value()
        self.assertIsNone(result)  # 5s < interval

        handler.setup()  # reset
        mock_time_module.time.return_value = 1006.0
        result = handler.get_value()
        self.assertIsNotNone(result)  # initial heartbeat again after reset
