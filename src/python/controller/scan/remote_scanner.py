import logging
import json
from typing import List, Optional, Tuple
import os
import hashlib
import shlex

from .scanner_process import IScanner, ScannerError
from common import overrides, Localization
from ssh import Sshcp, SshcpError, TRANSIENT_ERROR_PATTERNS, PERMANENT_ERROR_PATTERNS
from system import SystemFile

class RemoteScanner(IScanner):
    """
    Scanner implementation to scan the remote filesystem
    """

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
    def _parse_df_output(out) -> Tuple[Optional[int], Optional[int]]:
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

    @overrides(IScanner)
    def scan(self) -> Tuple[List[SystemFile], Optional[int], Optional[int]]:
        if not self.__install_done:
            self._install_scanfs()
            self.__install_done = True

        try:
            out = self.__ssh.shell("{} {}".format(
                shlex.quote(self.__remote_path_to_scan_script),
                shlex.quote(self.__remote_path_to_scan))
            )
        except SshcpError as e:
            self.logger.warning("Caught an SshcpError: {}".format(str(e)))
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
            raise ScannerError(
                Localization.Error.REMOTE_SERVER_SCAN.format(str(e).strip()),
                recoverable=recoverable
            )

        try:
            out_str = out.decode('utf-8') if isinstance(out, bytes) else out
            file_dicts = json.loads(out_str)
            remote_files = [SystemFile.from_dict(d) for d in file_dicts]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as err:
            self.logger.error("JSON decode error: {}\n{}".format(str(err), out))
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
            out = self.__ssh.shell("md5sum {} | awk '{{print $1}}' || echo".format(shlex.quote(self.__remote_path_to_scan_script)))
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
            self.__ssh.copy(local_path=self.__local_path_to_scan_script,
                            remote_path=self.__remote_path_to_scan_script)
        except SshcpError as e:
            self.logger.exception("Caught scp exception")
            raise ScannerError(
                Localization.Error.REMOTE_SERVER_INSTALL.format(str(e).strip()),
                recoverable=self._is_transient_ssh_error(e)
            )
