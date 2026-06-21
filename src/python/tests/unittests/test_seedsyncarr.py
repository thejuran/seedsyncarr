import configparser
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from common import Config
from common.encryption import is_ciphertext
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
        args, _ = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/config", args.config_dir)

        argv = []
        argv.append("--config_dir")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args, _ = Seedsyncarr._parse_args(argv)
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
        args, _ = Seedsyncarr._parse_args(argv)
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
        args, _ = Seedsyncarr._parse_args(argv)
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
        args, _ = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertEqual("/path/to/logdir", args.logdir)

        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args, _ = Seedsyncarr._parse_args(argv)
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
        args, _ = Seedsyncarr._parse_args(argv)
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
        args, _ = Seedsyncarr._parse_args(argv)
        self.assertIsNotNone(args)
        self.assertTrue(args.debug)

        argv = []
        argv.append("-c")
        argv.append("/path/to/config")
        argv.append("--html")
        argv.append("/path/to/html")
        argv.append("--scanfs")
        argv.append("/path/to/scanfs")
        args, _ = Seedsyncarr._parse_args(argv)
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

    def _make_mock_config(self, webhook_secret="", api_token="", decrypt_errors=None,
                          webhook_require_secret=False):
        mock_config = MagicMock()
        mock_config.general.webhook_secret = webhook_secret
        mock_config.general.api_token = api_token
        mock_config.general.webhook_require_secret = webhook_require_secret
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

    def test_startup_require_secret_without_secret_does_not_warn_accept_any_caller(self):
        """GUARD-02: fail-closed state must NOT emit the 'accept any caller' warning."""
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(
            webhook_secret="", api_token="configured", webhook_require_secret=True
        )
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertFalse(
            any("any caller" in call for call in warning_calls),
            msg="'accept any caller' warning must not fire when fail-closed (require_secret=True)"
        )

    def test_startup_require_secret_without_secret_warns_503(self):
        """GUARD-02: fail-closed state MUST emit the '503' warning."""
        mock_logger = MagicMock()
        mock_config = self._make_mock_config(
            webhook_secret="", api_token="configured", webhook_require_secret=True
        )
        Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(
            any("503" in call for call in warning_calls),
            msg="Expected a '503' warning when require_secret=True and no secret set"
        )


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


class TestSeedsyncarrLegacyFallback(unittest.TestCase):
    """Tests for GUARD-06: legacy ~/.seedsync fallback warning surfacing."""

    def _make_parse_argv(self, config_dir: str) -> list:
        return [
            "-c", config_dir,
            "--html", "/path/to/html",
            "--scanfs", "/path/to/scanfs",
        ]

    @patch("seedsyncarr.os.path.exists")
    def test_parse_args_emits_legacy_fallback_warning(self, mock_exists):
        """GUARD-06: when config_dir is absent and ~/.seedsync exists, _parse_args
        returns a non-None legacy_fallback_warning in the second tuple element so
        it can be emitted via the configured logger after _create_logger."""
        legacy_dir = os.path.expanduser("~/.seedsync")
        config_dir = "/nonexistent/config"

        def exists_side_effect(path):
            if path == config_dir:
                return False
            if path == legacy_dir:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        argv = self._make_parse_argv(config_dir)
        args, warning = Seedsyncarr._parse_args(argv)

        self.assertIsNotNone(
            warning,
            msg="Expected a non-None legacy_fallback_warning when fallback triggers"
        )
        self.assertIn(
            config_dir, warning,
            msg="Warning should mention the original config_dir"
        )
        self.assertIn(
            legacy_dir, warning,
            msg="Warning should mention the legacy fallback dir"
        )
        self.assertEqual(
            args.config_dir, legacy_dir,
            msg="args.config_dir should be updated to the legacy dir"
        )


def _next_consecutive(consecutive, auto, reset):
    """Mirror of the main()-side counter-normalization rule (Phase 114 D-03).

    Auto-recovery restarts increment the consecutive counter, EXCEPT a
    reset-at-cap auto restart normalizes it to 1 (a fresh budget, NOT cap+1 —
    finding 2). UI restarts (auto=False) never touch the counter (finding 1).
    """
    if not auto:
        return consecutive
    return 1 if reset else consecutive + 1


