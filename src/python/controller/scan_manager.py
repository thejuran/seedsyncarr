import signal
import threading
import time
from typing import Callable, List, Optional, Tuple

from common import Context, MultiprocessingLogger, AppError
from .scan import ScannerProcess, ScannerResult, ActiveScanner, LocalScanner, RemoteScanner


class ScannerProcessDiedError(AppError):
    """Raised when a scanner process has died unexpectedly without reporting an exception."""


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
    - Health monitoring (detecting dead processes)

    Thread-safety: The scanner processes run in separate processes and communicate
    via multiprocessing queues, which are inherently thread-safe. The ScanManager
    methods can be called from any thread.
    """

    # GAP-1: docker's default stop timeout. The live main-thread SIGTERM
    # handler latency was measured at 0.67-1.55 s (123-06), so the grace
    # window must comfortably exceed that while still being bounded by the
    # same deadline docker itself uses before escalating to SIGKILL.
    _SIGTERM_SHUTDOWN_GRACE_IN_SECS = 10.0

    def __init__(self,
                 context: Context,
                 mp_logger: MultiprocessingLogger,
                 clock: Callable[[], float] = time.monotonic):
        """
        Create the scan manager with all scanner processes.

        Args:
            context: Application context with config
            mp_logger: Multiprocessing logger for child processes
            clock: monotonic clock, injectable for tests
        """
        self.__context = context
        self.logger = context.logger.getChild("ScanManager")

        # Decide the password here
        password = context.config.lftp.remote_password if not context.config.lftp.use_ssh_key else None

        # Create the scanners. In-flight copies are always *.lftp (temp-file
        # transfers are forced on), so the local scanners always map the suffix.
        self.__active_scanner = ActiveScanner(
            context.config.lftp.local_path,
            use_temp_file=True
        )
        self.__local_scanner = LocalScanner(
            local_path=context.config.lftp.local_path,
            use_temp_file=True
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
        self.__clock = clock

        # D-01: set by the main thread's SIGTERM/SIGINT handler (via
        # Controller.note_shutdown_requested()) before it raises ServiceExit.
        # Read only by _check_process_health() to decide whether a dead
        # scanner is an expected stop or a genuine failure -- it never stops
        # anything itself and is independent of __started.
        self.__shutdown_requested = threading.Event()
        # GAP-1: records the clock reading (self.__clock()) when an
        # all-SIGTERM death was first seen without a shutdown request yet;
        # cleared implicitly whenever the manager is stopped and started
        # again via a fresh ScanManager instance.
        self.__sigterm_first_seen: Optional[float] = None

    def note_shutdown_requested(self) -> None:
        """
        Record that the main thread's SIGTERM/SIGINT handler has run.

        Called from the main thread (via Controller.note_shutdown_requested())
        before it raises ServiceExit. This only changes how the next health
        check reports scanner processes that are found dead -- it never
        stops anything itself and does not touch __started.
        """
        self.__shutdown_requested.set()

    def start(self) -> None:
        """
        Start all scanner processes.

        Must be called after construction and before pop_latest_results().

        If a process fails to start partway through, every process that
        already started is terminated and joined before the original
        exception propagates; processes never reached are left untouched.
        """
        self.logger.debug("Starting scanner processes")
        started = []
        for name, process in (("ActiveScanner", self.__active_scan_process),
                               ("LocalScanner", self.__local_scan_process),
                               ("RemoteScanner", self.__remote_scan_process)):
            try:
                process.start()
            except Exception:
                self.logger.error(
                    "Scanner start failed at {}; stopping {} already-started process(es) "
                    "after a failed scanner start".format(name, len(started))
                )
                self._terminate_and_join(started)
                raise
            started.append((name, process))
        self.__started = True

    def stop(self) -> None:
        """
        Terminate and join all scanner processes.

        Safe to call multiple times or if not started.
        """
        if not self.__started:
            return
        self.__started = False
        self._terminate_and_join_all()

    def _terminate_and_join_all(self) -> None:
        """Terminate and join all scanner processes unconditionally."""
        self.logger.debug("Stopping scanner processes")
        self._terminate_and_join([
            ("ActiveScanner", self.__active_scan_process),
            ("LocalScanner", self.__local_scan_process),
            ("RemoteScanner", self.__remote_scan_process),
        ])
        self.logger.debug("Scanner processes stopped")

    def _terminate_and_join(self, processes) -> None:
        """
        Terminate and join each ``(name, process)`` pair independently.

        One process's terminate() or join() raising does not skip the
        others: every raised error is logged via logger.exception, never
        swallowed silently. A process whose terminate() raised is not
        joined -- it may still be running, and join() has no bound, so
        joining it could block shutdown indefinitely.
        """
        joinable = []
        for name, process in processes:
            try:
                process.terminate()
            except Exception:
                self.logger.exception("Error terminating {} process".format(name))
            else:
                joinable.append((name, process))
        for name, process in joinable:
            try:
                process.join()
            except Exception:
                self.logger.exception("Error joining {} process".format(name))

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

    def update_active_files(self, file_names: List[str]) -> None:
        """
        Update the list of actively downloading/extracting files.

        This tells the active scanner which files to scan. The active scanner
        only scans files in this list, which allows for more frequent scans
        of actively changing files without scanning the entire filesystem.

        Args:
            file_names: List of file names currently active (downloading or extracting).
        """
        self.__active_scanner.set_active_files(file_names)

    def propagate_exceptions(self) -> None:
        """
        Propagate any exceptions from scanner processes to the caller.

        Also checks that all scanner processes are still alive. If a process
        has died without reporting an exception (e.g., killed by OOM or SIGKILL),
        raises ScannerProcessDiedError.

        Should be called periodically to detect and re-raise any errors
        that occurred in the scanner processes.

        Raises:
            Any exception that occurred in a scanner process.
            ScannerProcessDiedError if a process died without reporting an error.
        """
        # Drain exception queues first: if a process reported an error before dying,
        # the specific exception takes priority over the generic ScannerProcessDiedError.
        self.__active_scan_process.propagate_exception()
        self.__local_scan_process.propagate_exception()
        self.__remote_scan_process.propagate_exception()

        # Health check: detect processes that died without putting an exception
        # on the queue (e.g., SIGKILL, OOM killer, segfault).
        if self.__started:
            self._check_process_health()

    def _check_process_health(self) -> None:
        """
        Verify all scanner processes are still alive.

        If a process has died without reporting an exception via the exception
        queue, this raises ScannerProcessDiedError so the controller can
        handle the failure (e.g., restart or shut down gracefully).

        This catches the case where a process is killed externally (OOM, SIGKILL)
        and no exception reaches the parent process.

        GAP-1 (D-01, D-07): the container runs under `tini -g`, which forwards
        the container's SIGTERM to the whole process group. The forked scanner
        children run SIGTERM as SIG_DFL, so the kernel kills them the instant
        the main process receives the signal. The main thread's own handler
        (note_shutdown_requested()) does not necessarily run anywhere near
        that instant: CPython only runs Python-level signal handlers on the
        main thread, at its next bytecode boundary, and live measurement
        (123-06) found that handler running 0.67 to 1.55 s after the
        scanners died -- long enough to lose a one-ControllerJob-cycle grace.
        The decision is therefore made on a monotonic-clock window instead of
        a cycle count, so it does not depend on handler latency:

          (a) Shutdown is already requested: every dead process here is an
              expected stop, regardless of exitcode (INFO, no raise).
          (b) Shutdown is NOT yet requested, but every dead process was
              killed by SIGTERM: this is the same race as (a), just not yet
              resolved. The deadline is fixed at the first sighting and is
              _SIGTERM_SHUTDOWN_GRACE_IN_SECS (10.0 s, docker's default stop
              timeout) wide, so on a real `docker stop`/`docker restart`
              either the handler runs inside the window or docker SIGKILLs
              the container when the window ends -- the false ERROR cannot
              fire on that path whatever the handler latency. Any other
              death (OOM's SIGKILL, a non-zero exit, a mix that includes a
              non-SIGTERM code) is never given this grace period and raises
              on the same check it is first seen.

        Documented cost: a genuine SIGTERM-only death with no shutdown
        request surfaces up to 10 s plus one ControllerJob cycle later than
        before this change.
        """
        dead = []
        for name, process in (
                ("RemoteScanner", self.__remote_scan_process),
                ("LocalScanner", self.__local_scan_process),
                ("ActiveScanner", self.__active_scan_process)):
            if not process.is_alive():
                dead.append((name, process))

        if not dead:
            return

        if self.__shutdown_requested.is_set():
            self.__started = False
            names = ", ".join(
                "{} (exitcode {})".format(name, process.exitcode) for name, process in dead
            )
            self.logger.info(
                "Scanner process(es) stopped during shutdown: {}".format(names)
            )
            self._terminate_and_join_all()
            return

        if all(process.exitcode == -signal.SIGTERM for _, process in dead):
            now = self.__clock()
            if self.__sigterm_first_seen is None:
                self.__sigterm_first_seen = now
                names = ", ".join(name for name, _ in dead)
                self.logger.debug(
                    "Scanner process(es) ended by SIGTERM: {}; waiting up to {} s "
                    "for the shutdown request before reporting".format(
                        names, self._SIGTERM_SHUTDOWN_GRACE_IN_SECS
                    )
                )
                return
            if now - self.__sigterm_first_seen < self._SIGTERM_SHUTDOWN_GRACE_IN_SECS:
                return

        self.__started = False
        names = ", ".join(name for name, _ in dead)
        self.logger.error(
            "Scanner process(es) died unexpectedly: {}".format(names)
        )
        self._terminate_and_join_all()
        raise ScannerProcessDiedError(
            "A scanner process stopped unexpectedly. Please check server logs for details."
        )

    def force_local_scan(self) -> None:
        """
        Force an immediate local scan.

        Use after local file operations (e.g., deletion) to quickly
        update the model with the new filesystem state.
        """
        self.__local_scan_process.force_scan()

    def force_remote_scan(self) -> None:
        """
        Force an immediate remote scan.

        Use after remote file operations (e.g., deletion) to quickly
        update the model with the new filesystem state.
        """
        self.__remote_scan_process.force_scan()
