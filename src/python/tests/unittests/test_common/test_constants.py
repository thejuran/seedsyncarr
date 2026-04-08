import unittest

from common import Constants


class TestConstants(unittest.TestCase):

    def test_service_name(self):
        self.assertEqual("seedsyncarr", Constants.SERVICE_NAME)
        self.assertIsInstance(Constants.SERVICE_NAME, str)

    def test_main_thread_sleep_interval(self):
        self.assertEqual(0.5, Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS)
        self.assertIsInstance(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS, float)

    def test_max_log_size_in_bytes(self):
        self.assertEqual(10 * 1024 * 1024, Constants.MAX_LOG_SIZE_IN_BYTES)
        self.assertEqual(10485760, Constants.MAX_LOG_SIZE_IN_BYTES)
        self.assertIsInstance(Constants.MAX_LOG_SIZE_IN_BYTES, int)

    def test_log_backup_count(self):
        self.assertEqual(10, Constants.LOG_BACKUP_COUNT)
        self.assertIsInstance(Constants.LOG_BACKUP_COUNT, int)

    def test_web_access_log_name(self):
        self.assertEqual("web_access", Constants.WEB_ACCESS_LOG_NAME)
        self.assertIsInstance(Constants.WEB_ACCESS_LOG_NAME, str)

    def test_min_persist_to_file_interval(self):
        self.assertEqual(30, Constants.MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS)
        self.assertIsInstance(Constants.MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS, int)

    def test_json_pretty_print_indent(self):
        self.assertEqual(4, Constants.JSON_PRETTY_PRINT_INDENT)
        self.assertIsInstance(Constants.JSON_PRETTY_PRINT_INDENT, int)

    def test_lftp_temp_file_suffix(self):
        self.assertEqual(".lftp", Constants.LFTP_TEMP_FILE_SUFFIX)
        self.assertIsInstance(Constants.LFTP_TEMP_FILE_SUFFIX, str)

    def test_constants_values_are_positive(self):
        self.assertTrue(Constants.MAIN_THREAD_SLEEP_INTERVAL_IN_SECS > 0)
        self.assertTrue(Constants.MAX_LOG_SIZE_IN_BYTES > 0)
        self.assertTrue(Constants.LOG_BACKUP_COUNT > 0)
        self.assertTrue(Constants.MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS > 0)
        self.assertTrue(Constants.JSON_PRETTY_PRINT_INDENT > 0)
