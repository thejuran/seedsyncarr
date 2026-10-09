"""
Host-runnable contract tests for Lftp.status() error handling.

These mirror the status error-counter tests in
tests/integration/test_lftp/test_lftp_protocol.py, which need the Docker sshd
fixture and therefore only run in CI. Here pexpect is mocked and the REAL
LftpJobStatusParser and the REAL consecutive-error counter run, so the
contract is pinned on any host:

- a tolerated parse failure means "status unavailable" (None), never an empty
  job list ([]), because [] tells every consumer that all transfers are gone;
- the failure after MAX_CONSECUTIVE_STATUS_ERRORS escalates by raising, and
  keeps raising until a successful parse resets the counter;
- a genuinely empty `jobs -v` output is still a real empty list;
- a `jobs -v` that timed out is an incomplete observation and is also
  unavailable, whether its partial buffer is empty or happens to parse.
"""
import unittest
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pexpect

from lftp import lftp as lftp_mod
from lftp import LftpJobStatusParserError


# Malformed `jobs -v` block (final content line `bad string uh oh`); the real
# parser raises LftpJobStatusParserError on it.
_MALFORMED_JOBS_OUTPUT = """
        [0] queue (sftp://someone:@localhost)
        sftp://someone:@localhost/home/someone
        Now executing: [1] mirror -c /tmp/test_controllerw0sbqxe_/remote/ra /tmp/test_controllerw0sbqxe_/local/ -- 0/1.1k (0%)
        -[2] mirror -c /tmp/test_controllerw0sbqxe_/remote/rb /tmp/test_controllerw0sbqxe_/local/ -- 49/9.3k (0%)
        Commands queued:
        1.  pget -c "/tmp/test_controllerw0sbqxe_/remote/rc" -o "/tmp/test_controllerw0sbqxe_/local/"
        bad string uh oh
        """

# A valid `jobs -v` listing with exactly one running pget job.
_VALID_ONE_JOB_OUTPUT = """
        [0] queue (sftp://seedsyncarrtest:@localhost:22)
        sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
        Now executing: [1] pget -c /tmp/t/remote/A.rar -o /tmp/t/local/
        [1] pget -c /tmp/t/remote/A.rar -o /tmp/t/local/
        sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest
        `/tmp/t/remote/A.rar', got 100 of 1000 (10%)
        """

# A buffer that was cut off after the first job of a longer listing: the
# parser accepts it, but it is not a complete observation of lftp's jobs.
_PARTIAL_PARSEABLE_OUTPUT = _VALID_ONE_JOB_OUTPUT


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


class _TimedOut:
    """Script item: the `jobs -v` expect times out with `buffer` captured so far."""

    def __init__(self, buffer: str):
        self.buffer = buffer


def _make_lftp_with_scripted_process(script: list, sent_commands: Optional[List[str]] = None):
    """
    Construct an Lftp over a mocked pexpect process that drives the REAL
    Lftp.__run_command. Every sendline is recorded in `sent_commands`. When the
    last sent command is `jobs -v`, expect pops the next script item: a str
    completes with that output; a _TimedOut sets `before` to its buffer and
    raises pexpect.exceptions.TIMEOUT. Everything else completes with b"".
    """
    from lftp import Lftp
    if sent_commands is None:
        sent_commands = []
    remaining = list(script)

    mock_proc = MagicMock()
    mock_proc.isalive.return_value = True
    mock_proc.before = b""
    mock_proc.after = b""

    def _sendline(command):
        sent_commands.append(command)

    def _expect(pattern, timeout=None):
        if sent_commands and sent_commands[-1] == "jobs -v":
            item = remaining.pop(0)
            if isinstance(item, _TimedOut):
                mock_proc.before = item.buffer.encode()
                raise pexpect.exceptions.TIMEOUT("scripted")
            mock_proc.before = item.encode()
            return 0
        mock_proc.before = b""
        return 0

    mock_proc.sendline.side_effect = _sendline
    mock_proc.expect.side_effect = _expect

    with patch('pexpect.spawn') as mock_spawn:
        mock_spawn.return_value = mock_proc
        lftp = Lftp(
            address="localhost",
            port=22,
            user="testuser",
            password="testpass",
        )
    return lftp


