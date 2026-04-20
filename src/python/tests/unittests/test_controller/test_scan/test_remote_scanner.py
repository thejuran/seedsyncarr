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
