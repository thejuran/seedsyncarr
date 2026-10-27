"""
Regression tests for GAP-2 (D-01, lftp half): a bounded process-group SIGKILL
and reap fallback in Lftp.exit() when pexpect's own close(force=True) fails.

Incident class: on the gap build (123-12), both active-transfer restarts
(A1, A2) logged `Error stopping lftp during controller exit` /
`PtyProcessError: Could not terminate the child.` 1.80s and 1.65s after
SIGTERM. ptyprocess raises this only when the lftp pid is still unreaped 0.1s
after its own SIGKILL, and never reaps it afterwards. Idle restarts never hit
this path.

These tests drive the REAL Lftp.exit() over a deterministic fake pexpect
spawn (`_FakeLftpProcess`), a fake monotonic clock, a fake waiter (no real
sleep) and a fake process-group killer (no real kill syscall, no real
signals sent). No real processes and no real sleeps are used anywhere in
this file.

What each test pins:
- test_idle_close_succeeds_no_poll_no_signal_no_wait: a clean force close
  takes none of the new fallback path (byte-identical idle behaviour).
- test_exit_sends_exit_kill: exit() sends `exit kill`, not `exit`, so a
  numbered job surviving to exit time cannot move lftp to nohup background.
- test_child_dead_on_first_poll_is_reaped_without_signal: pexpect's own 0.1s
  check was simply too early; no signal needed, no error raised.
- test_child_exits_only_after_group_sigkill_is_reaped_without_error: the
  GAP-2 fallback itself -- one group SIGKILL, bounded polling, reaped.
- test_child_never_dies_raises_lftp_error_after_bounded_wait: the fallback is
  bounded (EXIT_REAP_TIMEOUT_SECS); a real leak is never hidden.
- test_group_already_gone_is_tolerated: a concurrent reaper already won the
  race; ProcessLookupError from killpg is not an error.
- test_isalive_status_unavailable_is_warning_not_raise: isalive() itself can
  raise (ECHILD); this is logged, not raised.
- test_graceful_failure_still_propagates_after_fallback_reap: a kill_all()
  failure is not masked by a successful fallback reap in the finally block.
- test_no_new_log_text_contains_harness_error_strings: the harness's
  detector strings never appear in a new log line, and no new line is ERROR.
- test_exit_reap_constants_and_defaults: the public bound and poll interval.
- test_describe_lftp_process_reads_state_and_children: the /proc diagnostic
  parser used in the WARNING/LftpError text, including its failure mode.
"""
import os
import re
import signal
import tempfile
import unittest
from typing import List, Optional, Tuple
from unittest.mock import patch

import pexpect

from lftp import Lftp, LftpError
from lftp.lftp import describe_lftp_process


_PROMPT = b"lftp testuser@localhost:~> "


class _FakeLftpProcess:
    """
    Minimal fake pexpect spawn for Lftp.exit()-path tests: answers every
    sendline with a fresh prompt (so kill_all()'s two commands and the final
    `exit kill` all complete normally), unless scripted to go permanently
    silent on one command (mirroring a wedged lftp, as in test_lftp_resync).
    """

    def __init__(self,
                 close_raises: bool = False,
                 alive_after_close: Optional[List[bool]] = None,
                 never_answer: Optional[str] = None,
                 isalive_raises_after_close: bool = False):
        self.pid = 4242
        self.buf = _PROMPT
        self.before = b""
        self.after = b""
        self.sent: List[str] = []
        self.close_raises = close_raises
        self.close_calls: List[bool] = []
        self._alive_after_close = list(alive_after_close) if alive_after_close is not None else [False]
        self._last_alive = False
        self.isalive_calls = 0
        self._isalive_raises_after_close = isalive_raises_after_close
        self._closed = False
        self._stuck = False
        self._never_answer = never_answer

    def isalive(self):
        if not self._closed:
            return True
        self.isalive_calls += 1
        if self._isalive_raises_after_close:
            raise pexpect.exceptions.ExceptionPexpect("Lost child process.")
        if self._alive_after_close:
            self._last_alive = self._alive_after_close.pop(0)
        return self._last_alive

    def close(self, force=False):
        self.close_calls.append(force)
        self._closed = True
        if self.close_raises:
            raise pexpect.exceptions.ExceptionPexpect("Could not terminate the child.")

    def sendline(self, s: str):
        self.sent.append(s)
        if self._stuck:
            return
        if self._never_answer is not None and s == self._never_answer:
            self._stuck = True
            return
        self.buf += _PROMPT

    def expect(self, pattern, timeout=None):
        rx = re.compile(pattern if isinstance(pattern, bytes) else pattern.encode())
        m = rx.search(self.buf)
        if not m:
            self.before = self.buf
            raise pexpect.exceptions.TIMEOUT("fake process: no match for {!r}".format(pattern))
        self.before, self.after, self.buf = self.buf[:m.start()], m.group(0), self.buf[m.end():]
        return 0


