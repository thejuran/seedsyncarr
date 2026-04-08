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
        self.assertEqual(["File.A"], result)

    def test_enqueue_and_process_no_match(self):
        self.manager.enqueue_import("Sonarr", "Unknown.File")
        result = self.manager.process(self.name_to_root)
        self.assertEqual([], result)

    def test_case_insensitive_matching(self):
        self.manager.enqueue_import("Sonarr", "file.a")
        result = self.manager.process(self.name_to_root)
        self.assertEqual(["File.A"], result)

    def test_multiple_enqueues_processed_in_one_call(self):
        self.manager.enqueue_import("Sonarr", "File.A")
        self.manager.enqueue_import("Radarr", "File.B")
        result = self.manager.process(self.name_to_root)
        self.assertIn("File.A", result)
        self.assertIn("File.B", result)
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
        self.assertEqual(["ShowDir"], result)

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
