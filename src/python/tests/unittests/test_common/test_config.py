import configparser
import os
import shutil
import tempfile
import unittest

from common import Config, ConfigError, PersistError
from common.config import InnerConfig, Checkers, Converters
from common.encryption import load_or_create_key, encrypt_field, is_ciphertext


def _build_config_ini(
    *,
    webhook_secret="",
    api_token="",
    remote_password="pass",
    sonarr_api_key="",
    radarr_api_key="",
    encryption_enabled=None,
    debug="False",
    verbose="False",
) -> str:
    """Build a full config INI string with parameterized secret fields.

    Used by encryption tests that need the same INI skeleton with different
    encrypted/plaintext values in the 5 secret fields.
    """
    sections = f"""[General]
debug={debug}
verbose={verbose}
webhook_secret={webhook_secret}
api_token={api_token}
allowed_hostname=

[Lftp]
remote_address=host
remote_username=user
remote_password={remote_password}
remote_port=22
remote_path=/remote
local_path=/local
remote_path_to_scan_script=/scan.sh
use_ssh_key=False
num_max_parallel_downloads=2
num_max_parallel_files_per_download=3
num_max_connections_per_root_file=4
num_max_connections_per_dir_file=5
num_max_total_connections=6
use_temp_file=False

[Controller]
interval_ms_remote_scan=30000
interval_ms_local_scan=10000
interval_ms_downloading_scan=2000
extract_path=/extract
use_local_path_as_extract_path=False
max_tracked_files=5000

[Web]
port=8800

[AutoQueue]
enabled=False
patterns_only=False
auto_extract=False

[Sonarr]
enabled=False
sonarr_url=
sonarr_api_key={sonarr_api_key}

[Radarr]
enabled=False
radarr_url=
radarr_api_key={radarr_api_key}

[AutoDelete]
enabled=False
dry_run=False
delay_seconds=60
"""
    if encryption_enabled is not None:
        sections += f"""
[Encryption]
enabled={encryption_enabled}
"""
    return sections


class TestConverters(unittest.TestCase):
    def test_int(self):
        self.assertEqual(0, Converters.int(None, "", "0"))
        self.assertEqual(1, Converters.int(None, "", "1"))
        self.assertEqual(-1, Converters.int(None, "", "-1"))
        self.assertEqual(5000, Converters.int(None, "", "5000"))
        self.assertEqual(-5000, Converters.int(None, "", "-5000"))
        with self.assertRaises(ConfigError) as e:
            Converters.int(TestConverters, "bad", "")
        self.assertEqual("Bad config: TestConverters.bad is empty", str(e.exception))
        with self.assertRaises(ConfigError) as e:
            Converters.int(TestConverters, "bad", "3.14")
        self.assertEqual("Bad config: TestConverters.bad (3.14) must be an integer value", str(e.exception))
        with self.assertRaises(ConfigError) as e:
            Converters.int(TestConverters, "bad", "cat")
        self.assertEqual("Bad config: TestConverters.bad (cat) must be an integer value", str(e.exception))

    def test_bool(self):
        self.assertEqual(True, Converters.bool(None, "", "True"))
        self.assertEqual(False, Converters.bool(None, "", "False"))
        self.assertEqual(True, Converters.bool(None, "", "true"))
        self.assertEqual(False, Converters.bool(None, "", "false"))
        self.assertEqual(True, Converters.bool(None, "", "TRUE"))
        self.assertEqual(False, Converters.bool(None, "", "FALSE"))
        self.assertEqual(True, Converters.bool(None, "", "1"))
        self.assertEqual(False, Converters.bool(None, "", "0"))
        with self.assertRaises(ConfigError) as e:
            Converters.bool(TestConverters, "bad", "")
        self.assertEqual("Bad config: TestConverters.bad is empty", str(e.exception))
        with self.assertRaises(ConfigError) as e:
            Converters.bool(TestConverters, "bad", "cat")
        self.assertEqual("Bad config: TestConverters.bad (cat) must be a boolean value", str(e.exception))
        with self.assertRaises(ConfigError) as e:
            Converters.bool(TestConverters, "bad", "-3.14")
        self.assertEqual("Bad config: TestConverters.bad (-3.14) must be a boolean value", str(e.exception))


class DummyInnerConfig(InnerConfig):
    c_prop1 = InnerConfig._create_property("prop1", Checkers.null, Converters.null)
    a_prop2 = InnerConfig._create_property("prop2", Checkers.null, Converters.null)
    b_prop3 = InnerConfig._create_property("prop3", Checkers.null, Converters.null)

    def __init__(self):
        self.c_prop1 = "1"
        self.a_prop2 = "2"
        self.b_prop3 = "3"


class DummyInnerConfig2(InnerConfig):
    prop_int = InnerConfig._create_property("prop_int", Checkers.null, Converters.int)
    prop_str = InnerConfig._create_property("prop_str", Checkers.string_nonempty, Converters.null)

    def __init__(self):
        self.prop_int = None
        self.prop_str = None


class TestInnerConfig(unittest.TestCase):
    def test_property_order(self):
        dummy_config = DummyInnerConfig()
        self.assertEqual(["c_prop1", "a_prop2", "b_prop3"], list(dummy_config.as_dict().keys()))

    def test_has_property(self):
        dummy_config = DummyInnerConfig()
        self.assertTrue(dummy_config.has_property("c_prop1"))
        self.assertTrue(dummy_config.has_property("a_prop2"))
        self.assertTrue(dummy_config.has_property("b_prop3"))
        self.assertFalse(dummy_config.has_property("not_prop"))
        self.assertFalse(dummy_config.has_property("__init__"))
        self.assertFalse(dummy_config.has_property(""))

    def test_checker_is_called(self):
        dummy_config = DummyInnerConfig2()
        dummy_config.prop_str = "a string"
        self.assertEqual("a string", dummy_config.prop_str)
        with self.assertRaises(ConfigError) as e:
            dummy_config.prop_str = ""
        self.assertEqual("Bad config: DummyInnerConfig2.prop_str is empty", str(e.exception))

    def test_converter_is_called(self):
        dummy_config = DummyInnerConfig2.from_dict({"prop_int": "5", "prop_str": "a"})
        self.assertEqual(5, dummy_config.prop_int)
        with self.assertRaises(ConfigError) as e:
            DummyInnerConfig2.from_dict({"prop_int": "cat", "prop_str": "a"})
        self.assertEqual("Bad config: DummyInnerConfig2.prop_int (cat) must be an integer value", str(e.exception))


