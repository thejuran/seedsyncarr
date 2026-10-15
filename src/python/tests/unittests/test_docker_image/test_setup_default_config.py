"""Regression tests for the container's first-run config setup script.

setup_default_config.sh runs at every container start and its output goes to
the container log. These tests run the real script (a copy with its fixed
paths pointed at a temp dir) against a settings.cfg holding a unique random
sentinel in every secret field, and assert that none of those values appear in
the script's stdout or stderr.

The secret list comes from Config.secret_fields(), so a newly added secret
field is covered automatically. Failure messages name the field only; they
never include the captured output, which would contain the sentinel.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from common import Config
from seedsyncarr import Seedsyncarr

# Resolves to the repo root locally (src/python/tests/unittests/test_docker_image/)
# and to / inside the CI test container (/src/tests/unittests/test_docker_image/),
# where compose.yml bind-mounts the docker-image scripts at /docker/build/docker-image.
SCRIPT = Path(__file__).resolve().parents[4] / "docker/build/docker-image/setup_default_config.sh"

_CONFIG_DIR_LINE = 'CONFIG_DIR="/config"'
_SCRIPT_PATH_LINE = 'SCRIPT_PATH="/app/python/seedsyncarr.py"'

_MIN_SECRET_FIELDS = 5


class TestSetupDefaultConfigScript(unittest.TestCase):
    def setUp(self):
        # A missing script must fail, not skip: a skip would let CI pass
        # silently if the compose bind mount were dropped.
        self.assertTrue(SCRIPT.is_file(), "setup_default_config.sh not found at {}".format(SCRIPT))
        self.temp_dir = tempfile.mkdtemp(prefix="test_setup_cfg_")
        self.addCleanup(shutil.rmtree, self.temp_dir)
        Config.set_keyfile_path(os.path.join(self.temp_dir, "secrets.key"))
        self.addCleanup(Config.set_keyfile_path, None)
        self.config_dir = os.path.join(self.temp_dir, "config")
        os.mkdir(self.config_dir)

    def _write_sentinel_config(self, local_path: str) -> dict:
        """Write a plaintext settings.cfg with a unique sentinel in every secret field.

        Returns {field_name: sentinel_value}.
        """
        config = Seedsyncarr._create_default_config()
        config.lftp.local_path = local_path
        sentinels = {}
        for attr, field, _section in Config.secret_fields():
            value = "SENTINEL-" + field + "-" + uuid.uuid4().hex
            setattr(getattr(config, attr), field, value)
            sentinels[field] = value
        self.assertGreaterEqual(len(sentinels), _MIN_SECRET_FIELDS)
        with open(os.path.join(self.config_dir, "settings.cfg"), "w") as f:
            f.write(config.to_str())
        return sentinels

    def _run_script(self) -> "tuple[int, str]":
        """Run a copy of the script pointed at the temp config dir and a stub app.

        Returns (returncode, stdout + stderr).
        """
        text = SCRIPT.read_text()
        # The real app is never run here: with a complete config, --exit would
        # still start the controller and web server.
        stub = os.path.join(self.temp_dir, "stub.py")
        with open(stub, "w"):
            pass
        replacements = [
            (_CONFIG_DIR_LINE, 'CONFIG_DIR="{}"'.format(self.config_dir)),
            (_SCRIPT_PATH_LINE, 'SCRIPT_PATH="{}"'.format(stub)),
        ]
        for old, new in replacements:
            self.assertEqual(text.count(old), 1, "expected exactly one '{}' line in the script".format(old))
            text = text.replace(old, new)
        copy = os.path.join(self.temp_dir, "setup_default_config.sh")
        with open(copy, "w") as f:
            f.write(text)
        proc = subprocess.run(["bash", copy], capture_output=True, text=True, timeout=30)
        return proc.returncode, proc.stdout + proc.stderr

    def _assert_no_secret_values(self, sentinels: dict, output: str):
        for field, value in sentinels.items():
            # assertFalse with a field-only message: the default message of a
            # membership assertion would print the whole captured output
            # (including the sentinel) on failure.
            self.assertFalse(value in output, "secret field {} appeared in startup output".format(field))

    def test_existing_config_prints_no_secret_values(self):
        sentinels = self._write_sentinel_config(local_path="/downloads/")
        returncode, output = self._run_script()
        self._assert_no_secret_values(sentinels, output)
        self.assertTrue("Config ready at" in output, "status line 'Config ready at' missing from startup output")
        self.assertEqual(returncode, 0, "script exited non-zero on an existing config")

    def test_first_run_config_prints_no_secret_values(self):
        # Only sentinel absence is asserted here: the placeholder replace uses
        # `sed -i`, whose syntax differs between GNU (CI) and BSD (macOS) sed.
        sentinels = self._write_sentinel_config(local_path="<replace me>")
        _returncode, output = self._run_script()
        self._assert_no_secret_values(sentinels, output)

    def test_script_is_executable_and_present(self):
        self.assertTrue(SCRIPT.is_file(), "setup_default_config.sh not found")
        self.assertTrue(os.access(SCRIPT, os.X_OK), "setup_default_config.sh is not executable")

    def test_secret_discovery_is_non_empty(self):
        # Guards against an empty discovery making the leak tests vacuous.
        self.assertGreaterEqual(len(Config.secret_fields()), _MIN_SECRET_FIELDS)
