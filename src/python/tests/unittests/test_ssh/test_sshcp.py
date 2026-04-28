import unittest
import os
import tempfile
import shutil
import filecmp
import logging
import sys

import pytest

from tests.utils import TestUtils
from common import overrides
from ssh import Sshcp, SshcpError


# Test credentials for Docker-based test container (see test/python/Dockerfile).
# These are NOT production secrets — they exist only in the ephemeral test environment.
_TEST_USER = "seedsyncarrtest"

# NOTE: password-auth path (Sshcp(password="...")) is not tested here because
# the test container uses key-only auth. See src/docker/test/python/Dockerfile.


class TestSshcp(unittest.TestCase):
    __KEEP_FILES = False  # for debugging

    @overrides(unittest.TestCase)
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_sshcp")
        self.local_dir = os.path.join(self.temp_dir, "local")
        os.mkdir(self.local_dir)
        self.remote_dir = os.path.join(self.temp_dir, "remote")
        os.mkdir(self.remote_dir)

        # Allow group access for the seedsyncarrtest account
        TestUtils.chmod_from_to(self.remote_dir, tempfile.gettempdir(), 0o775)

        # Note: seedsyncarrtest account must be set up. See DeveloperReadme.md for details
        self.host = "127.0.0.1"
        self.port = 22
        self.user = _TEST_USER

        self.logger = logging.getLogger()
        self._log_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self._log_handler)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self._log_handler.setFormatter(formatter)

        # Create local file
        self.local_file = os.path.join(self.local_dir, "file.txt")
        self.remote_file = os.path.join(self.remote_dir, "file2.txt")
        with open(self.local_file, "w") as f:
            f.write("this is a test file")

    @overrides(unittest.TestCase)
    def tearDown(self):
        self.logger.removeHandler(self._log_handler)
        if not self.__KEEP_FILES:
            shutil.rmtree(self.temp_dir)

    def test_ctor(self):
        sshcp = Sshcp(host=self.host, port=self.port)
        self.assertIsNotNone(sshcp)

    @pytest.mark.timeout(5)
    def test_copy(self):
        self.assertFalse(os.path.exists(self.remote_file))
        sshcp = Sshcp(host=self.host, port=self.port, user=self.user)
        sshcp.copy(local_path=self.local_file, remote_path=self.remote_file)

        self.assertTrue(filecmp.cmp(self.local_file, self.remote_file))

    @pytest.mark.timeout(5)
    def test_copy_error_missing_local_file(self):
        local_file = os.path.join(self.local_dir, "nofile.txt")
        self.assertFalse(os.path.exists(self.remote_file))
        self.assertFalse(os.path.exists(local_file))

        sshcp = Sshcp(host=self.host, port=self.port, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.copy(local_path=local_file, remote_path=self.remote_file)
        self.assertIn("No such file or directory", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_copy_error_missing_remote_dir(self):
        remote_file = os.path.join(self.remote_dir, "nodir", "file2.txt")
        self.assertFalse(os.path.exists(remote_file))

        sshcp = Sshcp(host=self.host, port=self.port, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.copy(local_path=self.local_file, remote_path=remote_file)
        self.assertIn("No such file or directory", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_copy_error_bad_host(self):
        sshcp = Sshcp(host="badhost", port=self.port, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.copy(local_path=self.local_file, remote_path=self.remote_file)
        # Accept various error formats from different SSH versions
        error_str = str(ctx.exception).lower()
        self.assertTrue(
            "bad hostname" in error_str or
            "connection refused" in error_str or
            "connection closed" in error_str or
            "name or service not known" in error_str or
            "could not resolve" in error_str or
            "no route to host" in error_str or
            "unknown error" in error_str or
            "temporary failure" in error_str,
            f"Unexpected error: {ctx.exception}"
        )

    @pytest.mark.timeout(5)
    def test_copy_error_bad_port(self):
        sshcp = Sshcp(host=self.host, port=666, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.copy(local_path=self.local_file, remote_path=self.remote_file)
        # Accept various error formats from different SSH versions
        error_str = str(ctx.exception).lower()
        self.assertTrue(
            "connection refused" in error_str or
            "connection closed" in error_str or
            "connection timed out" in error_str or
            "no route to host" in error_str or
            "unknown error" in error_str or
            "port" in error_str,
            f"Unexpected error: {ctx.exception}"
        )

    @pytest.mark.timeout(5)
    def test_shell(self):
        sshcp = Sshcp(host=self.host, port=self.port, user=self.user)
        out = sshcp.shell(f"cd {self.local_dir}; pwd")
        out_str = out.decode().strip()
        self.assertEqual(self.local_dir, out_str)

    @pytest.mark.timeout(5)
    def test_shell_with_escape_characters(self):
        sshcp = Sshcp(host=self.host, port=self.port, user=self.user)

        # single quotes
        _dir = os.path.join(self.remote_dir, "a a")
        out = sshcp.shell(f"mkdir '{_dir}' && cd '{_dir}' && pwd")
        out_str = out.decode().strip()
        self.assertEqual(_dir, out_str)

        # double quotes
        _dir = os.path.join(self.remote_dir, "a b")
        out = sshcp.shell(f'mkdir "{_dir}" && cd "{_dir}" && pwd')
        out_str = out.decode().strip()
        self.assertEqual(_dir, out_str)

        # single and double quotes - error out
        _dir = os.path.join(self.remote_dir, "a b")
        with self.assertRaises(ValueError):
            sshcp.shell(f'mkdir "{_dir}" && cd \'{_dir}\' && pwd')

    @pytest.mark.timeout(5)
    def test_shell_error_bad_host(self):
        sshcp = Sshcp(host="badhost", port=self.port, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.shell(f"cd {self.local_dir}; pwd")
        # Accept various error formats from different SSH versions
        error_str = str(ctx.exception).lower()
        self.assertTrue(
            "bad hostname" in error_str or
            "connection closed" in error_str or
            "name or service not known" in error_str or
            "could not resolve" in error_str or
            "no route to host" in error_str or
            "unknown error" in error_str or
            "temporary failure" in error_str,
            f"Unexpected error: {ctx.exception}"
        )

    @pytest.mark.timeout(5)
    def test_shell_error_bad_port(self):
        sshcp = Sshcp(host=self.host, port=6666, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.shell(f"cd {self.local_dir}; pwd")
        # Accept various error formats from different SSH versions
        error_str = str(ctx.exception).lower()
        self.assertTrue(
            "connection refused" in error_str or
            "connection closed" in error_str or
            "connection timed out" in error_str or
            "no route to host" in error_str or
            "unknown error" in error_str or
            "port" in error_str,
            f"Unexpected error: {ctx.exception}"
        )

    @pytest.mark.timeout(5)
    def test_shell_error_bad_command(self):
        sshcp = Sshcp(host=self.host, port=self.port, user=self.user)
        with self.assertRaises(SshcpError) as ctx:
            sshcp.shell("./some_bad_command.sh")
        self.assertIn("./some_bad_command.sh", str(ctx.exception))
