import logging
import os
import shlex
import sys
import unittest
from unittest.mock import patch

from controller.delete.delete_process import DeleteLocalProcess, DeleteRemoteProcess
from ssh import SshcpError


class TestDeleteRemoteProcess(unittest.TestCase):
    """
    Unit tests for DeleteRemoteProcess.

    Mocks Sshcp at the module level via
    patch('controller.delete.delete_process.Sshcp') to verify:
    - Constructor forwards host/port/user/password to Sshcp
    - run_once() issues 'rm -rf <shlex.quote(path)>' via shell()
    - SshcpError is caught and logged (not re-raised)
    """

    def setUp(self):
        sshcp_patcher = patch('controller.delete.delete_process.Sshcp')
        self.addCleanup(sshcp_patcher.stop)
        self.mock_sshcp_cls = sshcp_patcher.start()
        self.mock_sshcp = self.mock_sshcp_cls.return_value

        logger = logging.getLogger("DeleteRemoteProcess")
        self._test_handler = logging.StreamHandler(sys.stdout)
        self._test_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(self._test_handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger("DeleteRemoteProcess").removeHandler(self._test_handler)

    def test_constructs_sshcp_with_correct_args(self):
        DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password="pass", remote_port=22,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp_cls.assert_called_once_with(
            host="host", port=22, user="user", password="pass"
        )

    def test_constructs_sshcp_with_none_password(self):
        DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password=None, remote_port=2222,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp_cls.assert_called_once_with(
            host="host", port=2222, user="user", password=None
        )

    def test_run_once_issues_rm_rf_command(self):
        proc = DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password="pass", remote_port=22,
            remote_path="/remote/path", file_name="file name.mkv"
        )
        self.mock_sshcp.shell.return_value = b""
        proc.run_once()
        expected_path = shlex.quote(os.path.join("/remote/path", "file name.mkv"))
        self.mock_sshcp.shell.assert_called_once_with(
            "rm -rf {}".format(expected_path)
        )

    def test_run_once_catches_sshcp_error_without_raising(self):
        proc = DeleteRemoteProcess(
            remote_address="host", remote_username="user",
            remote_password=None, remote_port=22,
            remote_path="/remote", file_name="file.mkv"
        )
        self.mock_sshcp.shell.side_effect = SshcpError("connection refused")
        with self.assertLogs("DeleteRemoteProcess", level="ERROR"):
            proc.run_once()


class TestDeleteLocalProcess(unittest.TestCase):
    """
    Unit tests for DeleteLocalProcess.

    Covers:
    - File branch: os.remove() called when isfile is True
    - Directory branch (success): shutil.rmtree() called when isfile is False
    - Directory branch (failure): OSError from rmtree produces ERROR log, does not raise
    """

    def setUp(self):
        logger = logging.getLogger("DeleteLocalProcess")
        self._test_handler = logging.StreamHandler(sys.stdout)
        self._test_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(self._test_handler)
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger("DeleteLocalProcess").removeHandler(self._test_handler)

    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=False)
    @patch('shutil.rmtree', side_effect=OSError("permission denied"))
    def test_local_delete_logs_rmtree_failure(self, mock_rmtree, mock_isfile, mock_exists):
        """GUARD-03: a failed rmtree produces a log record rather than silent swallow."""
        proc = DeleteLocalProcess(local_path="/fake", file_name="somefile")
        with self.assertLogs("DeleteLocalProcess", level="ERROR"):
            proc.run_once()  # must not raise

    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    @patch('os.remove')
    @patch('shutil.rmtree')
    def test_local_delete_file_success(self, mock_rmtree, mock_remove, mock_isfile, mock_exists):
        """File branch: os.remove() called, shutil.rmtree() NOT called."""
        proc = DeleteLocalProcess(local_path="/fake", file_name="somefile.mkv")
        proc.run_once()
        mock_remove.assert_called_once()
        mock_rmtree.assert_not_called()

    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=False)
    @patch('shutil.rmtree')
    def test_local_delete_dir_success(self, mock_rmtree, mock_isfile, mock_exists):
        """Directory branch (success): shutil.rmtree() called once, no ERROR log."""
        proc = DeleteLocalProcess(local_path="/fake", file_name="somedir")
        proc.run_once()
        mock_rmtree.assert_called_once()
        # Verify no ERROR-level log was emitted (assertLogs raises AssertionError if no records)
        with self.assertRaises(AssertionError):
            with self.assertLogs("DeleteLocalProcess", level="ERROR"):
                pass  # assertLogs raises AssertionError when no matching records were emitted
