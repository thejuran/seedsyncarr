import unittest
import logging
import sys
from unittest.mock import patch, call, ANY
import tempfile
import os
import json
import hashlib
import shutil

from controller.scan import RemoteScanner, ScannerError
from ssh import SshcpError
from common import Localization

# Test-only credential for mock scanner — SSH is patched; this value never reaches a real server.


class TestRemoteScanner(unittest.TestCase):
    temp_dir = None
    temp_scan_script = None

    def setUp(self):
        ssh_patcher = patch('controller.scan.remote_scanner.Sshcp')
        self.addCleanup(ssh_patcher.stop)
        self.mock_ssh_cls = ssh_patcher.start()
        self.mock_ssh = self.mock_ssh_cls.return_value

        logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)

        # Ssh to return mangled binary by default
        self.mock_ssh.shell.return_value = b'error'

    @classmethod
    def setUpClass(cls):
        TestRemoteScanner.temp_dir = tempfile.mkdtemp(prefix="test_remote_scanner")
        TestRemoteScanner.temp_scan_script = os.path.join(TestRemoteScanner.temp_dir, "script")
        with open(TestRemoteScanner.temp_scan_script, "w") as f:
            f.write("")
        # Pre-compute the md5 of the empty scan script for tests that need it
        with open(TestRemoteScanner.temp_scan_script, "rb") as f:
            TestRemoteScanner.scan_script_md5 = hashlib.md5(f.read()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TestRemoteScanner.temp_dir)

    def test_correctly_initializes_ssh(self):
        self.ssh_args = {}

        def mock_ssh_ctor(**kwargs):
            self.ssh_args = kwargs

        self.mock_ssh_cls.side_effect = mock_ssh_ctor

        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.assertIsNotNone(scanner)
        self.assertEqual("my remote address", self.ssh_args["host"])
        self.assertEqual(1234, self.ssh_args["port"])
        self.assertEqual("my remote user", self.ssh_args["user"])
        self.assertEqual("my password", self.ssh_args["password"])

    def test_installs_scan_script_on_first_scan(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh returns error for md5sum check, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # first try
                return "".encode()
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()
        self.mock_ssh.copy.assert_called_once_with(
            local_path=TestRemoteScanner.temp_scan_script,
            remote_path="/remote/path/to/scan/script"
        )
        self.mock_ssh.copy.reset_mock()

        # should not be called the second time
        scanner.scan()
        self.mock_ssh.copy.assert_not_called()

    def test_copy_appends_scanfs_name_to_remote_path(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan"
        )

        self.ssh_run_command_count = 0

        # Ssh returns error for md5sum check, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # first try
                return "".encode()
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()
        # check for appended path ('script')
        self.mock_ssh.copy.assert_called_once_with(
            local_path=TestRemoteScanner.temp_scan_script,
            remote_path="/remote/path/to/scan/script"
        )

    def test_calls_correct_ssh_md5sum_command(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh returns error for md5sum check, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # first try
                return "".encode()
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()
        self.assertEqual(2, self.mock_ssh.shell.call_count)
        self.mock_ssh.shell.assert_has_calls([
            call("md5sum /remote/path/to/scan/script | awk '{print $1}' || echo"),
            call(ANY)
        ])

    def test_skips_install_on_md5sum_match(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh returns empty on md5sum, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # first try
                return "d41d8cd98f00b204e9800998ecf8427e".encode()
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()
        self.mock_ssh.copy.assert_not_called()
        self.mock_ssh.copy.reset_mock()

        # should not be called the second time either
        scanner.scan()
        self.mock_ssh.copy.assert_not_called()

    def test_installs_scan_script_on_any_md5sum_output(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh returns error for md5sum check, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # first try
                return "some output from md5sum".encode()
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()
        self.mock_ssh.copy.assert_called_once_with(
            local_path=TestRemoteScanner.temp_scan_script,
            remote_path="/remote/path/to/scan/script"
        )
        self.mock_ssh.copy.reset_mock()

    def test_raises_nonrecoverable_error_on_md5sum_error(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh returns error for md5sum check, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                raise SshcpError("an ssh error")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_INSTALL.format("an ssh error"), str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)

    def test_calls_correct_ssh_scan_command(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh returns error for md5sum check, empty pickle dump for later commands
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()
        self.assertEqual(2, self.mock_ssh.shell.call_count)
        self.mock_ssh.shell.assert_called_with(
            "/remote/path/to/scan/script /remote/path/to/scan"
        )

    def test_raises_nonrecoverable_error_on_first_failed_ssh(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh run command fails the first time with a non-timeout error
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first try
                raise SshcpError("an ssh error")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_SCAN.format("an ssh error"), str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)

    def test_raises_recoverable_error_on_first_run_timeout(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh run command times out on the first scan attempt
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first scan attempt - timeout
                raise SshcpError("Timed out")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_SCAN.format("Timed out"), str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)

    def test_raises_recoverable_error_on_first_run_connection_refused(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh run command gets connection refused on the first scan attempt
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first scan attempt - connection refused
                raise SshcpError("Connection refused by server")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_SCAN.format("Connection refused by server"),
            str(ctx.exception)
        )
        self.assertTrue(ctx.exception.recoverable)

    def test_recovers_after_first_run_timeout(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        local_md5 = TestRemoteScanner.scan_script_md5
        self.ssh_run_command_count = 0

        # First scan: install succeeds (md5 match skips copy), scan times out
        # Second scan: install skipped (already done), scan succeeds
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check (first scan) — matches, so copy is skipped
                return local_md5.encode()
            elif self.ssh_run_command_count == 2:
                # first scan attempt - timeout
                raise SshcpError("Timed out")
            else:
                # second scan attempt - succeeds (no install re-run)
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertTrue(ctx.exception.recoverable)

        # Retry succeeds — install is not re-run
        files = scanner.scan()
        self.assertEqual([], files)
        self.mock_ssh.copy.assert_not_called()
        self.assertEqual(3, self.mock_ssh.shell.call_count)

    def test_raises_nonrecoverable_error_on_system_scanner_error_with_timeout_in_message(self):
        """SystemScannerError is always fatal, even if the message also contains 'Timed out'"""
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                raise SshcpError("SystemScannerError: Timed out waiting for lock")
            else:
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertFalse(ctx.exception.recoverable)

    def test_raises_recoverable_error_on_md5sum_timeout(self):
        """Timeout during install_scanfs md5sum check is recoverable"""
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        # md5sum check times out
        def ssh_shell(*args):
            raise SshcpError("Timed out")
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_INSTALL.format("Timed out"), str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)

    def test_raises_recoverable_error_on_copy_timeout(self):
        """Timeout during install_scanfs copy is recoverable"""
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        # md5sum returns empty string (hash mismatch → triggers copy), copy times out
        self.mock_ssh.shell.return_value = b''

        def ssh_copy(*args, **kwargs):
            raise SshcpError("Timed out")
        self.mock_ssh.copy.side_effect = ssh_copy

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_INSTALL.format("Timed out"), str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)

    def test_raises_nonrecoverable_error_on_wrong_password_after_first_run(self):
        """Permanent SSH errors are fatal even after first successful scan"""
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        local_md5 = TestRemoteScanner.scan_script_md5
        self.ssh_run_command_count = 0

        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return local_md5.encode()
            elif self.ssh_run_command_count == 2:
                # first scan succeeds
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # second scan - wrong password (e.g. password was changed)
                raise SshcpError("Incorrect password")
            else:
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()  # succeeds
        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertFalse(ctx.exception.recoverable)

    def test_raises_nonrecoverable_error_on_host_key_change_after_first_run(self):
        """Host key changes are fatal even after first successful scan"""
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        local_md5 = TestRemoteScanner.scan_script_md5
        self.ssh_run_command_count = 0

        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return local_md5.encode()
            elif self.ssh_run_command_count == 2:
                # first scan succeeds
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # second scan - host key changed
                raise SshcpError("Remote host key has changed. This may indicate a MITM attack.")
            else:
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()  # succeeds
        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertFalse(ctx.exception.recoverable)

    def test_raises_recoverable_error_on_subsequent_failed_ssh(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh run command succeeds first time, raises error the second time
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first try
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # second try
                raise SshcpError("an ssh error")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()  # no error first time
        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_SCAN.format("an ssh error"), str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)

    def test_recovers_from_failed_ssh(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh run command succeeds first time, raises error the second time, fine after that
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first try
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # second try
                raise SshcpError("an ssh error")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()  # no error first time
        with self.assertRaises(ScannerError):
            scanner.scan()
        scanner.scan()
        self.assertEqual(4, self.mock_ssh.shell.call_count)

    def test_raises_nonrecoverable_error_on_failed_copy(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        # noinspection PyUnusedLocal
        def ssh_copy(*args, **kwargs):
            raise SshcpError("an scp error")
        self.mock_ssh.copy.side_effect = ssh_copy

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_INSTALL.format("an scp error"), str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)

    def test_raises_nonrecoverable_error_on_mangled_output(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        def ssh_shell(*args):
            return "mangled data".encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(Localization.Error.REMOTE_SERVER_SCAN.format("Invalid scan data"), str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)

    def test_raises_nonrecoverable_error_on_failed_scan(self):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=TestRemoteScanner.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script"
        )

        self.ssh_run_command_count = 0

        # Ssh run command raises error the first time, succeeds the second time
        # noinspection PyUnusedLocal
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first try
                raise SshcpError("SystemScannerError: something failed")
            else:
                # later tries
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with self.assertRaises(ScannerError) as ctx:
            scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_SCAN.format("SystemScannerError: something failed"),
            str(ctx.exception)
        )
        self.assertFalse(ctx.exception.recoverable)