class TestSeedsyncarrAutoRestart(unittest.TestCase):
    """Unit tests for the pure _should_auto_restart helper and the
    main()-side counter-normalization rule (RECOV-01 / Phase 114 D-03).

    The helper is pure: time is injected via now/current_run_start so the
    cases are deterministic. Every call unpacks the (should_restart,
    reset_applied) tuple.
    """

    CAP = 3
    RESET_SECS = 300

    def test_restart_within_cap_first_death_returns_true_false(self):
        # First death: budget remains, no current run start → no reset.
        now = datetime(2026, 6, 21, 12, 0, 0)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=0, cap=self.CAP,
            current_run_start=None, reset_secs=self.RESET_SECS, now=now)
        self.assertTrue(should)
        self.assertFalse(reset)

    def test_restart_within_cap_under_cap_young_run_returns_true_false(self):
        # Under cap (2 < 3); current run too young to reset.
        now = datetime(2026, 6, 21, 12, 0, 0)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=2, cap=self.CAP,
            current_run_start=now, reset_secs=self.RESET_SECS, now=now)
        self.assertTrue(should)
        self.assertFalse(reset)

    def test_restart_cap_exhausted_young_run_returns_false_false(self):
        # Cap reached (3 >= 3) and current run did NOT stay up past reset →
        # genuine exhaustion.
        now = datetime(2026, 6, 21, 12, 0, 0)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=self.CAP, cap=self.CAP,
            current_run_start=now, reset_secs=self.RESET_SECS, now=now)
        self.assertFalse(should)
        self.assertFalse(reset)

    def test_restart_reset_stayed_up_under_cap_returns_true_true(self):
        # A run that stayed up past the reset threshold (even under the cap)
        # is recognized as eligible AND signals a reset.
        now = datetime(2026, 6, 21, 12, 0, 0)
        run_start = now - timedelta(seconds=self.RESET_SECS + 1)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=1, cap=self.CAP,
            current_run_start=run_start, reset_secs=self.RESET_SECS, now=now)
        self.assertTrue(should)
        self.assertTrue(reset)

    def test_restart_reset_at_cap_returns_true_true(self):
        # Finding 1: the CURRENT run stayed up past reset before dying →
        # restart-eligible EVEN at the cap, and reset_applied is True.
        now = datetime(2026, 6, 21, 12, 0, 0)
        run_start = now - timedelta(seconds=self.RESET_SECS + 1)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=self.CAP, cap=self.CAP,
            current_run_start=run_start, reset_secs=self.RESET_SECS, now=now)
        self.assertTrue(should)
        self.assertTrue(reset)

    def test_restart_reset_boundary_exactly_at_threshold_no_reset(self):
        # Strictly greater-than: a run aged EXACTLY reset_secs does NOT reset.
        now = datetime(2026, 6, 21, 12, 0, 0)
        run_start = now - timedelta(seconds=self.RESET_SECS)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=self.CAP, cap=self.CAP,
            current_run_start=run_start, reset_secs=self.RESET_SECS, now=now)
        self.assertFalse(should)
        self.assertFalse(reset)

    def test_restart_fresh_budget_post_reset_quick_failure_returns_true_false(self):
        # Finding 2: after a reset-at-cap normalization main() set the counter
        # to 1; this next quick failure (1 < cap, run too young) is STILL
        # eligible and does NOT surface immediately.
        now = datetime(2026, 6, 21, 12, 0, 0)
        should, reset = Seedsyncarr._should_auto_restart(
            consecutive_restarts=1, cap=self.CAP,
            current_run_start=now, reset_secs=self.RESET_SECS, now=now)
        self.assertTrue(should)
        self.assertFalse(reset)

    def test_restart_reset_at_cap_normalizes_counter_to_one(self):
        # Finding 2 (counter-normalization rule): a reset-at-cap auto restart
        # maps cap → 1 (a fresh budget), NOT cap+1.
        self.assertEqual(
            1, _next_consecutive(self.CAP, auto=True, reset=True))
        # An auto restart WITHOUT reset increments normally.
        self.assertEqual(
            self.CAP + 1, _next_consecutive(self.CAP, auto=True, reset=False))
        # A UI restart (auto=False) leaves the counter unchanged.
        self.assertEqual(
            self.CAP, _next_consecutive(self.CAP, auto=False, reset=False))
