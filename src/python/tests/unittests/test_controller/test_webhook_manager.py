import unittest
from unittest.mock import MagicMock

from controller.webhook_manager import WebhookManager


class TestWebhookManager(unittest.TestCase):
    """Unit tests for WebhookManager."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.manager = WebhookManager(context=self.mock_context)
        # name_to_root: lowercased name -> root model file name
        self.name_to_root = {
            "file.a": "File.A",
            "file.b": "File.B",
            "file.c": "File.C",
        }

    def test_process_empty_queue_returns_empty(self):
        result = self.manager.process(self.name_to_root)
        self.assertEqual([], result)

    def test_enqueue_and_process_matching_file(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        result = self.manager.process(self.name_to_root)
        self.assertEqual([("File.A", "File.A")], result)

    def test_enqueue_and_process_no_match(self):
        self.manager.enqueue_import("Sonarr", "Unknown.File")
        result = self.manager.process(self.name_to_root)
        self.assertEqual([], result)

    def test_case_insensitive_matching(self):
        self.manager.enqueue_import("Sonarr", "file.a")
        result = self.manager.process(self.name_to_root)
        self.assertEqual([("File.A", "file.a")], result)

    def test_multiple_enqueues_processed_in_one_call(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.enqueue_import("Radarr", "File.B")
        result = self.manager.process(self.name_to_root)
        self.assertIn(("File.A", "File.A"), result)
        self.assertIn(("File.B", "File.B"), result)
        self.assertEqual(2, len(result))

    def test_queue_drained_after_process(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.process(self.name_to_root)
        # Second call should return empty
        result = self.manager.process(self.name_to_root)
        self.assertEqual([], result)

    def test_process_with_empty_model(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        result = self.manager.process({})
        self.assertEqual([], result)

    def test_enqueue_logs_info(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.logger.info.assert_called_with(
            "Sonarr webhook import enqueued: 'File.A'"
        )

    def test_matched_import_logs_info(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.process(self.name_to_root)
        self.manager.logger.info.assert_any_call(
            "Sonarr import detected: 'File.A' (matched SeedSyncarr file 'File.A')"
        )

    def test_unmatched_import_logs_warning(self):
        self.manager.enqueue_import("Sonarr", "Unknown.File")
        self.manager.process(self.name_to_root)
        self.manager.logger.warning.assert_any_call(
            "Sonarr webhook file 'Unknown.File' not found in SeedSyncarr model "
            "(checked 3 names including children)"
        )

    def test_child_file_matches_returns_root_name(self):
        """Webhook file matching a child file returns the root directory name."""
        name_to_root = {
            "showdir": "ShowDir",
            "episode.s01e01.mkv": "ShowDir",  # child mapped to root
        }
        self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
        result = self.manager.process(name_to_root)
        self.assertEqual([("ShowDir", "Episode.S01E01.mkv")], result)

    def test_child_file_match_logs_root_name(self):
        """Matched child file log shows the root model file name."""
        name_to_root = {
            "showdir": "ShowDir",
            "episode.s01e01.mkv": "ShowDir",
        }
        self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
        self.manager.process(name_to_root)
        self.manager.logger.info.assert_any_call(
            "Sonarr import detected: 'Episode.S01E01.mkv' (matched SeedSyncarr file 'ShowDir')"
        )

    def test_child_file_match_returns_root_and_child_tuple(self):
        """When webhook file matches a child basename, process() returns (root, child) tuple with child != root."""
        name_to_root = {
            "showdir": "ShowDir",
            "episode.s01e01.mkv": "ShowDir",  # child mapped to root
        }
        self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
        result = self.manager.process(name_to_root)
        self.assertEqual(1, len(result))
        root_name, matched_name = result[0]
        self.assertEqual("ShowDir", root_name)
        self.assertEqual("Episode.S01E01.mkv", matched_name)
        self.assertNotEqual(root_name, matched_name)

    # --- CWE-117 log-injection sanitization tests (Plan 101-04) ---

    def test_enqueue_sanitizes_newlines_in_log(self):
        """CRLF in webhook file_name must be escaped to \\r\\n tokens in log output (CWE-117)."""
        crlf_name = "File.A\r\ninjected"
        self.manager.enqueue_import("Sonarr", crlf_name)
        # Retrieve the actual call arg logged by info
        call_args = self.manager.logger.info.call_args_list
        self.assertTrue(call_args, "Expected at least one logger.info call")
        logged_msg = call_args[-1][0][0]
        # Must not contain a literal CR or LF
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in log output")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in log output")
        # Must contain the escaped token forms
        self.assertIn("\\r", logged_msg, "Escaped \\r token must appear in log output")
        self.assertIn("\\n", logged_msg, "Escaped \\n token must appear in log output")

    def test_enqueue_sanitizes_escape_char_in_log(self):
        """ESC byte (0x1b) in webhook file_name must be escaped to \\x1b in log output (CWE-117)."""
        esc_name = "File.A\x1binjected"
        self.manager.enqueue_import("Sonarr", esc_name)
        call_args = self.manager.logger.info.call_args_list
        self.assertTrue(call_args, "Expected at least one logger.info call")
        logged_msg = call_args[-1][0][0]
        # Must not contain a raw 0x1b byte
        self.assertNotIn("\x1b", logged_msg, "Raw ESC byte must not appear in log output")
        # Must contain the escaped hex form
        self.assertIn("\\x1b", logged_msg, "Escaped \\x1b must appear in log output")

    def test_queue_value_unchanged_with_newline(self):
        """file_name with embedded newline matching a model entry: returned matched tuple preserves RAW value."""
        # Map the lowercased version of the CRLF name to a root
        raw_name = "file.a\r\n"
        name_to_root_with_crlf = {raw_name.lower(): "File.A"}
        self.manager.enqueue_import("Sonarr", raw_name)
        result = self.manager.process(name_to_root_with_crlf)
        self.assertEqual(1, len(result), "Injection-bearing file name should match the model entry")
        root_name, matched_name = result[0]
        self.assertEqual("File.A", root_name)
        # matched_name must be the RAW value, not the sanitized log value
        self.assertEqual(raw_name, matched_name, "Returned matched_name must be the raw (unsanitized) value")
