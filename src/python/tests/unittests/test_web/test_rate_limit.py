"""
Unit tests for the rate_limit sliding-window decorator factory.
"""
import json
import unittest
from unittest.mock import patch

from web.rate_limit import rate_limit


class TestRateLimitUnderLimit(unittest.TestCase):
    """Tests that requests under the limit pass through normally."""

    def setUp(self):
        # Create a fresh decorated handler for each test
        def _handler():
            return "OK"

        self.handler = rate_limit(3, 60.0)(_handler)

    @patch("web.rate_limit.time")
    def test_first_call_passes_through(self, mock_time):
        mock_time.time.return_value = 1000.0
        result = self.handler()
        self.assertEqual("OK", result)

    @patch("web.rate_limit.time")
    def test_calls_under_limit_all_pass(self, mock_time):
        mock_time.time.return_value = 1000.0
        for _ in range(3):
            result = self.handler()
            self.assertEqual("OK", result)


class TestRateLimitOverLimit(unittest.TestCase):
    """Tests that requests over the limit receive HTTP 429."""

    def setUp(self):
        def _handler():
            return "OK"

        self.handler = rate_limit(3, 60.0)(_handler)

    @patch("web.rate_limit.time")
    def test_fourth_call_returns_429(self, mock_time):
        mock_time.time.return_value = 1000.0
        # First 3 calls should pass
        for _ in range(3):
            self.handler()
        # 4th call should be rate limited
        response = self.handler()
        self.assertEqual(429, response.status_code)

    @patch("web.rate_limit.time")
    def test_429_response_body_is_correct_json(self, mock_time):
        mock_time.time.return_value = 1000.0
        for _ in range(3):
            self.handler()
        response = self.handler()
        body = json.loads(response.body)
        self.assertEqual({"error": "Rate limit exceeded. Please try again later."}, body)

    @patch("web.rate_limit.time")
    def test_429_response_content_type_is_json(self, mock_time):
        mock_time.time.return_value = 1000.0
        for _ in range(3):
            self.handler()
        response = self.handler()
        self.assertEqual("application/json", response.content_type)

    @patch("web.rate_limit.time")
    def test_subsequent_calls_over_limit_also_return_429(self, mock_time):
        mock_time.time.return_value = 1000.0
        for _ in range(3):
            self.handler()
        # 4th and 5th calls should both be rate limited
        for _ in range(2):
            response = self.handler()
            self.assertEqual(429, response.status_code)


class TestRateLimitWindowReset(unittest.TestCase):
    """Tests that the sliding window resets correctly after expiry."""

    @patch("web.rate_limit.time")
    def test_requests_succeed_after_window_expires(self, mock_time):
        def _handler():
            return "OK"

        handler = rate_limit(3, 60.0)(_handler)

        # Fill up the window at t=1000
        mock_time.time.return_value = 1000.0
        for _ in range(3):
            handler()

        # 4th call at same time is rate limited
        response = handler()
        self.assertEqual(429, response.status_code)

        # Advance time past the window (60 seconds + 1)
        mock_time.time.return_value = 1061.0

        # Now requests should succeed again
        result = handler()
        self.assertEqual("OK", result)

    @patch("web.rate_limit.time")
    def test_sliding_window_only_counts_recent_requests(self, mock_time):
        """Requests at the edge of the window should slide out as time advances."""
        def _handler():
            return "OK"

        handler = rate_limit(3, 60.0)(_handler)

        # Make 2 requests at t=1000
        mock_time.time.return_value = 1000.0
        handler()
        handler()

        # Make 1 request at t=1020 (within window)
        mock_time.time.return_value = 1020.0
        handler()

        # At t=1062, the first 2 requests (at t=1000) fall outside the window
        # but the one at t=1020 is still in window
        mock_time.time.return_value = 1062.0
        # Only 1 request in window — should pass (limit is 3)
        result = handler()
        self.assertEqual("OK", result)


class TestRateLimitIndependentClosures(unittest.TestCase):
    """Tests that separate rate_limit() calls have independent state."""

    @patch("web.rate_limit.time")
    def test_two_handlers_have_independent_counters(self, mock_time):
        mock_time.time.return_value = 1000.0

        def _handler_a():
            return "A"

        def _handler_b():
            return "B"

        handler_a = rate_limit(3, 60.0)(_handler_a)
        handler_b = rate_limit(3, 60.0)(_handler_b)

        # Exhaust handler_a's limit
        for _ in range(3):
            handler_a()

        # handler_a is now rate limited
        response_a = handler_a()
        self.assertEqual(429, response_a.status_code)

        # handler_b should still work (independent counter)
        result_b = handler_b()
        self.assertEqual("B", result_b)

    @patch("web.rate_limit.time")
    def test_same_function_decorated_twice_has_independent_state(self, mock_time):
        mock_time.time.return_value = 1000.0

        def _handler():
            return "OK"

        handler_1 = rate_limit(3, 60.0)(_handler)
        handler_2 = rate_limit(3, 60.0)(_handler)

        # Exhaust handler_1
        for _ in range(3):
            handler_1()
        response_1 = handler_1()
        self.assertEqual(429, response_1.status_code)

        # handler_2 counter is independent
        result_2 = handler_2()
        self.assertEqual("OK", result_2)


class TestRateLimitFunctoolsWraps(unittest.TestCase):
    """Tests that functools.wraps preserves wrapped function metadata."""

    def test_wraps_preserves_function_name(self):
        def my_unique_handler():
            return "OK"

        decorated = rate_limit(3, 60.0)(my_unique_handler)
        self.assertEqual("my_unique_handler", decorated.__name__)

    def test_wraps_sets_wrapped_attribute(self):
        def my_unique_handler():
            return "OK"

        decorated = rate_limit(3, 60.0)(my_unique_handler)
        self.assertIs(my_unique_handler, decorated.__wrapped__)


class TestRateLimitArgPassthrough(unittest.TestCase):
    """Tests that *args and **kwargs are passed through to the wrapped handler."""

    @patch("web.rate_limit.time")
    def test_kwargs_passed_through(self, mock_time):
        mock_time.time.return_value = 1000.0
        received = {}

        def _handler(section, key, value):
            received["section"] = section
            received["key"] = key
            received["value"] = value
            return "OK"

        handler = rate_limit(3, 60.0)(_handler)
        result = handler(section="media", key="path", value="/downloads")
        self.assertEqual("OK", result)
        self.assertEqual("media", received["section"])
        self.assertEqual("path", received["key"])
        self.assertEqual("/downloads", received["value"])

    @patch("web.rate_limit.time")
    def test_positional_args_passed_through(self, mock_time):
        mock_time.time.return_value = 1000.0
        received = []

        def _handler(*args):
            received.extend(args)
            return "OK"

        handler = rate_limit(3, 60.0)(_handler)
        result = handler("arg1", "arg2")
        self.assertEqual("OK", result)
        self.assertEqual(["arg1", "arg2"], received)


if __name__ == "__main__":
    unittest.main()
