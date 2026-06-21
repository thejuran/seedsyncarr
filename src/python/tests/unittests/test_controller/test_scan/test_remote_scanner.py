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

        self._logger = logging.getLogger()
        self._log_handler = logging.StreamHandler(sys.stdout)
        self._logger.addHandler(self._log_handler)
        self._logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self._log_handler.setFormatter(formatter)

        # Ssh to return mangled binary by default
        self.mock_ssh.shell.return_value = b'error'

    def tearDown(self):
        self._logger.removeHandler(self._log_handler)

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
        # md5sum + main scan + df = 3 calls (Phase 74-02 added df)
        self.assertEqual(3, self.mock_ssh.shell.call_count)
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
        # md5sum + main scan + df = 3 calls (Phase 74-02 added df)
        self.assertEqual(3, self.mock_ssh.shell.call_count)
        # The main scan call (second of three) — assert_called_with looks at the LAST call,
        # which after Phase 74-02 is the df call. Use assert_has_calls instead.
        self.mock_ssh.shell.assert_any_call(
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
        files, _, _ = scanner.scan()
        self.assertEqual([], files)
        self.mock_ssh.copy.assert_not_called()
        # md5sum + failed scan + retry main + df = 4 calls (Phase 74-02 added df)
        self.assertEqual(4, self.mock_ssh.shell.call_count)

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

        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return local_md5.encode()
            elif self.ssh_run_command_count == 2:
                # first scan succeeds
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # df call after first scan (Phase 74-02 — silent fallback, returns to df parser)
                return b""
            elif self.ssh_run_command_count == 4:
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

        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return local_md5.encode()
            elif self.ssh_run_command_count == 2:
                # first scan succeeds
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # df call after first scan (Phase 74-02 — silent fallback)
                return b""
            elif self.ssh_run_command_count == 4:
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
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first try
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # df call after first scan (Phase 74-02 — silent fallback)
                return b""
            elif self.ssh_run_command_count == 4:
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
        def ssh_shell(*args):
            self.ssh_run_command_count += 1
            if self.ssh_run_command_count == 1:
                # md5sum check
                return b''
            elif self.ssh_run_command_count == 2:
                # first scan main
                return json.dumps([]).encode()
            elif self.ssh_run_command_count == 3:
                # df call after first scan (Phase 74-02 — silent fallback)
                return b""
            elif self.ssh_run_command_count == 4:
                # second scan main — raises
                raise SshcpError("an ssh error")
            else:
                # third scan main + its df, both succeed
                return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        scanner.scan()  # no error first time
        with self.assertRaises(ScannerError):
            scanner.scan()
        scanner.scan()
        # md5sum + scan1(main+df) + scan2(fail-no-df) + scan3(main+df) = 6 (Phase 74-02 added df after each successful main scan)
        self.assertEqual(6, self.mock_ssh.shell.call_count)

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


# ============================================================================
# Phase 74-02: capacity (df -B1) parser + SSH-failure fallback + shlex.quote
# ============================================================================

class TestParseDfOutput(unittest.TestCase):
    def test_happy_path(self):
        out = (b"Filesystem     1B-blocks       Used Available Use% Mounted on\n"
               b"/dev/sda1  2000000000000 1300000000000 700000000000  65% /mnt/seedbox\n")
        total, used = RemoteScanner._parse_df_output(out)
        self.assertEqual(2000000000000, total)
        self.assertEqual(1300000000000, used)

    def test_trailing_whitespace(self):
        out = (b"Filesystem 1B-blocks Used Available Use% Mounted on\n"
               b"/dev/sda1 2000000000000 1300000000000 700000000000 65% /mnt\n\n")
        total, used = RemoteScanner._parse_df_output(out)
        self.assertEqual(2000000000000, total)
        self.assertEqual(1300000000000, used)

    def test_missing_data_row(self):
        out = b"Filesystem 1B-blocks Used Available Use% Mounted on\n"
        total, used = RemoteScanner._parse_df_output(out)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_non_numeric_sizes(self):
        out = b"Filesystem 1B-blocks Used\n/dev/sda1 not_a_number also_not_a_number 0 0% /mnt\n"
        total, used = RemoteScanner._parse_df_output(out)
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_empty_output(self):
        total, used = RemoteScanner._parse_df_output(b"")
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_unicode_decode_error(self):
        total, used = RemoteScanner._parse_df_output(b"\xff\xfe\xff")
        self.assertIsNone(total)
        self.assertIsNone(used)

    def test_too_few_columns(self):
        out = b"Filesystem 1B-blocks\n/dev/sda1\n"
        total, used = RemoteScanner._parse_df_output(out)
        self.assertIsNone(total)
        self.assertIsNone(used)


class TestRemoteScannerShleQuote(unittest.TestCase):
    """Regression guard: df command MUST use shlex.quote on user-controlled path (T-74-05)."""

    def test_df_command_quotes_remote_path(self):
        ssh_patcher = patch('controller.scan.remote_scanner.Sshcp')
        self.addCleanup(ssh_patcher.stop)
        mock_ssh_cls = ssh_patcher.start()
        mock_ssh = mock_ssh_cls.return_value

        scanner = RemoteScanner(
            remote_address="host",
            remote_username="user",
            remote_password="pw",
            remote_port=22,
            remote_path_to_scan="/mnt/seedbox; rm -rf /",
            local_path_to_scan_script="/tmp/scanfs",
            remote_path_to_scan_script="/tmp/scanfs",
        )
        scanner._RemoteScanner__install_done = True
        mock_ssh.shell.side_effect = [
            b"[]",
            b"Filesystem 1B-blocks Used Available Use% Mounted on\n/dev/sda1 1000 500 500 50% /mnt\n",
        ]

        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertEqual(1000, total)
        self.assertEqual(500, used)
        df_cmd = mock_ssh.shell.call_args_list[1][0][0]
        self.assertIn("df -B1 ", df_cmd)
        self.assertIn("'/mnt/seedbox; rm -rf /'", df_cmd)


class TestRemoteScannerDfSshFailure(unittest.TestCase):
    def test_df_ssh_error_returns_none_capacity_but_preserves_files(self):
        ssh_patcher = patch('controller.scan.remote_scanner.Sshcp')
        self.addCleanup(ssh_patcher.stop)
        mock_ssh_cls = ssh_patcher.start()
        mock_ssh = mock_ssh_cls.return_value

        scanner = RemoteScanner(
            remote_address="host", remote_username="user", remote_password="pw",
            remote_port=22, remote_path_to_scan="/mnt/path",
            local_path_to_scan_script="/tmp/scanfs",
            remote_path_to_scan_script="/tmp/scanfs",
        )
        scanner._RemoteScanner__install_done = True
        mock_ssh.shell.side_effect = [
            b"[]",
            SshcpError("df connection reset"),
        ]

        files, total, used = scanner.scan()
        self.assertEqual([], files)
        self.assertIsNone(total)
        self.assertIsNone(used)


# ============================================================================
# Phase 101-06: CWE-117 log-injection sanitization for remote_scanner.py:118
# ============================================================================

class TestRemoteScannerLogSanitization(unittest.TestCase):
    """
    Tests for CWE-117 log-injection sanitization at remote_scanner.py:118
    (the JSON-decode-error log site in the except branch of scan()).

    The plan mandates:
    - test_json_decode_error_log_sanitized: CRLF-bearing malformed JSON bytes make
      json.loads raise; the "JSON decode error" ERROR log must have no literal CR/LF
      from the injected name; scan() raises ScannerError.
    - test_json_decode_error_log_no_nameerror_on_bytes: non-UTF8 bytes make the
      decode at line 114 itself raise (UnicodeDecodeError is a ValueError subclass,
      caught by the except); the except branch must NOT NameError on out_str
      (which is undefined when the decode raised); still raises ScannerError.
    - test_scan_still_parses_valid_output: well-formed JSON still parses to the
      expected SystemFile list (success path unaffected).
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_remote_scanner_sanitize")
        cls.temp_scan_script = os.path.join(cls.temp_dir, "script")
        with open(cls.temp_scan_script, "w") as f:
            f.write("")
        with open(cls.temp_scan_script, "rb") as f:
            cls.scan_script_md5 = hashlib.md5(f.read()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def _make_scanner(self, mock_ssh):
        scanner = RemoteScanner(
            remote_address="host",
            remote_username="user",
            remote_password="pw",
            remote_port=22,
            remote_path_to_scan="/remote/path",
            local_path_to_scan_script=self.temp_scan_script,
            remote_path_to_scan_script="/remote/path/script",
        )
        # Skip the install step
        scanner._RemoteScanner__install_done = True
        return scanner

    def test_json_decode_error_log_sanitized(self):
        """
        mock_ssh.shell returns a string (not bytes) with malformed JSON containing a
        CRLF-bearing remote name. When out is a str, json.loads raises immediately
        (no bytes-decode step), the except fires, scan() raises ScannerError, AND the
        'JSON decode error' ERROR log line has no literal CR/LF from the injected name.

        Using a string return value (not bytes) so that the CRLF in out is a literal
        control character that would appear verbatim in the log without sanitization.
        """
        with patch('controller.scan.remote_scanner.Sshcp') as mock_ssh_cls:
            mock_ssh = mock_ssh_cls.return_value
            scanner = self._make_scanner(mock_ssh)

            # Malformed JSON string (not bytes) with a CRLF-bearing remote filename.
            # When out is a str, out.decode is not called, so out_str = out directly,
            # and json.loads raises on the malformed JSON. The except then has out as a
            # str with literal CR/LF that must be sanitized in the log.
            injected_name = "file\r\nINJECTED_LINE.mkv"
            malformed_json_str = 'not-valid-json {"name": "' + injected_name + '"}'
            mock_ssh.shell.return_value = malformed_json_str

            with self.assertRaises(ScannerError) as ctx:
                with self.assertLogs("RemoteScanner", level=logging.ERROR) as cm:
                    scanner.scan()

            self.assertFalse(ctx.exception.recoverable)

            json_error_lines = [
                line for line in cm.output if "JSON decode error" in line
            ]
            self.assertGreater(len(json_error_lines), 0,
                               "Expected at least one 'JSON decode error' log line")
            for line in json_error_lines:
                self.assertNotIn("\r", line,
                                 "Literal CR from injected name must not appear in log")

    def test_json_decode_error_log_no_nameerror_on_bytes(self):
        """
        mock_ssh.shell returns non-UTF8 bytes that make the decode at line 114 raise
        (UnicodeDecodeError is a ValueError subclass, caught by the except).
        The except branch must NOT raise NameError on out_str (which is undefined when
        the decode itself raised). Still raises ScannerError.
        """
        with patch('controller.scan.remote_scanner.Sshcp') as mock_ssh_cls:
            mock_ssh = mock_ssh_cls.return_value
            scanner = self._make_scanner(mock_ssh)

            # Non-UTF8 bytes that will cause out.decode('utf-8') to raise UnicodeDecodeError
            non_utf8_bytes = b"\xff\xfe\xfd non-utf8 garbage"
            mock_ssh.shell.return_value = non_utf8_bytes

            # The except branch must not raise NameError — it must only raise ScannerError
            with self.assertLogs("RemoteScanner", level=logging.ERROR) as cm:
                with self.assertRaises(ScannerError) as ctx:
                    scanner.scan()

            self.assertFalse(ctx.exception.recoverable)

            json_error_lines = [
                line for line in cm.output if "JSON decode error" in line
            ]
            self.assertGreater(len(json_error_lines), 0,
                               "Expected 'JSON decode error' log line even for bytes-decode failure")

    def test_scan_still_parses_valid_output(self):
        """
        Well-formed JSON scan output still parses to the expected SystemFile list.
        The success path at lines 114-116 is unchanged — sanitization touched only
        the except-branch log.
        """
        with patch('controller.scan.remote_scanner.Sshcp') as mock_ssh_cls:
            mock_ssh = mock_ssh_cls.return_value
            scanner = self._make_scanner(mock_ssh)

            # Valid JSON: empty list (no files)
            mock_ssh.shell.side_effect = [
                json.dumps([]).encode('utf-8'),
                b"Filesystem 1B-blocks Used Available Use% Mounted on\n/dev/sda1 1000 500 500 50% /\n",
            ]

            files, total, used = scanner.scan()
            self.assertEqual([], files)


# ============================================================================
# Phase 114-01: name-resolution reclassification + bounded in-scan retry
# (SCAN-01/02/03). Retry is name-resolution ONLY (all resolver-string surfaces,
# case-insensitive) and is shared by the main-scan call AND the install
# md5sum/copy SSH ops via ONE bounded helper. Transient timeout/refused are NOT
# retried in-scan on either path.
# ============================================================================


class TestRemoteScannerNameResolutionMatcher(unittest.TestCase):
    """SCAN-01 classification: _is_name_resolution_ssh_error covers ALL resolver-
    string surfaces (collapsed "Bad hostname:" AND the raw non-zero-exit
    fallthrough strings) case-insensitively, while staying disjoint from
    timeout/refused/auth/host-key. These tests PASS in Task 1 (the matcher exists)."""

    def test_name_resolution_matches_collapsed_bad_hostname(self):
        self.assertTrue(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("Bad hostname: somehost")))

    def test_name_resolution_matches_raw_could_not_resolve(self):
        # Raw non-zero-exit fallthrough surface (sshcp.py:155), mixed case.
        self.assertTrue(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("ssh: Could not resolve hostname moon.usbx.me")))

    def test_name_resolution_matches_raw_name_or_service_not_known(self):
        self.assertTrue(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("ssh: connect to host x: Name or service not known")))

    def test_name_resolution_matches_raw_temporary_failure(self):
        # The exact resolver-string family from the 2026-06-19 incident.
        self.assertTrue(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("ssh: Could not resolve hostname x: Temporary failure in name resolution")))

    def test_name_resolution_matches_case_insensitive(self):
        # Proves the matcher lower-cases the message before comparing.
        self.assertTrue(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("COULD NOT RESOLVE HOSTNAME X")))

    def test_name_resolution_excludes_incorrect_password(self):
        self.assertFalse(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("Incorrect password")))

    def test_name_resolution_excludes_host_key_change(self):
        self.assertFalse(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("Remote host key has changed")))

    def test_name_resolution_excludes_timeout(self):
        self.assertFalse(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("Timed out")))

    def test_name_resolution_excludes_connection_refused(self):
        self.assertFalse(RemoteScanner._is_name_resolution_ssh_error(
            SshcpError("Connection refused by server")))

    def test_name_resolution_pattern_importable_and_covers_all_surfaces(self):
        from ssh import NAME_RESOLUTION_ERROR_PATTERNS
        self.assertIn("bad hostname:", NAME_RESOLUTION_ERROR_PATTERNS)
        self.assertIn("could not resolve hostname", NAME_RESOLUTION_ERROR_PATTERNS)
        self.assertIn("name or service not known", NAME_RESOLUTION_ERROR_PATTERNS)
        self.assertIn("temporary failure in name resolution", NAME_RESOLUTION_ERROR_PATTERNS)

    def test_bad_hostname_remains_in_permanent_patterns(self):
        from ssh import PERMANENT_ERROR_PATTERNS
        self.assertIn("Bad hostname:", PERMANENT_ERROR_PATTERNS)


class TestRemoteScannerNameResolutionRetry(unittest.TestCase):
    """SCAN-01/02/03 bounded in-scan retry on the MAIN-SCAN path and the INSTALL
    path. The retry/exhaust/bounded/transient-not-retried tests are RED until
    Task 2 builds the shared helper; the classification tests above pass in Task 1.

    The number of attempts the helper makes (RemoteScanner.__SCAN_MAX_ATTEMPTS)
    is read off the class so the bounded-count assertions track the production
    constant rather than a hard-coded literal."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_remote_scanner_nameres")
        cls.temp_scan_script = os.path.join(cls.temp_dir, "script")
        with open(cls.temp_scan_script, "w") as f:
            f.write("")
        with open(cls.temp_scan_script, "rb") as f:
            cls.scan_script_md5 = hashlib.md5(f.read()).hexdigest()
        # Production attempt cap (name-mangled class constant).
        cls.max_attempts = RemoteScanner._RemoteScanner__SCAN_MAX_ATTEMPTS

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        ssh_patcher = patch('controller.scan.remote_scanner.Sshcp')
        self.addCleanup(ssh_patcher.stop)
        self.mock_ssh_cls = ssh_patcher.start()
        self.mock_ssh = self.mock_ssh_cls.return_value
        self.mock_ssh.shell.return_value = b'error'

    def _make_scanner(self, install_done: bool):
        scanner = RemoteScanner(
            remote_address="my remote address",
            remote_username="my remote user",
            remote_password="my password",
            remote_port=1234,
            remote_path_to_scan="/remote/path/to/scan",
            local_path_to_scan_script=self.temp_scan_script,
            remote_path_to_scan_script="/remote/path/to/scan/script",
        )
        if install_done:
            scanner._RemoteScanner__install_done = True
        return scanner

    # ----- MAIN-SCAN path -----

    def test_name_resolution_retry_recovers_main_scan(self):
        """Collapsed "Bad hostname:" on the first main-scan attempt, success on the
        next attempt within the SAME scan() — scan() returns, no ScannerError."""
        scanner = self._make_scanner(install_done=True)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            if self.attempts == 1:
                raise SshcpError("Bad hostname: somehost")
            # Retry succeeds; the trailing call is df (silent fallback).
            return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            files, _, _ = scanner.scan()
        self.assertEqual([], files)
        self.assertEqual(1, mock_sleep.call_count)

    def test_name_resolution_raw_recovers_main_scan(self):
        """RAW resolver fallthrough string on the first main-scan attempt recovers."""
        scanner = self._make_scanner(install_done=True)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            if self.attempts == 1:
                raise SshcpError(
                    "ssh: Could not resolve hostname x: Temporary failure in name resolution")
            return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            files, _, _ = scanner.scan()
        self.assertEqual([], files)
        self.assertEqual(1, mock_sleep.call_count)

    def test_name_resolution_retry_exhausts_main_scan(self):
        """Collapsed name-resolution error on every main-scan attempt → fatal with
        the unchanged REMOTE_SERVER_SCAN message and recoverable=False (SCAN-03)."""
        scanner = self._make_scanner(install_done=True)

        def ssh_shell(*args):
            raise SshcpError("Bad hostname: somehost")
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_SCAN.format("Bad hostname: somehost"),
            str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)

    def test_name_resolution_retry_exhausts_raw_main_scan(self):
        """RAW resolver string exhaustion surfaces the SAME recoverable=False
        REMOTE_SERVER_SCAN surface as the collapsed form."""
        scanner = self._make_scanner(install_done=True)
        raw = "ssh: Could not resolve hostname x: Temporary failure in name resolution"

        def ssh_shell(*args):
            raise SshcpError(raw)
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_SCAN.format(raw),
            str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)

    def test_name_resolution_retry_bounded_main_scan(self):
        """The main-scan shell invocation count for one scan() never exceeds the cap."""
        scanner = self._make_scanner(install_done=True)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            raise SshcpError("Bad hostname: somehost")
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError):
                scanner.scan()
        self.assertLessEqual(self.attempts, self.max_attempts)
        self.assertEqual(self.max_attempts, self.attempts)

    def test_name_resolution_retry_bounded_raw_main_scan(self):
        """Bounded attempt count also holds for the RAW resolver surface."""
        scanner = self._make_scanner(install_done=True)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            raise SshcpError("ssh: Could not resolve hostname x")
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError):
                scanner.scan()
        self.assertLessEqual(self.attempts, self.max_attempts)

    def test_transient_timeout_not_retried_in_scan(self):
        """"Timed out" on the first main-scan attempt raises immediately on attempt
        1 (recoverable=True), with NO backoff sleep — pins the name-resolution-only
        invariant. Existing first-run timeout behavior is preserved."""
        scanner = self._make_scanner(install_done=True)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            raise SshcpError("Timed out")
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        # install_done=True so the first shell call IS the main scan.
        self.assertEqual(1, self.attempts)
        mock_sleep.assert_not_called()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_SCAN.format("Timed out"),
            str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)

    # ----- INSTALL path (__install_done is false) -----

    def test_install_name_resolution_recovers(self):
        """Fresh scanner (install runs): md5sum op raises a collapsed name-resolution
        error once then returns a hash MISMATCH so copy runs and succeeds, then the
        main scan returns — scan() returns with NO ScannerError."""
        scanner = self._make_scanner(install_done=False)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            if self.attempts == 1:
                # md5sum op: name-resolution blip
                raise SshcpError("Bad hostname: somehost")
            elif self.attempts == 2:
                # md5sum retry: mismatch → triggers copy
                return b""
            # main scan + df
            return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            files, _, _ = scanner.scan()
        self.assertEqual([], files)
        self.assertEqual(1, mock_sleep.call_count)
        self.mock_ssh.copy.assert_called_once()

    def test_install_name_resolution_recovers_copy(self):
        """Fresh scanner: the COPY op raises a collapsed name-resolution error once
        then succeeds; scan() returns with NO ScannerError."""
        scanner = self._make_scanner(install_done=False)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            if self.attempts == 1:
                # md5sum mismatch → triggers copy
                return b""
            return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        self.copy_attempts = 0

        def ssh_copy(*args, **kwargs):
            self.copy_attempts += 1
            if self.copy_attempts == 1:
                raise SshcpError("Bad hostname: somehost")
            return None
        self.mock_ssh.copy.side_effect = ssh_copy

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            files, _, _ = scanner.scan()
        self.assertEqual([], files)
        self.assertEqual(1, mock_sleep.call_count)
        self.assertEqual(2, self.copy_attempts)

    def test_install_name_resolution_raw_recovers(self):
        """Fresh scanner: md5sum op raises a RAW resolver fallthrough string once
        then recovers — pins the raw surface on the install path."""
        scanner = self._make_scanner(install_done=False)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            if self.attempts == 1:
                raise SshcpError(
                    "ssh: Could not resolve hostname x: Temporary failure in name resolution")
            elif self.attempts == 2:
                return b""  # md5sum mismatch → copy
            return json.dumps([]).encode()
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            files, _, _ = scanner.scan()
        self.assertEqual([], files)
        self.assertEqual(1, mock_sleep.call_count)

    def test_install_name_resolution_bounded(self):
        """Fresh scanner: md5sum op raises a name-resolution error forever → fatal
        with the unchanged REMOTE_SERVER_INSTALL message + recoverable=False, and a
        bounded md5sum-op call count (SCAN-02/03 on the install path)."""
        scanner = self._make_scanner(install_done=False)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            raise SshcpError("Bad hostname: somehost")
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_INSTALL.format("Bad hostname: somehost"),
            str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)
        self.assertLessEqual(self.attempts, self.max_attempts)
        self.assertEqual(self.max_attempts, self.attempts)

    def test_install_name_resolution_bounded_copy(self):
        """Fresh scanner: the COPY op raises a name-resolution error forever →
        bounded copy-op call count + REMOTE_SERVER_INSTALL recoverable=False."""
        scanner = self._make_scanner(install_done=False)
        # md5sum mismatch → triggers copy
        self.mock_ssh.shell.return_value = b""
        self.copy_attempts = 0

        def ssh_copy(*args, **kwargs):
            self.copy_attempts += 1
            raise SshcpError("Bad hostname: somehost")
        self.mock_ssh.copy.side_effect = ssh_copy

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_INSTALL.format("Bad hostname: somehost"),
            str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)
        self.assertLessEqual(self.copy_attempts, self.max_attempts)
        self.assertEqual(self.max_attempts, self.copy_attempts)

    def test_install_name_resolution_bounded_raw(self):
        """Fresh scanner: md5sum op raises a RAW resolver string forever → bounded
        + REMOTE_SERVER_INSTALL recoverable=False (raw surface on install path)."""
        scanner = self._make_scanner(install_done=False)
        raw = "ssh: connect to host x: Name or service not known"
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            raise SshcpError(raw)
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep'):
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_INSTALL.format(raw),
            str(ctx.exception))
        self.assertFalse(ctx.exception.recoverable)
        self.assertLessEqual(self.attempts, self.max_attempts)

    def test_install_timeout_unchanged(self):
        """Fresh scanner: md5sum op times out → raises immediately on attempt 1 with
        the existing REMOTE_SERVER_INSTALL("Timed out") recoverable=True surface, NO
        backoff sleep — proves timeout is NOT retried on the install path either."""
        scanner = self._make_scanner(install_done=False)
        self.attempts = 0

        def ssh_shell(*args):
            self.attempts += 1
            raise SshcpError("Timed out")
        self.mock_ssh.shell.side_effect = ssh_shell

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(1, self.attempts)
        mock_sleep.assert_not_called()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_INSTALL.format("Timed out"),
            str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)

    def test_install_timeout_unchanged_copy(self):
        """Fresh scanner: the COPY op times out → raises immediately on attempt 1
        with REMOTE_SERVER_INSTALL("Timed out") recoverable=True, NO backoff sleep."""
        scanner = self._make_scanner(install_done=False)
        # md5sum mismatch → triggers copy
        self.mock_ssh.shell.return_value = b""
        self.copy_attempts = 0

        def ssh_copy(*args, **kwargs):
            self.copy_attempts += 1
            raise SshcpError("Timed out")
        self.mock_ssh.copy.side_effect = ssh_copy

        with patch('controller.scan.remote_scanner.time.sleep') as mock_sleep:
            with self.assertRaises(ScannerError) as ctx:
                scanner.scan()
        self.assertEqual(1, self.copy_attempts)
        mock_sleep.assert_not_called()
        self.assertEqual(
            Localization.Error.REMOTE_SERVER_INSTALL.format("Timed out"),
            str(ctx.exception))
        self.assertTrue(ctx.exception.recoverable)
