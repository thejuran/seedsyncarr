import errno
import logging
import os
import re
import secrets
import signal
import time
from functools import wraps
from typing import Callable, Union, List, Optional

import pexpect

from common import AppError, sanitize_log_value
from .job_status_parser import LftpJobStatus, LftpJobStatusParser, LftpJobStatusParserError

# How many status errors are allowed before error propagates out
MAX_CONSECUTIVE_STATUS_ERRORS = 2

class LftpError(AppError):
    """
    Custom exception that describes the failure of the lftp command
    """
    pass


def describe_lftp_process(pid: int, proc_root: str = "/proc") -> str:
    """
    Best-effort diagnostic for a pid that is still unreaped: its /proc state
    letter and its live child-process count. Used only to enrich the
    GAP-2 fallback's WARNING/LftpError text; it never raises, since a pid
    that is already gone (or a sandboxed /proc) is itself diagnostic
    information, not a failure of this function.

    :param pid: process id to describe
    :param proc_root: root of the /proc filesystem (overridable for tests)
    :return: "state=<letter> child processes=<n>"; either field is "?" when
             it cannot be read or parsed
    """
    state = "?"
    try:
        with open(os.path.join(proc_root, str(pid), "stat"), "r") as f:
            contents = f.read()
        # comm (field 2) may itself contain spaces or parentheses, so the
        # state letter is the first token after the LAST ')' in the line.
        state = contents.rsplit(")", 1)[1].split()[0]
    except (OSError, ValueError, IndexError):
        state = "?"

    child_count = "?"
    try:
        children_path = os.path.join(proc_root, str(pid), "task", str(pid), "children")
        with open(children_path, "r") as f:
            contents = f.read()
        child_count = str(len(contents.split()))
    except (OSError, ValueError, IndexError):
        child_count = "?"

    return "state={} child processes={}".format(state, child_count)