class TestConfig(unittest.TestCase):
    def setUp(self):
        """Create a temp dir + keyfile path; inject into Config class state."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_config_enc")
        self.keyfile = os.path.join(self.temp_dir, "secrets.key")
        Config.set_keyfile_path(self.keyfile)
        self.addCleanup(Config.set_keyfile_path, None)
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def __check_unknown_error(self, cls, good_dict):
        """
        Helper method to check that a config class raises an error on
        an unknown key
        :param cls:
        :param good_dict:
        :return:
        """
        bad_dict = dict(good_dict)
        bad_dict["unknown"] = "how did this get here"
        with self.assertRaises(ConfigError) as error:
            cls.from_dict(bad_dict)
        self.assertTrue(str(error.exception).startswith("Unknown config"))

    def __check_missing_error(self, cls, good_dict, key):
        """
        Helper method to check that a config class raises an error on
        a missing key
        :param cls:
        :param good_dict:
        :param key:
        :return:
        """
        bad_dict = dict(good_dict)
        del bad_dict[key]
        with self.assertRaises(ConfigError) as error:
            cls.from_dict(bad_dict)
        self.assertTrue(str(error.exception).startswith("Missing config"))

    def __check_empty_error(self, cls, good_dict, key):
        """
        Helper method to check that a config class raises an error on
        a empty value
        :param cls:
        :param good_dict:
        :param key:
        :return:
        """
        bad_dict = dict(good_dict)
        bad_dict[key] = ""
        with self.assertRaises(ConfigError) as error:
            cls.from_dict(bad_dict)
        self.assertTrue(str(error.exception).startswith("Bad config"))
        bad_dict[key] = "   "
        with self.assertRaises(ConfigError) as error:
            cls.from_dict(bad_dict)
        self.assertTrue(str(error.exception).startswith("Bad config"))

    def check_common(self, cls, good_dict, keys):
        """
        Helper method to run some common checks
        :param cls:
        :param good_dict:
        :param keys:
        :return:
        """
        # unknown
        self.__check_unknown_error(cls, good_dict)

        for key in keys:
            # missing key
            self.__check_missing_error(cls, good_dict, key)
            # empty value
            self.__check_empty_error(cls, good_dict, key)

    def check_bad_value_error(self, cls, good_dict, key, value):
        """
        Helper method to check that a config class raises an error on
        a bad value
        :param cls:
        :param good_dict:
        :param key:
        :param value:
        :return:
        """
        bad_dict = dict(good_dict)
        bad_dict[key] = value
        with self.assertRaises(ConfigError) as error:
            cls.from_dict(bad_dict)
        self.assertTrue(str(error.exception).startswith("Bad config"))

    def test_has_section(self):
        config = Config()
        self.assertTrue(config.has_section("general"))
        self.assertTrue(config.has_section("lftp"))
        self.assertTrue(config.has_section("controller"))
        self.assertTrue(config.has_section("web"))
        self.assertTrue(config.has_section("autoqueue"))
        self.assertTrue(config.has_section("sonarr"))
        self.assertTrue(config.has_section("radarr"))
        self.assertTrue(config.has_section("autodelete"))
        self.assertFalse(config.has_section("nope"))
        self.assertFalse(config.has_section("from_file"))
        self.assertFalse(config.has_section("__init__"))

    def test_general(self):
        good_dict = {
            "debug": "True",
            "verbose": "False",
            "webhook_secret": "",
            "api_token": "",
            "allowed_hostname": "",
            "webhook_require_secret": "False",
        }
        general = Config.General.from_dict(good_dict)
        self.assertEqual(True, general.debug)
        self.assertEqual(False, general.verbose)
        self.assertEqual("", general.webhook_secret)
        self.assertEqual("", general.api_token)
        self.assertEqual(False, general.webhook_require_secret)

        # webhook_secret with non-empty value
        good_dict_with_secret = dict(good_dict)
        good_dict_with_secret["webhook_secret"] = "mysecret"
        general_with_secret = Config.General.from_dict(good_dict_with_secret)
        self.assertEqual("mysecret", general_with_secret.webhook_secret)

        # api_token with non-empty value
        good_dict_with_token = dict(good_dict)
        good_dict_with_token["api_token"] = "mytoken"
        general_with_token = Config.General.from_dict(good_dict_with_token)
        self.assertEqual("mytoken", general_with_token.api_token)

        # check_common only covers fields that raise on empty (Checkers.string_nonempty)
        # webhook_secret and api_token use Checkers.null so they allow empty strings — not included here
        self.check_common(Config.General,
                          good_dict,
                          {
                              "debug",
                              "verbose",
                          })

        # webhook_secret and api_token must be present (missing key still raises)
        self.__check_missing_error(Config.General, good_dict, "webhook_secret")
        self.__check_missing_error(Config.General, good_dict, "api_token")
        self.__check_missing_error(Config.General, good_dict, "allowed_hostname")

        # bad values
        self.check_bad_value_error(Config.General, good_dict, "debug", "SomeString")
        self.check_bad_value_error(Config.General, good_dict, "debug", "-1")
        self.check_bad_value_error(Config.General, good_dict, "verbose", "SomeString")
        self.check_bad_value_error(Config.General, good_dict, "verbose", "-1")

    def test_general_webhook_require_secret_back_compat(self):
        """from_dict without webhook_require_secret key loads with default False (D-06, BUG-02)."""
        general_section = {
            "debug": "True",
            "verbose": "False",
            "webhook_secret": "",
            "api_token": "",
            "allowed_hostname": "",
            # webhook_require_secret intentionally absent — old config file
        }
        minimal_dict = {
            "General": general_section,
            "Lftp": {
                "remote_address": "h", "remote_username": "u", "remote_password": "p",
                "remote_port": "22", "remote_path": "/r", "local_path": "/l",
                "remote_path_to_scan_script": "/s", "use_ssh_key": "False",
                "num_max_parallel_downloads": "2", "num_max_parallel_files_per_download": "3",
                "num_max_connections_per_root_file": "4", "num_max_connections_per_dir_file": "5",
                "num_max_total_connections": "6", "use_temp_file": "False", "rate_limit": "0",
            },
            "Controller": {
                "interval_ms_remote_scan": "30000", "interval_ms_local_scan": "10000",
                "interval_ms_downloading_scan": "1000", "extract_path": "/e",
                "use_local_path_as_extract_path": "True", "max_tracked_files": "10000",
            },
            "Web": {"port": "8800"},
            "AutoQueue": {"enabled": "False", "patterns_only": "False", "auto_extract": "True"},
        }
        # Must not raise — from_dict injects "False" default
        config = Config.from_dict(minimal_dict)
        self.assertIs(False, config.general.webhook_require_secret)

    def test_general_webhook_require_secret_true(self):
        """from_dict with webhook_require_secret: True loads correctly (BUG-02)."""
        good_dict_with_flag = {
            "debug": "True",
            "verbose": "False",
            "webhook_secret": "mysecret",
            "api_token": "",
            "allowed_hostname": "",
            "webhook_require_secret": "True",
        }
        general = Config.General.from_dict(good_dict_with_flag)
        self.assertIs(True, general.webhook_require_secret)

    def test_default_config_roundtrips_require_secret(self):
        """First-run default config serializes and reloads without ConfigError (BLOCKER-1, BUG-02).

        Replicates exactly what _create_default_config() does, then verifies that
        Config.to_str() -> Config.from_str() succeeds with flag==False.
        A None / 'None' value would raise ConfigError in Converters.bool on reload.
        """
        from seedsyncarr import Seedsyncarr
        config = Seedsyncarr._create_default_config()
        serialized = config.to_str()
        reloaded = Config.from_str(serialized)
        self.assertIs(False, reloaded.general.webhook_require_secret)

    def test_general_webhook_require_secret_explicit_none_defaults_false(self):
        """from_dict with explicit None value for webhook_require_secret defaults to False.

        Codex medium: a present-but-None key must be treated the same as an absent key.
        Without this, None bypasses Converters.bool on first load, then serializes as 'None'
        and raises ConfigError on the next reload (BLOCKER-1 variant).
        """
        general_section = {
            "debug": "True",
            "verbose": "False",
            "webhook_secret": "",
            "api_token": "",
            "allowed_hostname": "",
            "webhook_require_secret": None,  # explicit None — must be treated as absent
        }
        minimal_dict = {
            "General": general_section,
            "Lftp": {
                "remote_address": "h", "remote_username": "u", "remote_password": "p",
                "remote_port": "22", "remote_path": "/r", "local_path": "/l",
                "remote_path_to_scan_script": "/s", "use_ssh_key": "False",
                "num_max_parallel_downloads": "2", "num_max_parallel_files_per_download": "3",
                "num_max_connections_per_root_file": "4", "num_max_connections_per_dir_file": "5",
                "num_max_total_connections": "6", "use_temp_file": "False", "rate_limit": "0",
            },
            "Controller": {
                "interval_ms_remote_scan": "30000", "interval_ms_local_scan": "10000",
                "interval_ms_downloading_scan": "1000", "extract_path": "/e",
                "use_local_path_as_extract_path": "True", "max_tracked_files": "10000",
            },
            "Web": {"port": "8800"},
            "AutoQueue": {"enabled": "False", "patterns_only": "False", "auto_extract": "True"},
        }
        # Must not raise — from_dict must collapse None to "False"
        config = Config.from_dict(minimal_dict)
        self.assertIs(False, config.general.webhook_require_secret)

    def test_lftp(self):
        good_dict = {
            "remote_address": "remote.server.com",
            "remote_username": "remote-user",
            "remote_password": "password",
            "remote_port": "3456",
            "remote_path": "/path/on/remote/server",
            "local_path": "/path/on/local/server",
            "remote_path_to_scan_script": "/path/on/remote/server/to/scan/script",
            "use_ssh_key": "False",
            "num_max_parallel_downloads": "2",
            "num_max_parallel_files_per_download": "3",
            "num_max_connections_per_root_file": "4",
            "num_max_connections_per_dir_file": "6",
            "num_max_total_connections": "7",
            "use_temp_file": "True",
            "rate_limit": "0"
        }
        lftp = Config.Lftp.from_dict(good_dict)
        self.assertEqual("remote.server.com", lftp.remote_address)
        self.assertEqual("remote-user", lftp.remote_username)
        self.assertEqual("password", lftp.remote_password)
        self.assertEqual(3456, lftp.remote_port)
        self.assertEqual("/path/on/remote/server", lftp.remote_path)
        self.assertEqual("/path/on/local/server", lftp.local_path)
        self.assertEqual("/path/on/remote/server/to/scan/script", lftp.remote_path_to_scan_script)
        self.assertEqual(False, lftp.use_ssh_key)
        self.assertEqual(2, lftp.num_max_parallel_downloads)
        self.assertEqual(3, lftp.num_max_parallel_files_per_download)
        self.assertEqual(4, lftp.num_max_connections_per_root_file)
        self.assertEqual(6, lftp.num_max_connections_per_dir_file)
        self.assertEqual(7, lftp.num_max_total_connections)
        self.assertEqual(True, lftp.use_temp_file)
        self.assertEqual(0, lftp.rate_limit)

        # rate_limit with positive value
        good_dict_throttled = dict(good_dict)
        good_dict_throttled["rate_limit"] = "1024"
        lftp_throttled = Config.Lftp.from_dict(good_dict_throttled)
        self.assertEqual(1024, lftp_throttled.rate_limit)

        self.check_common(Config.Lftp,
                          good_dict,
                          {
                              "remote_address",
                              "remote_username",
                              "remote_password",
                              "remote_port",
                              "remote_path",
                              "local_path",
                              "remote_path_to_scan_script",
                              "use_ssh_key",
                              "num_max_parallel_downloads",
                              "num_max_parallel_files_per_download",
                              "num_max_connections_per_root_file",
                              "num_max_connections_per_dir_file",
                              "num_max_total_connections",
                              "use_temp_file",
                              "rate_limit"
                          })

        # bad values
        self.check_bad_value_error(Config.Lftp, good_dict, "remote_port", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "remote_port", "0")
        self.check_bad_value_error(Config.Lftp, good_dict, "use_ssh_key", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "use_ssh_key", "SomeString")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_parallel_downloads", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_parallel_downloads", "0")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_parallel_files_per_download", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_parallel_files_per_download", "0")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_connections_per_root_file", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_connections_per_root_file", "0")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_connections_per_dir_file", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_connections_per_dir_file", "0")
        self.check_bad_value_error(Config.Lftp, good_dict, "num_max_total_connections", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "use_temp_file", "-1")
        self.check_bad_value_error(Config.Lftp, good_dict, "use_temp_file", "SomeString")
        self.check_bad_value_error(Config.Lftp, good_dict, "rate_limit", "-1")

    def test_controller(self):
        good_dict = {
            "interval_ms_remote_scan": "30000",
            "interval_ms_local_scan": "10000",
            "interval_ms_downloading_scan": "2000",
            "extract_path": "/extract/path",
            "use_local_path_as_extract_path": "True",
            "max_tracked_files": "10000"
        }
        controller = Config.Controller.from_dict(good_dict)
        self.assertEqual(30000, controller.interval_ms_remote_scan)
        self.assertEqual(10000, controller.interval_ms_local_scan)
        self.assertEqual(2000, controller.interval_ms_downloading_scan)
        self.assertEqual("/extract/path", controller.extract_path)
        self.assertEqual(True, controller.use_local_path_as_extract_path)
        self.assertEqual(10000, controller.max_tracked_files)

        self.check_common(Config.Controller,
                          good_dict,
                          {
                              "interval_ms_remote_scan",
                              "interval_ms_local_scan",
                              "interval_ms_downloading_scan",
                              "extract_path",
                              "use_local_path_as_extract_path",
                              "max_tracked_files"
                          })

        # bad values
        self.check_bad_value_error(Config.Controller, good_dict, "interval_ms_remote_scan", "-1")
        self.check_bad_value_error(Config.Controller, good_dict, "interval_ms_remote_scan", "0")
        self.check_bad_value_error(Config.Controller, good_dict, "interval_ms_local_scan", "-1")
        self.check_bad_value_error(Config.Controller, good_dict, "interval_ms_local_scan", "0")
        self.check_bad_value_error(Config.Controller, good_dict, "interval_ms_downloading_scan", "-1")
        self.check_bad_value_error(Config.Controller, good_dict, "interval_ms_downloading_scan", "0")
        self.check_bad_value_error(Config.Controller, good_dict, "use_local_path_as_extract_path", "SomeString")
        self.check_bad_value_error(Config.Controller, good_dict, "use_local_path_as_extract_path", "-1")
        self.check_bad_value_error(Config.Controller, good_dict, "max_tracked_files", "-1")
        self.check_bad_value_error(Config.Controller, good_dict, "max_tracked_files", "0")

    def test_web(self):
        good_dict = {
            "port": "1234",
        }
        web = Config.Web.from_dict(good_dict)
        self.assertEqual(1234, web.port)

        self.check_common(Config.Web,
                          good_dict,
                          {
                              "port"
                          })

        # bad values
        self.check_bad_value_error(Config.Web, good_dict, "port", "-1")
        self.check_bad_value_error(Config.Web, good_dict, "port", "0")

    def test_autoqueue(self):
        good_dict = {
            "enabled": "True",
            "patterns_only": "False",
            "auto_extract": "True"
        }
        autoqueue = Config.AutoQueue.from_dict(good_dict)
        self.assertEqual(True, autoqueue.enabled)
        self.assertEqual(False, autoqueue.patterns_only)

        self.check_common(Config.AutoQueue,
                          good_dict,
                          {
                              "enabled",
                              "patterns_only",
                              "auto_extract"
                          })

        # bad values
        self.check_bad_value_error(Config.AutoQueue, good_dict, "enabled", "SomeString")
        self.check_bad_value_error(Config.AutoQueue, good_dict, "enabled", "-1")
        self.check_bad_value_error(Config.AutoQueue, good_dict, "patterns_only", "SomeString")
        self.check_bad_value_error(Config.AutoQueue, good_dict, "patterns_only", "-1")
        self.check_bad_value_error(Config.AutoQueue, good_dict, "auto_extract", "SomeString")
        self.check_bad_value_error(Config.AutoQueue, good_dict, "auto_extract", "-1")

    def test_from_file(self):
        # Create empty config file
        config_file = tempfile.NamedTemporaryFile(mode="w", suffix="test_config", delete=False)
        self.addCleanup(os.remove, config_file.name)  # runs SECOND (registered first)
        self.addCleanup(config_file.close)            # runs FIRST (registered last)

        config_file.write("""
        [General]
        debug=False
        verbose=True

        [Lftp]
        remote_address=remote.server.com
        remote_username=remote-user
        remote_password=remote-pass
        remote_port = 3456
        remote_path=/path/on/remote/server
        local_path=/path/on/local/server
        remote_path_to_scan_script=/path/on/remote/server/to/scan/script
        use_ssh_key=True
        num_max_parallel_downloads=2
        num_max_parallel_files_per_download=3
        num_max_connections_per_root_file=4
        num_max_connections_per_dir_file=5
        num_max_total_connections=7
        use_temp_file=False

        [Controller]
        interval_ms_remote_scan=30000
        interval_ms_local_scan=10000
        interval_ms_downloading_scan=2000
        extract_path=/path/where/to/extract/stuff
        use_local_path_as_extract_path=False
        max_tracked_files=5000

        [Web]
        port=88

        [AutoQueue]
        enabled=False
        patterns_only=True
        auto_extract=True
        """)
        config_file.flush()
        config = Config.from_file(config_file.name)

        self.assertEqual(False, config.general.debug)
        self.assertEqual(True, config.general.verbose)

        self.assertEqual("remote.server.com", config.lftp.remote_address)
        self.assertEqual("remote-user", config.lftp.remote_username)
        self.assertEqual("remote-pass", config.lftp.remote_password)
        self.assertEqual(3456, config.lftp.remote_port)
        self.assertEqual("/path/on/remote/server", config.lftp.remote_path)
        self.assertEqual("/path/on/local/server", config.lftp.local_path)
        self.assertEqual("/path/on/remote/server/to/scan/script", config.lftp.remote_path_to_scan_script)
        self.assertEqual(True, config.lftp.use_ssh_key)
        self.assertEqual(2, config.lftp.num_max_parallel_downloads)
        self.assertEqual(3, config.lftp.num_max_parallel_files_per_download)
        self.assertEqual(4, config.lftp.num_max_connections_per_root_file)
        self.assertEqual(5, config.lftp.num_max_connections_per_dir_file)
        self.assertEqual(7, config.lftp.num_max_total_connections)
        self.assertEqual(False, config.lftp.use_temp_file)
        # Backward compatibility: rate_limit defaults to 0 when missing from INI
        self.assertEqual(0, config.lftp.rate_limit)

        self.assertEqual(30000, config.controller.interval_ms_remote_scan)
        self.assertEqual(10000, config.controller.interval_ms_local_scan)
        self.assertEqual(2000, config.controller.interval_ms_downloading_scan)
        self.assertEqual("/path/where/to/extract/stuff", config.controller.extract_path)
        self.assertEqual(False, config.controller.use_local_path_as_extract_path)
        self.assertEqual(5000, config.controller.max_tracked_files)

        self.assertEqual(88, config.web.port)

        self.assertEqual(False, config.autoqueue.enabled)
        self.assertEqual(True, config.autoqueue.patterns_only)
        self.assertEqual(True, config.autoqueue.auto_extract)

        # unknown section error
        config_file.write("""
        [Unknown]
        key=value
        """)
        config_file.flush()
        with self.assertRaises(ConfigError) as error:
            Config.from_file(config_file.name)
        self.assertTrue(str(error.exception).startswith("Unknown section"))

    def test_to_file(self):
        _tmp = tempfile.NamedTemporaryFile(suffix="test_config", delete=False)
        _tmp.close()
        config_file_path = _tmp.name
        self.addCleanup(os.remove, config_file_path)

        config = Config()
        config.general.debug = True
        config.general.verbose = False
        config.general.webhook_secret = ""
        config.general.api_token = ""
        config.general.allowed_hostname = ""
        config.general.webhook_require_secret = False
        config.lftp.remote_address = "server.remote.com"
        config.lftp.remote_username = "user-on-remote-server"
        config.lftp.remote_password = "pass-on-remote-server"
        config.lftp.remote_port = 3456
        config.lftp.remote_path = "/remote/server/path"
        config.lftp.local_path = "/local/server/path"
        config.lftp.remote_path_to_scan_script = "/remote/server/path/to/script"
        config.lftp.use_ssh_key = True
        config.lftp.num_max_parallel_downloads = 6
        config.lftp.num_max_parallel_files_per_download = 7
        config.lftp.num_max_connections_per_root_file = 2
        config.lftp.num_max_connections_per_dir_file = 3
        config.lftp.num_max_total_connections = 4
        config.lftp.use_temp_file = True
        config.lftp.rate_limit = 0
        config.controller.interval_ms_remote_scan = 1234
        config.controller.interval_ms_local_scan = 5678
        config.controller.interval_ms_downloading_scan = 9012
        config.controller.extract_path = "/path/extract/stuff"
        config.controller.use_local_path_as_extract_path = True
        config.controller.max_tracked_files = 10000
        config.web.port = 13
        config.autoqueue.enabled = True
        config.autoqueue.patterns_only = True
        config.autoqueue.auto_extract = False
        config.sonarr.enabled = False
        config.sonarr.sonarr_url = "http://localhost:8989"
        config.sonarr.sonarr_api_key = "abc123"
        config.radarr.enabled = False
        config.radarr.radarr_url = "http://localhost:7878"
        config.radarr.radarr_api_key = "def456"
        config.autodelete.enabled = False
        config.autodelete.dry_run = True
        config.autodelete.delay_seconds = 60
        config.encryption.enabled = False
        config.to_file(config_file_path)
        with open(config_file_path, "r") as f:
            actual_str = f.read()
        print(actual_str)

        golden_str = """
        [General]
        debug = True
        verbose = False
        webhook_secret =
        api_token =
        allowed_hostname =
        webhook_require_secret = False

        [Lftp]
        remote_address = server.remote.com
        remote_username = user-on-remote-server
        remote_password = pass-on-remote-server
        remote_port = 3456
        remote_path = /remote/server/path
        local_path = /local/server/path
        remote_path_to_scan_script = /remote/server/path/to/script
        use_ssh_key = True
        num_max_parallel_downloads = 6
        num_max_parallel_files_per_download = 7
        num_max_connections_per_root_file = 2
        num_max_connections_per_dir_file = 3
        num_max_total_connections = 4
        use_temp_file = True
        rate_limit = 0

        [Controller]
        interval_ms_remote_scan = 1234
        interval_ms_local_scan = 5678
        interval_ms_downloading_scan = 9012
        extract_path = /path/extract/stuff
        use_local_path_as_extract_path = True
        max_tracked_files = 10000

        [Web]
        port = 13

        [AutoQueue]
        enabled = True
        patterns_only = True
        auto_extract = False

        [Sonarr]
        enabled = False
        sonarr_url = http://localhost:8989
        sonarr_api_key = abc123

        [Radarr]
        enabled = False
        radarr_url = http://localhost:7878
        radarr_api_key = def456

        [AutoDelete]
        enabled = False
        dry_run = True
        delay_seconds = 60

        [Encryption]
        enabled = False
        """

        golden_lines = [s.strip() for s in golden_str.splitlines()]
        golden_lines = list(filter(None, golden_lines))  # remove blank lines
        actual_lines = [s.strip() for s in actual_str.splitlines()]
        actual_lines = list(filter(None, actual_lines))  # remove blank lines

        self.assertEqual(len(golden_lines), len(actual_lines))
        for i, _ in enumerate(golden_lines):
            self.assertEqual(golden_lines[i], actual_lines[i])

    # ── SEC-02 encryption tests ───────────────────────────────────────────────

    def _build_plaintext_config(self) -> "Config":
        """Return a fully-populated Config with encryption disabled and plaintext secrets.

        Used as a fixture by the 6 encryption tests so field population is not
        repeated in each test body. Matches the field set used in test_to_file.
        """
        c = Config()
        c.general.debug = False
        c.general.verbose = False
        c.general.webhook_secret = "my_webhook"
        c.general.api_token = "my_token"
        c.general.allowed_hostname = ""
        c.general.webhook_require_secret = False
        c.lftp.remote_address = "remote.host"
        c.lftp.remote_username = "remote_user"
        c.lftp.remote_password = "my_pass"
        c.lftp.remote_port = 22
        c.lftp.remote_path = "/remote"
        c.lftp.local_path = "/local"
        c.lftp.remote_path_to_scan_script = "/remote/scan.sh"
        c.lftp.use_ssh_key = False
        c.lftp.num_max_parallel_downloads = 2
        c.lftp.num_max_parallel_files_per_download = 3
        c.lftp.num_max_connections_per_root_file = 4
        c.lftp.num_max_connections_per_dir_file = 5
        c.lftp.num_max_total_connections = 6
        c.lftp.use_temp_file = False
        c.lftp.rate_limit = 0
        c.controller.interval_ms_remote_scan = 30000
        c.controller.interval_ms_local_scan = 10000
        c.controller.interval_ms_downloading_scan = 2000
        c.controller.extract_path = "/extract"
        c.controller.use_local_path_as_extract_path = False
        c.controller.max_tracked_files = 5000
        c.web.port = 8800
        c.autoqueue.enabled = False
        c.autoqueue.patterns_only = False
        c.autoqueue.auto_extract = False
        c.sonarr.enabled = False
        c.sonarr.sonarr_url = ""
        c.sonarr.sonarr_api_key = "my_sonarr_key"
        c.radarr.enabled = False
        c.radarr.radarr_url = ""
        c.radarr.radarr_api_key = "my_radarr_key"
        c.autodelete.enabled = False
        c.autodelete.dry_run = False
        c.autodelete.delay_seconds = 60
        c.encryption.enabled = False
        return c

    def test_encryption_disabled_by_default(self):
        """81-02-03 / SEC-02 #3b: Config loaded without [Encryption] section defaults to disabled.

        Proves backward compatibility: existing installs that never heard of
        encryption load normally with encryption.enabled == False.
        This test intentionally does NOT call set_keyfile_path — the setUp value
        is irrelevant; backward compat must work regardless of keyfile state.
        """
        # Build a full config string WITHOUT any [Encryption] section
        content = """
