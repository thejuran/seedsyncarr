import unittest
from unittest.mock import MagicMock

from common import Config
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

    def _make_mock_config(self, webhook_secret="", api_token=""):
        mock_config = MagicMock()
        mock_config.general.webhook_secret = webhook_secret
        mock_config.general.api_token = api_token
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
