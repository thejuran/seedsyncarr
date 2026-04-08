import json
import unittest
from unittest.mock import patch
from logging import LogRecord

from web.handler.stream_log import CachedQueueLogHandler
from web.serialize import SerializeLogRecord


def create_log_record(created: float, msg: str) -> LogRecord:
    record = LogRecord(
        name=None,
        level=None,
        pathname=None,
        lineno=None,
        msg=msg,
        args=None,
        exc_info=None
    )
    record.created = created
    return record


class TestCachedQueueLogHandler(unittest.TestCase):
    @patch("web.handler.stream_log.time")
    def test_caches_new_records(self, mock_time_module):
        time_func = mock_time_module.time

        cache = CachedQueueLogHandler(history_size_in_ms=3000)

        # Set current time at 10000 ms
        time_func.return_value = 10.0

        # Create some records between 7000 ms - 10000 ms
        record1 = create_log_record(7.5, "record1")
        record2 = create_log_record(8.5, "record2")
        record3 = create_log_record(9.5, "record3")

        # Pass them to cache
        cache.emit(record1)
        cache.emit(record2)
        cache.emit(record3)

        # Get cached record, all of them should be there
        actual = cache.get_cached_records()
        self.assertEqual(3, len(actual))
        self.assertEqual("record1", actual[0].msg)
        self.assertEqual(7.5, actual[0].created)
        self.assertEqual("record2", actual[1].msg)
        self.assertEqual(8.5, actual[1].created)
        self.assertEqual("record3", actual[2].msg)
        self.assertEqual(9.5, actual[2].created)

    @patch("web.handler.stream_log.time")
    def test_prunes_old_records(self, mock_time_module):
        time_func = mock_time_module.time

        cache = CachedQueueLogHandler(history_size_in_ms=3000)

        # Set current time at 10000 ms
        time_func.return_value = 10.0

        # Create some records between 0 ms - 10000 ms
        record1 = create_log_record(0.5, "record1")
        record2 = create_log_record(5.5, "record2")
        record3 = create_log_record(7.5, "record3")
        record4 = create_log_record(9.5, "record4")

        # Pass them to cache
        cache.emit(record1)
        cache.emit(record2)
        cache.emit(record3)
        cache.emit(record4)

        # Get cached record, only newer than 7000ms should be there
        actual = cache.get_cached_records()
        self.assertEqual(2, len(actual))
        self.assertEqual("record3", actual[0].msg)
        self.assertEqual(7.5, actual[0].created)
        self.assertEqual("record4", actual[1].msg)
        self.assertEqual(9.5, actual[1].created)

    @patch("web.handler.stream_log.time")
    def test_prunes_old_records_at_get_time(self, mock_time_module):
        time_func = mock_time_module.time

        cache = CachedQueueLogHandler(history_size_in_ms=3000)

        # Set current time at 10000 ms
        time_func.return_value = 10.0

        # Create some records between 7000 ms - 10000 ms
        record1 = create_log_record(7.5, "record1")
        record2 = create_log_record(8.5, "record2")
        record3 = create_log_record(9.5, "record3")
        record4 = create_log_record(10.0, "record4")

        # Pass them to cache
        cache.emit(record1)
        cache.emit(record2)
        cache.emit(record3)
        cache.emit(record4)

        # Now set the current time to 12000 ms
        time_func.return_value = 12.0

        # Get cached record, only newer than 9000ms should be there
        actual = cache.get_cached_records()
        self.assertEqual(2, len(actual))
        self.assertEqual("record3", actual[0].msg)
        self.assertEqual(9.5, actual[0].created)
        self.assertEqual("record4", actual[1].msg)
        self.assertEqual(10.0, actual[1].created)

    @patch("web.handler.stream_log.time")
    def test_cache_can_be_disabled(self, mock_time_module):
        time_func = mock_time_module.time

        cache = CachedQueueLogHandler(history_size_in_ms=0)

        # Set current time at 10000 ms
        time_func.return_value = 10.0

        # Create some records in past and future
        record1 = create_log_record(7.5, "record1")
        record2 = create_log_record(10.0, "record2")
        record3 = create_log_record(11.5, "record3")

        # Pass them to cache
        cache.emit(record1)
        cache.emit(record2)
        cache.emit(record3)

        # Get cached record, should return nothing
        actual = cache.get_cached_records()
        self.assertEqual(0, len(actual))


def _parse_sse_message(sse_text: str) -> dict:
    """
    Parse an SSE message produced by SerializeLogRecord.record() and return
    the decoded JSON payload dict.  The SSE format is:

        event: log-record\ndata: {...}\n\n
    """
    for line in sse_text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[len("data:"):].strip())
    raise ValueError("No data line found in SSE message: {!r}".format(sse_text))


class TestSerializeLogRecordRedaction(unittest.TestCase):
    def _make_record(self, msg: str, exc_text: str = None) -> LogRecord:
        record = LogRecord(
            name="test.logger",
            level=20,  # INFO
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=None,
            exc_info=None,
        )
        record.exc_text = exc_text
        return record

    def test_redacts_lftp_password_from_log_message(self):
        """LFTP -u user,password argument: password portion is replaced."""
        msg = "command: lftp -p 22 -u remoteuser,secretpass123 sftp://host.example.com"
        record = self._make_record(msg)
        sse = SerializeLogRecord().record(record)
        payload = _parse_sse_message(sse)
        message = payload["message"]
        self.assertIn("-u remoteuser,**REDACTED**", message)
        self.assertNotIn("secretpass123", message)

    def test_redacts_password_equals_pattern(self):
        """Generic password=<value> pattern is replaced."""
        msg = "Login failed: password=mysecret"
        record = self._make_record(msg)
        sse = SerializeLogRecord().record(record)
        payload = _parse_sse_message(sse)
        message = payload["message"]
        self.assertIn("password=**REDACTED**", message)
        self.assertNotIn("mysecret", message)

    def test_preserves_normal_messages(self):
        """Normal log messages pass through without modification."""
        msg = "Downloading file.txt from remote server"
        record = self._make_record(msg)
        sse = SerializeLogRecord().record(record)
        payload = _parse_sse_message(sse)
        self.assertEqual(msg, payload["message"])

    def test_redacts_password_in_format_args(self):
        """Password passed as a format argument is caught via getMessage()."""
        record = LogRecord(
            name="test.logger", level=20, pathname="test.py", lineno=1,
            msg="connecting with -u user,%s", args=("secretpass123",), exc_info=None,
        )
        sse = SerializeLogRecord().record(record)
        payload = _parse_sse_message(sse)
        message = payload["message"]
        self.assertIn("**REDACTED**", message)
        self.assertNotIn("secretpass123", message)

    def test_redacts_password_in_exception_traceback(self):
        """Passwords embedded in exc_text are scrubbed before SSE output."""
        exc_text = (
            "Traceback (most recent call last):\n"
            "  File 'lftp.py', line 66, in connect\n"
            "    command: lftp -u admin,supersecretpass sftp://storage.box\n"
            "LftpError: connection refused"
        )
        record = self._make_record("LFTP connection error", exc_text=exc_text)
        sse = SerializeLogRecord().record(record)
        payload = _parse_sse_message(sse)
        exc_tb = payload["exc_tb"]
        self.assertIn("-u admin,**REDACTED**", exc_tb)
        self.assertNotIn("supersecretpass", exc_tb)
