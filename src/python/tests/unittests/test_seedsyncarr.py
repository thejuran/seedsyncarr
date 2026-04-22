import configparser
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from common import Config
from common.encryption import encrypt_field, is_ciphertext, load_or_create_key
from seedsyncarr import Seedsyncarr


class TestSeedsyncarr(unittest.TestCase):
    def test_args_config(self):
        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/config", args.config_dir)

        argv = []
        argv.append("--config_dir")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/config", args.config_dir)

        argv = []
        with self.assertRaises(SystemExit):
            Seedsyncarr._parse_args(argv)

    def test_args_html(self):
        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        argv.append("--html")
        argv.append("/path/to/html")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/html", args.html)

    def test_args_scanfs(self):
        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/scanfs", args.scanfs)

    def test_args_logdir(self):
        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--logdir")
        argv.append("/path/to/logdir")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/logdir", args.logdir)

        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertIsNone(args.logdir)

    def test_args_debug(self):
        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        argv.append("-d")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertTrue(args.debug)

        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--debug")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertTrue(args.debug)

        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertFalse(args.debug)

    def test_default_config(self):
        config = Seedsyncarr._create_default_config()
        # Test that default config doesn't have any uninitialized values
        config_dict = config.as_dict()
        for section, inner_config in config_dict.items():
            for key in inner_config:
                self.assertIsNotNone(inner_config[key],
                                     msg="{}.{} is uninitialized".format(section, key))

        # Test that default config is a valid config
        config_dict = config.as_dict()
        config2 = Config.from_dict(config_dict)
        config2_dict = config2.as_dict()
        self.assertEqual(config_dict, config2_dict)

    def test_detect_incomplete_config(self):
        # Test a complete config
        config = Seedsyncarr._create_default_config()
        incomplete_value = config.lftp.remote_address
        config.lftp.remote_address = "value"
        config.lftp.remote_password = "value"
        config.lftp.remote_username = "value"
        config.lftp.remote_path = "value"
        config.lftp.local_path = "value"
        config.lftp.remote_path_to_scan_script = "value"
        self.assertFalse(Seedsyncarr._detect_incomplete_config(config))

        # Test incomplete configs
        config.lftp.remote_address = incomplete_value
        self.assertTrue(Seedsyncarr._detect_incomplete_config(config))
        config.lftp.remote_address = "value"

        config.lftp.remote_username = incomplete_value
        self.assertTrue(Seedsyncarr._detect_incomplete_config(config))
        config.lftp.remote_username = "value"

        config.lftp.remote_path = incomplete_value
        self.assertTrue(Seedsyncarr._detect_incomplete_config(config))
        config.lftp.remote_path = "value"

        config.lftp.local_path = incomplete_value
        self.assertTrue(Seedsyncarr._detect_incomplete_config(config))
        config.lftp.local_path = "value"

        config.lftp.remote_path_to_scan_script = incomplete_value
        self.assertTrue(Seedsyncarr._detect_incomplete_config(config))
        config.lftp.remote_path_to_scan_script = "value"


class TestSeedsyncarrApiTokenConfig(unittest.TestCase):
    """Tests for api_token config field defaults and round-trip behavior."""

    def test_default_config_has_empty_api_token(self):
        """Default config has empty api_token — user must set explicitly."""
        config = Seedsyncarr._create_default_config()
        self.assertEqual("", config.general.api_token)
        config_dict = config.as_dict()
        self.assertIsNotNone(config_dict["General"]["api_token"])

    def test_config_from_dict_without_api_token_defaults_to_empty(self):
        config_dict = Seedsyncarr._create_default_config().as_dict()
        del config_dict["General"]["api_token"]
        config = Config.from_dict(config_dict)
        self.assertEqual("", config.general.api_token)

    def test_config_from_dict_with_api_token_preserves_value(self):
        config_dict = Seedsyncarr._create_default_config().as_dict()
        config_dict["General"]["api_token"] = "my-secret-token"
        config = Config.from_dict(config_dict)
        self.assertEqual("my-secret-token", config.general.api_token)