[General]
debug=False
verbose=True
webhook_secret=my_secret
api_token=my_token
allowed_hostname=

[Lftp]
remote_address=remote.host
remote_username=user
remote_password=pass
remote_port=22
remote_path=/remote
local_path=/local
remote_path_to_scan_script=/scan.sh
use_ssh_key=False
num_max_parallel_downloads=2
num_max_parallel_files_per_download=3
num_max_connections_per_root_file=4
num_max_connections_per_dir_file=5
num_max_total_connections=6
use_temp_file=False

[Controller]
interval_ms_remote_scan=30000
interval_ms_local_scan=10000
interval_ms_downloading_scan=2000
extract_path=/extract
use_local_path_as_extract_path=False
max_tracked_files=5000

[Web]
port=8800

[AutoQueue]
enabled=False
patterns_only=False
auto_extract=False
"""
        config = Config.from_str(content)
        self.assertEqual(False, config.encryption.enabled)
        self.assertEqual([], config._decrypt_errors)
        # Backward compatibility: rate_limit defaults to 0 when missing from INI
        self.assertEqual(0, config.lftp.rate_limit)

    def test_enable_new_install_encrypts_on_write(self):
        """81-02-01 / SEC-02 #1b: First run with flag enabled encrypts all 5 secrets in to_str().

        setUp injects self.keyfile as the keyfile path; the keyfile is created
        on first load_or_create_key call inside to_str.
        """
        c = self._build_plaintext_config()
        c.encryption.enabled = True

        serialized = c.to_str()

        # Parse the output to inspect individual field values
        parser = configparser.ConfigParser()
        parser.read_string(serialized)

        # All 5 secret fields must be Fernet tokens (start with gAAAAA)
        self.assertTrue(
            is_ciphertext(parser.get("General", "webhook_secret")),
            "General.webhook_secret not encrypted"
        )
        self.assertTrue(
            is_ciphertext(parser.get("General", "api_token")),
            "General.api_token not encrypted"
        )
        self.assertTrue(
            is_ciphertext(parser.get("Lftp", "remote_password")),
            "Lftp.remote_password not encrypted"
        )
        self.assertTrue(
            is_ciphertext(parser.get("Sonarr", "sonarr_api_key")),
            "Sonarr.sonarr_api_key not encrypted"
        )
        self.assertTrue(
            is_ciphertext(parser.get("Radarr", "radarr_api_key")),
            "Radarr.radarr_api_key not encrypted"
        )
        # Keyfile must have been created
        self.assertTrue(os.path.isfile(self.keyfile), "Keyfile not created by to_str")

    def test_from_file_enabled_decrypts(self):
        """81-02-02 / SEC-02 #2: Read path transparently decrypts; callers see plaintext.

        Writes an INI with [Encryption] enabled=True and pre-encrypted values,
        then calls Config.from_file and asserts all 5 fields come back as plaintext.
        """
        key = load_or_create_key(self.keyfile)

        encrypted_webhook = encrypt_field(key, "known_webhook")
        encrypted_token = encrypt_field(key, "known_token")
        encrypted_pass = encrypt_field(key, "known_pass")
        encrypted_sonarr = encrypt_field(key, "known_sonarr")
        encrypted_radarr = encrypt_field(key, "known_radarr")

        content = _build_config_ini(
            webhook_secret=encrypted_webhook,
            api_token=encrypted_token,
            remote_password=encrypted_pass,
            sonarr_api_key=encrypted_sonarr,
            radarr_api_key=encrypted_radarr,
            encryption_enabled="True",
        )

        # Write to a temp file and read back via from_file (exercises Persist.from_file)
        cfg_file = os.path.join(self.temp_dir, "settings.cfg")
        with open(cfg_file, "w") as f:
            f.write(content)

        config = Config.from_file(cfg_file)

        self.assertEqual("known_webhook", config.general.webhook_secret)
        self.assertEqual("known_token", config.general.api_token)
        self.assertEqual("known_pass", config.lftp.remote_password)
        self.assertEqual("known_sonarr", config.sonarr.sonarr_api_key)
        self.assertEqual("known_radarr", config.radarr.radarr_api_key)
        self.assertEqual([], config._decrypt_errors)

    def test_disable_restores_plaintext(self):
        """81-02-04 / SEC-02 #4: enable→disable round-trip preserves all 5 values.

        After disabling encryption the next to_str() output must contain plaintext
        values (no gAAAAA prefix) for all 5 secret fields.
        """
        # Step 1: build config with encryption enabled → serialize to get ciphertext
        c = self._build_plaintext_config()
        c.encryption.enabled = True
        encrypted_serialized = c.to_str()

        # Step 2: parse back → all 5 fields are decrypted in memory
        c2 = Config.from_str(encrypted_serialized)
        self.assertEqual("my_webhook", c2.general.webhook_secret)
        self.assertEqual("my_token", c2.general.api_token)
        self.assertEqual("my_pass", c2.lftp.remote_password)
        self.assertEqual("my_sonarr_key", c2.sonarr.sonarr_api_key)
        self.assertEqual("my_radarr_key", c2.radarr.radarr_api_key)

        # Step 3: flip flag off and serialize → must produce plaintext
        c2.encryption.enabled = False
        plaintext_serialized = c2.to_str()

        parser = configparser.ConfigParser()
        parser.read_string(plaintext_serialized)

        self.assertEqual("my_webhook", parser.get("General", "webhook_secret"))
        self.assertEqual("my_token", parser.get("General", "api_token"))
        self.assertEqual("my_pass", parser.get("Lftp", "remote_password"))
        self.assertEqual("my_sonarr_key", parser.get("Sonarr", "sonarr_api_key"))
        self.assertEqual("my_radarr_key", parser.get("Radarr", "radarr_api_key"))

        # None of the fields should start with gAAAAA
        self.assertFalse(is_ciphertext(parser.get("General", "webhook_secret")))
        self.assertFalse(is_ciphertext(parser.get("General", "api_token")))
        self.assertFalse(is_ciphertext(parser.get("Lftp", "remote_password")))
        self.assertFalse(is_ciphertext(parser.get("Sonarr", "sonarr_api_key")))
        self.assertFalse(is_ciphertext(parser.get("Radarr", "radarr_api_key")))

    def test_from_str_enabled_with_plaintext_falls_back(self):
        """SEC-02 criterion #3 in-memory half: plaintext values on an encryption-enabled
        config are preserved as plaintext in memory (no error).

        The re-encrypt-on-next-write is plan 03's startup hook; this test only
        verifies the read path does NOT corrupt plaintext values and does NOT
        populate _decrypt_errors for them (plaintext is not a decrypt error).
        """
        content = _build_config_ini(
            webhook_secret="my_webhook",
            api_token="my_token",
            remote_password="my_pass",
            sonarr_api_key="my_sonarr_key",
            radarr_api_key="my_radarr_key",
            encryption_enabled="True",
        )
        config = Config.from_str(content)
        # Plaintext values must survive the read path untouched
        self.assertEqual("my_webhook", config.general.webhook_secret)
        self.assertEqual("my_token", config.general.api_token)
        self.assertEqual("my_pass", config.lftp.remote_password)
        self.assertEqual("my_sonarr_key", config.sonarr.sonarr_api_key)
        self.assertEqual("my_radarr_key", config.radarr.radarr_api_key)
        # Plaintext is NOT a decrypt error
        self.assertEqual([], config._decrypt_errors)

    def test_to_str_raises_when_enabled_without_keyfile_path(self):
        """T-81-02-05: to_str raises ConfigError when encryption.enabled=True but
        _keyfile_path is None (prevents silent no-op that leaves plaintext on disk).
        """
        # Explicitly reset the keyfile path set by setUp
        Config.set_keyfile_path(None)

        c = self._build_plaintext_config()
        c.encryption.enabled = True

        with self.assertRaises(ConfigError) as ctx:
            c.to_str()
        self.assertIn("keyfile path", str(ctx.exception))

    def test_from_str_invalid_encryption_enabled_value(self):
        """TC-2: A non-boolean value for Encryption.enabled defaults to disabled
        rather than raising a ValueError through _strtobool."""
        content = """
