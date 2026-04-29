import json
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
        mock_serialize_cls.status.assert_called_once_with(self.mock_status)

    @patch('web.handler.status.SerializeStatusJson')
    def test_get_status_body_is_serialized(self, mock_serialize_cls):
        mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
        response = self.handler._StatusHandler__handle_get_status()
        self.assertEqual('{"server":{"up":true}}', response.body)
        mock_serialize_cls.status.assert_called_once_with(self.mock_status)

    @patch('web.handler.status.SerializeStatusJson')
    def test_get_status_calls_serializer_with_status(self, mock_serialize_cls):
        mock_serialize_cls.status.return_value = '{"server":{"up":true}}'
        self.handler._StatusHandler__handle_get_status()
        mock_serialize_cls.status.assert_called_once_with(self.mock_status)


class TestStatusHandlerRateLimit(unittest.TestCase):
    """Rate limit integration tests for status endpoint."""

    @patch('web.rate_limit.time')
    def test_status_rate_limited_at_60_per_60s(self, mock_time):
        """status should reject requests after 60 within 60s."""
        mock_time.time.return_value = 1000.0
        from web.rate_limit import rate_limit

        mock_status = MagicMock()
        handler = StatusHandler(mock_status)

        with patch('web.handler.status.SerializeStatusJson') as mock_serialize:
            mock_serialize.status.return_value = '{"server":{"up":true}}'
            rate_limited = rate_limit(max_requests=60, window_seconds=60.0)(
                handler._StatusHandler__handle_get_status
            )

            # First 60 should succeed
            for i in range(60):
                response = rate_limited()
                self.assertEqual(200, response.status_code)

            # 61st should be rate limited
            response = rate_limited()
            self.assertEqual(429, response.status_code)
            body = json.loads(response.body)
            self.assertIn("Rate limit", body["error"])