class Lftp:
    """
    Lftp command utility
    """
    __SET_NUM_PARALLEL_FILES = "mirror:parallel-transfer-count"
    __SET_NUM_CONNECTIONS_PGET = "pget:default-n"
    __SET_NUM_CONNECTIONS_MIRROR = "mirror:use-pget-n"
    __SET_NUM_MAX_TOTAL_CONNECTIONS = "net:connection-limit"
    __SET_RATE_LIMIT = "net:limit-rate"
    __SET_MIN_CHUNK_SIZE = "pget:min-chunk-size"
    __SET_NUM_PARALLEL_JOBS = "cmd:queue-parallel"
    __SET_MOVE_BACKGROUND_ON_EXIT = "cmd:move-background"
    __SET_COMMAND_AT_EXIT = "cmd:at-exit"
    __SET_USE_TEMP_FILE = "xfer:use-temp-file"
    __SET_TEMP_FILE_NAME = "xfer:temp-file-name"
    __SET_SFTP_AUTO_CONFIRM = "sftp:auto-confirm"
    __SET_SFTP_CONNECT_PROGRAM = "sftp:connect-program"

    # Short timeout for the resync sentinel, so a still-wedged lftp fails fast
    # instead of blocking the caller for the full command timeout.
    RESYNC_TIMEOUT_SECS = 15
    __SYNC_MARKER_PREFIX = "SEEDSYNCARR-SYNC-"

    # Bound on the GAP-2 post-force-close reap fallback (20x pexpect's own
    # 0.1s post-SIGKILL check); see exit()'s docstring.
    EXIT_REAP_TIMEOUT_SECS = 2.0
    # Poll interval while waiting for the fallback's SIGKILL to be reaped.
    EXIT_REAP_POLL_INTERVAL_SECS = 0.05

    def __init__(self,
                 address: str,
                 port: int,
                 user: str,
                 password: Optional[str],
                 *,
                 clock: Callable[[], float] = time.monotonic,
                 waiter: Callable[[float], None] = time.sleep,
                 kill_group: Callable[[int, int], None] = os.killpg,
                 describe_process: Callable[[int], str] = describe_lftp_process):
        self.__clock = clock
        self.__waiter = waiter
        self.__kill_group = kill_group
        self.__describe_process = describe_process
        self.__user = user
        self.__password = password
        self.__address = address
        self.__base_remote_dir_path = ""
        self.__base_local_dir_path = ""
        self.logger = logging.getLogger("Lftp")
        self.__expect_pattern = "lftp {}@{}:.*>".format(self.__user, self.__address)
        self.__job_status_parser = LftpJobStatusParser()
        self.__timeout = 180  # in seconds
        self.__consecutive_status_errors = 0
        # Set when the most recent command's expect timed out, i.e. its output
        # is an incomplete observation. Only status() consults it.
        self.__last_command_timed_out = False
        # Set False on any expect TIMEOUT: the timed-out command's late output
        # and prompt may still arrive, so no command output is trusted until
        # __resync proves a fresh command boundary.
        self.__synced = True

        self.__log_command_output = False
        self.__pending_error = None

        args = [
            "-p", str(port),
            "-u", "{},{}".format(self.__user, self.__password if self.__password else ""),
            "sftp://{}".format(self.__address)
        ]
        self.__process = pexpect.spawn("/usr/bin/lftp", args)
        self.__process.expect(self.__expect_pattern)
        self.__setup()

    def set_verbose_logging(self, verbose: bool):
        self.__log_command_output = verbose

    def __setup(self):
        """
        Setup the lftp instance with default settings
        """
        # Set to kill on exit to prevent a zombie process
        self.__set(Lftp.__SET_COMMAND_AT_EXIT, "\"kill all\"")
        # Auto-add server to known host file
        self.sftp_auto_confirm = True

    def with_check_process(method: Callable):
        """
        Decorator that checks for a valid process before executing
        the decorated method
        """
        @wraps(method)
        def wrapper(inst: "Lftp", *args, **kwargs):
            if inst.__process is None or not inst.__process.isalive():
                raise LftpError("lftp process is not running")
            return method(inst, *args, **kwargs)
        return wrapper

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("Lftp")
        self.__job_status_parser.set_base_logger(self.logger)

    def set_base_remote_dir_path(self, base_remote_dir_path: str):
        self.__base_remote_dir_path = base_remote_dir_path

    def set_base_local_dir_path(self, base_local_dir_path: str):
        self.__base_local_dir_path = base_local_dir_path

    def raise_pending_error(self):
        """
        Raise any pending errors
        Errors show up late after a command is executed
        This method raises any errors that were detected while executing the next command
        """
        if self.__pending_error:
            error = self.__pending_error
            self.__pending_error = None
            raise LftpError(error)

    def __resync(self) -> bool:
        """
        Prove a fresh command boundary on the pty stream with a nonce sentinel.

        lftp's `echo` removes the quotes around the nonce, while the tty echo of
        the typed command keeps them, so only lftp's real output can match the
        unquoted marker. A new nonce per attempt means stale output from an
        earlier attempt never satisfies a later one.
        :return: True once synchronized, False if the sentinel did not complete
        """
        nonce = secrets.token_hex(8)
        self.__process.sendline('echo {}"{}"-END'.format(Lftp.__SYNC_MARKER_PREFIX, nonce))
        marker = re.escape("{}{}-END".format(Lftp.__SYNC_MARKER_PREFIX, nonce)).encode()
        try:
            self.__process.expect(marker, timeout=Lftp.RESYNC_TIMEOUT_SECS)
            self.__process.expect(self.__expect_pattern, timeout=Lftp.RESYNC_TIMEOUT_SECS)
        except pexpect.exceptions.TIMEOUT:
            self.logger.warning("Lftp resync attempt timed out; status stays unavailable")
            return False
        self.__synced = True
        self.logger.info("Lftp command stream resynchronized")
        return True

    @with_check_process
    def __run_command(self, command: str):
        if self.__log_command_output:
            self.logger.debug("command: {}".format(command.encode('utf8', 'surrogateescape')))
        if not self.__synced and not self.__resync():
            raise LftpError("lftp command stream not synchronized")
        self.__last_command_timed_out = False
        self.__process.sendline(command)
        try:
            self.__process.expect(self.__expect_pattern, timeout=self.__timeout)
        except pexpect.exceptions.TIMEOUT:
            self.__last_command_timed_out = True
            self.__synced = False
            self.logger.warning("Lftp timeout exception")
        finally:
            before = self.__process.before
            out = before.decode('utf8', 'replace') if isinstance(before, bytes) else ""
            out = out.strip()  # remove any CRs

            if self.__log_command_output:
                self.logger.debug("out ({} bytes):\n {}".format(len(out), sanitize_log_value(out)))
                after_raw = self.__process.after
                after = after_raw.decode('utf8', 'replace').strip() if isinstance(after_raw, bytes) else ""
                self.logger.debug("after: {}".format(sanitize_log_value(after)))

        # let's try and detect some errors
        if self.__detect_errors_from_output(out):
            # we need to consume the actual output so that
            # it doesn't get passed onto next command
            error_out = out
            try:
                self.__process.expect(self.__expect_pattern, timeout=self.__timeout)
            except pexpect.exceptions.TIMEOUT:
                self.__last_command_timed_out = True
                self.__synced = False
                self.logger.warning("Lftp timeout exception")
            finally:
                out = self.__process.before.decode('utf8', 'replace')
                out = out.strip()  # remove any CRs
                if self.__log_command_output:
                    self.logger.debug("retry out ({} bytes):\n {}".format(len(out), sanitize_log_value(out)))
                    after = self.__process.after.decode('utf8', 'replace').strip() \
                        if self.__process.after not in (pexpect.TIMEOUT, None) else ""
                    self.logger.debug("retry after: {}".format(sanitize_log_value(after)))
                self.logger.error("Lftp detected error: {}".format(sanitize_log_value(error_out)))
                # save pending error
                self.__pending_error = error_out
        return out

    @staticmethod
    def __detect_errors_from_output(out: str) -> bool:
        errors = [
            "pget: Access failed",
            "pget-chunk: Access failed",
            "mirror: Access failed",
            "Login failed: Login incorrect"
        ]
        for error in errors:
            if error in out:
                return True
        return False

    def __set(self, setting: str, value: str):
        """
        Set a setting in the lftp runtime
        """
        self.__run_command("set {} {}".format(setting, value))

    def __get(self, setting: str) -> str:
        """
        Get a setting from the lftp runtime
        """
        out = self.__run_command("set -a | grep {}".format(setting))
        m = re.search("set {} (.*)".format(setting), out)
        if not m or not m.group or not m.group(1):
            raise LftpError("Failed to get setting '{}'. Output: '{}'".format(setting, out))
        return m.group(1).strip()

    @staticmethod
    def __to_bool(value: str) -> bool:
        # sets are taken from LFTP manual
        if value.lower() in {"true", "on", "yes", "1", "+"}:
            return True
        elif value.lower() in {"false",  "off", "no", "0", "-"}:
            return False
        else:
            raise LftpError("Cannot convert value '{}' to boolean".format(value))

    @property
    def num_connections_per_dir_file(self) -> int:
        return int(self.__get(Lftp.__SET_NUM_CONNECTIONS_MIRROR))

    @num_connections_per_dir_file.setter
    def num_connections_per_dir_file(self, num_connections: int):
        if num_connections < 1:
            raise ValueError("Number of connections must be positive")
        self.__set(Lftp.__SET_NUM_CONNECTIONS_MIRROR, str(num_connections))

    @property
    def num_connections_per_root_file(self) -> int:
        return int(self.__get(Lftp.__SET_NUM_CONNECTIONS_PGET))

    @num_connections_per_root_file.setter
    def num_connections_per_root_file(self, num_connections: int):
        if num_connections < 1:
            raise ValueError("Number of connections must be positive")
        self.__set(Lftp.__SET_NUM_CONNECTIONS_PGET, str(num_connections))

    @property
    def num_max_total_connections(self) -> int:
        return int(self.__get(Lftp.__SET_NUM_MAX_TOTAL_CONNECTIONS))

    @num_max_total_connections.setter
    def num_max_total_connections(self, num_connections: int):
        if num_connections < 0:
            raise ValueError("Number of connections must be zero or greater")
        self.__set(Lftp.__SET_NUM_MAX_TOTAL_CONNECTIONS, str(num_connections))

    @property
    def num_parallel_files(self) -> int:
        return int(self.__get(Lftp.__SET_NUM_PARALLEL_FILES))

    @num_parallel_files.setter
    def num_parallel_files(self, num_parallel_files: int):
        if num_parallel_files < 1:
            raise ValueError("Number of parallel files must be positive")
        self.__set(Lftp.__SET_NUM_PARALLEL_FILES, str(num_parallel_files))

    @property
    def rate_limit(self) -> str:
        return self.__get(Lftp.__SET_RATE_LIMIT)

    @rate_limit.setter
    def rate_limit(self, rate_limit: Union[int, str]):
        self.__set(Lftp.__SET_RATE_LIMIT, str(rate_limit))

    @property
    def min_chunk_size(self) -> str:
        return self.__get(Lftp.__SET_MIN_CHUNK_SIZE)

    @min_chunk_size.setter
    def min_chunk_size(self, min_chunk_size: Union[int, str]):
        self.__set(Lftp.__SET_MIN_CHUNK_SIZE, str(min_chunk_size))

    @property
    def num_parallel_jobs(self) -> int:
        return int(self.__get(Lftp.__SET_NUM_PARALLEL_JOBS))

    @num_parallel_jobs.setter
    def num_parallel_jobs(self, num_parallel_jobs: int):
        if num_parallel_jobs < 1:
            raise ValueError("Number of parallel jobs must be positive")
        self.__set(Lftp.__SET_NUM_PARALLEL_JOBS, str(num_parallel_jobs))

    @property
    def move_background_on_exit(self) -> bool:
        return Lftp.__to_bool(self.__get(Lftp.__SET_MOVE_BACKGROUND_ON_EXIT))

    @move_background_on_exit.setter
    def move_background_on_exit(self, move_background_on_exit: bool):
        self.__set(Lftp.__SET_MOVE_BACKGROUND_ON_EXIT, str(int(move_background_on_exit)))

    @property
    def use_temp_file(self) -> bool:
        return Lftp.__to_bool(self.__get(Lftp.__SET_USE_TEMP_FILE))

    @use_temp_file.setter
    def use_temp_file(self, use_temp_file: bool):
        self.__set(Lftp.__SET_USE_TEMP_FILE, str(int(use_temp_file)))

    @property
    def temp_file_name(self) -> str:
        return self.__get(Lftp.__SET_TEMP_FILE_NAME)

    @temp_file_name.setter
    def temp_file_name(self, temp_file_name: str):
        self.__set(Lftp.__SET_TEMP_FILE_NAME, temp_file_name)

    @property
    def sftp_auto_confirm(self) -> bool:
        return Lftp.__to_bool(self.__get(Lftp.__SET_SFTP_AUTO_CONFIRM))

    @sftp_auto_confirm.setter
    def sftp_auto_confirm(self, auto_confirm: bool):
        self.__set(Lftp.__SET_SFTP_AUTO_CONFIRM, str(int(auto_confirm)))

    @property
    def sftp_connect_program(self) -> str:
        return self.__get(Lftp.__SET_SFTP_CONNECT_PROGRAM)

    @sftp_connect_program.setter
    def sftp_connect_program(self, program: str):
        self.__set(Lftp.__SET_SFTP_CONNECT_PROGRAM, program)

    def status(self) -> Optional[List[LftpJobStatus]]:
        """
        Return a status list of queued and running jobs.

        :return: the parsed job list, which is empty only when lftp genuinely
                 has no jobs; or None when the status is unavailable, meaning
                 either the `jobs -v` command did not complete (pexpect timeout;
                 the partial buffer is not parsed) or a tolerated parse error
                 occurred. None must never be treated as "no jobs".
        :raises LftpJobStatusParserError: once more than
                 MAX_CONSECUTIVE_STATUS_ERRORS consecutive parse failures have
                 occurred, and on every further failure until a successful parse
                 resets the counter. Timeouts neither count toward nor reset
                 that counter. Neither does an unsynchronized command stream
                 (after a timeout, until a sentinel resync succeeds), which also
                 returns None.
        """
        try:
            out = self.__run_command("jobs -v")
        except LftpError as e:
            if "not synchronized" in str(e):
                self.logger.warning("Lftp status unavailable: command stream not synchronized")
                return None
            raise
        if self.__last_command_timed_out:
            self.logger.warning("Lftp status command timed out; status unavailable")
            return None
        try:
            statuses = self.__job_status_parser.parse(out)
            self.__consecutive_status_errors = 0
        except LftpJobStatusParserError:
            self.__consecutive_status_errors += 1
            if self.__consecutive_status_errors <= MAX_CONSECUTIVE_STATUS_ERRORS:
                self.logger.warning(
                    f"Ignoring status error (count={self.__consecutive_status_errors}); status unavailable"
                )
                return None
            else:
                raise
        return statuses

    def queue(self, name: str, is_dir: bool):
        """
        Queues a job for download
        This method may cause an exception to be generated in a later method call:
          * Wrong type (is_dir) is specified
          * File/folder does not exist
        :param name: name of file or folder to download
        :param is_dir: true if folder, false if file
        """
        # Escape single and double quotes in any string used in queue command
        # Also reject newline/CR/null which could inject arbitrary LFTP commands via sendline()
        def escape(s: str) -> str:
            if '\n' in s or '\r' in s or '\x00' in s:
                raise LftpError("Invalid characters in filename: {}".format(repr(s)))
            return s.replace("'", "\\'").replace("\"", "\\\"")

        command = " ".join([
            "queue",
            "'",
            "pget" if not is_dir else "mirror",
            "-c",
            "\"{remote_dir}/{filename}\"".format(remote_dir=escape(self.__base_remote_dir_path),
                                                 filename=escape(name)),
            "-o" if not is_dir else "",
            "\"{local_dir}/\"".format(local_dir=escape(self.__base_local_dir_path)),
            "'"
        ])
        self.__run_command(command)

    def kill(self, name: str) -> bool:
        """
        Kill a queued or running job
        :return: True if job of given name was found, False otherwise
        """
        # Unavailable status is not "job absent": returning False here would let
        # the caller mark a still-running download as stopped.
        statuses = self.status()
        if statuses is None:
            raise LftpJobStatusParserError("Lftp status unavailable; cannot locate job to kill")
        # look for this name in the status list
        job_to_kill = None
        for status in statuses:
            if status.name == name:
                job_to_kill = status
                break
        if job_to_kill is None:
            self.logger.debug("Kill failed to find job '{}'".format(sanitize_log_value(name)))
            return False
        # Note: there's a chance that job ids change between when we called status
        #       and when we execute the kill command
        #       in this case the wrong job may be killed, there's nothing we can do about it
        if job_to_kill.state == LftpJobStatus.State.RUNNING:
            self.logger.debug("Killing running job '{}'...".format(sanitize_log_value(name)))
            self.__run_command("kill {}".format(job_to_kill.id))
        elif job_to_kill.state == LftpJobStatus.State.QUEUED:
            self.logger.debug("Killing queued job '{}'...".format(sanitize_log_value(name)))
            self.__run_command("queue --delete {}".format(job_to_kill.id))
        else:
            raise NotImplementedError("Unsupported state {}".format(str(job_to_kill.state)))
        return True

    def kill_all(self):
        """
        Kills are jobs, queued or downloading
        """
        # empty the queue and kill running jobs
        self.__run_command("queue -d *")
        self.__run_command("kill all")

    def exit(self):
        """
        Exit the lftp process. The instance cannot be used after this call.

        The process is force-closed even when the graceful kill/exit commands
        fail (e.g. the command stream could not be resynchronized after a
        timeout); the graceful failure still propagates after the close.

        Sends "exit kill" rather than "exit": lftp's documented behaviour is
        to move itself to nohup mode in the background (forking a detached,
        new-session child) if it is asked to exit while jobs are still
        running. "exit kill" kills all numbered jobs first, so that fork
        path is never taken and a process-group signal can always reach it.

        GAP-2 (D-01): pexpect's own close(force=True) sends SIGHUP, SIGCONT,
        SIGINT and SIGKILL to the child, waiting up to 0.1s of in-kernel exit
        after each. During an active transfer the lftp pid can still be
        mid-exit (e.g. blocked tearing down sockets/dirty pages) when that
        0.1s elapses, so ptyprocess raises PtyProcessError("Could not
        terminate the child.") -- which pexpect re-raises as
        ExceptionPexpect -- without reaping the child. On a clean (idle)
        shutdown this path is never taken: close() returns normally and
        exit() does nothing further.

        Only when close(force=True) raises does this fall back to:
        one isalive() poll (which itself reaps a child that has since died),
        then, if still alive, a SIGKILL to the child's own process group
        (safe: the pid is confirmed unreaped, so group <pid> can only be the
        session/process group lftp created as its own leader via
        pty.fork()), then bounded polling (EXIT_REAP_TIMEOUT_SECS, default
        2.0s) for it to be reaped. If it is still alive at the deadline,
        this raises LftpError so the leak surfaces honestly instead of being
        silently swallowed.
        """
        try:
            self.kill_all()
            self.__process.sendline("exit kill")
        finally:
            try:
                self.__process.close(force=True)
            except pexpect.exceptions.ExceptionPexpect:
                self.__reap_after_failed_close()

    def __poll_isalive(self) -> Optional[bool]:
        """
        :return: True if still alive, False if reaped, None if the status
                 itself is unavailable (pexpect raised, e.g. ECHILD)
        """
        try:
            return self.__process.isalive()
        except pexpect.exceptions.ExceptionPexpect:
            return None

    def __reap_after_failed_close(self) -> None:
        """
        GAP-2 fallback, reached only after pexpect's own close(force=True)
        raised ExceptionPexpect. See exit()'s docstring for the mechanism.
        """
        pid = self.__process.pid
        start = self.__clock()

        status = self.__poll_isalive()
        if status is None:
            self.logger.warning(
                "Lftp process {} status unavailable after force close; it was already reaped elsewhere".format(pid)
            )
            return
        if status is False:
            elapsed = self.__clock() - start
            self.logger.info(
                "Lftp process {} reaped after force close in {:.2f}s (group kill sent: no)".format(pid, elapsed)
            )
            return

        describe = self.__describe_process(pid)
        self.logger.warning(
            "Lftp process {} did not exit on force close ({}); sending SIGKILL to its process group".format(
                pid, describe
            )
        )
        try:
            self.__kill_group(pid, signal.SIGKILL)
        except ProcessLookupError:
            # Already gone: a concurrent reaper (or the kernel) won the race.
            pass
        except OSError as e:
            self.logger.warning(
                "Lftp process {} process-group SIGKILL failed: {}".format(
                    pid, errno.errorcode.get(e.errno, str(e.errno))
                )
            )

        while True:
            status = self.__poll_isalive()
            if status is False:
                elapsed = self.__clock() - start
                self.logger.info(
                    "Lftp process {} reaped after force close in {:.2f}s (group kill sent: yes)".format(pid, elapsed)
                )
                return
            if status is None:
                self.logger.warning(
                    "Lftp process {} status unavailable after force close; "
                    "it was already reaped elsewhere".format(pid)
                )
                return
            now = self.__clock()
            if now >= start + Lftp.EXIT_REAP_TIMEOUT_SECS:
                describe = self.__describe_process(pid)
                raise LftpError(
                    "Lftp process {} still running {}s after SIGKILL to its process group ({})".format(
                        pid, Lftp.EXIT_REAP_TIMEOUT_SECS, describe
                    )
                )
            remaining = start + Lftp.EXIT_REAP_TIMEOUT_SECS - now
            self.__waiter(min(Lftp.EXIT_REAP_POLL_INTERVAL_SECS, remaining))

    # Mark decorators as static (must be at end of class)
    # Source: https://stackoverflow.com/a/3422823
    with_check_process = staticmethod(with_check_process)