[General]
debug=False
verbose=False
webhook_secret=my_secret
api_token=my_token
allowed_hostname=

[Lftp]
remote_address=remote.host
remote_username=user
remote_password=pass
remote_port=22
remote_path=/remote
local_path=/local
remote_path_to_scan_script=/scan.sh
use_ssh_key=False
num_max_parallel_downloads=2
num_max_parallel_files_per_download=3
num_max_connections_per_root_file=4
num_max_connections_per_dir_file=5
num_max_total_connections=6
use_temp_file=False

[Controller]
interval_ms_remote_scan=30000
interval_ms_local_scan=10000
interval_ms_downloading_scan=2000
extract_path=/extract
use_local_path_as_extract_path=False
max_tracked_files=5000

[Web]
port=8800

[AutoQueue]
enabled=False
patterns_only=False
auto_extract=False

[Encryption]
enabled=not_a_bool
"""
        config = Config.from_str(content)
        self.assertEqual(False, config.encryption.enabled)
        self.assertEqual([], config._decrypt_errors)

    def test_from_str_keyfile_gone_with_ciphertext(self):
        """Architecture-6: When the keyfile is missing but config contains ciphertext,
        from_str must NOT create a new key (which would orphan the existing ciphertext).
        Instead it records decrypt errors for every ciphertext field."""
        key = load_or_create_key(self.keyfile)
        encrypted_pass = encrypt_field(key, "my_pass")

        os.remove(self.keyfile)
        self.assertFalse(os.path.isfile(self.keyfile))

        content = """
