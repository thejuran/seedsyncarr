# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
from unittest.mock import MagicMock, patch

from web.handler.status import StatusHandler


class TestStatusHandler(unittest.TestCase):
    def setUp(self):
        self.mock_status = MagicMock()
        self.handler = StatusHandler(self.mock_status)

    @patch('web.handler.status.SerializeStatusJson')
    def test_get_status_returns_200(self, mock_serialize_cls):
        mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
        response = self.handler._StatusHandler__handle_get_status()
        self.assertEqual(200, response.status_code)

    @patch('web.handler.status.SerializeStatusJson')
    def test_get_status_body_is_serialized(self, mock_serialize_cls):
        mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
        response = self.handler._StatusHandler__handle_get_status()
        self.assertEqual('{"server":{"up":true}}', response.body)

    @patch('web.handler.status.SerializeStatusJson')
    def test_get_status_calls_serializer_with_status(self, mock_serialize_cls):
        mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
        self.handler._StatusHandler__handle_get_status()
        mock_serialize_cls.status.assert_called_once_with(self.mock_status)
