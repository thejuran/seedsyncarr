from abc import ABC, abstractmethod
import collections
import threading
from typing import Dict, List, Optional, Tuple
from threading import Lock
from queue import Queue
from enum import Enum

from .scan_manager import ScanManager
from .lftp_manager import LftpManager
from .file_operation_manager import FileOperationManager
from .command_processor import CommandProcessor
from .auto_delete_manager import AutoDeleteManager
from .model_pipeline import ModelPipeline
from .webhook_manager import WebhookManager
from .extract import ExtractStatusResult, ExtractCompletedResult
from .model_builder import ModelBuilder
from .scan import ScannerResult
from .memory_monitor import MemoryMonitor
from common import Context, AppError, MultiprocessingLogger, sanitize_log_value
from model import ModelError, ModelFile, Model, ModelDiff, IModelListener
from lftp import LftpJobStatus
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
        # BUG-03 criterion #2: dedicated shutdown signal for the auto-delete path.
        # exit() sets this UNDER __auto_delete_lock (same lock window as the
        # timer-cancel loop) so the set() is strictly ordered against the
        # callback's lock-serialized final-commit step.  Do NOT reuse __started
        # (it is set False at the END of exit(), too late to block a mid-callback
        # dispatch; see D-03).
        self.__shutdown_event = threading.Event()

        # Command dispatch collaborator — receives already-constructed manager instances
        # (D-05: mock.patch targets resolve against controller.controller where they are
        # constructed; CommandProcessor constructs none of them)
        self.__command_processor = CommandProcessor(
            lftp_manager=self.__lftp_manager,
            file_op_manager=self.__file_op_manager,
            persist=self.__persist,
            logger=self.logger,
        )

        # Auto-delete BFS+coverage collaborator — receives already-constructed instances
        # (D-05: no manager constructed here; injected objects are the same instances
        # Controller holds so mock.patch targets remain bound in controller.controller).
        # No lock injected: Controller.__execute_auto_delete owns all lock acquisition
        # and release; AutoDeleteManager.run_bfs_and_coverage acquires no lock (D-03).
        self.__auto_delete_mgr = AutoDeleteManager(
            context=self.__context,
            persist=self.__persist,
            file_op_manager=self.__file_op_manager,
            logger=self.logger,
        )

        # Model-update pipeline collaborator — receives already-constructed manager instances
        # (D-05: no manager constructed here; injected objects are the same instances
        # Controller holds so mock.patch targets remain bound in controller.controller).
        # model_lock is the SAME Lock object (D-03); stored as _model_lock in the
        # collaborator (single-underscore, identity preserved — Pitfall 3 avoidance).
        self.__model_pipeline = ModelPipeline(
            context=self.__context,
            persist=self.__persist,
            model=self.__model,
            model_lock=self.__model_lock,
            model_builder=self.__model_builder,
            scan_manager=self.__scan_manager,
            lftp_manager=self.__lftp_manager,
            file_op_manager=self.__file_op_manager,
            logger=self.logger,
        )

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
            # Signal shutdown and cancel all pending auto-delete timers.
            # __shutdown_event.set() runs FIRST, inside the SAME lock as the
            # cancel loop.  This orders the signal against the callback's
            # lock-serialized final-commit step (D-02, D-04): a callback that
            # has not yet entered its final __auto_delete_lock block will see
            # the event set and return without popping imported_children or
            # dispatching delete_local.  No thread join/drain is required
            # because the lock — not a join — serializes shutdown vs dispatch.
            # Lock ordering note: exit() takes ONLY __auto_delete_lock (never
            # __model_lock).  The callback releases __model_lock before
            # re-acquiring __auto_delete_lock for the final commit, so there
            # is no circular wait and no deadlock risk.
            with self.__auto_delete_lock:
                self.__shutdown_event.set()
                for file_name, timer in list(self.__pending_auto_deletes.items()):
                    timer.cancel()
                    self.logger.debug("Canceled pending auto-delete for '{}'".format(sanitize_log_value(file_name)))
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
        """Forwarding wrapper — logic lives in ModelPipeline.collect_scan_results (D-06/109-03)."""
        return self.__model_pipeline.collect_scan_results()

    def _collect_lftp_status(self) -> Optional[List[LftpJobStatus]]:
        """Forwarding wrapper — logic lives in ModelPipeline.collect_lftp_status (D-06/109-03)."""
        return self.__model_pipeline.collect_lftp_status()

    def _collect_extract_results(self) -> Tuple[Optional[ExtractStatusResult], List[ExtractCompletedResult]]:
        """Forwarding wrapper — logic lives in ModelPipeline.collect_extract_results (D-06/109-03)."""
        return self.__model_pipeline.collect_extract_results()

    def _set_import_status(self, model: Model, file_name: str) -> None:
        """Forwarding wrapper — logic lives in ModelPipeline._set_import_status (D-06/109-03).
        Kept on Controller (no leading-underscore guard in plan grep) because
        test_controller.py:212,240 assigns c._set_import_status = MagicMock() to intercept
        the __check_webhook_imports call path, which requires this name to be a method on
        Controller that Controller's own code calls via self._set_import_status(...).
        """
        return self.__model_pipeline._set_import_status(model, file_name)

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
        """Forwarding wrapper — logic lives in ModelPipeline.feed_model_builder (D-06/109-03)."""
        return self.__model_pipeline.feed_model_builder(
            remote_scan, local_scan, active_scan, lftp_statuses, extract_statuses, extracted_results
        )

    def _detect_and_track_queued(self, diff: ModelDiff) -> None:
        """Forwarding wrapper — logic lives in ModelPipeline.detect_and_track_queued (D-06/109-03)."""
        return self.__model_pipeline.detect_and_track_queued(diff)

    def _detect_and_track_download(self, diff: ModelDiff) -> None:
        """Forwarding wrapper — logic lives in ModelPipeline.detect_and_track_download (D-06/109-03)."""
        return self.__model_pipeline.detect_and_track_download(diff)

    def _prune_extracted_files(self) -> None:
        """Forwarding wrapper — logic lives in ModelPipeline.prune_extracted_files (D-06/109-03)."""
        return self.__model_pipeline.prune_extracted_files()

    def _apply_model_diff(self, diffs: List[ModelDiff]) -> None:
        """Forwarding wrapper — logic lives in ModelPipeline.apply_model_diff (D-06/109-03)."""
        return self.__model_pipeline.apply_model_diff(diffs)

    def _build_and_apply_model(self, latest_remote_scan: Optional[ScannerResult]) -> None:
        """Forwarding wrapper — logic lives in ModelPipeline.build_and_apply_model (D-06/109-03)."""
        return self.__model_pipeline.build_and_apply_model(latest_remote_scan)

    @staticmethod
    def _should_update_capacity(old: Optional[int], new: Optional[int]) -> bool:
        """
        >1% change gate (D-12/D-13). Returns True when the new value should be
        written to Status.storage.
        """
        if new is None:
            return False
        if old is None:
            return True
        if old == 0:
            return new != 0
        return abs(new - old) / abs(old) > 0.01

    def _update_controller_status(self,
                                  remote_scan: Optional[ScannerResult],
                                  local_scan: Optional[ScannerResult]) -> None:
        """
        Update the controller status with latest scan information.

        Writes storage capacity (Phase 74) gated by the >1% change rule
        (D-12/D-13) per-side independently (D-15). A None total/used pair
        leaves that side untouched (silent fallback per D-16).
        """
        if remote_scan is not None:
            self.__context.status.controller.latest_remote_scan_time = remote_scan.timestamp
            self.__context.status.controller.latest_remote_scan_failed = remote_scan.failed
            self.__context.status.controller.latest_remote_scan_error = remote_scan.error_message
            if remote_scan.total_bytes is not None and remote_scan.used_bytes is not None:
                # Per-field gate: total and used are independent under D-12/D-15 so
                # a sub-1% change on one must not drag the other into a write.
                if Controller._should_update_capacity(
                        self.__context.status.storage.remote_total, remote_scan.total_bytes):
                    self.__context.status.storage.remote_total = remote_scan.total_bytes
                if Controller._should_update_capacity(
                        self.__context.status.storage.remote_used, remote_scan.used_bytes):
                    self.__context.status.storage.remote_used = remote_scan.used_bytes
        if local_scan is not None:
            self.__context.status.controller.latest_local_scan_time = local_scan.timestamp
            if local_scan.total_bytes is not None and local_scan.used_bytes is not None:
                if Controller._should_update_capacity(
                        self.__context.status.storage.local_total, local_scan.total_bytes):
                    self.__context.status.storage.local_total = local_scan.total_bytes
                if Controller._should_update_capacity(
                        self.__context.status.storage.local_used, local_scan.used_bytes):
                    self.__context.status.storage.local_used = local_scan.used_bytes

    # =========================================================================
    # End of __update_model() helper methods
    # =========================================================================

    def __update_model(self):
        """
        Advance the model state. Delegates collect->feed->build pipeline to ModelPipeline;
        retains _update_active_file_tracking and _update_controller_status on the coordinator
        (circular-import avoidance + __active_downloading_file_names ownership, D-06/109-03).
        """
        # Pipeline runs collect, feed, and build stages; returns collected values
        # needed by the retained coordinator stages.
        latest_remote_scan, latest_local_scan, lftp_statuses, latest_extract_statuses = \
            self.__model_pipeline.update_model()

        # Retained coordinator stage: writes __active_downloading_file_names (test-pinned field)
        self._update_active_file_tracking(lftp_statuses, latest_extract_statuses)

        # Retained coordinator stage: calls Controller._should_update_capacity (circular-import guard)
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
                    self.logger.debug("ModelError looking up '{}' for webhook mapping".format(sanitize_log_value(root_name)))

        # Process outside lock -- webhook_manager only touches its own thread-safe Queue
        newly_imported = self.__webhook_manager.process(name_to_root)

        if newly_imported:
            # Window 2: Update model import status for all newly imported files under single lock
            with self.__model_lock:
                for root_name, matched_name in newly_imported:
                    # Backward-compat root tracking (D-05) -- drives UI badge + existing dedup
                    self.__persist.imported_file_names.add(root_name)
                    # Per-child tracking (D-07) -- lowercased basename for case-insensitive
                    # comparison in the coverage guard. See matched_name comment in
                    # WebhookManager.process docstring.
                    #
                    # WR-01 guard: skip add_imported_child when the webhook's matched_name
                    # is the root itself (e.g. Sonarr's releaseTitle/series.title fallback
                    # chain when episodeFile.sourcePath is absent from the payload). A
                    # root-level match carries no per-child information; recording the
                    # root name as a "child" would poison imported_children[root] with a
                    # useless value and block auto-delete indefinitely on real packs.
                    # Leaving the key absent lets D-14 grandfather the root as fully
                    # imported, preserving pre-phase-75 auto-delete behavior for the
                    # releaseTitle/series.title fallback paths.
                    if matched_name.lower() != root_name.lower():
                        self.__persist.add_imported_child(root_name, matched_name.lower())
                    # Sanitize webhook-supplied matched_name and remote-scanner-sourced
                    # root_name before logging to prevent log-injection (CWE-117).
                    safe_matched = sanitize_log_value(matched_name)
                    self.logger.info(
                        "Recorded webhook import: '{}' (child: '{}')".format(
                            sanitize_log_value(root_name), safe_matched
                        )
                    )
                    self._set_import_status(self.__model, root_name)

            # Schedule auto-deletes outside lock -- Timer operations only.
            # De-duplicate roots: two child webhooks in one cycle would otherwise
            # schedule the same root twice (the second call cancels the first timer
            # and rearms -- benign but wasteful). Iterate unique roots explicitly.
            if self.__context.config.autodelete.enabled:
                for root_name in {r for r, _ in newly_imported}:
                    self.__schedule_auto_delete(root_name)

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
                "Scheduled auto-delete of '{}' in {} seconds".format(sanitize_log_value(file_name), delay)
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
        # Remove from tracking dict; entry guard for shutdown (BUG-03 criterion #2).
        # Checking __shutdown_event inside __auto_delete_lock is the fast-path:
        # if exit() has already set the event under the same lock, we can return
        # immediately without doing any model read — the callback is a no-op.
        with self.__auto_delete_lock:
            self.__pending_auto_deletes.pop(file_name, None)
            if self.__shutdown_event.is_set():
                return

        # Re-check config -- user might have disabled auto-delete after timer was scheduled
        if not self.__context.config.autodelete.enabled:
            self.logger.info(
                "Auto-delete skipped for '{}': feature was disabled".format(sanitize_log_value(file_name))
            )
            return

        # Check dry-run mode
        if self.__context.config.autodelete.dry_run:
            self.logger.info(
                "DRY-RUN: Would delete local file '{}'".format(sanitize_log_value(file_name))
            )
            return

        # Get file from model under lock -- ensures file still exists in model
        # at the moment we read it, preventing use of a stale reference.
        # State guards also run under the lock so we check against a consistent
        # snapshot of the model (states can flip as scanners update).
        deletable_states = (
            ModelFile.State.DEFAULT,
            ModelFile.State.DOWNLOADED,
            ModelFile.State.EXTRACTED,
        )
        with self.__model_lock:
            try:
                file = self.__model.get_file(file_name)
            except ModelError:
                self.logger.debug(
                    "File '{}' no longer in model, skipping auto-delete".format(sanitize_log_value(file_name))
                )
                return

            # State guard: do not delete a file that is mid-lifecycle. Mirrors
            # __handle_delete_command so the Timer path cannot race an in-flight
            # sync, queue, or extract when a re-download arrives between
            # scheduling and firing (e.g., Deluge re-seed triggers a re-sync).
            if file.state not in deletable_states:
                self.logger.info(
                    "Auto-delete skipped for '{}': file is in state {}".format(
                        sanitize_log_value(file_name), str(file.state)
                    )
                )
                return

            # Pack guard + coverage-basename collection: delegated to AutoDeleteManager.
            # run_bfs_and_coverage performs BFS over descendants in a single pass:
            # (a) Pack guard: skip if ANY child is in an active state. Prevents wiping
            #     a season pack while a sibling is still being downloaded or extracted
            #     (Sonarr's per-episode webhook schedules the pack root).
            # (b) Coverage collection: gather lowercased basenames of all on-disk
            #     video children for the coverage guard (D-08, D-09).
            # Caller holds __model_lock; AutoDeleteManager acquires NO lock (D-03).
            if file.is_dir:
                skip, reason, _on_disk_videos = self.__auto_delete_mgr.run_bfs_and_coverage(
                    file, file_name, deletable_states
                )
                if skip:
                    if reason == "bfs_limit":
                        # Terminal skip: Timer does not re-arm for this firing.
                        # Clear the per-child entry so imported_children isn't
                        # stranded on a permanently-oversized pack. All other
                        # skip paths are retriable and leave the entry intact.
                        self.__persist.imported_children.pop(file_name, None)
                    return

            # Final commit: serialize BOTH against exit()'s shutdown signal AND the
            # webhook path's add_imported_child. Lock order is __model_lock THEN
            # __auto_delete_lock (exit() takes ONLY __auto_delete_lock and never
            # __model_lock, so this ordering cannot deadlock). The pop runs under
            # __model_lock so it is mutually exclusive with add_imported_child
            # (controller.py:804), which also mutates imported_children under
            # __model_lock. The shutdown re-check stays under __auto_delete_lock so
            # it remains ordered against exit()'s __shutdown_event.set() (both use
            # the same lock — set() cannot interleave between check and pop).
            #
            # WR-02 semantics: the coverage guard above already committed the "delete
            # is final" decision. Any child added by a concurrent webhook between the
            # coverage guard and the pop is for a future import cycle. The pop here
            # is inside __model_lock so add_imported_child (also under __model_lock)
            # cannot race it — no TOCTOU window between guard and pop.
            with self.__auto_delete_lock:
                if self.__shutdown_event.is_set():
                    return  # no pop, no dispatch (D-02: shutdown has committed)
                # WR-02: clear the per-child entry before dispatching delete_local.
                self.__persist.imported_children.pop(file_name, None)

        # delete_local is safe outside lock -- it spawns a subprocess; holding
        # __model_lock across a blocking subprocess call would starve model updates.
        # `file` is captured above; ModelFile is frozen/immutable after add.
        self.__file_op_manager.delete_local(file)
        self.logger.info("Auto-deleted local file '{}'".format(sanitize_log_value(file_name)))

    def __process_commands(self):
        def _notify_failure(_command: Controller.Command, _msg: str, _code: int = 400):
            # Sanitize _msg for log output only — _msg is built from command.filename
            # (user-supplied via URL path / bulk JSON) and could otherwise forge log entries.
            self.logger.warning("Command failed. {}".format(sanitize_log_value(_msg)))
            for _callback in _command.callbacks:
                _callback.on_failure(_msg, _code)

        while not self.__command_queue.empty():
            command = self.__command_queue.get()
            self.logger.info("Received command {} for file {}".format(str(command.action), sanitize_log_value(command.filename)))
            with self.__model_lock:
                try:
                    file = self.__model.get_file(command.filename)
                except ModelError:
                    _notify_failure(command, "File '{}' not found".format(command.filename), 404)
                    continue

            # __model_lock is now released. Delegate to CommandProcessor — no lock held here.
            # delete_local (DELETE_LOCAL/DELETE_REMOTE) spawns a subprocess; it MUST run
            # outside the lock to avoid starving model updates.
            success, error_msg, error_code = self.__command_processor.handle(file, command)

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
