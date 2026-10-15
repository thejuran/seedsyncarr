"""
Regression tests for LFTP command-stream resynchronization after a timeout.

Incident class (backlog 999.2, raised by the codex adversarial review of the
`jobs -v` timeout handling): all lftp commands share one pexpect pty stream.
When a command's `expect` times out, lftp's prompt for that command still
arrives later. Without resynchronization that late, stale prompt satisfies the
NEXT command's `expect`, so the next `jobs -v` returns empty output that parses
as `[]`, which every consumer reads as "lftp has no jobs" and which clears
observed and submitted-transfer protection.

These tests drive the REAL Lftp.__run_command over a fake pty byte buffer
(`_FakeStream`) that echoes each sent line, releases scripted output, and only
satisfies `expect` from what is actually in the buffer, exactly like pexpect.

`test_stale_prompt_after_timeout_never_yields_empty_status` fails with an
AssertionError against an Lftp that does not resynchronize after a timeout.
"""
import re
import unittest
from typing import Dict, List, Optional
from unittest.mock import patch

import pexpect

from lftp import Lftp, LftpError


_PROMPT = b"lftp testuser@localhost:~> "
_SYNC_PREFIX = "echo SEEDSYNCARR-SYNC-"
_SYNC_LINE_RE = re.compile(r'^echo SEEDSYNCARR-SYNC-"([0-9a-f]+)"-END$')

# A valid `jobs -v` listing with exactly one running pget job (same fixture as
# test_lftp_status_contract._VALID_ONE_JOB_OUTPUT).
_VALID_ONE_JOB_OUTPUT = (
    b"[0] queue (sftp://seedsyncarrtest:@localhost:22)\r\n"
    b"sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest\r\n"
    b"Now executing: [1] pget -c /tmp/t/remote/A.rar -o /tmp/t/local/\r\n"
    b"[1] pget -c /tmp/t/remote/A.rar -o /tmp/t/local/\r\n"
    b"sftp://seedsyncarrtest:@localhost:22/home/seedsyncarrtest\r\n"
    b"`/tmp/t/remote/A.rar', got 100 of 1000 (10%)\r\n"
)

# Sync responses for the sentinel `echo` command.
SYNC_OK = "ok"                    # lftp prints the unquoted marker, then a prompt
SYNC_TIMEOUT = "timeout"          # nothing after the tty echo (lftp still wedged)
SYNC_PROMPT_ONLY = "prompt_only"  # a prompt arrives but no unquoted marker


class _FakeStream:
    """
    Byte buffer emulating a pty. sendline() appends the tty echo of the line,
    then releases that command's next scripted chunk (or a fresh prompt when the
    command is not scripted). expect() regex-searches the buffer and consumes
    through the match; on no match it leaves the buffer intact, sets `before`
    to it, and raises pexpect.exceptions.TIMEOUT.
    """

    def __init__(self):
        # lftp prints a prompt once it has connected; the ctor expects it.
        self.buf = _PROMPT
        self.before = b""
        self.after = b""
        self.sent: List[str] = []
        # command -> list of scripted chunks; None means "no output yet" (timeout)
        self.responses: Dict[str, List[Optional[bytes]]] = {}
        # successive behaviours of the sentinel echo command
        self.sync_behaviours: List[str] = []

    def isalive(self):
        return True

    def close(self, force=False):
        self.closed_force = force

    def inject(self, data: bytes):
        """Append late output (e.g. a delayed stale prompt) between commands."""
        self.buf += data

    def sendline(self, s: str):
        self.sent.append(s)
        self.buf += s.encode() + b"\r\n"  # tty echo, quotes included
        sync = _SYNC_LINE_RE.match(s)
        if sync:
            behaviour = self.sync_behaviours.pop(0) if self.sync_behaviours else SYNC_OK
            if behaviour == SYNC_OK:
                # lftp's echo performs quote removal on its argument
                self.buf += "SEEDSYNCARR-SYNC-{}-END\r\n".format(sync.group(1)).encode() + _PROMPT
            elif behaviour == SYNC_PROMPT_ONLY:
                self.buf += _PROMPT
            return
        queue = self.responses.get(s)
        if queue:
            chunk = queue.pop(0)
            if chunk is not None:
                self.buf += chunk
            return
        self.buf += _PROMPT

    def expect(self, pattern, timeout=None):
        rx = re.compile(pattern if isinstance(pattern, bytes) else pattern.encode())
        m = rx.search(self.buf)
        if not m:
            self.before = self.buf
            self.after = pexpect.exceptions.TIMEOUT
            raise pexpect.exceptions.TIMEOUT("fake stream: no match for {!r}".format(pattern))
        self.before, self.after, self.buf = self.buf[:m.start()], m.group(0), self.buf[m.end():]
        return 0

    def sync_nonces(self) -> List[str]:
        return [m.group(1) for m in (_SYNC_LINE_RE.match(s) for s in self.sent) if m]


