import unittest
import json
import logging

from .test_serialize import parse_stream
from web.serialize import SerializeLogRecord


class TestSerializeLogRecord(unittest.TestCase):
    def test_event_names(self):
        serialize = SerializeLogRecord()
        logger = logging.getLogger()
        record = logger.makeRecord(
            name=None,
            level=None,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        self.assertEqual("log-record", out["event"])

    def test_record_time(self):
        serialize = SerializeLogRecord()
        logger = logging.getLogger()
        record = logger.makeRecord(
            name=None,
            level=None,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual(str(record.created), data["time"])

    def test_record_level_name(self):
        serialize = SerializeLogRecord()
        logger = logging.getLogger()

        record = logger.makeRecord(
            name=None,
            level=logging.DEBUG,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("DEBUG", data["level_name"])

        record = logger.makeRecord(
            name=None,
            level=logging.INFO,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("INFO", data["level_name"])

        record = logger.makeRecord(
            name=None,
            level=logging.WARNING,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("WARNING", data["level_name"])

        record = logger.makeRecord(
            name=None,
            level=logging.ERROR,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("ERROR", data["level_name"])

        record = logger.makeRecord(
            name=None,
            level=logging.CRITICAL,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("CRITICAL", data["level_name"])

    def test_record_logger_name(self):
        serialize = SerializeLogRecord()
        logger = logging.getLogger()
        record = logger.makeRecord(
            name="myloggername",
            level=None,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("myloggername", data["logger_name"])

    def test_record_message(self):
        serialize = SerializeLogRecord()
        logger = logging.getLogger()
        record = logger.makeRecord(
            name=None,
            level=None,
            fn=None,
            lno=None,
            msg="my logger msg",
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("my logger msg", data["message"])

    def test_record_exception_text(self):
        serialize = SerializeLogRecord()
        logger = logging.getLogger()

        # When there's exc_text already there
        record = logger.makeRecord(
            name=None,
            level=None,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        record.exc_text = "My traceback"
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("My traceback", data["exc_tb"])

        # When there's exc_info but no exc_text
        record = logger.makeRecord(
            name=None,
            level=None,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=(None, ValueError(), None),
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual("ValueError", data["exc_tb"])

        # When there's neither
        record = logger.makeRecord(
            name=None,
            level=None,
            fn=None,
            lno=None,
            msg=None,
            args=None,
            exc_info=None,
            func=None,
            sinfo=None
        )
        out = parse_stream(serialize.record(record))
        data = json.loads(out["data"])
        self.assertEqual(None, data["exc_tb"])


class TestRedactSensitive(unittest.TestCase):
    """
    Tests for SerializeLogRecord._redact_sensitive() — covers SSH topology
    redaction (LOG-01, LOG-02) and false-positive safety (LOG-03).

    _redact_sensitive() is a @staticmethod so it can be tested directly
    without constructing full LogRecord objects.
    """

    # ------------------------------------------------------------------ #
    # Redaction tests (LOG-01, LOG-02): these must show **REDACTED**       #
    # ------------------------------------------------------------------ #

    def test_redact_sftp_url(self):
        """LFTP sftp:// URL containing user@host must be redacted."""
        result = SerializeLogRecord._redact_sensitive(
            "Connecting to sftp://myuser@seedbox.example.com/downloads"
        )
        self.assertNotIn("myuser", result)
        self.assertNotIn("seedbox.example.com", result)
        self.assertIn("sftp://", result)  # protocol prefix preserved
        self.assertIn("**REDACTED**", result)

    def test_redact_ssh_command_args_user_at_host(self):
        """SSH command list with user@host standalone token must be redacted."""
        result = SerializeLogRecord._redact_sensitive(
            "Command: ['ssh', '-p', '22', 'myuser@seedbox.example.com', 'ls']"
        )
        self.assertNotIn("myuser@seedbox", result)
        self.assertIn("**REDACTED**@**REDACTED**", result)

    def test_redact_scp_user_at_host_colon_path(self):
        """SCP-style user@host:path destination token must be redacted."""
        result = SerializeLogRecord._redact_sensitive(
            "Command: ['scp', 'myuser@seedbox.example.com:/remote/path', '/local/path']"
        )
        self.assertNotIn("myuser@seedbox", result)
        self.assertIn("**REDACTED**@**REDACTED**", result)

    def test_redact_lftp_prompt(self):
        """LFTP shell prompt containing user@host must be redacted."""
        result = SerializeLogRecord._redact_sensitive(
            "lftp myuser@seedbox.example.com:~>"
        )
        self.assertNotIn("myuser@seedbox", result)
        self.assertIn("**REDACTED**@**REDACTED**", result)

    # ------------------------------------------------------------------ #
    # False-positive safety tests (LOG-03): must NOT redact                #
    # ------------------------------------------------------------------ #

    def test_no_redact_filename_with_at(self):
        """Filename with @ in the middle must not be redacted."""
        msg = "Downloading file@720p.mkv"
        result = SerializeLogRecord._redact_sensitive(msg)
        self.assertEqual(msg, result)

    def test_no_redact_filename_at_version(self):
        """Version-style filename with @ must not be redacted."""
        msg = "Processing release@1.0.tar.gz"
        result = SerializeLogRecord._redact_sensitive(msg)
        self.assertEqual(msg, result)

    def test_no_redact_embedded_at_in_path(self):
        """Path with @ mid-word must not be redacted."""
        msg = "/downloads/show@720p/file.mkv"
        result = SerializeLogRecord._redact_sensitive(msg)
        self.assertEqual(msg, result)

    # ------------------------------------------------------------------ #
    # Existing pattern preservation                                         #
    # ------------------------------------------------------------------ #

    def test_existing_password_redaction_preserved(self):
        """Existing LFTP -u password redaction must still work."""
        result = SerializeLogRecord._redact_sensitive("-u myuser,secretpass123")
        self.assertNotIn("secretpass123", result)
        self.assertIn("**REDACTED**", result)