class TestSeedsyncarrStartupWarnings(unittest.TestCase):
    """Tests for startup security warning emission (WHOOK-02, WARN-01, WARN-02, WARN-03)."""

    def _make_mock_config(self, webhook_secret="", api_token="", decrypt_errors=None):
        mock_config = MagicMock()
        mock_config.general.webhook_secret = webhook_secret
        mock_config.general.api_token = api_token
        mock_config._decrypt_errors = decrypt_errors if decrypt_errors is not None else []
        return mock_config

    def test_startup_warns_when_webhook_secret_empty(self):
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(webhook_secret="", api_token="configured")
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(
            any("webhook_secret" in call for call in warning_calls),
            msg="Expected a warning containing 'webhook_secret'"
        )

    def test_startup_warns_when_api_token_empty(self):
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(webhook_secret="configured", api_token="")
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(
            any("API token" in call for call in warning_calls),
            msg="Expected a warning containing 'API token'"
        )
        self.assertTrue(
            any("0.0.0.0" in call for call in warning_calls),
            msg="Expected a warning containing '0.0.0.0'"
        )

    def test_startup_no_warning_when_secrets_configured(self):
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(webhook_secret="configured", api_token="configured")
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        mock_logger.warning.assert_not_called()

    def test_startup_logs_info_when_token_configured(self):
        """When token IS configured, log an info message about auth being active."""
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(webhook_secret="configured", api_token="configured")
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        self.assertTrue(
            any("Bearer authentication" in call for call in info_calls),
            msg="Expected an info message about Bearer authentication"
        )

    def test_startup_warns_both_when_both_empty(self):
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(webhook_secret="", api_token="")
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        # 3 warnings: webhook_secret + api_token + 0.0.0.0
        self.assertEqual(3, mock_logger.warning.call_count)

    def test_startup_warnings_do_not_raise(self):
        """Warnings are advisory only — no exception should be raised (WARN-03)."""
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(webhook_secret="", api_token="")
        # Must not raise
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)

    def test_decrypt_failure_emits_warning(self):
        """SEC-02 #5b: each entry in _decrypt_errors emits one warning mentioning
        the field path and keyfile reference (81-03-02)."""
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(
            decrypt_errors=["General.api_token", "Lftp.remote_password"]
        )
        Seedsyncarr._emit_decrypt_warnings(mock_logger, mock_config)
        # At least 2 warning calls — one per field
        self.assertGreaterEqual(mock_logger.warning.call_count, 2)
        warning_texts = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(
            any("General.api_token" in t for t in warning_texts),
            msg="Expected a warning mentioning 'General.api_token'"
        )
        self.assertTrue(
            any("Lftp.remote_password" in t for t in warning_texts),
            msg="Expected a warning mentioning 'Lftp.remote_password'"
        )
        # Each warning must mention the keyfile so operators know what to check
        for text in warning_texts:
            self.assertTrue(
                "secrets.key" in text or "keyfile" in text,
                msg="Expected warning to mention secrets.key or keyfile, got: {}".format(text)
            )

    def test_decrypt_warning_does_not_raise(self):
        """SEC-02 #5b advisory-only contract: decrypt warnings must never crash
        startup regardless of the _decrypt_errors contents (81-03-02)."""
        mock_logger = MagicMock()

        # Sub-case 1: populated list — returns normally, no exception
        mock_config = self._make_mock_config(
            decrypt_errors=["General.api_token"]
        )
        Seedsyncarr._emit_decrypt_warnings(mock_logger, mock_config)

        # Sub-case 2: empty list — silent no-op, no warnings
        mock_logger_empty = MagicMock()
        mock_config_empty = self._make_mock_config(decrypt_errors=[])
        Seedsyncarr._emit_decrypt_warnings(mock_logger_empty, mock_config_empty)
        mock_logger_empty.warning.assert_not_called()

        # Sub-case 3: config missing _decrypt_errors attr entirely (backward-compat
        # for stale mocks). The method uses getattr(..., []) so must be a silent no-op.
        mock_logger_noattr = MagicMock()
        mock_config_noattr = MagicMock(spec=[])  # no attributes at all
        Seedsyncarr._emit_decrypt_warnings(mock_logger_noattr, mock_config_noattr)
        mock_logger_noattr.warning.assert_not_called()


