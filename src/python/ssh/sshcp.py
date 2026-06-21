import logging
import time

import pexpect

from common import AppError

class SshcpError(AppError):
    """
    Custom exception that describes the failure of the ssh command
    """
    pass

# Error message prefixes that indicate transient network issues (timeouts,
# connection drops, unreachable hosts). Consumers can use these to decide
# whether a failed SSH operation is worth retrying.
TRANSIENT_ERROR_PATTERNS = ("Timed out", "Connection refused by server")

# Error message prefixes that indicate permanent configuration problems
# (wrong credentials, changed host keys, bad hostnames). These should not
# be retried — the user needs to fix the configuration.
PERMANENT_ERROR_PATTERNS = ("Incorrect password", "Remote host key has changed", "Bad hostname:")

# Error substrings that indicate a NAME-RESOLUTION (DNS) failure. These are
# transient AT THE RETRY LAYER (a momentary DNS blip clears within a bounded
# retry window — see Phase 114 D-01), but stay PERMANENT at the classification
# layer: "Bad hostname:" intentionally appears in BOTH this tuple AND
# PERMANENT_ERROR_PATTERNS, so a name-resolution failure surfaces fatal once the
# bounded retry helper exhausts its attempts (lowest blast radius per D-01).
#
# This tuple must cover EVERY resolver-string surface the SSH layer can present:
#   1. The COLLAPSED form "Bad hostname: {host}" — raised by the two literally
#      matched pexpect indices 3 ("Could not resolve hostname") and 5 ("Name or
#      service not known") at sshcp.py:97-98 / :128-129.
#   2. The RAW non-zero-exit fallthrough strings — raised verbatim from
#      `sp.before` at sshcp.py:151-155 with NO collapse, e.g.
#      "ssh: Could not resolve hostname host: Temporary failure in name resolution".
# Matching only "Bad hostname:" would leave the raw surfaces non-retryable.
#
# Entries are LOWER-CASE because the matcher (RemoteScanner._is_name_resolution_ssh_error)
# lower-cases the message before comparing — the raw fallthrough casing varies
# across SSH versions (test_sshcp.py asserts on `str(...).lower()`). The full
# "temporary failure in name resolution" substring (not the bare "temporary
# failure") is used so the tuple does not over-match an unrelated non-resolver
# "temporary failure" while still satisfying the test_sshcp.py contract.
#
# Name-resolution is the ONLY error class safe to retry in-scan (it fails fast);
# timeout/connection-refused can each block up to the 180s per-command timeout
# and are NOT retried in-scan on either the main-scan or install path.
NAME_RESOLUTION_ERROR_PATTERNS = (
    "bad hostname:",
    "could not resolve hostname",
    "name or service not known",
    "temporary failure in name resolution",
)

