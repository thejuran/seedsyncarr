import unittest
from unittest.mock import MagicMock, ANY

from web.handler.server import ServerHandler


class TestServerHandler(unittest.TestCase):
    def setUp(self):
        self.mock_context = MagicMock()
        self.handler = ServerHandler(self.mock_context)

    def test_initial_state_not_restart_requested(self):
        self.assertFalse(self.handler.is_restart_requested())

    def test_restart_handler_returns_200(self):
        response = self.handler._ServerHandler__handle_action_restart()
        self.assertEqual(200, response.status_code)

    def test_restart_handler_returns_requested_restart_body(self):
        response = self.handler._ServerHandler__handle_action_restart()
        self.assertEqual("Requested restart", response.body)

    def test_restart_sets_restart_requested(self):
        self.handler._ServerHandler__handle_action_restart()
        self.assertTrue(self.handler.is_restart_requested())

    def test_restart_idempotent(self):
        response1 = self.handler._ServerHandler__handle_action_restart()
        response2 = self.handler._ServerHandler__handle_action_restart()
        self.assertEqual(200, response1.status_code)
        self.assertEqual(200, response2.status_code)
        self.assertTrue(self.handler.is_restart_requested())

    def test_restart_logs_info(self):
        self.handler._ServerHandler__handle_action_restart()
        self.handler.logger.info.assert_called()
        log_message = self.handler.logger.info.call_args[0][0]
        self.assertIn("restart", log_message.lower())

    def test_constructor_creates_child_logger(self):
        self.mock_context.logger.getChild.assert_called_once_with("ServerActionHandler")

    def test_restart_route_registered_as_post(self):
        """ENDP-01: Restart endpoint must use POST method."""
        mock_web_app = MagicMock()
        self.handler.add_routes(mock_web_app)
        mock_web_app.add_post_handler.assert_called_once_with(
            "/server/command/restart",
            unittest.mock.ANY  # the private handler method
        )
        # Ensure add_handler (GET) was NOT called
        mock_web_app.add_handler.assert_not_called()
