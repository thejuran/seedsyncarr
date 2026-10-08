import unittest
from unittest.mock import MagicMock

from controller.webhook_manager import WebhookManager


def _lookup(*entries):
    """
    Build the process() lookup from (basename, path, root) triples:
    lowercased basename -> {case-preserving relative path -> root name}.
    """
    result = {}
    for basename, path, root in entries:
        result.setdefault(basename.lower(), {})[path] = root
    return result


class TestWebhookManager(unittest.TestCase):
    """Unit tests for WebhookManager."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.manager = WebhookManager(context=self.mock_context)
        # name_to_paths: lowercased basename -> {path -> root model file name}
        self.name_to_paths = _lookup(
            ("File.A", "File.A", "File.A"),
            ("File.B", "File.B", "File.B"),
            ("File.C", "File.C", "File.C"),
        )

    def test_process_empty_queue_returns_empty(self):
        result = self.manager.process(self.name_to_paths)
        self.assertEqual([], result)

    def test_enqueue_and_process_matching_file(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        result = self.manager.process(self.name_to_paths)
        self.assertEqual([("File.A", "File.A")], result)

    def test_enqueue_and_process_no_match(self):
        self.manager.enqueue_import("Sonarr", "Unknown.File")
        result = self.manager.process(self.name_to_paths)
        self.assertEqual([], result)

    def test_case_insensitive_matching(self):
        self.manager.enqueue_import("Sonarr", "file.a")
        result = self.manager.process(self.name_to_paths)
        self.assertEqual([("File.A", "file.a")], result)

    def test_multiple_enqueues_processed_in_one_call(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.enqueue_import("Radarr", "File.B")
        result = self.manager.process(self.name_to_paths)
        self.assertIn(("File.A", "File.A"), result)
        self.assertIn(("File.B", "File.B"), result)
        self.assertEqual(2, len(result))

    def test_queue_drained_after_process(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.process(self.name_to_paths)
        # Second call should return empty
        result = self.manager.process(self.name_to_paths)
        self.assertEqual([], result)

    def test_process_with_empty_model(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        result = self.manager.process({})
        self.assertEqual([], result)

    def test_enqueue_logs_info_with_provenance(self):
        self.manager.enqueue_import(
            "Sonarr", "File.A",
            provenance="eventType=Download, episodeFile.sourcePath"
        )
        self.manager.logger.info.assert_called_with(
            "Sonarr webhook import enqueued: 'File.A' "
            "(eventType=Download, episodeFile.sourcePath)"
        )

    def test_matched_import_logs_info_with_provenance(self):
        self.manager.enqueue_import(
            "Sonarr", "File.A",
            provenance="eventType=Download, episodeFile.sourcePath"
        )
        self.manager.process(self.name_to_paths)
        self.manager.logger.info.assert_any_call(
            "Sonarr import detected: 'File.A' (matched SeedSyncarr file 'File.A'; "
            "eventType=Download, episodeFile.sourcePath)"
        )

    def test_unmatched_import_logs_warning(self):
        self.manager.enqueue_import("Sonarr", "Unknown.File")
        self.manager.process(self.name_to_paths)
        self.manager.logger.warning.assert_any_call(
            "Sonarr webhook file 'Unknown.File' not found in SeedSyncarr model "
            "(checked 3 names including children)"
        )

    def test_child_file_matches_returns_root_name(self):
        """Webhook file matching a child file returns the root directory name."""
        name_to_paths = _lookup(
            ("ShowDir", "ShowDir", "ShowDir"),
            ("Episode.S01E01.mkv", "ShowDir/Episode.S01E01.mkv", "ShowDir"),  # child mapped to root
        )
        self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
        result = self.manager.process(name_to_paths)
        self.assertEqual([("ShowDir", "Episode.S01E01.mkv")], result)

    def test_child_file_match_logs_root_name(self):
        """Matched child file log shows the root model file name."""
        name_to_paths = _lookup(
            ("ShowDir", "ShowDir", "ShowDir"),
            ("Episode.S01E01.mkv", "ShowDir/Episode.S01E01.mkv", "ShowDir"),  # child mapped to root
        )
        self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
        self.manager.process(name_to_paths)
        self.manager.logger.info.assert_any_call(
            "Sonarr import detected: 'Episode.S01E01.mkv' (matched SeedSyncarr file 'ShowDir'; )"
        )

    def test_child_file_match_returns_root_and_child_tuple(self):
        """When webhook file matches a child basename, process() returns (root, child) tuple with child != root."""
        name_to_paths = _lookup(
            ("ShowDir", "ShowDir", "ShowDir"),
            ("Episode.S01E01.mkv", "ShowDir/Episode.S01E01.mkv", "ShowDir"),  # child mapped to root
        )
        self.manager.enqueue_import("Sonarr", "Episode.S01E01.mkv")
        result = self.manager.process(name_to_paths)
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
        name_to_paths_with_crlf = {raw_name.lower(): {"File.A": "File.A"}}
        self.manager.enqueue_import("Sonarr", raw_name)
        result = self.manager.process(name_to_paths_with_crlf)
        self.assertEqual(1, len(result), "Injection-bearing file name should match the model entry")
        root_name, matched_name = result[0]
        self.assertEqual("File.A", root_name)
        # matched_name must be the RAW value, not the sanitized log value
        self.assertEqual(raw_name, matched_name, "Returned matched_name must be the raw (unsanitized) value")

    # --- Ambiguous-name rejection tests ---

    def _import_detected_info_calls(self):
        return [
            c for c in self.manager.logger.info.call_args_list
            if "import detected" in c[0][0]
        ]

    def test_ambiguous_name_across_roots_is_rejected_with_one_warning(self):
        """D-03/D-08: a basename in two releases returns nothing and logs one warning."""
        lookup = _lookup(
            ("sample.mkv", "Rel.A/sample.mkv", "Rel.A"),
            ("sample.mkv", "Rel.B/sample.mkv", "Rel.B"),
        )
        self.manager.enqueue_import("Sonarr", "sample.mkv")
        result = self.manager.process(lookup)
        self.assertEqual([], result)
        self.assertEqual(1, self.manager.logger.warning.call_count)
        msg = self.manager.logger.warning.call_args[0][0]
        self.assertIn("'sample.mkv'", msg)
        self.assertIn("Rel.A", msg)
        self.assertIn("Rel.B", msg)
        self.assertIn("ambiguous", msg)
        self.assertIn("no import credit or automatic cleanup authorized", msg)
        self.assertEqual([], self._import_detected_info_calls())

    def test_ambiguous_name_within_one_root_lists_both_paths(self):
        """D-03/D-08: two paths in one release are ambiguous; the single root is listed once."""
        lookup = _lookup(
            ("movie.mkv", "Pack/Disc1/movie.mkv", "Pack"),
            ("movie.mkv", "Pack/Disc2/movie.mkv", "Pack"),
        )
        self.manager.enqueue_import("Radarr", "movie.mkv")
        result = self.manager.process(lookup)
        self.assertEqual([], result)
        self.assertEqual(1, self.manager.logger.warning.call_count)
        msg = self.manager.logger.warning.call_args[0][0]
        self.assertIn("Pack/Disc1/movie.mkv", msg)
        self.assertIn("Pack/Disc2/movie.mkv", msg)
        self.assertIn("['Pack']", msg)
        self.assertIn("ambiguous", msg)

    def test_single_path_in_lookup_is_a_match(self):
        """D-02: one distinct path (however often referenced) is an ordinary match."""
        lookup = _lookup(
            ("ep.a.mkv", "Rel.A/ep.a.mkv", "Rel.A"),
            ("ep.a.mkv", "Rel.A/ep.a.mkv", "Rel.A"),
        )
        self.manager.enqueue_import("Sonarr", "ep.a.mkv")
        result = self.manager.process(lookup)
        self.assertEqual([("Rel.A", "ep.a.mkv")], result)
        self.manager.logger.warning.assert_not_called()

    def test_ambiguous_warning_sanitizes_crlf_in_name_roots_and_paths(self):
        """D-09: webhook name, roots and paths are all escaped in the ambiguity warning (CWE-117)."""
        raw_name = "sample.mkv\r\nX"
        lookup = {
            raw_name.lower(): {
                "Rel\r\nA/sample.mkv\r\nX": "Rel\r\nA",
                "Rel.B/sample.mkv\r\nX": "Rel.B",
            }
        }
        self.manager.enqueue_import("Sonarr", raw_name, provenance="p\r\nq")
        result = self.manager.process(lookup)
        self.assertEqual([], result)
        call_args = self.manager.logger.warning.call_args_list
        self.assertTrue(call_args, "Expected at least one logger.warning call")
        logged_msg = call_args[-1][0][0]
        self.assertNotIn("\n", logged_msg, "Literal LF must not appear in log output")
        self.assertNotIn("\r", logged_msg, "Literal CR must not appear in log output")
        self.assertIn("\\r", logged_msg, "Escaped \\r token must appear in log output")
        self.assertIn("\\n", logged_msg, "Escaped \\n token must appear in log output")
        self.assertIn("Rel\\r\\nA", logged_msg)

    def test_ambiguous_warning_caps_path_list(self):
        """D-08: the path list is capped at 10 with a (+N more) suffix."""
        paths = ["Pack/Disc{:02d}/movie.mkv".format(i) for i in range(12)]
        lookup = {"movie.mkv": {p: "Pack" for p in paths}}
        self.manager.enqueue_import("Radarr", "movie.mkv")
        result = self.manager.process(lookup)
        self.assertEqual([], result)
        msg = self.manager.logger.warning.call_args[0][0]
        self.assertIn("(+2 more)", msg)
        self.assertEqual(10, msg.count("Pack/Disc"))
        self.assertIn("matches 12 distinct", msg)

    def test_matched_import_log_sanitizes_root_name(self):
        """The one-path INFO line escapes a control-char-bearing root name (CWE-117)."""
        lookup = {"file.a": {"Root\r\nX": "Root\r\nX"}}
        self.manager.enqueue_import("Sonarr", "File.A")
        result = self.manager.process(lookup)
        self.assertEqual([("Root\r\nX", "File.A")], result)
        calls = self._import_detected_info_calls()
        self.assertEqual(1, len(calls))
        logged_msg = calls[0][0][0]
        self.assertNotIn("\n", logged_msg)
        self.assertNotIn("\r", logged_msg)
        self.assertIn("Root\\r\\nX", logged_msg)
