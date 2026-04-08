# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
from unittest.mock import MagicMock, patch

from controller import LftpManager
from lftp import LftpError, LftpJobStatusParserError


class TestLftpManager(unittest.TestCase):
    """Unit tests for LftpManager."""

    def setUp(self):
        """Set up mocked context for tests."""
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()

        # Mock config attributes
        self.mock_context.config.lftp.remote_address = "remote.server.com"
        self.mock_context.config.lftp.remote_port = 22
        self.mock_context.config.lftp.remote_username = "user"
        self.mock_context.config.lftp.remote_password = "password"  # Test-only credential — not a real secret (mock, no real connection)
        self.mock_context.config.lftp.use_ssh_key = False
        self.mock_context.config.lftp.remote_path = "/remote/path"
        self.mock_context.config.lftp.local_path = "/local/path"
        self.mock_context.config.lftp.num_max_parallel_downloads = 2
        self.mock_context.config.lftp.num_max_parallel_files_per_download = 3
        self.mock_context.config.lftp.num_max_connections_per_root_file = 4
        self.mock_context.config.lftp.num_max_connections_per_dir_file = 2
        self.mock_context.config.lftp.num_max_total_connections = 8
        self.mock_context.config.lftp.use_temp_file = True
        self.mock_context.config.general.verbose = False

    @patch('controller.lftp_manager.Lftp')
    def test_init_creates_lftp_with_correct_config(self, mock_lftp_class):
        """Test that __init__ creates Lftp with correct configuration."""
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)  # noqa: F841

        # Verify Lftp was created with correct arguments
        mock_lftp_class.assert_called_once_with(
            address="remote.server.com",
            port=22,
            user="user",
            password="password"
        )

        # Verify configuration was applied
        self.assertEqual(mock_lftp.num_parallel_jobs, 2)
        self.assertEqual(mock_lftp.num_parallel_files, 3)
        self.assertEqual(mock_lftp.num_connections_per_root_file, 4)
        self.assertEqual(mock_lftp.num_connections_per_dir_file, 2)
        self.assertEqual(mock_lftp.num_max_total_connections, 8)
        self.assertTrue(mock_lftp.use_temp_file)

    @patch('controller.lftp_manager.Lftp')
    def test_init_uses_none_password_with_ssh_key(self, mock_lftp_class):
        """Test that SSH key mode uses None for password."""
        self.mock_context.config.lftp.use_ssh_key = True
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)  # noqa: F841

        # Verify Lftp was created with password=None
        call_args = mock_lftp_class.call_args
        self.assertIsNone(call_args.kwargs['password'])

    @patch('controller.lftp_manager.Lftp')
    def test_queue_delegates_to_lftp(self, mock_lftp_class):
        """Test that queue() delegates to Lftp.queue()."""
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        manager.queue("test_file", is_dir=True)

        mock_lftp.queue.assert_called_once_with("test_file", True)

    @patch('controller.lftp_manager.Lftp')
    def test_queue_propagates_lftp_error(self, mock_lftp_class):
        """Test that queue() propagates LftpError."""
        mock_lftp = MagicMock()
        mock_lftp.queue.side_effect = LftpError("Queue failed")
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)

        with self.assertRaises(LftpError):
            manager.queue("test_file", is_dir=False)

    @patch('controller.lftp_manager.Lftp')
    def test_kill_delegates_to_lftp(self, mock_lftp_class):
        """Test that kill() delegates to Lftp.kill()."""
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        manager.kill("test_file")

        mock_lftp.kill.assert_called_once_with("test_file")

    @patch('controller.lftp_manager.Lftp')
    def test_kill_propagates_lftp_error(self, mock_lftp_class):
        """Test that kill() propagates LftpError."""
        mock_lftp = MagicMock()
        mock_lftp.kill.side_effect = LftpError("Kill failed")
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)

        with self.assertRaises(LftpError):
            manager.kill("test_file")

    @patch('controller.lftp_manager.Lftp')
    def test_status_returns_lftp_status(self, mock_lftp_class):
        """Test that status() returns Lftp status."""
        mock_lftp = MagicMock()
        mock_status = [MagicMock(), MagicMock()]
        mock_lftp.status.return_value = mock_status
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        result = manager.status()

        self.assertEqual(result, mock_status)
        mock_lftp.status.assert_called_once()

    @patch('controller.lftp_manager.Lftp')
    def test_status_returns_none_on_lftp_error(self, mock_lftp_class):
        """Test that status() returns None on LftpError."""
        mock_lftp = MagicMock()
        mock_lftp.status.side_effect = LftpError("Status failed")
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        result = manager.status()

        self.assertIsNone(result)

    @patch('controller.lftp_manager.Lftp')
    def test_status_returns_none_on_parser_error(self, mock_lftp_class):
        """Test that status() returns None on LftpJobStatusParserError."""
        mock_lftp = MagicMock()
        mock_lftp.status.side_effect = LftpJobStatusParserError("Parse failed")
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        result = manager.status()

        self.assertIsNone(result)

    @patch('controller.lftp_manager.Lftp')
    def test_exit_delegates_to_lftp(self, mock_lftp_class):
        """Test that exit() delegates to Lftp.exit()."""
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        manager.exit()

        mock_lftp.exit.assert_called_once()

    @patch('controller.lftp_manager.Lftp')
    def test_raise_pending_error_delegates_to_lftp(self, mock_lftp_class):
        """Test that raise_pending_error() delegates to Lftp."""
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        manager.raise_pending_error()

        mock_lftp.raise_pending_error.assert_called_once()

    @patch('controller.lftp_manager.Lftp')
    def test_lftp_property_returns_underlying_lftp(self, mock_lftp_class):
        """Test that lftp property returns the underlying Lftp instance."""
        mock_lftp = MagicMock()
        mock_lftp_class.return_value = mock_lftp

        manager = LftpManager(self.mock_context)
        result = manager.lftp

        self.assertIs(result, mock_lftp)


if __name__ == '__main__':
    unittest.main()