class TestSeedsyncarrReencrypt(unittest.TestCase):
    """Tests for the startup re-encrypt-plaintext-on-enable hook (SEC-02 #3a, 81-03-01)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_reencrypt_")
        self.keyfile = os.path.join(self.temp_dir, "secrets.key")
        self.settings_path = os.path.join(self.temp_dir, "settings.cfg")
        Config.set_keyfile_path(self.keyfile)
        self.addCleanup(Config.set_keyfile_path, None)
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def _build_config_with_plaintext(self) -> Config:
        """Return a Config instance with encryption.enabled=True and 5 plaintext secrets."""
        config = Seedsyncarr._create_default_config()
        config.general.webhook_secret = "my_webhook_secret"
        config.general.api_token = "my_api_token"
        config.lftp.remote_password = "my_remote_password"
        config.lftp.remote_address = "remote.host"
        config.lftp.remote_username = "user"
        config.lftp.remote_port = 22
        config.lftp.remote_path = "/remote/path"
        config.lftp.local_path = "/local/path"
        config.sonarr.sonarr_api_key = "my_sonarr_key"
        config.radarr.radarr_api_key = "my_radarr_key"
        config.encryption.enabled = True
        return config

    def test_enable_existing_plaintext_reencrypts(self):
        """SEC-02 criterion #3a: _reencrypt_plaintext_if_needed detects plaintext
        secret fields when encryption.enabled=True and re-writes settings.cfg with
        Fernet-encrypted values; a subsequent from_file round-trip recovers
        plaintext values (81-03-01)."""
        # Step 1: build config with encryption=True and 5 plaintext secrets,
        # then write to disk via to_file (this will encrypt them since enabled=True).
        config = self._build_config_with_plaintext()
        config.to_file(self.settings_path)

        # Step 2: simulate the "plaintext-after-enable" case by writing a fresh
        # settings.cfg that has enabled=True but plaintext values (as if the user
        # manually added [Encryption] enabled=True without restarting the app).
        # We do this by toggling to False for the write, then patching back to True.
        config_for_disk = self._build_config_with_plaintext()
        config_for_disk.encryption.enabled = False  # write plaintext
        config_for_disk.to_file(self.settings_path)

        # Manually patch [Encryption] enabled back to True in the file
        parser = configparser.ConfigParser()
        parser.read(self.settings_path)
        if not parser.has_section("Encryption"):
            parser.add_section("Encryption")
        parser.set("Encryption", "enabled", "True")
        with open(self.settings_path, "w") as f:
            parser.write(f)

        # Step 3: load config from the patched file — plaintext preserved in memory
        reloaded = Config.from_file(self.settings_path)
        self.assertTrue(reloaded.encryption.enabled)
        self.assertEqual("my_api_token", reloaded.general.api_token)
        self.assertEqual("my_webhook_secret", reloaded.general.webhook_secret)

        # Step 4: call the re-encrypt hook (simulates what Seedsyncarr.run() does)
        mock_logger = MagicMock()
        Seedsyncarr._reencrypt_plaintext_if_needed(reloaded, self.settings_path, mock_logger)

        # Step 5: assert the on-disk values are now ciphertext
        parser_after = configparser.ConfigParser()
        parser_after.read(self.settings_path)
        self.assertTrue(
            is_ciphertext(parser_after.get("General", "api_token")),
            "api_token should be ciphertext after re-encrypt"
        )
        self.assertTrue(
            is_ciphertext(parser_after.get("General", "webhook_secret")),
            "webhook_secret should be ciphertext after re-encrypt"
        )
        self.assertTrue(
            is_ciphertext(parser_after.get("Lftp", "remote_password")),
            "remote_password should be ciphertext after re-encrypt"
        )
        self.assertTrue(
            is_ciphertext(parser_after.get("Sonarr", "sonarr_api_key")),
            "sonarr_api_key should be ciphertext after re-encrypt"
        )
        self.assertTrue(
            is_ciphertext(parser_after.get("Radarr", "radarr_api_key")),
            "radarr_api_key should be ciphertext after re-encrypt"
        )

        # Step 6: round-trip — load again and confirm plaintext values are recovered
        final = Config.from_file(self.settings_path)
        self.assertEqual("my_api_token", final.general.api_token)
        self.assertEqual("my_webhook_secret", final.general.webhook_secret)
        self.assertEqual("my_remote_password", final.lftp.remote_password)
        self.assertEqual("my_sonarr_key", final.sonarr.sonarr_api_key)
        self.assertEqual("my_radarr_key", final.radarr.radarr_api_key)
