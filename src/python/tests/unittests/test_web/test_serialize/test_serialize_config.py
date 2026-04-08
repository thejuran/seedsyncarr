import unittest
import json

from common import Config
from web.serialize import SerializeConfig


class TestSerializeConfig(unittest.TestCase):
    def test_section_general(self):
        config = Config()
        config.general.debug = True
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertIn("general", out_dict)
        self.assertEqual(True, out_dict["general"]["debug"])

    def test_section_lftp(self):
        config = Config()
        config.lftp.remote_address = "server.remote.com"
        config.lftp.remote_username = "user-on-remote-server"
        config.lftp.remote_port = 3456
        config.lftp.remote_path = "/remote/server/path"
        config.lftp.local_path = "/local/server/path"
        config.lftp.remote_path_to_scan_script = "/remote/server/path/to/script"
        config.lftp.num_max_parallel_downloads = 6
        config.lftp.num_max_parallel_files_per_download = 7
        config.lftp.num_max_connections_per_root_file = 2
        config.lftp.num_max_connections_per_dir_file = 3
        config.lftp.num_max_total_connections = 4
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertIn("lftp", out_dict)
        # SSH topology fields are redacted (CONF-03)
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_address"])
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_username"])
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_path"])
        # Non-sensitive fields are preserved
        self.assertEqual(3456, out_dict["lftp"]["remote_port"])
        self.assertEqual("/local/server/path", out_dict["lftp"]["local_path"])
        self.assertEqual("/remote/server/path/to/script", out_dict["lftp"]["remote_path_to_scan_script"])
        self.assertEqual(6, out_dict["lftp"]["num_max_parallel_downloads"])
        self.assertEqual(7, out_dict["lftp"]["num_max_parallel_files_per_download"])
        self.assertEqual(2, out_dict["lftp"]["num_max_connections_per_root_file"])
        self.assertEqual(3, out_dict["lftp"]["num_max_connections_per_dir_file"])
        self.assertEqual(4, out_dict["lftp"]["num_max_total_connections"])

    def test_section_controller(self):
        config = Config()
        config.controller.interval_ms_remote_scan = 1234
        config.controller.interval_ms_local_scan = 5678
        config.controller.interval_ms_downloading_scan = 9012
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertIn("controller", out_dict)
        self.assertEqual(1234, out_dict["controller"]["interval_ms_remote_scan"])
        self.assertEqual(5678, out_dict["controller"]["interval_ms_local_scan"])
        self.assertEqual(9012, out_dict["controller"]["interval_ms_downloading_scan"])

    def test_section_web(self):
        config = Config()
        config.web.port = 8080
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertIn("web", out_dict)
        self.assertEqual(8080, out_dict["web"]["port"])

    def test_section_autoqueue(self):
        config = Config()
        config.autoqueue.enabled = True
        config.autoqueue.patterns_only = False
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertIn("autoqueue", out_dict)
        self.assertEqual(True, out_dict["autoqueue"]["enabled"])
        self.assertEqual(False, out_dict["autoqueue"]["patterns_only"])

    def test_config_redacts_remote_password(self):
        config = Config()
        config.lftp.remote_password = "secret123"
        config.lftp.remote_address = "server.remote.com"
        config.lftp.remote_username = "user"
        config.lftp.remote_port = 22
        config.lftp.remote_path = "/remote/path"
        config.lftp.local_path = "/local/path"
        config.lftp.remote_path_to_scan_script = "/remote/scan"
        config.lftp.num_max_parallel_downloads = 1
        config.lftp.num_max_parallel_files_per_download = 1
        config.lftp.num_max_connections_per_root_file = 1
        config.lftp.num_max_connections_per_dir_file = 1
        config.lftp.num_max_total_connections = 0
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_password"])
        self.assertNotIn("secret123", out)

    def test_config_redacts_sonarr_api_key(self):
        config = Config()
        config.sonarr.enabled = True
        config.sonarr.sonarr_url = "http://sonarr.local"
        config.sonarr.sonarr_api_key = "sonarr-api-key-abc123"
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["sonarr"]["sonarr_api_key"])
        self.assertNotIn("sonarr-api-key-abc123", out)

    def test_config_redacts_radarr_api_key(self):
        config = Config()
        config.radarr.enabled = True
        config.radarr.radarr_url = "http://radarr.local"
        config.radarr.radarr_api_key = "radarr-api-key-xyz789"
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["radarr"]["radarr_api_key"])
        self.assertNotIn("radarr-api-key-xyz789", out)

    def test_config_redacts_webhook_secret(self):
        config = Config()
        config.general.webhook_secret = "super-secret-webhook-key"
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["general"]["webhook_secret"])
        self.assertNotIn("super-secret-webhook-key", out)

    def test_config_redacts_and_preserves_fields(self):
        config = Config()
        config.lftp.remote_address = "seedbox.example.com"
        config.lftp.remote_port = 2222
        config.lftp.remote_username = "myuser"
        config.lftp.remote_password = "should-be-redacted"
        config.lftp.remote_path = "/remote/path"
        config.lftp.local_path = "/local/path"
        config.lftp.remote_path_to_scan_script = "/remote/scan"
        config.lftp.num_max_parallel_downloads = 3
        config.lftp.num_max_parallel_files_per_download = 2
        config.lftp.num_max_connections_per_root_file = 1
        config.lftp.num_max_connections_per_dir_file = 1
        config.lftp.num_max_total_connections = 0
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        # SSH topology fields are redacted (CONF-03)
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_address"])
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_username"])
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_path"])
        # Non-sensitive field is preserved as-is
        self.assertEqual(2222, out_dict["lftp"]["remote_port"])
        # Sensitive field is redacted
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_password"])

    def test_config_redacts_remote_address(self):
        config = Config()
        config.lftp.remote_address = "seedbox.example.com"
        config.lftp.remote_username = "user"
        config.lftp.remote_password = "pass"
        config.lftp.remote_port = 22
        config.lftp.remote_path = "/remote/path"
        config.lftp.local_path = "/local/path"
        config.lftp.remote_path_to_scan_script = "/remote/scan"
        config.lftp.num_max_parallel_downloads = 1
        config.lftp.num_max_parallel_files_per_download = 1
        config.lftp.num_max_connections_per_root_file = 1
        config.lftp.num_max_connections_per_dir_file = 1
        config.lftp.num_max_total_connections = 0
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_address"])
        self.assertNotIn("seedbox.example.com", out)

    def test_config_redacts_remote_username(self):
        config = Config()
        config.lftp.remote_address = "server.example.com"
        config.lftp.remote_username = "sshuser"
        config.lftp.remote_password = "pass"
        config.lftp.remote_port = 22
        config.lftp.remote_path = "/remote/path"
        config.lftp.local_path = "/local/path"
        config.lftp.remote_path_to_scan_script = "/remote/scan"
        config.lftp.num_max_parallel_downloads = 1
        config.lftp.num_max_parallel_files_per_download = 1
        config.lftp.num_max_connections_per_root_file = 1
        config.lftp.num_max_connections_per_dir_file = 1
        config.lftp.num_max_total_connections = 0
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_username"])
        self.assertNotIn("sshuser", out)

    def test_config_redacts_remote_path(self):
        config = Config()
        config.lftp.remote_address = "server.example.com"
        config.lftp.remote_username = "user"
        config.lftp.remote_password = "pass"
        config.lftp.remote_port = 22
        config.lftp.remote_path = "/secret/seedbox/path"
        config.lftp.local_path = "/local/path"
        config.lftp.remote_path_to_scan_script = "/remote/scan"
        config.lftp.num_max_parallel_downloads = 1
        config.lftp.num_max_parallel_files_per_download = 1
        config.lftp.num_max_connections_per_root_file = 1
        config.lftp.num_max_connections_per_dir_file = 1
        config.lftp.num_max_total_connections = 0
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["lftp"]["remote_path"])
        self.assertNotIn("/secret/seedbox/path", out)

    def test_config_redacts_api_token(self):
        config = Config()
        config.general.api_token = "super-secret-token"
        out = SerializeConfig.config(config)
        out_dict = json.loads(out)
        self.assertEqual("**REDACTED**", out_dict["general"]["api_token"])
        self.assertNotIn("super-secret-token", out)
