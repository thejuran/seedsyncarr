"""
Tests for CWE-117 log-injection sanitization in lftp.py.

These tests pin:
- kill() job-name log sites (lines 356/362/365): escaped in log, raw name used for matching
- __run_command output-diagnostic log sites (lines 126/129/144/147/148): escaped in log,
  raw output returned from __run_command unchanged

This is a focused test module that avoids the full pexpect-heavy Lftp integration suite.
"""
import logging
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from lftp import LftpJobStatus


CRLF_NAME = "torrent\r\nINJECTED_LINE name"
CRLF_OUTPUT = "some lftp output\r\nforged line\r\nmore output"


def _make_scanner(name: str, state: LftpJobStatus.State, job_id: int) -> LftpJobStatus:
    """Build a minimal LftpJobStatus stub for kill() testing."""
    status = LftpJobStatus(
        job_id=job_id,
        job_type=LftpJobStatus.Type.MIRROR,
        state=state,
        name=name,
        flags="-c",
    )
    return status


def _make_lftp_with_mocked_process():
    """
    Construct an Lftp instance with all pexpect and SSH machinery mocked so
    we can call methods directly without a running lftp process.
    """
    from lftp import Lftp
    with patch('pexpect.spawn') as mock_spawn:
        mock_proc = MagicMock()
        mock_proc.isalive.return_value = True
        mock_proc.before = b""
        mock_proc.after = b""
        mock_proc.expect.return_value = 0
        mock_spawn.return_value = mock_proc

        # Construct; __init__ calls __setup which calls __run_command internally.
        lftp = Lftp(
            address="localhost",
            port=22,
            user="testuser",
            password="testpass",
        )
    return lftp


class TestKillLogSanitization(unittest.TestCase):
    """
    Tests for kill() log-injection sanitization at lines 356/362/365.
    """

    def _make_lftp(self):
        return _make_lftp_with_mocked_process()

    def test_kill_failed_log_sanitized(self):
        """
        kill() with a job name containing CRLF, where status() returns no match.
        The "Kill failed to find job" debug log must contain no literal newline from
        the injected name — it must be escaped.
        """
        lftp = self._make_lftp()
        # status() returns an empty list — no match found
        lftp.status = MagicMock(return_value=[])

        with self.assertLogs("Lftp", level="DEBUG") as cm:
            result = lftp.kill(CRLF_NAME)

        self.assertFalse(result)
        # The log output must NOT contain a literal CR or LF from the injected name
        log_output = "\n".join(cm.output)
        # The log line containing "Kill failed" must be present
        kill_failed_lines = [line for line in cm.output if "Kill failed to find job" in line]
        self.assertEqual(1, len(kill_failed_lines), "Expected exactly one 'Kill failed' log line")
        kill_line = kill_failed_lines[0]
        # No literal \r\n injection allowed (the log handler output may add real newlines between
        # record entries — we check the message content itself)
        self.assertNotIn("INJECTED_LINE", kill_line,
                         "Raw CRLF injection must not appear verbatim in log")
        # The escaped form should be present
        self.assertIn(r"\r", kill_line)
        self.assertIn(r"\n", kill_line)

    def test_kill_running_log_sanitized(self):
        """
        kill() with a CRLF-bearing job name that matches a RUNNING stub status.
        The "Killing running job" debug log must be escaped.
        """
        lftp = self._make_lftp()
        running_status = _make_scanner(CRLF_NAME, LftpJobStatus.State.RUNNING, job_id=42)
        lftp.status = MagicMock(return_value=[running_status])

        # __run_command will be called for "kill 42" — mock it out
        lftp._Lftp__run_command = MagicMock(return_value="")

        with self.assertLogs("Lftp", level="DEBUG") as cm:
            result = lftp.kill(CRLF_NAME)

        self.assertTrue(result)
        killing_lines = [line for line in cm.output if "Killing running job" in line]
        self.assertEqual(1, len(killing_lines), "Expected exactly one 'Killing running job' log line")
        kill_line = killing_lines[0]
        self.assertNotIn("INJECTED_LINE", kill_line,
                         "Raw CRLF injection must not appear verbatim in log")
        self.assertIn(r"\r", kill_line)
        self.assertIn(r"\n", kill_line)

    def test_kill_name_match_uses_raw_name(self):
        """
        status.name == name comparison must use the raw name (not the sanitized version).
        A status whose name equals the raw CRLF-bearing string is found.
        """
        lftp = self._make_lftp()
        # The status name is the raw CRLF-bearing name
        running_status = _make_scanner(CRLF_NAME, LftpJobStatus.State.RUNNING, job_id=7)
        lftp.status = MagicMock(return_value=[running_status])
        lftp._Lftp__run_command = MagicMock(return_value="")

        result = lftp.kill(CRLF_NAME)
        # The job was found — matching used the raw name correctly
        self.assertTrue(result)
        # __run_command was called with "kill 7" (the raw job id)
        lftp._Lftp__run_command.assert_called_once_with("kill 7")

    def test_run_command_output_log_sanitized(self):
        """
        __run_command with CRLF-bearing pexpect output: the "out (... bytes)" debug log
        must be escaped, but the value RETURNED by __run_command is the RAW unsanitized output.
        """
        lftp = self._make_lftp()
        proc = lftp._Lftp__process
        # Enable verbose logging so the out/after log lines fire
        lftp.set_verbose_logging(True)

        raw_out = CRLF_OUTPUT
        # before holds the raw bytes of the output
        proc.before = raw_out.encode('utf-8')
        proc.after = b"lftp testuser@localhost:~> "
        proc.expect.return_value = 0

        with self.assertLogs("Lftp", level="DEBUG") as cm:
            returned = lftp._Lftp__run_command("jobs -v")

        # The returned value must be the raw (unsanitized) stripped output
        self.assertEqual(raw_out.strip(), returned,
                         "Returned output must be the raw unsanitized value")

        # The debug log lines must have escaped versions
        out_lines = [line for line in cm.output if "out (" in line and "bytes)" in line]
        self.assertGreater(len(out_lines), 0, "Expected at least one 'out (N bytes)' log line")
        out_line = out_lines[0]
        self.assertNotIn("INJECTED_LINE", out_line,
                         "Raw CRLF injection must not appear verbatim in log")
        self.assertIn(r"\r", out_line)
        self.assertIn(r"\n", out_line)


if __name__ == "__main__":
    unittest.main()