[General]
debug=False
verbose=False
webhook_secret=plain_secret
api_token=plain_token
allowed_hostname=

[Lftp]
remote_address=host
remote_username=user
remote_password={password}
remote_port=22
remote_path=/remote
local_path=/local
remote_path_to_scan_script=/scan.sh
use_ssh_key=False
num_max_parallel_downloads=2
num_max_parallel_files_per_download=3
num_max_connections_per_root_file=4
num_max_connections_per_dir_file=5
num_max_total_connections=6
use_temp_file=False

[Controller]
interval_ms_remote_scan=30000
interval_ms_local_scan=10000
interval_ms_downloading_scan=2000
extract_path=/extract
use_local_path_as_extract_path=False
max_tracked_files=5000

[Web]
port=8800

[AutoQueue]
enabled=False
patterns_only=False
auto_extract=False

[Encryption]
enabled=True
""".format(password=encrypted_pass)

        config = Config.from_str(content)
        self.assertFalse(os.path.isfile(self.keyfile), "keyfile must NOT be created")
        self.assertIn("Lftp.remote_password", config._decrypt_errors)
        self.assertEqual(1, len(config._decrypt_errors), "expected exactly one decrypt error")
        self.assertEqual(encrypted_pass, config.lftp.remote_password)

    # ── end SEC-02 encryption tests ───────────────────────────────────────────

    def test_persist_read_error(self):
        # bad section
        content = """
        [Web
        port=88
        """
        with self.assertRaises(PersistError):
            Config.from_str(content)

        # bad value
        content = """
        [Web]
        port88
        """
        with self.assertRaises(PersistError):
            Config.from_str(content)

        # bad line
        content = """
        [Web]
        port=88
        what am i doing here
        """
        with self.assertRaises(PersistError):
            Config.from_str(content)


# ── ARCH-02: declarative secret discovery tests ───────────────────────────────

class TestSecretFieldDiscovery(unittest.TestCase):
    """Tests for Config.secret_fields() dynamic discovery API (ARCH-02).

    These tests were written BEFORE the implementation (TDD RED step).
    Each test class that mutates class state cleans up in tearDown.
    """

    def setUp(self) -> None:
        """Create temp dir + keyfile for Fernet round-trip tests."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_secret_discovery")
        self.keyfile = os.path.join(self.temp_dir, "secrets.key")
        Config.set_keyfile_path(self.keyfile)
        self.addCleanup(Config.set_keyfile_path, None)
        self.addCleanup(shutil.rmtree, self.temp_dir)
        # Track injected state for teardown
        self._injected_prop: Optional[property] = None
        self._injected_prop_name: Optional[str] = None

    def tearDown(self) -> None:
        """Remove any injected temporary PROP from Config.General and __prop_addon_map."""
        if self._injected_prop_name is not None and self._injected_prop is not None:
            # Remove the property from Config.General
            if hasattr(Config.General, self._injected_prop_name):
                delattr(Config.General, self._injected_prop_name)
            # Remove the PropMetadata entry from the shared global map
            pam = InnerConfig._InnerConfig__prop_addon_map  # type: ignore[attr-defined]
            pam.pop(self._injected_prop, None)
            self._injected_prop = None
            self._injected_prop_name = None

    def test_discovery_iterates_all_sections_returns_exactly_five_real_triples(self) -> None:
        """F1: discovery API returns exactly the 5 known (attr, field, ini_section) triples.

        The discovery MUST iterate ALL mapped Config sections (not just
        General/Lftp/Sonarr/Radarr), so that a future secret=True field in any
        section (Controller, Web, AutoQueue, AutoDelete, Encryption) is auto-picked-up.
        """
        triples = list(Config.secret_fields())
        # Must return exactly 5 entries — same set as the hand-maintained tuple removed in ARCH-02
        self.assertEqual(5, len(triples), f"Expected 5 triples, got {len(triples)}: {triples}")
        # Exact expected set (order within the set is flexible; we sort for comparison)
        expected = {
            ("general", "webhook_secret", "General"),
            ("general", "api_token", "General"),
            ("lftp", "remote_password", "Lftp"),
            ("sonarr", "sonarr_api_key", "Sonarr"),
            ("radarr", "radarr_api_key", "Radarr"),
        }
        self.assertEqual(expected, set(triples))

    def test_encryption_enabled_not_discovered(self) -> None:
        """T-81-02-07: Encryption.enabled is absent from discovery output.

        The Encryption section IS iterated by the all-sections walk, but
        enabled stays secret=False so it yields nothing.
        """
        triples = list(Config.secret_fields())
        attrs_fields = [(attr, field) for attr, field, _ in triples]
        # Encryption.enabled must never appear
        self.assertNotIn(("encryption", "enabled"), attrs_fields)
        # More generally: no Encryption section entry at all
        sections = [ini_section for _, _, ini_section in triples]
        self.assertNotIn("Encryption", sections)

    def test_secret_field_on_unmapped_subclass_not_discovered(self) -> None:
        """F3: A secret=True PROP on an unmapped throwaway subclass does NOT appear.

        __prop_addon_map is a SHARED GLOBAL across all InnerConfig subclasses.
        The per-class filter in the discovery API must prevent cross-contamination.
        """
        # Create a throwaway unmapped subclass with a secret=True PROP
        class _ThrowawaySecret(InnerConfig):
            throwaway_secret = InnerConfig._create_property(
                "throwaway_secret", Checkers.null, Converters.null, secret=True
            )

            def __init__(self) -> None:
                super().__init__()
                self.throwaway_secret = None

        try:
            triples = list(Config.secret_fields())
            fields = [(attr, field) for attr, field, _ in triples]
            # The throwaway's secret field must NOT appear
            self.assertNotIn(("_throwawaysecret", "throwaway_secret"), fields)
            # More robustly: still exactly 5 real triples
            self.assertEqual(5, len(triples))
        finally:
            # Clean up the throwaway's __prop_addon_map entry
            prop = _ThrowawaySecret.throwaway_secret
            pam = InnerConfig._InnerConfig__prop_addon_map  # type: ignore[attr-defined]
            pam.pop(prop, None)

    def test_secret_field_round_trips_through_fernet(self) -> None:
        """F2, criterion #2: A temp secret=True PROP injected into Config.General is
        auto-discovered AND round-trips through real to_str -> from_str Fernet path.

        The injected field must appear in Config.secret_fields() output and its
        value must be ciphertext on disk and original plaintext after decrypt.
        This test asserts discovery + Fernet round-trip ONLY.
        It does NOT assert any redacted-response behavior (_SENSITIVE_FIELDS is OUT OF SCOPE).
        """
        # Inject a temporary secret=True PROP into Config.General
        temp_prop_name = "_test_temp_secret_field"
        temp_prop = InnerConfig._create_property(
            temp_prop_name, Checkers.null, Converters.null, secret=True
        )
        setattr(Config.General, temp_prop_name, temp_prop)
        self._injected_prop = temp_prop
        self._injected_prop_name = temp_prop_name

        # Also need to add the field to General.__init__ so from_dict works.
        # We accomplish this by directly setting on an instance after construction.
        # The round-trip test uses to_str -> from_str, which goes through from_dict.
        # Because from_dict calls from_dict on General's dict, and the injected PROP
        # is now on Config.General, it will appear in as_dict output and be expected
        # in from_dict input. We need the default Config() general to not crash.
        # Patch General.__init__ to also init the temp field.
        original_general_init = Config.General.__init__

        def _patched_general_init(self_inner: "Config.General") -> None:
            original_general_init(self_inner)
            # Directly set the private backing store so the property getter works
            setattr(self_inner, f"__{temp_prop_name}", None)

        Config.General.__init__ = _patched_general_init  # type: ignore[method-assign]
        self.addCleanup(setattr, Config.General, "__init__", original_general_init)

        try:
            # 1. Verify the injected field appears in discovery output
            triples = list(Config.secret_fields())
            found = any(field == temp_prop_name for _, field, _ in triples)
            self.assertTrue(
                found,
                f"Injected temp field '{temp_prop_name}' not found in secret_fields(): {triples}"
            )

            # 2. Build a config with a plaintext value for the temp field + encryption enabled
            c = Config()
            c.general.debug = False
            c.general.verbose = False
            c.general.webhook_secret = ""
            c.general.api_token = ""
            c.general.allowed_hostname = ""
            c.general.webhook_require_secret = False
            c.lftp.remote_address = "host"
            c.lftp.remote_username = "user"
            c.lftp.remote_password = "pass"
            c.lftp.remote_port = 22
            c.lftp.remote_path = "/r"
            c.lftp.local_path = "/l"
            c.lftp.remote_path_to_scan_script = "/s.sh"
            c.lftp.use_ssh_key = False
            c.lftp.num_max_parallel_downloads = 2
            c.lftp.num_max_parallel_files_per_download = 3
            c.lftp.num_max_connections_per_root_file = 4
            c.lftp.num_max_connections_per_dir_file = 5
            c.lftp.num_max_total_connections = 6
            c.lftp.use_temp_file = False
            c.lftp.rate_limit = 0
            c.controller.interval_ms_remote_scan = 30000
            c.controller.interval_ms_local_scan = 10000
            c.controller.interval_ms_downloading_scan = 2000
            c.controller.extract_path = "/e"
            c.controller.use_local_path_as_extract_path = False
            c.controller.max_tracked_files = 5000
            c.web.port = 8800
            c.autoqueue.enabled = False
            c.autoqueue.patterns_only = False
            c.autoqueue.auto_extract = False
            c.sonarr.enabled = False
            c.sonarr.sonarr_url = ""
            c.sonarr.sonarr_api_key = ""
            c.radarr.enabled = False
            c.radarr.radarr_url = ""
            c.radarr.radarr_api_key = ""
            c.autodelete.enabled = False
            c.autodelete.dry_run = False
            c.autodelete.delay_seconds = 60
            c.encryption.enabled = True
            # Set the injected temp field value
            setattr(c.general, f"__{temp_prop_name}", "my_temp_secret_value")

            # 3. Serialize: the temp field should be encrypted in the output
            serialized = c.to_str()
            parser = configparser.ConfigParser()
            parser.read_string(serialized)
            on_disk_value = parser.get("General", temp_prop_name)
            self.assertTrue(
                is_ciphertext(on_disk_value),
                f"Expected ciphertext on disk for '{temp_prop_name}', got: {on_disk_value!r}"
            )

            # 4. Deserialize: the temp field must come back as plaintext
            reloaded = Config.from_str(serialized)
            decrypted_value = getattr(reloaded.general, temp_prop_name)
            self.assertEqual(
                "my_temp_secret_value",
                decrypted_value,
                f"Round-trip failed: got {decrypted_value!r} instead of 'my_temp_secret_value'"
            )
        finally:
            # tearDown handles cleanup of the injected PROP and __prop_addon_map entry
            pass
