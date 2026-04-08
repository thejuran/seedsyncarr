from abc import ABC, abstractmethod
import collections
import threading
from typing import Dict, List, Optional, Tuple
from threading import Lock
from queue import Queue
from enum import Enum
import copy

from .scan_manager import ScanManager
from .lftp_manager import LftpManager
from .file_operation_manager import FileOperationManager
from .webhook_manager import WebhookManager
from .extract import ExtractStatusResult, ExtractCompletedResult
from .model_builder import ModelBuilder
from .scan import ScannerResult
from .memory_monitor import MemoryMonitor
from common import Context, AppError, MultiprocessingLogger
from model import ModelError, ModelFile, Model, ModelDiff, ModelDiffUtil, IModelListener
from lftp import LftpError, LftpJobStatus, LftpJobStatusParserError
from .controller_persist import ControllerPersist

class ControllerError(AppError):
    """
    Exception indicating a controller error
    """
    pass

class Controller:
    """
    Top-level class that controls the behaviour of the app
    """
    class Command:
        """
        Class by which clients of Controller can request Actions to be executed
        Supports callbacks by which clients can be notified of action success/failure
        Note: callbacks will be executed in Controller thread, so any heavy computation
              should be moved out of the callback
        """
        class Action(Enum):
            QUEUE = 0
            STOP = 1
            EXTRACT = 2
            DELETE_LOCAL = 3
            DELETE_REMOTE = 4

        class ICallback(ABC):
            """Command callback interface"""
            @abstractmethod
            def on_success(self):
                """Called on successful completion of action"""
                pass

            @abstractmethod
            def on_failure(self, error: str, error_code: int = 400):
                """
                Called on action failure.

                Args:
                    error: Human-readable error message
                    error_code: HTTP status code for the error (default 400)
                        - 400: Bad request (invalid state, validation error)
                        - 404: Resource not found
                        - 409: Conflict (resource in wrong state)
                        - 500: Internal server error
                """
                pass

        def __init__(self, action: Action, filename: str):
            self.action = action
            self.filename = filename
            self.callbacks = []

        def add_callback(self, callback: ICallback):
            self.callbacks.append(callback)

    def __init__(self,
                 context: Context,
                 persist: ControllerPersist,
                 webhook_manager: WebhookManager):
        self.__context = context
        self.__persist = persist
        self.__webhook_manager = webhook_manager
        self.logger = context.logger.getChild("Controller")
        # Set logger for persist to enable eviction logging
        self.__persist.set_base_logger(self.logger)

        # The command queue
        self.__command_queue = Queue()

        # The model
        self.__model = Model()
        self.__model.set_base_logger(self.logger)
        # Lock for the model
        # Note: While the scanners are in a separate process, the rest of the application
        #       is threaded in a single process. (The webserver is bottle+paste which is
        #       multi-threaded). Therefore it is safe to use a threading Lock for the model
        #       (the scanner processes never try to access the model)
        self.__model_lock = Lock()

        # Model builder
        self.__model_builder = ModelBuilder()
        self.__model_builder.set_base_logger(self.logger)
        self.__model_builder.set_downloaded_files(self.__persist.downloaded_file_names)
        self.__model_builder.set_extracted_files(self.__persist.extracted_file_names)

        # Setup multiprocess logging (needed by managers)
        self.__mp_logger = MultiprocessingLogger(self.logger)

        # Setup the LFTP manager
        self.__lftp_manager = LftpManager(context=self.__context)

        # Setup the scan manager
        self.__scan_manager = ScanManager(
            context=self.__context,
            mp_logger=self.__mp_logger
        )

        # Setup the file operation manager
        self.__file_op_manager = FileOperationManager(
            context=self.__context,
            mp_logger=self.__mp_logger,
            force_local_scan_callback=self.__scan_manager.force_local_scan,
            force_remote_scan_callback=self.__scan_manager.force_remote_scan
        )

        # Keep track of active downloading files
        self.__active_downloading_file_names = []

        # Memory monitor for detecting leaks
        self.__memory_monitor = MemoryMonitor()
        self.__memory_monitor.set_base_logger(self.logger)
        self.__memory_monitor.register_data_source(
            'downloaded_files',
            lambda: len(self.__persist.downloaded_file_names)
        )
        self.__memory_monitor.register_data_source(
            'extracted_files',
            lambda: len(self.__persist.extracted_file_names)
        )
        self.__memory_monitor.register_data_source(
            'stopped_files',
            lambda: len(self.__persist.stopped_file_names)
        )
        self.__memory_monitor.register_data_source(
            'model_files',
            lambda: len(self.__model.get_file_names())
        )
        # Register eviction stats for bounded collections
        self.__memory_monitor.register_data_source(
            'downloaded_evictions',
            lambda: self.__persist.downloaded_file_names.total_evictions
        )
        self.__memory_monitor.register_data_source(
            'extracted_evictions',
            lambda: self.__persist.extracted_file_names.total_evictions
        )
        self.__memory_monitor.register_data_source(
            'stopped_evictions',
            lambda: self.__persist.stopped_file_names.total_evictions
        )
        self.__memory_monitor.register_data_source(
            'imported_files',
            lambda: len(self.__persist.imported_file_names)
        )
        self.__memory_monitor.register_data_source(
            'imported_evictions',
            lambda: self.__persist.imported_file_names.total_evictions
        )

        # Pending auto-delete timers: file_name -> Timer
        self.__pending_auto_deletes: Dict[str, threading.Timer] = {}
        self.__auto_delete_lock = threading.Lock()

        self.__started = False

    def start(self):
        """
        Start the controller
        Must be called after ctor and before process()
        """
        self.logger.debug("Starting controller")
        self.__scan_manager.start()
        self.__file_op_manager.start()
        self.__mp_logger.start()
        self.__started = True

    def process(self):
        """
        Advance the controller state
        This method should return relatively quickly as the heavy lifting is done by concurrent tasks
        """
        if not self.__started:
            raise ControllerError("Cannot process, controller is not started")
        self.__propagate_exceptions()
        self.__file_op_manager.cleanup_completed_processes()
        self.__process_commands()
        self.__update_model()
        # Periodically log memory statistics
        self.__memory_monitor.log_stats_if_due()
        # Process webhook imports
        self.__check_webhook_imports()

    def exit(self):
        self.logger.debug("Exiting controller")
        if self.__started:
            # Cancel all pending auto-delete timers
            with self.__auto_delete_lock:
                for file_name, timer in list(self.__pending_auto_deletes.items()):
                    timer.cancel()
                    self.logger.debug("Canceled pending auto-delete for '{}'".format(file_name))
                self.__pending_auto_deletes.clear()

            self.__lftp_manager.exit()
            self.__scan_manager.stop()
            self.__file_op_manager.stop()
            self.__mp_logger.stop()
            self.__started = False
            self.logger.info("Exited controller")

    def get_model_files(self) -> List[ModelFile]:
        """
        Returns a copy of all the model files
        """
        with self.__model_lock:
            model_files = self.__get_model_files()
        return model_files

    def is_file_stopped(self, filename: str) -> bool:
        """
        Check if a file was explicitly stopped by the user.
        Used by AutoQueue to avoid re-queuing files that were stopped.

        :param filename: Name of the file to check
        :return: True if the file is in the stopped files set
        """
        return filename in self.__persist.stopped_file_names

    def is_file_downloaded(self, filename: str) -> bool:
        """
        Check if a file was previously downloaded successfully.
        Used by AutoQueue to avoid re-queuing files that were already
        downloaded but may have been moved/deleted by external tools (e.g., Sonarr).

        :param filename: Name of the file to check
        :return: True if the file is in the downloaded files set
        """
        result = filename in self.__persist.downloaded_file_names
        if not result:
            self.logger.debug(
                "File '{}' not in downloaded list (size={}, evictions={})".format(
                    filename,
                    len(self.__persist.downloaded_file_names),
                    self.__persist.downloaded_file_names.total_evictions
                )
            )
        return result

    def add_model_listener(self, listener: IModelListener):
        """
        Adds a listener to the controller's model
        """
        with self.__model_lock:
            self.__model.add_listener(listener)

    def remove_model_listener(self, listener: IModelListener):
        """
        Removes a listener from the controller's model
        """
        with self.__model_lock:
            self.__model.remove_listener(listener)

    def get_model_files_and_add_listener(self, listener: IModelListener):
        """
        Adds a listener and returns the current state of model files in one atomic operation
        This guarantees that model update events are not missed or duplicated for the clients
        Without an atomic operation, the following scenarios can happen:
            1. get_model() -> model updated -> add_listener()
               The model update never propagates to client
            2. add_listener() -> model updated -> get_model()
               The model update is duplicated on client side (once through listener, and once
               through the model).
        """
        with self.__model_lock:
            self.__model.add_listener(listener)
            model_files = self.__get_model_files()
        return model_files

    def queue_command(self, command: Command):
        self.__command_queue.put(command)

    def __get_model_files(self) -> List[ModelFile]:
        # Files are frozen (immutable) after being added to the model,
        # so we can safely return direct references without deep copying.
        # This significantly reduces memory churn on API requests.
        model_files = []
        for filename in self.__model.get_file_names():
            model_files.append(self.__model.get_file(filename))
        return model_files

    # =========================================================================
    # __update_model() helper methods
    # =========================================================================

    def _collect_scan_results(self) -> Tuple[Optional[ScannerResult], Optional[ScannerResult], Optional[ScannerResult]]:
        """
        Collect the latest scan results from all scanner processes.

        Returns:
            Tuple of (remote_scan, local_scan, active_scan) results.
            Each element is None if no new result is available.
        """
        return self.__scan_manager.pop_latest_results()

    def _collect_lftp_status(self) -> Optional[List[LftpJobStatus]]:
        """
        Collect the current LFTP job statuses.

        Returns:
            List of LftpJobStatus objects, or None if an error occurred.
        """
        return self.__lftp_manager.status()

    def _collect_extract_results(self) -> Tuple[Optional[ExtractStatusResult], List[ExtractCompletedResult]]:
        """
        Collect extract process status and completed extractions.

        Returns:
            Tuple of (extract_statuses, completed_extractions).
            extract_statuses is None if no new status available.
            completed_extractions is a list of completed extraction results.
        """
        latest_extract_statuses = self.__file_op_manager.pop_extract_statuses()
        latest_extracted_results = self.__file_op_manager.pop_completed_extractions()
        return latest_extract_statuses, latest_extracted_results

    def _set_import_status(self, model: Model, file_name: str) -> None:
        """
        Set import_status to IMPORTED on a model file if not already set.
        Creates a mutable copy, updates status, and writes back to model.

        Args:
            model: The model to update (may be the live model or a new model being built)
            file_name: Name of the file to update
        """
        try:
            file = model.get_file(file_name)
        except ModelError:
            return
        if file.import_status != ModelFile.ImportStatus.IMPORTED:
            new_file = copy.copy(file)
            # noinspection PyProtectedMember
            new_file._unfreeze()
            # Fix parent references after shallow copy so children point to new_file
            for child in new_file.get_children():
                child._ModelFile__parent = new_file
            new_file.import_status = ModelFile.ImportStatus.IMPORTED
            model.update_file(new_file)

    def _update_active_file_tracking(self,
                                     lftp_statuses: Optional[List[LftpJobStatus]],
                                     extract_statuses: Optional[ExtractStatusResult]) -> None:
        """
        Update the lists of actively downloading and extracting files.

        Also updates the active scanner with the combined list of active files.

        Args:
            lftp_statuses: Current LFTP job statuses, or None.
            extract_statuses: Current extract statuses, or None.
        """
        if lftp_statuses is not None:
            self.__active_downloading_file_names = [
                s.name for s in lftp_statuses if s.state == LftpJobStatus.State.RUNNING
            ]

        # Update the file operation manager's tracking of active extractions
        self.__file_op_manager.update_active_extracting_files(extract_statuses)

        # Update the active scanner's state via the scan manager
        self.__scan_manager.update_active_files(
            self.__active_downloading_file_names +
            self.__file_op_manager.get_active_extracting_file_names()
        )

    def _feed_model_builder(self,
                            remote_scan: Optional[ScannerResult],
                            local_scan: Optional[ScannerResult],
                            active_scan: Optional[ScannerResult],
                            lftp_statuses: Optional[List[LftpJobStatus]],
                            extract_statuses: Optional[ExtractStatusResult],
                            extracted_results: List) -> None:
        """
        Feed the model builder with all collected data.

        Updates the model builder's state with new scan results, LFTP statuses,
        and extract information. Also updates persist state for completed extractions.

        Args:
            remote_scan: Latest remote scan result, or None.
            local_scan: Latest local scan result, or None.
            active_scan: Latest active (downloading) scan result, or None.
            lftp_statuses: Current LFTP job statuses, or None.
            extract_statuses: Current extract statuses, or None.
            extracted_results: List of completed extraction results.
        """
        if remote_scan is not None:
            self.__model_builder.set_remote_files(remote_scan.files)
        if local_scan is not None:
            self.__model_builder.set_local_files(local_scan.files)
        if active_scan is not None:
            self.__model_builder.set_active_files(active_scan.files)
        if lftp_statuses is not None:
            self.__model_builder.set_lftp_statuses(lftp_statuses)
        if extract_statuses is not None:
            self.__model_builder.set_extract_statuses(extract_statuses.statuses)
        if extracted_results:
            for result in extracted_results:
                self.__persist.extracted_file_names.add(result.name)
            self.__model_builder.set_extracted_files(self.__persist.extracted_file_names)

    def _detect_and_track_queued(self, diff: ModelDiff) -> None:
        """
        Detect if a file has started downloading and update persist state.

        A file is added to tracking when it is DOWNLOADING and has local content
        (local_size > 0). This ensures that files which were started but never
        completed are still tracked and won't be auto-queued again.

        We don't track when merely QUEUED because stopping a queued file should
        return it to DEFAULT state, not mark it as DELETED.

        Args:
            diff: A single model diff entry.
        """
        new_file = diff.new_file
        if not new_file:
            return

        # Only track when DOWNLOADING with actual local content
        if new_file.state != ModelFile.State.DOWNLOADING:
            return
        if not new_file.local_size or new_file.local_size <= 0:
            return

        # Check if file is already tracked
        if new_file.name in self.__persist.downloaded_file_names:
            return

        # Check if this is a new transition to downloading with content
        should_track = False
        if diff.change == ModelDiff.Change.ADDED:
            should_track = True
        elif diff.change == ModelDiff.Change.UPDATED:
            old_file = diff.old_file
            old_state = old_file.state if old_file else None
            old_local_size = old_file.local_size if old_file else None

            # Track if transitioning from non-downloading state
            if old_state not in (ModelFile.State.DOWNLOADING, ModelFile.State.DOWNLOADED):
                should_track = True
            # Also track if was downloading but had no content before
            elif old_state == ModelFile.State.DOWNLOADING and (old_local_size is None or old_local_size <= 0):
                should_track = True

        if should_track:
            self.__persist.downloaded_file_names.add(new_file.name)
            self.__model_builder.set_downloaded_files(self.__persist.downloaded_file_names)

    def _detect_and_track_download(self, diff: ModelDiff) -> None:
        """
        Detect if a file was just downloaded and update persist state.

        A file is considered "just downloaded" if:
        - It was added in DOWNLOADED state, OR
        - It was updated and transitioned TO DOWNLOADED state from a non-DOWNLOADED state

        Note: Files are also tracked when downloading (see _detect_and_track_queued),
        so this mainly handles edge cases where a file appears already downloaded.

        Args:
            diff: A single model diff entry.
        """
        downloaded = False
        if diff.change == ModelDiff.Change.ADDED and \
                diff.new_file.state == ModelFile.State.DOWNLOADED:
            downloaded = True
        elif diff.change == ModelDiff.Change.UPDATED and \
                diff.new_file.state == ModelFile.State.DOWNLOADED and \
                diff.old_file.state != ModelFile.State.DOWNLOADED:
            downloaded = True

        if downloaded:
            self.__persist.downloaded_file_names.add(diff.new_file.name)
            self.__model_builder.set_downloaded_files(self.__persist.downloaded_file_names)

    def _prune_extracted_files(self) -> None:
        """
        Remove deleted files from the extracted files tracking list.

        This prevents files from going to EXTRACTED state if they are re-downloaded
        after being deleted locally.

        Must be called while holding the model lock.
        """
        remove_extracted_file_names = set()
        existing_file_names = self.__model.get_file_names()

        for extracted_file_name in self.__persist.extracted_file_names:
            if extracted_file_name in existing_file_names:
                file = self.__model.get_file(extracted_file_name)
                if file.state == ModelFile.State.DELETED:
                    # Deleted locally, remove
                    remove_extracted_file_names.add(extracted_file_name)
            # Note: Files not in model could be because scans aren't available yet

        if remove_extracted_file_names:
            self.logger.info("Removing from extracted list: {}".format(remove_extracted_file_names))
            self.__persist.extracted_file_names.difference_update(remove_extracted_file_names)
            self.__model_builder.set_extracted_files(self.__persist.extracted_file_names)

    def _prune_downloaded_files(self, latest_remote_scan: Optional[ScannerResult]) -> None:
        """
        Prune downloaded files tracking list.

        Note: downloaded_file_names uses a BoundedOrderedSet with LRU eviction,
        so no manual pruning is needed to prevent unbounded growth.

        Files are intentionally kept in the tracking set even when deleted from
        both local and remote. This prevents re-downloading files that were:
        - Downloaded by SeedSyncarr
        - Deleted/moved by external tools (e.g., Sonarr)
        - Later re-uploaded to remote (e.g., new episode with same name)

        The BoundedOrderedSet will automatically evict the oldest entries when
        the configured limit (default 10,000) is reached.

        Must be called while holding the model lock.

        Args:
            latest_remote_scan: Latest remote scan result (unused, kept for API compatibility).
        """
        # No pruning needed - BoundedOrderedSet handles eviction automatically
        pass

    def _apply_model_diff(self, model_diff: List[ModelDiff]) -> None:
        """
        Apply model differences to update the internal model state.

        For each diff entry:
        - ADDED: Add the new file to the model
        - REMOVED: Remove the old file from the model
        - UPDATED: Update the file in the model

        Also detects newly downloaded files and updates tracking.

        Must be called while holding the model lock.

        Args:
            model_diff: List of model diff entries to apply.
        """
        for diff in model_diff:
            if diff.change == ModelDiff.Change.ADDED:
                self.__model.add_file(diff.new_file)
            elif diff.change == ModelDiff.Change.REMOVED:
                self.__model.remove_file(diff.old_file.name)
            elif diff.change == ModelDiff.Change.UPDATED:
                self.__model.update_file(diff.new_file)

            # Detect if a file was just queued or downloaded and update persist state
            self._detect_and_track_queued(diff)
            self._detect_and_track_download(diff)

    def _build_and_apply_model(self, latest_remote_scan: Optional[ScannerResult]) -> None:
        """
        Build a new model and apply changes if the model builder has updates.

        This method:
        1. Builds a new model from the model builder
        2. Diffs the new model against the current model
        3. Applies the diff (add/remove/update files)
        4. Tracks newly downloaded files
        5. Prunes stale entries from extracted/downloaded tracking lists

        All model operations are performed while holding the model lock.

        Args:
            latest_remote_scan: Latest remote scan result, used for pruning decisions.
        """
        if not self.__model_builder.has_changes():
            return

        new_model = self.__model_builder.build_model()

        # Apply import_status from persisted set BEFORE diffing.
        # Model builder creates files with default import_status=NONE.
        # Without this, every rebuild cycle produces spurious SSE events:
        #   update(NONE) then update(IMPORTED), causing repeated frontend toasts.
        for file_name in new_model.get_file_names():
            if file_name in self.__persist.imported_file_names:
                self._set_import_status(new_model, file_name)

        # Lock the model for all modifications
        with self.__model_lock:
            # Diff the new model with old model
            model_diff = ModelDiffUtil.diff_models(self.__model, new_model)

            # Apply changes to the model
            self._apply_model_diff(model_diff)

            # Prune stale tracking entries
            self._prune_extracted_files()
            self._prune_downloaded_files(latest_remote_scan)

    def _update_controller_status(self,
                                  remote_scan: Optional[ScannerResult],
                                  local_scan: Optional[ScannerResult]) -> None:
        """
        Update the controller status with latest scan information.

        Args:
            remote_scan: Latest remote scan result, or None.
            local_scan: Latest local scan result, or None.
        """
        if remote_scan is not None:
            self.__context.status.controller.latest_remote_scan_time = remote_scan.timestamp
            self.__context.status.controller.latest_remote_scan_failed = remote_scan.failed
            self.__context.status.controller.latest_remote_scan_error = remote_scan.error_message
        if local_scan is not None:
            self.__context.status.controller.latest_local_scan_time = local_scan.timestamp

    # =========================================================================
    # End of __update_model() helper methods
    # =========================================================================

    def __update_model(self):
        """
        Advance the model state by collecting data from all sources and updating accordingly.

        This method orchestrates the model update process:
        1. Collect scan results, LFTP status, and extract results
        2. Update active file tracking for the active scanner
        3. Feed collected data to the model builder
        4. Build and apply model changes (if any)
        5. Update controller status with scan timestamps

        The actual work is delegated to focused helper methods for maintainability.
        """
        # Step 1: Collect all data from external sources
        latest_remote_scan, latest_local_scan, latest_active_scan = self._collect_scan_results()
        lftp_statuses = self._collect_lftp_status()
        latest_extract_statuses, latest_extracted_results = self._collect_extract_results()

        # Step 2: Update active file tracking
        self._update_active_file_tracking(lftp_statuses, latest_extract_statuses)

        # Step 3: Feed data to model builder
        self._feed_model_builder(
            latest_remote_scan,
            latest_local_scan,
            latest_active_scan,
            lftp_statuses,
            latest_extract_statuses,
            latest_extracted_results
        )

        # Step 4: Build and apply model changes
        self._build_and_apply_model(latest_remote_scan)

        # Step 5: Update controller status
        self._update_controller_status(latest_remote_scan, latest_local_scan)

    def __check_webhook_imports(self):
        """
        Process webhook import events and update persist state.
        Also sets import_status on model files for UI badge display.

        Builds a comprehensive name lookup that includes both root-level
        model file names and child file names (mapped back to their root
        parent). This allows matching when Sonarr/Radarr reports a child
        file name (e.g., an episode file inside a downloaded directory).

        Thread safety: model reads and mutations are protected by __model_lock.
        Two lock windows are used to keep critical sections minimal:
          Window 1 (read): build name_to_root dict
          Window 2 (mutate): update model import_status per imported file
        The webhook_manager.process() call and auto-delete scheduling run
        outside the lock (thread-safe Queue and Timer operations respectively).
        """
        # Window 1: Build name-to-root lookup under lock
        # lowercased name -> root model file name
        # Includes both root names and all child file names
        name_to_root = {}
        with self.__model_lock:
            for root_name in self.__model.get_file_names():
                name_to_root[root_name.lower()] = root_name
                try:
                    root_file = self.__model.get_file(root_name)
                    if root_file.is_dir:
                        # BFS over children to collect all child names
                        frontier = collections.deque(root_file.get_children())
                        while frontier:
                            child = frontier.popleft()
                            name_to_root[child.name.lower()] = root_name
                            frontier.extend(child.get_children())
                except ModelError:
                    self.logger.debug("ModelError looking up '{}' for webhook mapping".format(root_name))

        # Process outside lock -- webhook_manager only touches its own thread-safe Queue
        newly_imported = self.__webhook_manager.process(name_to_root)

        if newly_imported:
            # Window 2: Update model import status for all newly imported files under single lock
            with self.__model_lock:
                for file_name in newly_imported:
                    self.__persist.imported_file_names.add(file_name)
                    self.logger.info("Recorded webhook import: '{}'".format(file_name))
                    self._set_import_status(self.__model, file_name)

            # Schedule auto-deletes outside lock -- Timer operations only
            if self.__context.config.autodelete.enabled:
                for file_name in newly_imported:
                    self.__schedule_auto_delete(file_name)

    def __schedule_auto_delete(self, file_name: str):
        """Schedule auto-delete of local file after safety delay."""
        with self.__auto_delete_lock:
            # Cancel existing timer if file was re-detected
            if file_name in self.__pending_auto_deletes:
                self.__pending_auto_deletes[file_name].cancel()
                del self.__pending_auto_deletes[file_name]

            delay = self.__context.config.autodelete.delay_seconds
            timer = threading.Timer(delay, self.__execute_auto_delete, args=[file_name])
            timer.daemon = True  # Don't prevent process exit
            self.__pending_auto_deletes[file_name] = timer
            timer.start()
            self.logger.info(
                "Scheduled auto-delete of '{}' in {} seconds".format(file_name, delay)
            )

    def __execute_auto_delete(self, file_name: str):
        """Execute auto-delete of local file (called by Timer after delay).

        Thread safety: the model.get_file() call is protected by __model_lock.
        delete_local() runs OUTSIDE the lock -- it spawns a subprocess, and
        holding the lock across a blocking subprocess call would starve model
        updates on the controller thread.

        ModelFile is frozen (immutable) after being added to the model, so
        the `file` reference is safe to use after releasing the lock.
        """
        # Remove from tracking dict
        with self.__auto_delete_lock:
            self.__pending_auto_deletes.pop(file_name, None)

        # Re-check config -- user might have disabled auto-delete after timer was scheduled
        if not self.__context.config.autodelete.enabled:
            self.logger.info(
                "Auto-delete skipped for '{}': feature was disabled".format(file_name)
            )
            return

        # Check dry-run mode
        if self.__context.config.autodelete.dry_run:
            self.logger.info(
                "DRY-RUN: Would delete local file '{}'".format(file_name)
            )
            return

        # Get file from model under lock -- ensures file still exists in model
        # at the moment we read it, preventing use of a stale reference.
        with self.__model_lock:
            try:
                file = self.__model.get_file(file_name)
            except ModelError:
                self.logger.debug(
                    "File '{}' no longer in model, skipping auto-delete".format(file_name)
                )
                return
        # delete_local is safe outside lock -- it spawns a subprocess, holding
        # the lock during a blocking subprocess call would starve model updates.
        # ModelFile is frozen/immutable after add, so `file` reference is safe.
        self.__file_op_manager.delete_local(file)
        self.logger.info("Auto-deleted local file '{}'".format(file_name))

    def __handle_queue_command(self, file: ModelFile, command: Command) -> (bool, str, int):
        """
        Handle QUEUE command action.
        Returns (success, error_message, error_code) tuple.
        """
        if file.remote_size is None:
            return False, "File '{}' does not exist remotely".format(command.filename), 404
        try:
            self.__lftp_manager.queue(file.name, file.is_dir)
            # Remove from stopped files - user explicitly wants to download this
            self.__persist.stopped_file_names.discard(file.name)
            return True, None, None
        except LftpError as e:
            return False, "Lftp error: {}".format(str(e)), 500

    def __handle_stop_command(self, file: ModelFile, command: Command) -> (bool, str, int):
        """
        Handle STOP command action.
        Returns (success, error_message, error_code) tuple.
        """
        if file.state not in (ModelFile.State.DOWNLOADING, ModelFile.State.QUEUED):
            return False, "File '{}' is not Queued or Downloading".format(command.filename), 409
        try:
            self.__lftp_manager.kill(file.name)
            # Track this file as stopped so it won't be auto-queued on restart
            self.__persist.stopped_file_names.add(file.name)
            return True, None, None
        except (LftpError, LftpJobStatusParserError) as e:
            return False, "Lftp error: {}".format(str(e)), 500

    def __handle_extract_command(self, file: ModelFile, command: Command) -> (bool, str, int):
        """
        Handle EXTRACT command action.
        Returns (success, error_message, error_code) tuple.
        """
        # Note: We don't check the is_extractable flag because it's just a guess
        if file.state not in (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED
        ):
            return False, "File '{}' in state {} cannot be extracted".format(
                command.filename, str(file.state)
            ), 409
        elif file.local_size is None:
            return False, "File '{}' does not exist locally".format(command.filename), 404
        else:
            self.__file_op_manager.extract(file)
            return True, None, None

    def __handle_delete_command(self, file: ModelFile, command: Command) -> (bool, str, int):
        """
        Handle DELETE_LOCAL and DELETE_REMOTE command actions.
        Returns (success, error_message, error_code) tuple.
        """
        if command.action == Controller.Command.Action.DELETE_LOCAL:
            if file.state not in (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED
            ):
                return False, "Local file '{}' cannot be deleted in state {}".format(
                    command.filename, str(file.state)
                ), 409
            elif file.local_size is None:
                return False, "File '{}' does not exist locally".format(command.filename), 404
            else:
                self.__file_op_manager.delete_local(file)
                # Track as stopped to prevent auto-queuing on restart
                self.__persist.stopped_file_names.add(command.filename)
                return True, None, None

        elif command.action == Controller.Command.Action.DELETE_REMOTE:
            if file.state not in (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED,
                ModelFile.State.DELETED
            ):
                return False, "Remote file '{}' cannot be deleted in state {}".format(
                    command.filename, str(file.state)
                ), 409
            elif file.remote_size is None:
                return False, "File '{}' does not exist remotely".format(command.filename), 404
            else:
                self.__file_op_manager.delete_remote(file)
                return True, None, None

        return False, "Unknown delete action", 500

    def __process_commands(self):
        def _notify_failure(_command: Controller.Command, _msg: str, _code: int = 400):
            self.logger.warning("Command failed. {}".format(_msg))
            for _callback in _command.callbacks:
                _callback.on_failure(_msg, _code)

        while not self.__command_queue.empty():
            command = self.__command_queue.get()
            self.logger.info("Received command {} for file {}".format(str(command.action), command.filename))
            with self.__model_lock:
                try:
                    file = self.__model.get_file(command.filename)
                except ModelError:
                    _notify_failure(command, "File '{}' not found".format(command.filename), 404)
                    continue

            success = False
            error_msg = None
            error_code = 400

            if command.action == Controller.Command.Action.QUEUE:
                success, error_msg, error_code = self.__handle_queue_command(file, command)

            elif command.action == Controller.Command.Action.STOP:
                success, error_msg, error_code = self.__handle_stop_command(file, command)

            elif command.action == Controller.Command.Action.EXTRACT:
                success, error_msg, error_code = self.__handle_extract_command(file, command)

            elif command.action in (Controller.Command.Action.DELETE_LOCAL,
                                    Controller.Command.Action.DELETE_REMOTE):
                success, error_msg, error_code = self.__handle_delete_command(file, command)

            if not success:
                _notify_failure(command, error_msg, error_code)
                continue

            # If we get here, it was a success
            for callback in command.callbacks:
                callback.on_success()

    def __propagate_exceptions(self):
        """
        Propagate any exceptions from child processes/threads to this thread
        """
        self.__lftp_manager.raise_pending_error()
        self.__scan_manager.propagate_exceptions()
        self.__mp_logger.propagate_exception()
        self.__file_op_manager.propagate_exception()