class _FakeClock:
    """
    Mutable monotonic-clock stand-in (never a lambda bound to a name, ruff
    E731). Starts at 0.0: summing many additions of a non-power-of-two
    interval (0.05) onto a larger base (e.g. 1000.0, closer to a real
    time.monotonic() reading) accumulates more binary floating-point
    rounding error per addition, which can make the running total land
    fractionally short of an exact N * 0.05 deadline. Starting at 0.0 keeps
    these tests' arithmetic exact, matching real time.monotonic()/time.sleep()
    behaviour where OS scheduling rounds actual elapsed time up, not down.
    """

    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now


class _FakeWaiter:
    """Records each requested wait and advances the paired fake clock by it; never sleeps."""

    def __init__(self, clock: _FakeClock):
        self._clock = clock
        self.calls: List[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self._clock.now += seconds


class _FakeKillGroup:
    """Records each (pid, sig) call; optionally raises a scripted exception instead."""

    def __init__(self, raise_exc: Optional[BaseException] = None):
        self.calls: List[Tuple[int, int]] = []
        self._raise_exc = raise_exc

    def __call__(self, pid: int, sig: int) -> None:
        self.calls.append((pid, sig))
        if self._raise_exc is not None:
            raise self._raise_exc


def _fake_describe_process(pid: int) -> str:
    return "state=D child processes=1"


def _make_lftp(proc: _FakeLftpProcess,
               clock: _FakeClock,
               waiter: _FakeWaiter,
               kill_group: _FakeKillGroup,
               describe=_fake_describe_process) -> Lftp:
    with patch('pexpect.spawn') as mock_spawn:
        mock_spawn.return_value = proc
        lftp = Lftp(
            address="localhost",
            port=22,
            user="testuser",
            password="testpass",
            clock=clock,
            waiter=waiter,
            kill_group=kill_group,
            describe_process=describe,
        )
    return lftp


class TestLftpExitIdlePathUnchanged(unittest.TestCase):
    def test_idle_close_succeeds_no_poll_no_signal_no_wait(self):
        proc = _FakeLftpProcess(close_raises=False)
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup()
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertNoLogs("Lftp", level="INFO"):
            result = lftp.exit()

        self.assertIsNone(result)
        self.assertEqual([], waiter.calls)
        self.assertEqual([], kill_group.calls)
        self.assertEqual(0, proc.isalive_calls)

    def test_exit_sends_exit_kill(self):
        proc = _FakeLftpProcess(close_raises=False)
        clock = _FakeClock()
        lftp = _make_lftp(proc, clock, _FakeWaiter(clock), _FakeKillGroup())

        lftp.exit()

        self.assertEqual("exit kill", proc.sent[-1])


class TestLftpExitFallbackReap(unittest.TestCase):
    def test_child_dead_on_first_poll_is_reaped_without_signal(self):
        proc = _FakeLftpProcess(close_raises=True, alive_after_close=[False])
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup()
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertLogs("Lftp", level="INFO") as cm:
            lftp.exit()

        self.assertEqual([], kill_group.calls)
        self.assertEqual([], waiter.calls)
        reaped = [line for line in cm.output if "reaped after force close" in line]
        self.assertEqual(1, len(reaped))
        self.assertIn("group kill sent: no", reaped[0])

    def test_child_exits_only_after_group_sigkill_is_reaped_without_error(self):
        proc = _FakeLftpProcess(close_raises=True, alive_after_close=[True, True, True, False])
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup()
        start = clock.now
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertLogs("Lftp", level="INFO") as cm:
            lftp.exit()

        self.assertEqual([(4242, signal.SIGKILL)], kill_group.calls)
        warnings = [line for line in cm.output if "did not exit on force close" in line]
        self.assertEqual(1, len(warnings))
        self.assertIn("state=D child processes=1", warnings[0])
        reaped = [line for line in cm.output if "reaped after force close" in line]
        self.assertEqual(1, len(reaped))
        self.assertIn("group kill sent: yes", reaped[0])
        for call in waiter.calls:
            self.assertLessEqual(call, 0.05)
        self.assertLess(clock.now - start, 2.0)

    def test_child_never_dies_raises_lftp_error_after_bounded_wait(self):
        proc = _FakeLftpProcess(close_raises=True, alive_after_close=[True])
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup()
        start = clock.now
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertRaises(LftpError) as ctx:
            lftp.exit()

        self.assertIn("4242", str(ctx.exception))
        self.assertIn("still running 2.0s", str(ctx.exception))
        self.assertEqual([(4242, signal.SIGKILL)], kill_group.calls)
        self.assertGreaterEqual(len(waiter.calls), 1)
        self.assertLessEqual(len(waiter.calls), 40)
        self.assertGreaterEqual(clock.now, start + 2.0)
        self.assertLess(clock.now, start + 2.0 + 0.05)

    def test_group_already_gone_is_tolerated(self):
        proc = _FakeLftpProcess(close_raises=True, alive_after_close=[True, False])
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup(raise_exc=ProcessLookupError())
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertLogs("Lftp", level="INFO") as cm:
            lftp.exit()

        self.assertEqual(1, len(kill_group.calls))
        reaped = [line for line in cm.output if "reaped after force close" in line]
        self.assertEqual(1, len(reaped))

    def test_isalive_status_unavailable_is_warning_not_raise(self):
        proc = _FakeLftpProcess(close_raises=True, isalive_raises_after_close=True)
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup()
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertLogs("Lftp", level="WARNING") as cm:
            lftp.exit()

        warnings = [line for line in cm.output if "status unavailable after force close" in line]
        self.assertEqual(1, len(warnings))
        self.assertEqual([], kill_group.calls)

    def test_graceful_failure_still_propagates_after_fallback_reap(self):
        proc = _FakeLftpProcess(close_raises=True, alive_after_close=[False], never_answer="queue -d *")
        clock = _FakeClock()
        waiter = _FakeWaiter(clock)
        kill_group = _FakeKillGroup()
        lftp = _make_lftp(proc, clock, waiter, kill_group)

        with self.assertLogs("Lftp", level="INFO") as cm:
            with self.assertRaises(LftpError) as ctx:
                lftp.exit()

        self.assertIn("not synchronized", str(ctx.exception))
        reaped = [line for line in cm.output if "reaped after force close" in line]
        self.assertEqual(1, len(reaped))


class TestLftpExitNoHarnessDetectorStrings(unittest.TestCase):
    def test_no_new_log_text_contains_harness_error_strings(self):
        with self.assertLogs("Lftp", level="DEBUG") as cm:
            clock1 = _FakeClock()
            proc1 = _FakeLftpProcess(close_raises=True, alive_after_close=[False])
            lftp1 = _make_lftp(proc1, clock1, _FakeWaiter(clock1), _FakeKillGroup())
            lftp1.exit()

            clock2 = _FakeClock()
            proc2 = _FakeLftpProcess(close_raises=True, alive_after_close=[True, True, True, False])
            lftp2 = _make_lftp(proc2, clock2, _FakeWaiter(clock2), _FakeKillGroup())
            lftp2.exit()

            clock3 = _FakeClock()
            proc3 = _FakeLftpProcess(close_raises=True, alive_after_close=[True])
            lftp3 = _make_lftp(proc3, clock3, _FakeWaiter(clock3), _FakeKillGroup())
            with self.assertRaises(LftpError):
                lftp3.exit()

            clock4 = _FakeClock()
            proc4 = _FakeLftpProcess(close_raises=True, isalive_raises_after_close=True)
            lftp4 = _make_lftp(proc4, clock4, _FakeWaiter(clock4), _FakeKillGroup())
            lftp4.exit()

        for record in cm.records:
            self.assertNotEqual("ERROR", record.levelname)
        for line in cm.output:
            self.assertNotIn("Could not terminate the child", line)
            self.assertNotIn("Error stopping", line)


class TestLftpExitReapConstants(unittest.TestCase):
    def test_exit_reap_constants_and_defaults(self):
        self.assertEqual(2.0, Lftp.EXIT_REAP_TIMEOUT_SECS)
        self.assertEqual(0.05, Lftp.EXIT_REAP_POLL_INTERVAL_SECS)


class TestDescribeLftpProcess(unittest.TestCase):
    def test_describe_lftp_process_reads_state_and_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_dir = os.path.join(tmp, "4242")
            task_dir = os.path.join(pid_dir, "task", "4242")
            os.makedirs(task_dir)
            with open(os.path.join(pid_dir, "stat"), "w") as f:
                f.write("4242 (lftp (x)) D 1 4242 4242 0 -1")
            with open(os.path.join(task_dir, "children"), "w") as f:
                f.write("100 101 ")
            self.assertEqual("state=D child processes=2", describe_lftp_process(4242, proc_root=tmp))

        with tempfile.TemporaryDirectory() as empty_tmp:
            self.assertEqual("state=? child processes=?", describe_lftp_process(4242, proc_root=empty_tmp))


if __name__ == "__main__":
    unittest.main()
