import threading
from typing import List, Optional, Callable

from common import Context, MultiprocessingLogger, AppOneShotProcess, sanitize_log_value
from model import ModelFile
from .extract import ExtractProcess, ExtractStatus
from .delete import DeleteLocalProcess, DeleteRemoteProcess
from .root_reservation import RootReservation

class CommandProcessWrapper:
    """
    Wraps any one-shot command processes launched by the file operation manager.

    ``reservation`` is the per-root reservation the wrapper owns while its
    child runs (local deletions only); it is released once the child is
    observed dead, on launch failure, or on stop().
    """
    def __init__(self,
                 process: AppOneShotProcess,
                 post_callback: Callable,
                 reservation: Optional[RootReservation] = None):
        self.process = process
        self.post_callback = post_callback
        self.reservation = reservation

class FileOperationManager:
    """
    Manages file operations (extract, delete) and their processes.

    Responsible for:
    - Extract process lifecycle and operations
    - Delete process creation and tracking (local and remote)
    - Command process cleanup
    - Active extracting file tracking

    Thread-safety: The ExtractProcess uses multiprocessing queues which are
    inherently thread-safe. Delete processes are one-shot and tracked in a
    list guarded by __processes_lock: delete_local is called from the
    auto-delete Timer thread as well as the controller thread, while
    cleanup_completed_processes sweeps the list on the controller thread.
    The lock is a leaf: it is held only to append to or swap the list, never
    while starting a process, running a callback, releasing a reservation or
    propagating an exception.

    Root reservations: delete_local may be handed the per-root reservation
    (see root_reservation.py). The wrapper owns it for the child's whole
    lifetime, because delete_local returns as soon as the child has started
    and the deletion itself runs afterwards.

    Leak bound: a reservation handed to delete_local is released at the
    latest on the first Controller.process() cycle after the child dies, on
    launch failure, or by stop(); the registry is process-local, so a restart
    starts empty. One residual: a stop() that runs while another thread is
    between start() returning and the append in __launch_and_track does not
    see that wrapper; its token then stays in the registry until the app
    exits, which is harmless because Controller.exit() is terminal (no
    further QUEUE is processed) and the registry does not persist.
    """

    def __init__(self,
                 context: Context,
                 mp_logger: MultiprocessingLogger,
                 force_local_scan_callback: Callable,
                 force_remote_scan_callback: Callable):
        """
        Create the file operation manager.

        Args:
            context: Application context with config and logger
            mp_logger: Multiprocessing logger for child processes
            force_local_scan_callback: Callback to trigger a local scan after delete
            force_remote_scan_callback: Callback to trigger a remote scan after delete
        """
        self.__context = context
        self.__mp_logger = mp_logger
        self.logger = context.logger.getChild("FileOperationManager")
        self.__force_local_scan = force_local_scan_callback
        self.__force_remote_scan = force_remote_scan_callback

        # Decide the password for remote operations
        self.__password = (
            context.config.lftp.remote_password
            if not context.config.lftp.use_ssh_key
            else None
        )

        # Setup extract process
        if context.config.controller.use_local_path_as_extract_path:
            out_dir_path = context.config.lftp.local_path
        else:
            out_dir_path = context.config.controller.extract_path
        self.__extract_process = ExtractProcess(
            out_dir_path=out_dir_path,
            local_path=context.config.lftp.local_path
        )
        self.__extract_process.set_multiprocessing_logger(mp_logger)

        # Track active extracting files
        self.__active_extracting_file_names: List[str] = []

        # Track active command processes (delete operations); guarded by
        # __processes_lock because the auto-delete Timer thread appends too
        self.__active_command_processes: List[CommandProcessWrapper] = []
        self.__processes_lock = threading.Lock()

        self.__started = False

    def start(self) -> None:
        """
        Start the extract process.

        Must be called after construction and before using extract operations.
        """
        self.logger.debug("Starting file operation manager")
        self.__extract_process.start()
        self.__started = True

    def stop(self) -> None:
        """
        Stop the extract process and wait for it to terminate.

        Safe to call multiple times or if not started. Releases every root
        reservation still owned by a tracked delete process (the children are
        not joined); this runs even when the manager was never started.
        """
        with self.__processes_lock:
            wrappers = list(self.__active_command_processes)
        for wrapper in wrappers:
            if wrapper.reservation is not None:
                wrapper.reservation.release()
                self.logger.debug("Released root reservation for '{}' on stop".format(
                    sanitize_log_value(wrapper.reservation.name)
                ))

        if not self.__started:
            return

        self.logger.debug("Stopping file operation manager")
        self.__extract_process.terminate()
        self.__extract_process.join()
        self.__started = False
        self.logger.debug("File operation manager stopped")

    def extract(self, file: ModelFile) -> None:
        """
        Queue a file for extraction.

        Args:
            file: The model file to extract
        """
        self.__extract_process.extract(file)

    def pop_extract_statuses(self) -> Optional[object]:
        """
        Get the latest extract statuses.

        Returns:
            Extract statuses object, or None if no new statuses available.
        """
        return self.__extract_process.pop_latest_statuses()

    def pop_completed_extractions(self) -> List:
        """
        Get completed extraction results.

        Returns:
            List of completed extraction results.
        """
        return self.__extract_process.pop_completed()

    def get_active_extracting_file_names(self) -> List[str]:
        """
        Get the list of files currently being extracted.

        Returns:
            List of file names being extracted.
        """
        return self.__active_extracting_file_names

    def update_active_extracting_files(self, extract_statuses: Optional[object]) -> None:
        """
        Update the list of actively extracting files based on extract statuses.

        Args:
            extract_statuses: Current extract statuses, or None.
        """
        if extract_statuses is not None:
            self.__active_extracting_file_names = [
                s.name for s in extract_statuses.statuses
                if s.state == ExtractStatus.State.EXTRACTING
            ]

    def __launch_and_track(self, wrapper: CommandProcessWrapper) -> None:
        """
        Start the wrapper's process, then register it for cleanup.

        Start, then register -- deliberately; do not reorder to
        append-then-start. multiprocessing.Process.is_alive() is False until
        start() has run, and cleanup_completed_processes keys on is_alive()
        alone. A wrapper registered before start() could be reaped as
        "finished" by a concurrent Controller.process() cycle and its
        reservation released before the deletion even began. Registering only
        after start() returned makes that interleaving impossible without any
        launch-state bookkeeping. This is the only place a wrapper is ever
        appended.

        On start() failure nothing is registered, the reservation (if any) is
        released inline and the exception propagates.
        """
        try:
            wrapper.process.start()
        except Exception:
            if wrapper.reservation is not None:
                wrapper.reservation.release()
            raise
        with self.__processes_lock:
            self.__active_command_processes.append(wrapper)

    def delete_local(self, file: ModelFile, reservation: Optional[RootReservation] = None) -> bool:
        """
        Start a local file deletion process.

        Returns as soon as the child has started; the deletion itself runs in
        the child afterwards.

        Args:
            file: The model file to delete locally
            reservation: Optional per-root reservation. From entry the manager
                owns it and releases it when the child is observed dead, on
                launch failure, or on stop(); the caller must not release it
                afterwards.

        Returns:
            True if delete process was started successfully
        """
        try:
            process = DeleteLocalProcess(
                local_path=self.__context.config.lftp.local_path,
                file_name=file.name
            )
            process.set_multiprocessing_logger(self.__mp_logger)
        except Exception:
            if reservation is not None:
                reservation.release()
            raise
        wrapper = CommandProcessWrapper(
            process=process,
            post_callback=self.__force_local_scan,
            reservation=reservation
        )
        self.__launch_and_track(wrapper)
        return True

    def delete_remote(self, file: ModelFile) -> bool:
        """
        Start a remote file deletion process.

        Args:
            file: The model file to delete remotely

        Returns:
            True if delete process was started successfully
        """
        process = DeleteRemoteProcess(
            remote_address=self.__context.config.lftp.remote_address,
            remote_username=self.__context.config.lftp.remote_username,
            remote_password=self.__password,
            remote_port=self.__context.config.lftp.remote_port,
            remote_path=self.__context.config.lftp.remote_path,
            file_name=file.name
        )
        process.set_multiprocessing_logger(self.__mp_logger)
        wrapper = CommandProcessWrapper(
            process=process,
            post_callback=self.__force_remote_scan
        )
        self.__launch_and_track(wrapper)
        return True

    def cleanup_completed_processes(self) -> None:
        """
        Cleanup completed command processes and execute their callbacks.

        Should be called periodically to clean up finished delete operations
        and trigger any post-operation callbacks (like forcing a scan).

        A finished wrapper's root reservation is released whatever the
        child's exit status, before its exception is propagated, so a crashed
        child can never pin the root. Keying on is_alive() alone is sound
        because only started children are ever registered (__launch_and_track).
        """
        with self.__processes_lock:
            snapshot = list(self.__active_command_processes)
        still_active = []
        finished = []
        for wrapper in snapshot:
            if wrapper.process.is_alive():
                still_active.append(wrapper)
            else:
                finished.append(wrapper)

        # Swap the list first; wrappers appended by another thread during the
        # sweep are kept.
        with self.__processes_lock:
            snapshot_ids = {id(w) for w in snapshot}
            appended = [w for w in self.__active_command_processes if id(w) not in snapshot_ids]
            self.__active_command_processes = still_active + appended

        for index, wrapper in enumerate(finished):
            try:
                try:
                    # Do the post callback
                    wrapper.post_callback()
                finally:
                    if wrapper.reservation is not None:
                        wrapper.reservation.release()
                # Propagate any exception
                wrapper.process.propagate_exception()
            except Exception:
                # Keep the not-yet-handled finished wrappers tracked so the
                # next sweep (or stop()) still runs their callbacks and
                # releases their reservations.
                with self.__processes_lock:
                    self.__active_command_processes.extend(finished[index + 1:])
                raise

    def propagate_exception(self) -> None:
        """
        Propagate any exceptions from the extract process.

        Should be called periodically to detect and re-raise any errors.

        Raises:
            Any exception that occurred in the extract process.
        """
        self.__extract_process.propagate_exception()