class Sshcp:
    """
    Scp command utility
    """
    __TIMEOUT_SECS = 180

    def __init__(self,
                 host: str,
                 port: int,
                 user: str = None,
                 password: str = None):
        if host is None:
            raise ValueError("Hostname not specified.")
        self.__host = host
        self.__port = port
        self.__user = user
        self.__password = password
        self.logger = logging.getLogger(self.__class__.__name__)

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild(self.__class__.__name__)

    def __run_command(self,
                      command: str,
                      flags: list,
                      args: list) -> bytes:

        command_args = [command]
        command_args += flags

        # Common flags
        command_args += [
            "-o", "StrictHostKeyChecking=accept-new",  # accept new host keys, reject changed ones
            "-o", "LogLevel=error",  # suppress warnings
        ]

        if self.__password is None:
            command_args += [
                "-o", "PasswordAuthentication=no",  # don't ask for password
            ]
        else:
            command_args += [
                "-o", "PubkeyAuthentication=no"  # don't use key authentication
            ]

        command_args += args

        self.logger.debug("Command: {}".format(command_args))

        start_time = time.time()
        sp = pexpect.spawn(command_args[0], command_args[1:])
        try:
            if self.__password is not None:
                i = sp.expect([
                    'password: ',  # i=0, all's good
                    pexpect.EOF,  # i=1, unknown error
                    'lost connection',  # i=2, connection refused
                    'Could not resolve hostname',  # i=3, bad hostname
                    'Connection refused',  # i=4, connection refused
                    'Name or service not known',  # i=5, bad hostname (newer SSH)
                    'No route to host',  # i=6, bad host (newer SSH)
                    'Connection timed out',  # i=7, connection timeout (newer SSH)
                    'REMOTE HOST IDENTIFICATION HAS CHANGED',  # i=8, host key changed (possible MITM)
                ])
                if i > 0:
                    before = sp.before.decode().strip() if sp.before != pexpect.EOF else ""
                    after = sp.after.decode().strip() if sp.after != pexpect.EOF else ""
                    self.logger.warning("Command failed: '{} - {}'".format(before, after))
                if i == 1:
                    error_msg = "Unknown error"
                    if sp.before.decode().strip():
                        error_msg += " - " + sp.before.decode().strip()
                    raise SshcpError(error_msg)
                elif i in {3, 5}:
                    raise SshcpError("Bad hostname: {}".format(self.__host))
                elif i in {2, 4, 6, 7}:
                    error_msg = "Connection refused by server"
                    if sp.before.decode().strip():
                        error_msg += " - " + sp.before.decode().strip()
                    raise SshcpError(error_msg)
                elif i == 8:
                    raise SshcpError("Remote host key has changed. This may indicate a MITM attack. Remove the old key from ~/.ssh/known_hosts to continue.")
                sp.sendline(self.__password)

            i = sp.expect(
                [
                    pexpect.EOF,  # i=0, all's good
                    'password: ',  # i=1, wrong password
                    'lost connection',  # i=2, connection refused
                    'Could not resolve hostname',  # i=3, bad hostname
                    'Connection refused',  # i=4, connection refused
                    'Name or service not known',  # i=5, bad hostname (newer SSH)
                    'No route to host',  # i=6, bad host (newer SSH)
                    'Connection timed out',  # i=7, connection timeout (newer SSH)
                    'REMOTE HOST IDENTIFICATION HAS CHANGED',  # i=8, host key changed (possible MITM)
                ],
                timeout=self.__TIMEOUT_SECS
            )
            if i > 0:
                before = sp.before.decode().strip() if sp.before != pexpect.EOF else ""
                after = sp.after.decode().strip() if sp.after != pexpect.EOF else ""
                self.logger.warning("Command failed: '{} - {}'".format(before, after))
            if i == 1:
                raise SshcpError("Incorrect password")
            elif i in {3, 5}:
                raise SshcpError("Bad hostname: {}".format(self.__host))
            elif i in {2, 4, 6, 7}:
                error_msg = "Connection refused by server"
                if sp.before.decode().strip():
                    error_msg += " - " + sp.before.decode().strip()
                raise SshcpError(error_msg)
            elif i == 8:
                raise SshcpError("Remote host key has changed. This may indicate a MITM attack. Remove the old key from ~/.ssh/known_hosts to continue.")

        except pexpect.exceptions.TIMEOUT:
            self.logger.exception("Timed out")
            self.logger.error("Command output before:\n{}".format(sp.before))
            sp.close()
            raise SshcpError("Timed out")
        except SshcpError:
            sp.close()
            raise
        sp.close()
        end_time = time.time()

        self.logger.debug("Return code: {}".format(sp.exitstatus))
        self.logger.debug("Command took {:.3f}s".format(end_time-start_time))
        if sp.exitstatus != 0:
            before = sp.before.decode().strip() if sp.before != pexpect.EOF else ""
            after = sp.after.decode().strip() if sp.after != pexpect.EOF else ""
            self.logger.warning("Command failed: '{} - {}'".format(before, after))
            raise SshcpError(sp.before.decode().strip())

        return sp.before.replace(b'\r\n', b'\n').strip()

    def shell(self, command: str) -> bytes:
        """
        Run a shell command on remote service and return output
        """
        if not command:
            raise ValueError("Command cannot be empty")

        # Reject commands with both quote types (preserved for API compatibility)
        if "'" in command and '"' in command:
            # I don't know how to handle this yet...
            raise ValueError("Command cannot contain both single and double quotes")

        # No local-shell quoting needed: pexpect.spawn passes args directly to
        # the ssh process (no shell interpolation), so the command string is
        # forwarded as-is to the remote shell which handles quoting correctly.
        flags = [
            "-p", str(self.__port),  # port
        ]
        args = [
            "{}@{}".format(self.__user, self.__host),
            command
        ]
        return self.__run_command(
            command="ssh",
            flags=flags,
            args=args
        )

    def copy(self, local_path: str, remote_path: str):
        """
        Copies local file at local_path to remote remote_path
        """
        if not local_path:
            raise ValueError("Local path cannot be empty")
        if not remote_path:
            raise ValueError("Remote path cannot be empty")

        flags = [
            "-q",  # quiet
            "-P", str(self.__port),  # port
        ]
        args = [
            local_path,
            "{}@{}:{}".format(self.__user, self.__host, remote_path)
        ]
        self.__run_command(
            command="scp",
            flags=flags,
            args=args
        )