def _script_run_command(outputs: list):
    """
    Return a replacement for Lftp.__run_command that pops the next scripted
    output for `jobs -v` and returns "" for any other command (property
    setters also go through __run_command).
    """
    remaining = list(outputs)

    def _run(cmd):
        if cmd == "jobs -v":
            return remaining.pop(0)
        return ""
    return _run


class TestLftpStatusBoundary(unittest.TestCase):

    def test_tolerated_parse_failures_report_unavailable_not_empty(self):
        """
        XFER-03: each tolerated parse failure must report the status as
        unavailable (None). Pre-fix: AssertionError, [] is returned.
        """
        lftp = _make_lftp_with_mocked_process()
        n = lftp_mod.MAX_CONSECUTIVE_STATUS_ERRORS
        with patch.object(lftp, "_Lftp__run_command",
                          side_effect=_script_run_command([_MALFORMED_JOBS_OUTPUT] * n)):
            for i in range(n):
                self.assertIsNone(lftp.status(), f"failure {i+1} must be unavailable (None), never []")

    def test_boundary_sequence_pinned_exactly(self):
        """
        XFER-03: tolerated failures -> None, the next failure raises, a success
        resets the counter, tolerated failures -> None again, and an empty
        output is a genuine []. Pre-fix: AssertionError at the first None check.
        """
        lftp = _make_lftp_with_mocked_process()
        n = lftp_mod.MAX_CONSECUTIVE_STATUS_ERRORS
        script = ([_MALFORMED_JOBS_OUTPUT] * (n + 1)
                  + [_VALID_ONE_JOB_OUTPUT]
                  + [_MALFORMED_JOBS_OUTPUT] * n
                  + [""])
        with patch.object(lftp, "_Lftp__run_command", side_effect=_script_run_command(script)):
            for i in range(n):
                self.assertIsNone(lftp.status(), f"failure {i+1} must be unavailable (None)")
            with self.assertRaises(LftpJobStatusParserError):
                lftp.status()
            statuses = lftp.status()
            self.assertIsNotNone(statuses)
            self.assertEqual(1, len(statuses))
            for i in range(n):
                self.assertIsNone(lftp.status(), f"failure {i+1} after reset must be unavailable (None)")
            self.assertEqual([], lftp.status())

    def test_empty_output_is_genuinely_empty_list(self):
        """XFER-03 preservation: an empty `jobs -v` is a real empty job list."""
        lftp = _make_lftp_with_mocked_process()
        with patch.object(lftp, "_Lftp__run_command", side_effect=_script_run_command([""])):
            self.assertEqual([], lftp.status())

    def test_escalation_does_not_reset_counter(self):
        """
        Preservation: after escalation, further failures keep raising until a
        successful parse resets the counter.
        """
        lftp = _make_lftp_with_mocked_process()
        n = lftp_mod.MAX_CONSECUTIVE_STATUS_ERRORS
        with patch.object(lftp, "_Lftp__run_command",
                          side_effect=_script_run_command([_MALFORMED_JOBS_OUTPUT] * (n + 2))):
            for _ in range(n):
                lftp.status()
            with self.assertRaises(LftpJobStatusParserError):
                lftp.status()
            with self.assertRaises(LftpJobStatusParserError):
                lftp.status()

    def test_timed_out_status_with_empty_buffer_is_unavailable(self):
        """
        XFER-02/XFER-03: `jobs -v` timed out with nothing captured. Pre-fix:
        AssertionError, the empty buffer parses to [].
        """
        lftp = _make_lftp_with_scripted_process([_TimedOut("")])
        self.assertIsNone(lftp.status(), "a timed-out jobs -v is an incomplete observation, not an empty job list")

    def test_timed_out_status_with_partial_parseable_buffer_is_unavailable(self):
        """
        XFER-02/XFER-03: `jobs -v` timed out after a parseable prefix of the
        listing was captured. Pre-fix: AssertionError, a truncated job list is
        returned.
        """
        lftp = _make_lftp_with_scripted_process([_TimedOut(_PARTIAL_PARSEABLE_OUTPUT)])
        self.assertIsNone(lftp.status(), "a timed-out jobs -v must not yield a truncated job list")