def _make_lftp(stream: _FakeStream) -> Lftp:
    with patch('pexpect.spawn') as mock_spawn:
        mock_spawn.return_value = stream
        lftp = Lftp(
            address="localhost",
            port=22,
            user="testuser",
            password="testpass",
        )
    return lftp


class TestLftpResync(unittest.TestCase):
    def test_stale_prompt_after_timeout_never_yields_empty_status(self):
        stream = _FakeStream()
        lftp = _make_lftp(stream)
        stream.responses["jobs -v"] = [
            None,                                  # #1: lftp is wedged, no prompt
            _VALID_ONE_JOB_OUTPUT + _PROMPT,       # #2: the real listing
        ]

        self.assertIsNone(lftp.status())

        # The prompt of the timed-out `jobs -v` arrives late, before the next call.
        stream.inject(_PROMPT)

        statuses = lftp.status()
        self.assertNotEqual([], statuses,
                            "a stale prompt from a timed-out command became a trusted empty job list")
        self.assertIsNotNone(statuses)
        self.assertEqual(1, len(statuses))
        self.assertEqual("A.rar", statuses[0].name)
        # The boundary was proven by exactly one sentinel round-trip.
        self.assertEqual(1, len(stream.sync_nonces()))

    def test_unsynced_resync_failure_keeps_status_unavailable_and_queue_raises(self):
        stream = _FakeStream()
        lftp = _make_lftp(stream)
        stream.responses["jobs -v"] = [None, None, None]
        stream.sync_behaviours = [SYNC_TIMEOUT, SYNC_TIMEOUT, SYNC_TIMEOUT]

        self.assertIsNone(lftp.status())  # the original timeout
        self.assertIsNone(lftp.status())  # resync fails: still unavailable, never []
        self.assertEqual(0, lftp._Lftp__consecutive_status_errors)

        with self.assertRaises(LftpError) as ctx:
            lftp.queue("x", False)
        self.assertIn("not synchronized", str(ctx.exception))
        # No queue command reached lftp while the stream was unsynchronized.
        self.assertFalse(any(s.startswith("queue ") for s in stream.sent))

    def test_exit_force_closes_after_command_timeout_and_failed_resync(self):
        stream = _FakeStream()
        lftp = _make_lftp(stream)
        stream.responses["jobs -v"] = [None]
        stream.sync_behaviours = [SYNC_TIMEOUT, SYNC_TIMEOUT]

        self.assertIsNone(lftp.status())  # the original command timeout
        self.assertIsNone(lftp.status())  # a failed resync

        with self.assertRaises(LftpError):
            lftp.exit()  # kill_all cannot resync, but the process is still closed
        self.assertTrue(getattr(stream, "closed_force", False))

    def test_exit_force_closes_after_command_timeout(self):
        stream = _FakeStream()
        lftp = _make_lftp(stream)
        stream.responses["jobs -v"] = [None]
        stream.sync_behaviours = [SYNC_TIMEOUT]

        self.assertIsNone(lftp.status())  # the original command timeout

        with self.assertRaises(LftpError):
            lftp.exit()  # kill_all's resync attempt fails
        self.assertTrue(getattr(stream, "closed_force", False))

    def test_resync_marker_ignores_tty_echo(self):
        stream = _FakeStream()
        lftp = _make_lftp(stream)
        stream.responses["jobs -v"] = [None, _VALID_ONE_JOB_OUTPUT + _PROMPT]
        # First attempt: the quoted tty echo and a prompt arrive, but no unquoted
        # marker. The echo alone must not prove the boundary.
        stream.sync_behaviours = [SYNC_PROMPT_ONLY, SYNC_OK]

        self.assertIsNone(lftp.status())   # the original timeout
        self.assertIsNone(lftp.status())   # echo-only attempt: still unsynchronized
        self.assertEqual(1, len(stream.sync_nonces()))
        self.assertEqual(1, stream.sent.count("jobs -v"),
                         "jobs -v must not be sent before a sentinel round-trip succeeds")

        statuses = lftp.status()           # unquoted marker + prompt: synchronized
        self.assertIsNotNone(statuses)
        self.assertEqual(1, len(statuses))
        self.assertEqual(2, len(stream.sync_nonces()))

    def test_resync_uses_fresh_nonce_each_attempt(self):
        stream = _FakeStream()
        lftp = _make_lftp(stream)
        stream.responses["jobs -v"] = [None]
        stream.sync_behaviours = [SYNC_TIMEOUT, SYNC_TIMEOUT]

        self.assertIsNone(lftp.status())
        self.assertIsNone(lftp.status())
        self.assertIsNone(lftp.status())

        nonces = stream.sync_nonces()
        self.assertEqual(2, len(nonces))
        self.assertNotEqual(nonces[0], nonces[1])
        for s in stream.sent:
            if s.startswith(_SYNC_PREFIX):
                self.assertRegex(s, _SYNC_LINE_RE)


if __name__ == "__main__":
    unittest.main()
