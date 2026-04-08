# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest

from common import Localization


class TestLocalizationError(unittest.TestCase):

    def test_missing_file_string_exists(self):
        self.assertIsNotNone(Localization.Error.MISSING_FILE)

    def test_missing_file_format(self):
        self.assertEqual(
            "The file '/tmp/foo' doesn't exist.",
            Localization.Error.MISSING_FILE.format("/tmp/foo")
        )

    def test_remote_server_scan_string_exists(self):
        self.assertIsNotNone(Localization.Error.REMOTE_SERVER_SCAN)

    def test_remote_server_scan_format(self):
        self.assertEqual(
            "An error occurred while scanning the remote server: 'connection refused'.",
            Localization.Error.REMOTE_SERVER_SCAN.format("connection refused")
        )

    def test_remote_server_install_string_exists(self):
        self.assertIsNotNone(Localization.Error.REMOTE_SERVER_INSTALL)

    def test_remote_server_install_format(self):
        self.assertEqual(
            "An error occurred while installing scanner script to remote server: 'permission denied'.",
            Localization.Error.REMOTE_SERVER_INSTALL.format("permission denied")
        )

    def test_local_server_scan_string_exists(self):
        self.assertIsNotNone(Localization.Error.LOCAL_SERVER_SCAN)
        self.assertNotIn("{}", Localization.Error.LOCAL_SERVER_SCAN)

    def test_settings_incomplete_string_exists(self):
        self.assertIsNotNone(Localization.Error.SETTINGS_INCOMPLETE)
        self.assertNotIn("{}", Localization.Error.SETTINGS_INCOMPLETE)

    def test_all_strings_are_str_type(self):
        self.assertIsInstance(Localization.Error.MISSING_FILE, str)
        self.assertIsInstance(Localization.Error.REMOTE_SERVER_SCAN, str)
        self.assertIsInstance(Localization.Error.REMOTE_SERVER_INSTALL, str)
        self.assertIsInstance(Localization.Error.LOCAL_SERVER_SCAN, str)
        self.assertIsInstance(Localization.Error.SETTINGS_INCOMPLETE, str)
