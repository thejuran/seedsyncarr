from typing import List, Optional, Tuple

from common import Context, MultiprocessingLogger
from .scan import ScannerProcess, ScannerResult, ActiveScanner, LocalScanner, RemoteScanner

class ScanManager:
    """
    Manages all scanning processes (remote, local, active).

    Responsible for:
    - Creating and owning scanner instances and their processes
    - Lifecycle management (start/stop)
    - Collecting scan results
    - Updating active file tracking
    - Exception propagation
    - Force scan triggers

    Thread-safety: The scanner processes run in separate processes and communicate
    via multiprocessing queues, which are inherently thread-safe. The ScanManager
    methods can be called from any thread.
    """

    def __init__(self,
                 context: Context,
                 mp_logger: MultiprocessingLogger):
        """
        Create the scan manager with all scanner processes.

        Args:
            context: Application context with config
            mp_logger: Multiprocessing logger for child processes
        """
        self.__context = context
        self.logger = context.logger.getChild("ScanManager")

        # Decide the password here
        password = context.config.lftp.remote_password if not context.config.lftp.use_ssh_key else None

        # Create the scanners
        self.__active_scanner = ActiveScanner(context.config.lftp.local_path)
        self.__local_scanner = LocalScanner(
            local_path=context.config.lftp.local_path,
            use_temp_file=context.config.lftp.use_temp_file
        )
        self.__remote_scanner = RemoteScanner(
            remote_address=context.config.lftp.remote_address,
            remote_username=context.config.lftp.remote_username,
            remote_password=password,
            remote_port=context.config.lftp.remote_port,
            remote_path_to_scan=context.config.lftp.remote_path,
            local_path_to_scan_script=context.args.local_path_to_scanfs,
            remote_path_to_scan_script=context.config.lftp.remote_path_to_scan_script
        )

        # Create the scanner processes
        self.__active_scan_process = ScannerProcess(
            scanner=self.__active_scanner,
            interval_in_ms=context.config.controller.interval_ms_downloading_scan,
            verbose=False
        )
        self.__local_scan_process = ScannerProcess(
            scanner=self.__local_scanner,
            interval_in_ms=context.config.controller.interval_ms_local_scan,
        )
        self.__remote_scan_process = ScannerProcess(
            scanner=self.__remote_scanner,
            interval_in_ms=context.config.controller.interval_ms_remote_scan,
        )

        # Setup multiprocess logging
        self.__active_scan_process.set_multiprocessing_logger(mp_logger)
        self.__local_scan_process.set_multiprocessing_logger(mp_logger)
        self.__remote_scan_process.set_multiprocessing_logger(mp_logger)

        self.__started = False

    def start(self):
        """
        Start all scanner processes.

        Must be called after construction and before pop_latest_results().
        """
        self.logger.debug("Starting scanner processes")
        self.__active_scan_process.start()
        self.__local_scan_process.start()
        self.__remote_scan_process.start()
        self.__started = True

    def stop(self):
        """
        Terminate and join all scanner processes.

        Safe to call multiple times or if not started.
        """
        if not self.__started:
            return

        self.logger.debug("Stopping scanner processes")
        self.__active_scan_process.terminate()
        self.__local_scan_process.terminate()
        self.__remote_scan_process.terminate()
        self.__active_scan_process.join()
        self.__local_scan_process.join()
        self.__remote_scan_process.join()
        self.__started = False
        self.logger.debug("Scanner processes stopped")

    def pop_latest_results(self) -> Tuple[Optional[ScannerResult], Optional[ScannerResult], Optional[ScannerResult]]:
        """
        Get latest results from all scanner processes.

        Drains each scanner's result queue and returns the most recent result.
        This is a non-blocking operation.

        Returns:
            Tuple of (remote_result, local_result, active_result).
            Each element is None if no new result is available since the last call.
        """
        remote_result = self.__remote_scan_process.pop_latest_result()
        local_result = self.__local_scan_process.pop_latest_result()
        active_result = self.__active_scan_process.pop_latest_result()
        return remote_result, local_result, active_result

    def update_active_files(self, file_names: List[str]):
        """
        Update the list of actively downloading/extracting files.

        This tells the active scanner which files to scan. The active scanner
        only scans files in this list, which allows for more frequent scans
        of actively changing files without scanning the entire filesystem.

        Args:
            file_names: List of file names currently active (downloading or extracting).
        """
        self.__active_scanner.set_active_files(file_names)

    def propagate_exceptions(self):
        """
        Propagate any exceptions from scanner processes to the caller.

        Should be called periodically to detect and re-raise any errors
        that occurred in the scanner processes.

        Raises:
            Any exception that occurred in a scanner process.
        """
        self.__active_scan_process.propagate_exception()
        self.__local_scan_process.propagate_exception()
        self.__remote_scan_process.propagate_exception()

    def force_local_scan(self):
        """
        Force an immediate local scan.

        Use after local file operations (e.g., deletion) to quickly
        update the model with the new filesystem state.
        """
        self.__local_scan_process.force_scan()

    def force_remote_scan(self):
        """
        Force an immediate remote scan.

        Use after remote file operations (e.g., deletion) to quickly
        update the model with the new filesystem state.
        """
        self.__remote_scan_process.force_scan()
