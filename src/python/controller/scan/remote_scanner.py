import logging
import json
from typing import Callable, List, Optional, Tuple, Union
import os
import hashlib
import shlex
import random
import time

from .scanner_process import IScanner, ScannerError
from common import overrides, Localization, sanitize_log_value
from ssh import (Sshcp, SshcpError, TRANSIENT_ERROR_PATTERNS,
                 PERMANENT_ERROR_PATTERNS, NAME_RESOLUTION_ERROR_PATTERNS)
from system import SystemFile

class RemoteScanner(IScanner):
    """
    Scanner implementation to scan the remote filesystem
    """

    # Bounded in-scan retry tuning for NAME-RESOLUTION (DNS) failures only
    # (Phase 114 D-02; convention: __UPPER mangled class constants, mirroring
    # Sshcp.__TIMEOUT_SECS). Because only fast-failing name-resolution is
    # retried, the worst-case added in-scan latency is just the backoff sleeps
    # (~3s total), never a stack of 180s SSH timeouts — true on both the
    # main-scan and install paths.
    __SCAN_MAX_ATTEMPTS = 3          # total attempts incl. the first
    __SCAN_BACKOFF_BASE_SECS = 1.0   # exponential base: 1s, 2s, (4s)
    __SCAN_BACKOFF_CEILING_SECS = 4.0
    __SCAN_BACKOFF_JITTER = 0.2      # ±20% jitter

    @staticmethod
    def _is_transient_ssh_error(error: SshcpError) -> bool:
        """Check if an SSH error is transient (timeout, connection refused, etc.)"""
        msg = str(error)
        return any(pattern in msg for pattern in TRANSIENT_ERROR_PATTERNS)

    @staticmethod
    def _is_permanent_ssh_error(error: SshcpError) -> bool:
        """Check if an SSH error is a permanent config problem (wrong password, bad host, etc.)"""
        msg = str(error)
        return any(pattern in msg for pattern in PERMANENT_ERROR_PATTERNS)

    @staticmethod
    def _is_name_resolution_ssh_error(error: SshcpError) -> bool:
        """Check if an SSH error is a name-resolution (DNS) failure.

        Name-resolution failures are the ONLY error class retried by the bounded
        retry helper: they fail fast, so a momentary DNS blip can clear inside a
        tight in-scan retry window (timeout/connection-refused are NOT retried
        in-scan — each can block up to the 180s Sshcp per-command timeout). The
        same helper wraps BOTH the main scan SSH call and the install-path
        md5sum/copy SSH ops; on exhaustion the failure surfaces fatal.

        Unlike ``_is_transient_ssh_error`` / ``_is_permanent_ssh_error`` (which
        compare CASE-SENSITIVELY), this matcher is CASE-INSENSITIVE: it lower-cases
        the message before comparing against the already-lower-cased
        ``NAME_RESOLUTION_ERROR_PATTERNS``. This is required because the SSH layer
        presents name-resolution failures on TWO surfaces and only one collapses:
        the COLLAPSED "Bad hostname:" (pexpect indices 3/5, sshcp.py:97-98/:128-129)
        AND the RAW non-zero-exit fallthrough strings (sshcp.py:155 raw
        ``sp.before``) such as "Could not resolve hostname" / "Name or service not
        known" / "Temporary failure in name resolution", whose casing varies
        across SSH versions.

        The name-resolution patterns are DISJOINT from
        ``TRANSIENT_ERROR_PATTERNS`` ("Timed out", "Connection refused by server")
        and from the non-resolver members of ``PERMANENT_ERROR_PATTERNS``
        ("Incorrect password", "Remote host key has changed"): none of "timed out",
        "connection refused", "incorrect password", or "remote host key has
        changed" is a substring of any name-resolution pattern, so timeout/
        refused/auth/host-key keep their existing classification + immediate-raise
        behavior — the retry gate stays name-resolution ONLY (Phase 114 D-01).

        Args:
            error: The SSH error to classify.

        Returns:
            True if the error message contains a name-resolution substring.
        """
        msg = str(error).lower()
        return any(pattern in msg for pattern in NAME_RESOLUTION_ERROR_PATTERNS)

    @staticmethod
    def _parse_df_output(out: Union[bytes, str]) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse `df -B1 <path>` output. Returns (total_bytes, used_bytes), or
        (None, None) on any parse failure (silent fallback per D-16). Never raises.
        """
        try:
            text = out.decode("utf-8") if isinstance(out, (bytes, bytearray)) else out
        except UnicodeDecodeError:
            return (None, None)
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return (None, None)
        parts = lines[-1].split()
        if len(parts) < 3:
            return (None, None)
        try:
            total = int(parts[1])
            used = int(parts[2])
        except (ValueError, IndexError):
            return (None, None)
        return (total, used)

    def __init__(self,
                 remote_address: str,
                 remote_username: str,
                 remote_password: Optional[str],
                 remote_port: int,
                 remote_path_to_scan: str,
                 local_path_to_scan_script: str,
                 remote_path_to_scan_script: str):
        self.logger = logging.getLogger("RemoteScanner")
        self.__remote_path_to_scan = remote_path_to_scan
        self.__local_path_to_scan_script = local_path_to_scan_script
        self.__remote_path_to_scan_script = remote_path_to_scan_script
        self.__ssh = Sshcp(host=remote_address,
                           port=remote_port,
                           user=remote_username,
                           password=remote_password)
        self.__install_done = False  # Whether scanfs has been installed successfully
        self.__first_run = True     # Whether the first successful scan has completed

        # Append scan script name to remote path if not there already
        script_name = os.path.basename(self.__local_path_to_scan_script)
        if os.path.basename(self.__remote_path_to_scan_script) != script_name:
            self.__remote_path_to_scan_script = os.path.join(self.__remote_path_to_scan_script, script_name)

    @overrides(IScanner)
    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("RemoteScanner")
        self.__ssh.set_base_logger(self.logger)

    def __to_scanner_error(self, e: SshcpError) -> ScannerError:
        """Convert a non-retried main-scan SshcpError to a ScannerError, preserving
        the existing __first_run-aware recoverable classification byte-for-byte.

        This is the immediate-raise branch for the main scan: SystemScannerError
        and permanent errors are fatal; before the first successful scan a
        non-transient error is fatal (so the user is prompted); transient
        timeout/refused stay recoverable (and recover on the next scan interval).
        Name-resolution exhaustion does NOT go through here — the scan() caller
        raises recoverable=False for it directly (SCAN-03).
        """
        recoverable = True
        # Any scanner errors are fatal, regardless of transience
        if "SystemScannerError" in str(e):
            recoverable = False
        # Permanent SSH errors (wrong password, host key changed, bad
        # hostname) are always fatal — retrying won't help.
        elif self._is_permanent_ssh_error(e):
            recoverable = False
        # Before the first successful scan, non-transient errors are
        # fatal so the user is prompted to correct them. Transient
        # network issues (timeouts, connection refused) are retried.
        elif self.__first_run and not self._is_transient_ssh_error(e):
            recoverable = False
        return ScannerError(
            Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()),
            recoverable=recoverable
        )

    def __sleep_backoff(self, attempt: int):
        """Sleep a bounded, jittered exponential backoff before the next attempt.

        Backoff/shutdown tradeoff (Phase 114 D-02): this uses a bare time.sleep
        with a low __SCAN_BACKOFF_CEILING_SECS ceiling rather than wiring the
        scanner process's terminate Event into RemoteScanner. During a backoff
        sleep the scanner child cannot observe its terminate Event, so a shutdown
        landing mid-backoff may hit the AppProcess 1s terminate poll and
        force-terminate (safe, just slightly noisy). This is accepted to keep the
        change minimal and avoid adding a non-trivial attribute to a spawn-pickled
        object. Documented ONCE here because the shared helper applies it to both
        the main-scan and install paths.
        """
        delay = self.__SCAN_BACKOFF_BASE_SECS * (2 ** (attempt - 1))
        delay = min(delay, self.__SCAN_BACKOFF_CEILING_SECS)
        jitter = delay * self.__SCAN_BACKOFF_JITTER
        delay = delay + random.uniform(-jitter, jitter)
        if delay > 0:
            time.sleep(delay)

    def __ssh_call_with_name_resolution_retry(self,
                                              ssh_call: Callable[[], object],
                                              op_label: str) -> object:
        """Run an SSH op with a bounded, NAME-RESOLUTION-ONLY retry + backoff.

        The single retry gate is _is_name_resolution_ssh_error (any resolver-string
        surface, case-insensitive). On a non-retryable error (transient
        timeout/refused, permanent, SystemScannerError) OR on name-resolution
        exhaustion the original SshcpError is RE-RAISED unchanged, so each caller's
        own except converts it on its own path (main scan -> __to_scanner_error /
        REMOTE_SERVER_SCAN; install -> the existing REMOTE_SERVER_INSTALL except).
        The helper itself NEVER constructs a ScannerError, so each path keeps its
        localized message + recoverable rule and SCAN-03 stays byte-for-byte.

        Used by BOTH the main scan SSH call and the install-path md5sum/copy ops.

        Args:
            ssh_call: Zero-argument callable performing the SSH op; its result is
                returned on success.
            op_label: Short literal describing the op, for logging only.

        Returns:
            The result of ssh_call() on success.
        """
        for attempt in range(1, self.__SCAN_MAX_ATTEMPTS + 1):
            try:
                return ssh_call()
            except SshcpError as e:
                self.logger.warning(
                    "Caught an SshcpError during %s (attempt %d/%d): %s",
                    op_label, attempt, self.__SCAN_MAX_ATTEMPTS,
                    sanitize_log_value(str(e)))
                # The SOLE retry gate is name-resolution (any resolver-string
                # surface, case-insensitive). Transient timeout/refused are NOT
                # retried in-scan.
                retryable = self._is_name_resolution_ssh_error(e)
                if not retryable:
                    raise   # transient/permanent/SystemScannerError — not retried
                if attempt < self.__SCAN_MAX_ATTEMPTS:
                    self.__sleep_backoff(attempt)
                    continue
                raise       # name-resolution exhausted — re-raise unchanged

    @overrides(IScanner)
    def scan(self) -> Tuple[List[SystemFile], Optional[int], Optional[int]]:
        if not self.__install_done:
            self._install_scanfs()
            self.__install_done = True

        try:
            out = self.__ssh_call_with_name_resolution_retry(
                lambda: self.__ssh.shell("{} {}".format(
                    shlex.quote(self.__remote_path_to_scan_script),
                    shlex.quote(self.__remote_path_to_scan))),
                "main scan"
            )
        except SshcpError as e:
            # A name-resolution error reaching here means the bounded retry
            # exhausted (collapsed OR raw resolver surface) — surface fatal with
            # the unchanged REMOTE_SERVER_SCAN message (SCAN-03 byte-for-byte).
            if self._is_name_resolution_ssh_error(e):
                raise ScannerError(
                    Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()),
                    recoverable=False
                )
            # Transient/permanent/SystemScannerError were re-raised by the helper
            # on the first attempt — convert with the existing __first_run-aware
            # recoverable classification.
            raise self.__to_scanner_error(e)

        try:
            out_str = out.decode('utf-8') if isinstance(out, bytes) else out
            file_dicts = json.loads(out_str)
            remote_files = [SystemFile.from_dict(d) for d in file_dicts]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as err:
            # out_str (line 114, inside the try) is NOT guaranteed defined here —
            # if the decode at line 114 itself raised (UnicodeDecodeError is a
            # ValueError subclass and is caught by this except), out_str would be
            # undefined (NameError). Derive a safe string locally with errors='replace'
            # to avoid any decode exception, then sanitize BOTH values (CWE-117).
            safe_out = out.decode('utf-8', errors='replace') if isinstance(out, bytes) else str(out)
            self.logger.error("JSON decode error: {}\n{}".format(
                sanitize_log_value(str(err)),
                sanitize_log_value(safe_out)))
            raise ScannerError(
                Localization.Error.REMOTE_SERVER_SCAN.format("Invalid scan data"),
                recoverable=False
            )

        self.__first_run = False

        # Capacity collection — silent fallback per D-16 (ancillary, never fatal)
        total_bytes: Optional[int] = None
        used_bytes: Optional[int] = None
        try:
            df_out = self.__ssh.shell("df -B1 {}".format(shlex.quote(self.__remote_path_to_scan)))
            total_bytes, used_bytes = RemoteScanner._parse_df_output(df_out)
            if total_bytes is None or used_bytes is None:
                self.logger.warning("df output parse failed for '%s': %r",
                                    self.__remote_path_to_scan, df_out)
        except SshcpError as err:
            self.logger.warning("df SSH call failed for '%s': %s",
                                self.__remote_path_to_scan, err)

        return remote_files, total_bytes, used_bytes

    def _install_scanfs(self):
        # Check md5sum on remote to see if we can skip installation
        with open(self.__local_path_to_scan_script, "rb") as f:
            local_md5sum = hashlib.md5(f.read()).hexdigest()
        self.logger.debug("Local scanfs md5sum = {}".format(local_md5sum))
        try:
            out = self.__ssh_call_with_name_resolution_retry(
                lambda: self.__ssh.shell(
                    "md5sum {} | awk '{{print $1}}' || echo".format(
                        shlex.quote(self.__remote_path_to_scan_script))),
                "scanfs install md5sum"
            )
            out = out.decode('utf-8').strip()
            if out == local_md5sum:
                self.logger.info("Skipping remote scanfs installation: already installed")
                return
        except SshcpError as e:
            self.logger.exception("Caught scp exception")
            raise ScannerError(
                Localization.Error.REMOTE_SERVER_INSTALL.format(str(e).strip()),
                recoverable=self._is_transient_ssh_error(e)
            )

        # Go ahead and install
        self.logger.info("Installing local:{} to remote:{}".format(
            self.__local_path_to_scan_script,
            self.__remote_path_to_scan_script
        ))
        if not os.path.isfile(self.__local_path_to_scan_script):
            raise ScannerError(
                Localization.Error.REMOTE_SERVER_SCAN.format(
                    "Failed to find scanfs executable at {}".format(self.__local_path_to_scan_script)
                ),
                recoverable=False
            )
        try:
            self.__ssh_call_with_name_resolution_retry(
                lambda: self.__ssh.copy(
                    local_path=self.__local_path_to_scan_script,
                    remote_path=self.__remote_path_to_scan_script),
                "scanfs install copy"
            )
        except SshcpError as e:
            self.logger.exception("Caught scp exception")
            raise ScannerError(
                Localization.Error.REMOTE_SERVER_INSTALL.format(str(e).strip()),
                recoverable=self._is_transient_ssh_error(e)
            )
