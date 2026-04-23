from typing import List, Optional

from common import Context, Constants
from lftp import Lftp, LftpError, LftpJobStatus, LftpJobStatusParserError

class LftpManager:
    """
    Manages the LFTP process for file transfers.

    Responsible for:
    - LFTP initialization and configuration
    - Queue/stop command execution
    - Status collection
    - Lifecycle management (exit)
    - Exception propagation

    Thread-safety: The Lftp class handles its own thread safety for the
    underlying LFTP process communication. LftpManager methods can be
    called from any thread.
    """

    def __init__(self, context: Context):
        """
        Create the LFTP manager with configured LFTP instance.

        Args:
            context: Application context with config and logger
        """
        self.__context = context
        self.logger = context.logger.getChild("LftpManager")

        # Decide the password here
        password = context.config.lftp.remote_password if not context.config.lftp.use_ssh_key else None

        # Create and configure LFTP
        self.__lftp = Lftp(
            address=context.config.lftp.remote_address,
            port=context.config.lftp.remote_port,
            user=context.config.lftp.remote_username,
            password=password
        )
        self.__lftp.set_base_logger(self.logger)
        self.__lftp.set_base_remote_dir_path(context.config.lftp.remote_path)
        self.__lftp.set_base_local_dir_path(context.config.lftp.local_path)

        # Configure LFTP parameters
        self.__lftp.num_parallel_jobs = context.config.lftp.num_max_parallel_downloads
        self.__lftp.num_parallel_files = context.config.lftp.num_max_parallel_files_per_download
        self.__lftp.num_connections_per_root_file = context.config.lftp.num_max_connections_per_root_file
        self.__lftp.num_connections_per_dir_file = context.config.lftp.num_max_connections_per_dir_file
        self.__lftp.num_max_total_connections = context.config.lftp.num_max_total_connections
        self.__lftp.use_temp_file = context.config.lftp.use_temp_file
        self.__lftp.temp_file_name = "*" + Constants.LFTP_TEMP_FILE_SUFFIX
        self.__lftp.set_verbose_logging(context.config.general.verbose)

        # Apply rate limit from config (0 = unlimited)
        if context.config.lftp.rate_limit is not None and context.config.lftp.rate_limit > 0:
            self.__lftp.rate_limit = context.config.lftp.rate_limit

        # Track the last-applied rate_limit so we only send the lftp command
        # when the config value actually changes at runtime.
        self.__applied_rate_limit = context.config.lftp.rate_limit

    @property
    def lftp(self) -> Lftp:
        """
        Direct access to the underlying Lftp instance.

        This property is primarily intended for testing purposes where
        white-box access to Lftp parameters (like rate_limit) is needed.

        Returns:
            The underlying Lftp instance.
        """
        return self.__lftp

    def __sync_rate_limit(self) -> None:
        """
        Re-apply rate_limit from the live config if it changed since the last
        queue() call.  The config set REST API updates config.lftp.rate_limit
        in memory; this method propagates that change to the running lftp
        process so e2e tests (and users) can throttle downloads at runtime
        without restarting the app.

        A value of 0 means unlimited (lftp default).
        """
        current = self.__context.config.lftp.rate_limit
        if current != self.__applied_rate_limit:
            self.logger.info("rate_limit changed: {} -> {}".format(
                self.__applied_rate_limit, current
            ))
            self.__lftp.rate_limit = current if current is not None else 0
            self.__applied_rate_limit = current

    def queue(self, file_name: str, is_dir: bool) -> None:
        """
        Queue a file or directory for download.

        Syncs the rate_limit from config before issuing the lftp queue command
        so that runtime config changes (via the REST API) take effect on the
        next download without requiring an app restart.

        Args:
            file_name: Name of the file/directory to queue
            is_dir: True if the target is a directory

        Raises:
            LftpError: If LFTP fails to queue the file
        """
        self.__sync_rate_limit()
        self.__lftp.queue(file_name, is_dir)

    def kill(self, file_name: str) -> None:
        """
        Stop/kill a queued or downloading transfer.

        Args:
            file_name: Name of the file to stop

        Raises:
            LftpError: If LFTP fails to kill the transfer
            LftpJobStatusParserError: If status parsing fails
        """
        self.__lftp.kill(file_name)

    def status(self) -> Optional[List[LftpJobStatus]]:
        """
        Get the current status of all LFTP jobs.

        Returns:
            List of LftpJobStatus objects, or None if an error occurred.
        """
        try:
            return self.__lftp.status()
        except (LftpError, LftpJobStatusParserError) as e:
            self.logger.warning("Caught lftp error: {}".format(str(e)))
            return None

    def exit(self) -> None:
        """
        Exit the LFTP process.

        Safe to call multiple times.
        """
        self.__lftp.exit()

    def raise_pending_error(self) -> None:
        """
        Propagate any pending exceptions from the LFTP process.

        Should be called periodically to detect and re-raise any errors
        that occurred in the LFTP process.

        Raises:
            Any exception that occurred in the LFTP process.
        """
        self.__lftp.raise_pending_error()
