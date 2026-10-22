from abc import ABC, abstractmethod
import collections
import threading
import time
from typing import Callable, Dict, List, Mapping, NamedTuple, Optional, Tuple
from threading import Lock
from queue import Queue
from enum import Enum

from .scan_manager import ScanManager
from .lftp_manager import LftpManager
from .file_operation_manager import FileOperationManager
from .command_processor import CommandProcessor
from .root_reservation import RootReservations
from .arr_queue import ArrQueueClient
from .completion_gate import CompletionGate, Verdict
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
from .webhook_manager import _format_capped

# Upper bound on consecutive re-arms of one root's auto-delete Timer after a
# retriable skip (root or a child still mid-lifecycle, pack not fully imported
# yet). At the default 300 s delay this waits ~2 h for an extraction or the
# rest of a pack's imports before giving up with a WARNING. Terminal skips
# never re-arm. Incident 2026-09-16: the Timer fired once while the root was
# EXTRACTING, was skipped, and nothing ever re-armed it -- a 77 GB local copy
# was stranded for good.
_AUTO_DELETE_MAX_REARMS = 24

# Human-readable deferral reasons for AutoDeleteManager's retriable skip codes
# (its own log line already carries the child name / missing basenames).
_AUTO_DELETE_DEFER_REASONS = {
    "unsafe_child": "a child is still in an active state",
    "partial_coverage": "not every on-disk video child has been imported yet",
}

# AutoDeleteManager skip codes that never re-arm. The per-child
# imported_children entry is popped so a stale or poisoned record is not
# stranded; safety does not depend on that record because the guard runs
# before coverage on every firing.
_AUTO_DELETE_TERMINAL_SKIPS = frozenset({"bfs_limit", "duplicate_basename"})

# Webhook import notices that cannot be credited yet (the root is still
# transferring and the named child is not yet visible as fully transferred,
# usually scan lag) are kept in memory and re-evaluated every cycle. Bounded
# in count and age so repeated or bogus webhooks cannot grow it without limit.
_PENDING_NOTICE_MAX = 1000
_PENDING_NOTICE_TTL_SECS = 6 * 3600


class _PendingNotice(NamedTuple):
    """A webhook import notice waiting for its child to finish transferring.

    path is the single case-preserving model path the name resolved to when
    the notice arrived ("Root/sub/child.mkv", or the root name itself for a
    root-level match). generation is the root's transfer-lifecycle generation
    at insertion; a notice from an older generation is never replayed.
    """
    root_name: str
    matched_name: str
    path: str
    generation: int
    inserted_at: float


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

        class Origin(Enum):
            """Who requested the command. AUTO commands re-check the
            stopped/downloaded guards at execution time and never clear them;
            USER commands clear tracking to start a fresh lifecycle."""
            USER = 0
            AUTO = 1

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
                        - 428: Precondition required (completion could not be
                               verified; resend with release_unverified)
                        - 500: Internal server error
                """
                pass

        def __init__(self, action: Action, filename: str,
                     origin: "Controller.Command.Origin" = None,
                     release_unverified: bool = False):
            self.action = action
            self.filename = filename
            self.origin = origin if origin is not None else Controller.Command.Origin.USER
            # One-shot user confirmation to transfer a root whose completion
            # could not be verified. Lives only on this command and is never
            # persisted, so the approval is never remembered (D-08). Honored
            # for USER queue commands only.
            self.release_unverified = bool(release_unverified)
            self.callbacks = []

        def add_callback(self, callback: ICallback):
            self.callbacks.append(callback)

    def __init__(self,
                 context: Context,
                 persist: ControllerPersist,
                 webhook_manager: WebhookManager,
                 persist_callback: Optional[Callable[[], None]] = None):
        self.__context = context
        self.__persist = persist
        self.__webhook_manager = webhook_manager
        # Writes the controller persist to disk right away. Called after an
        # early import credit so a crash before the periodic save cannot lose
        # it. Invoked on the controller thread with no controller lock held.
        self.__persist_callback = persist_callback
        # Pending webhook import notices keyed (root_name, matched_name);
        # controller thread only.
        self.__pending_child_notices: "collections.OrderedDict[Tuple[str, str], _PendingNotice]" = \
            collections.OrderedDict()
        # Per-root transfer-lifecycle generation, bumped whenever the root's
        # lifecycle resets (USER requeue, re-grab, removal) so a pending
        # notice from the previous lifecycle can never be replayed.
        self.__root_lifecycle_generation: Dict[str, int] = collections.defaultdict(int)
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

        # Completion gate: decides from Sonarr/Radarr queue evidence whether a
        # remote root has finished downloading before any transfer may start.
        # Constructed here (D-05) so patch('controller.controller.CompletionGate')
        # and patch('controller.controller.ArrQueueClient') bind in tests.
        self.__arr_queue_client = ArrQueueClient(context=self.__context)
        self.__completion_gate = CompletionGate(context=self.__context, client=self.__arr_queue_client)

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
        # Consecutive deferrals per root (see __defer_auto_delete); guarded by
        # __auto_delete_lock like the Timer dict it shadows.
        self.__auto_delete_rearms: Dict[str, int] = {}
        # Per-root auto-delete epoch, guarded by __auto_delete_lock. Every
        # Timer is stamped with the epoch current when it was armed; a USER
        # requeue or a lifecycle reset bumps it (see _cancel_auto_delete), so
        # a Timer from the previous lifecycle that is already running can
        # neither delete nor re-arm itself.
        self.__auto_delete_epochs: Dict[str, int] = collections.defaultdict(int)
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
        # Per-root reservation shared by queue submission (CommandProcessor) and
        # both deletion paths (auto-delete Timer, manual Delete Local) so a
        # deletion and a submission for the same root can never overlap.
        self.__root_reservations = RootReservations()
        self.__command_processor = CommandProcessor(
            lftp_manager=self.__lftp_manager,
            file_op_manager=self.__file_op_manager,
            persist=self.__persist,
            logger=self.logger,
            root_reservations=self.__root_reservations,
            completion_gate=self.__completion_gate,
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
            completion_gate=self.__completion_gate,
            on_lifecycle_reset=self._on_root_lifecycle_reset,
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
                self.__auto_delete_rearms.clear()

            # Each cleanup runs independently: a failure in one (e.g. lftp's
            # graceful exit failing on an unsynchronized command stream) must
            # never leave the remaining child processes running.
            for component, stop in (("lftp", self.__lftp_manager.exit),
                                    ("scanner", self.__scan_manager.stop),
                                    ("file operations", self.__file_op_manager.stop),
                                    ("multiprocessing logger", self.__mp_logger.stop)):
                try:
                    stop()
                except Exception:
                    self.logger.exception("Error stopping {} during controller exit".format(component))
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

    def evaluate_completion(self, candidates: Mapping[str, Optional[int]]) -> Dict[str, Verdict]:
        """
        Completion verdicts for every auto-queue candidate (name -> remote size).

        Runs on the controller thread (AutoQueue shares it) and never waits on
        an arr: the gate starts queue fetches on daemon workers and decides
        from the latest completed snapshots, so a first or forced fetch still
        in flight yields a hold for this cycle and a verdict on a later one.
        The gate owns refresh and backoff, so calling this every cycle is safe.
        Names absent from `candidates` leave the hold registry.
        """
        return self.__completion_gate.evaluate(candidates)

    def completion_verdict(self, name: str, remote_size: Optional[int]) -> Verdict:
        """
        Completion verdict for one root, with the same thread and non-blocking
        guarantees as evaluate_completion(). Other roots' holds are untouched.
        """
        return self.__completion_gate.verdict(name, remote_size)

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

        The UI scan fields are written from every scan; the successful-scan
        clocks (latest_successful_*_scan_time) only advance when the scan did
        not fail, so AutoQueue stability is never measured across a failed scan.
        """
        if remote_scan is not None:
            self.__context.status.controller.latest_remote_scan_time = remote_scan.timestamp
            self.__context.status.controller.latest_remote_scan_failed = remote_scan.failed
            self.__context.status.controller.latest_remote_scan_error = remote_scan.error_message
            if not remote_scan.failed:
                self.__context.status.controller.latest_successful_remote_scan_time = \
                    remote_scan.timestamp
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
            if not local_scan.failed:
                self.__context.status.controller.latest_successful_local_scan_time = \
                    local_scan.timestamp
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
          Window 1 (read): build name_to_paths (lowercased basename ->
            {case-preserving path -> root})
          Window 2 (mutate): update model import_status per imported file
        webhook_manager.process() returns only unambiguous matches: a name
        that resolves to two or more distinct model paths is rejected there,
        so nothing in Window 2 can record, badge or arm auto-delete for it.
        The webhook_manager.process() call and auto-delete scheduling run
        outside the lock (thread-safe Queue and Timer operations respectively).

        Early child credit (IMP-03): when the root is not yet committed but is
        a remote release SeedSyncarr is transferring (QUEUED/DOWNLOADING), a
        child-level notice whose child is the unique file of that name and is
        DOWNLOADED with local_size == remote_size is credited to
        imported_children[root] and persisted immediately via the persist
        callback. A notice whose child is not complete yet is kept pending
        (bounded by _PENDING_NOTICE_MAX and _PENDING_NOTICE_TTL_SECS), bound
        to its resolved model path and the root's lifecycle generation, and
        revalidated every cycle before either acceptance path: it must still
        resolve to exactly one path, equal to its stored path under its stored
        root, in the current generation. Pending notices are discarded on a
        USER requeue, a lifecycle reset or root removal (_discard_pending_notices).
        A pending notice already being tracked is also credited or kept after
        the root's transfer ends and until it commits (122-10, D-06c); a
        FRESH notice never gets this treatment and still requires transfer
        evidence. Credit alone never authorizes deletion (D-14): it never
        commits the root or marks it imported. When a credited root later
        commits to downloaded, the arm-on-commit pass marks it imported and
        arms auto-delete, whose coverage guard then decides.
        """
        # Window 1: Build the basename lookup under lock
        # lowercased basename -> {case-preserving relative path -> root model file name}
        # Includes both root names and all child file names. Keeping every
        # path per basename (instead of last-writer-wins) lets process()
        # detect a name that is ambiguous across or within releases. Only
        # the key is lowercased, so case-distinct paths stay distinct.
        name_to_paths: Dict[str, Dict[str, str]] = {}
        with self.__model_lock:
            for root_name in self.__model.get_file_names():
                name_to_paths.setdefault(root_name.lower(), {})[root_name] = root_name
                try:
                    root_file = self.__model.get_file(root_name)
                    if root_file.is_dir:
                        # BFS over children carrying each child's parent path.
                        # Paths are '/'-joined identity keys built from names,
                        # not filesystem paths.
                        frontier = collections.deque(
                            (c, root_name) for c in root_file.get_children()
                        )
                        while frontier:
                            child, parent_path = frontier.popleft()
                            child_path = parent_path + "/" + child.name
                            name_to_paths.setdefault(child.name.lower(), {})[child_path] = root_name
                            frontier.extend((g, child_path) for g in child.get_children())
                except ModelError:
                    self.logger.debug("ModelError looking up '{}' for webhook mapping".format(sanitize_log_value(root_name)))

        # Revalidate every pending notice against the CURRENT lookup before it
        # can reach either acceptance path below. A replayed notice must pass
        # the same exactly-one-path rule WebhookManager.process applies to a
        # fresh event, still resolve to the path it was bound to, and belong
        # to the root's current transfer lifecycle.
        now = time.monotonic()
        for key, notice in list(self.__pending_child_notices.items()):
            if self._revalidate_pending_notice(notice, name_to_paths, now) is not None:
                self.__pending_child_notices.pop(key, None)

        # Process outside lock -- webhook_manager only touches its own thread-safe Queue
        fresh = self.__webhook_manager.process(name_to_paths)

        # Pending notices first, then fresh events; one entry per
        # (root, matched) key. Value = the resolved model path, or None when
        # the name has no single path under the root (only possible for an
        # injected event); a None path is never kept pending.
        events: "collections.OrderedDict[Tuple[str, str], Optional[str]]" = collections.OrderedDict()
        for key, notice in self.__pending_child_notices.items():
            events[key] = notice.path
        for root_name, matched_name in fresh:
            key = (root_name, matched_name)
            if key not in events:
                events[key] = self.__resolve_path(name_to_paths, root_name, matched_name)

        # Roots that passed the evidence gate (or committed holding credits);
        # only these are recorded as imported and scheduled for auto-delete.
        accepted_roots = set()
        persist_changed = False
        transferring_states = (ModelFile.State.DOWNLOADING, ModelFile.State.QUEUED)
        # Window 2: credit / record imports under a single lock
        with self.__model_lock:
            for (root_name, matched_name), path in events.items():
                key = (root_name, matched_name)
                # Evidence gate: only record imports for releases with
                # download evidence — already committed to downloaded, or a
                # complete local copy of a remote release (committed here,
                # covering the race where the arr imports before the next
                # model build runs the commit pass). A match with no
                # evidence (incident 2026-08-21: a foreign local-only dir
                # like 'iplayer' matched via a child basename) is logged
                # and ignored so it can never arm auto-delete.
                if root_name not in self.__persist.downloaded_file_names:
                    try:
                        root_file = self.__model.get_file(root_name)
                    except ModelError:
                        root_file = None
                    has_evidence = (
                        root_file is not None and
                        root_file.remote_size is not None and
                        root_file.local_size is not None and
                        root_file.local_size >= root_file.remote_size
                    )
                    if not has_evidence:
                        # The root may still be transferring (incident
                        # 2026-10-09, Days of Hope: three episode notices
                        # arrived ~1 min before the pack committed and were
                        # lost). Credit a fully transferred child now; keep a
                        # notice whose child is not visible as complete yet.
                        # A credit writes imported_children ONLY: it never
                        # commits the root, never marks it imported and never
                        # arms auto-delete, so whole-folder deletion still
                        # needs the root committed plus full coverage.
                        transferring = (
                            root_file is not None and
                            root_file.remote_size is not None and
                            root_file.state in transferring_states
                        )
                        # Post-transfer window (122-10, D-06c): the root's
                        # lftp job can end (no LftpJobStatus leaves it
                        # DEFAULT) with the local scan still lagging, or --
                        # only reachable when a test injects the model
                        # directly and skips the commit pass -- the root can
                        # already show DOWNLOADED with a stale size
                        # aggregate, in both cases before the commit pass has
                        # run (2026-10-22 sandbox: SSA122.Alpha2.S01). A key
                        # still present in __pending_child_notices here has,
                        # this very cycle, passed _revalidate_pending_notice
                        # (same lifecycle generation, unique path, not
                        # expired) and could only have been kept while this
                        # root was DOWNLOADING/QUEUED -- a stronger
                        # known-tracked-root signal than a fresh notice ever
                        # gets. Such a notice is still credited or kept here
                        # as long as the root still has a remote copy. A
                        # FRESH notice (never pending) for a root that is not
                        # transferring still needs transfer evidence,
                        # unchanged (incident 2026-08-21: a foreign
                        # local-only dir matched via a child basename).
                        post_transfer_pending = (
                            key in self.__pending_child_notices and
                            root_file is not None and
                            root_file.remote_size is not None
                        )
                        # A root-level notice for a directory root carries
                        # no per-child information: replayed at commit it
                        # would mark the pack imported with no
                        # imported_children entry, and the coverage guard
                        # would grandfather the whole pack for deletion.
                        # Only child-level notices are credited or kept.
                        root_level_dir = (
                            (transferring or post_transfer_pending) and root_file.is_dir and
                            matched_name.lower() == root_name.lower()
                        )
                        if (not transferring and not post_transfer_pending) or \
                                path is None or root_level_dir:
                            self.__pending_child_notices.pop(key, None)
                            self.logger.warning(
                                "Ignoring webhook import for '{}': not downloaded "
                                "by SeedSyncarr (no transfer evidence)".format(
                                    sanitize_log_value(root_name)
                                )
                            )
                            continue
                        post_transfer_only = post_transfer_pending and not transferring
                        if post_transfer_only:
                            self.logger.debug(
                                "Keeping webhook notice '{}' for '{}': transfer "
                                "finished, awaiting commit".format(
                                    sanitize_log_value(matched_name), sanitize_log_value(root_name)
                                )
                            )
                        if matched_name.lower() != root_name.lower() and \
                                self.__credit_early_child(root_file, root_name, matched_name):
                            self.__pending_child_notices.pop(key, None)
                            persist_changed = True
                            continue
                        self.__keep_pending_notice(
                            root_name, matched_name, path, now,
                            reason="transfer finished, awaiting commit" if post_transfer_only
                            else "root still transferring",
                        )
                        continue
                    self.logger.info(
                        "Committing '{}' to downloaded list on import evidence".format(
                            sanitize_log_value(root_name)
                        )
                    )
                    self.__persist.downloaded_file_names.add(root_name)
                # Accepted. A replayed notice only gets here after passing
                # revalidation this cycle, so it is consumed now.
                self.__pending_child_notices.pop(key, None)
                accepted_roots.add(root_name)
                persist_changed = True
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

            # Arm on commit (level-triggered every cycle, so it also covers a
            # restart): a root holding early credits that has since committed
            # to downloaded is marked imported and scheduled like a webhook
            # accept. Coverage still decides whether the Timer deletes.
            model_names = self.__model.get_file_names()
            for root_name in list(self.__persist.imported_children.keys()):
                if root_name not in self.__persist.downloaded_file_names or \
                        root_name in self.__persist.imported_file_names or \
                        root_name not in model_names:
                    continue
                self.__persist.imported_file_names.add(root_name)
                self._set_import_status(self.__model, root_name)
                self.logger.info(
                    "Import credit for '{}' applied on commit".format(sanitize_log_value(root_name))
                )
                accepted_roots.add(root_name)
                persist_changed = True

        # Persist outside every controller lock (the callback takes only the
        # persist-file lock). A failure is logged; the periodic save retries.
        if persist_changed and self.__persist_callback is not None:
            try:
                self.__persist_callback()
            except Exception as e:
                self.logger.warning(
                    "Immediate persist after import credit failed: {}".format(type(e).__name__)
                )

        # Schedule auto-deletes outside lock -- Timer operations only.
        # Only roots that passed the evidence gate are scheduled; the set
        # also de-duplicates roots (two child webhooks in one cycle would
        # otherwise re-arm the same root's timer -- benign but wasteful).
        if accepted_roots and self.__context.config.autodelete.enabled:
            for root_name in accepted_roots:
                self.__schedule_auto_delete(root_name)

    @staticmethod
    def __resolve_path(name_to_paths: Dict[str, Dict[str, str]],
                       root_name: str, matched_name: str) -> Optional[str]:
        """The single model path matched_name resolves to under root_name, or None."""
        candidates = name_to_paths.get(matched_name.lower()) or {}
        if len(candidates) != 1:
            return None
        path, owner = next(iter(candidates.items()))
        return path if owner == root_name else None

    def __credit_early_child(self, root_file: ModelFile, root_name: str, matched_name: str) -> bool:
        """Credit matched_name to imported_children[root_name] if that child is
        fully transferred. Caller holds __model_lock and has checked that
        either the root is a remote release SeedSyncarr is transferring, or
        it holds a revalidated pending notice for this child (122-10,
        D-06c).

        The child must be the unique non-directory descendant with that name,
        in state DOWNLOADED with local_size == remote_size.
        """
        target = matched_name.lower()
        matches = []
        frontier = collections.deque(root_file.get_children())
        while frontier:
            node = frontier.popleft()
            if not node.is_dir and node.name.lower() == target:
                matches.append(node)
            frontier.extend(node.get_children())
        if len(matches) != 1:
            return False
        child = matches[0]
        if child.state != ModelFile.State.DOWNLOADED or child.remote_size is None or \
                child.local_size != child.remote_size:
            return False
        self.__persist.add_imported_child(root_name, target)
        self.logger.info(
            "Credited early import of '{}' in '{}' (root still transferring)".format(
                sanitize_log_value(matched_name), sanitize_log_value(root_name)
            )
        )
        return True

    def __keep_pending_notice(self, root_name: str, matched_name: str, path: str, now: float,
                              reason: str = "root still transferring") -> None:
        """Hold a notice that cannot be credited yet (controller thread only).

        reason documents why it is being kept, for the DEBUG line below: the
        root is still transferring, or (122-10, D-06c) its transfer has
        ended but it has not yet committed and this notice was already
        pending in the current lifecycle.
        """
        key = (root_name, matched_name)
        if key not in self.__pending_child_notices:
            self.__pending_child_notices[key] = _PendingNotice(
                root_name, matched_name, path,
                self.__root_lifecycle_generation[root_name], now,
            )
            while len(self.__pending_child_notices) > _PENDING_NOTICE_MAX:
                (old_root, old_matched), _ = self.__pending_child_notices.popitem(last=False)
                self.logger.warning(
                    "Dropping oldest pending webhook import '{}' for '{}': more than {} "
                    "pending notices".format(
                        sanitize_log_value(old_matched), sanitize_log_value(old_root),
                        _PENDING_NOTICE_MAX
                    )
                )
        self.logger.debug(
            "Deferring webhook notice '{}' for '{}': {}".format(
                sanitize_log_value(matched_name), sanitize_log_value(root_name), reason
            )
        )

    def _revalidate_pending_notice(self, notice: _PendingNotice,
                                   name_to_paths: Dict[str, Dict[str, str]],
                                   now: float) -> Optional[str]:
        """Check a pending notice against the current model lookup.

        Returns None if the notice may be replayed this cycle, otherwise the
        reason it must be discarded (already logged). Applies the same
        exactly-one-path rule WebhookManager.process uses for fresh events,
        then requires that path to be the one the notice was bound to, under
        the same root, in the root's current lifecycle generation. Controller
        thread only.
        """
        safe_child = sanitize_log_value(notice.matched_name)
        safe_root = sanitize_log_value(notice.root_name)
        if notice.generation != self.__root_lifecycle_generation[notice.root_name]:
            self.logger.debug(
                "Discarding pending webhook import '{}' for '{}': lifecycle generation "
                "changed".format(safe_child, safe_root)
            )
            return "lifecycle generation changed"
        candidates = name_to_paths.get(notice.matched_name.lower()) or {}
        if len(candidates) > 1:
            self.logger.warning(
                "Pending webhook import '{}' is ambiguous: matches {} distinct SeedSyncarr "
                "paths in release(s) {} ({}); "
                "no import credit or automatic cleanup authorized".format(
                    safe_child, len(candidates),
                    _format_capped(sorted(set(candidates.values()))),
                    _format_capped(sorted(candidates)),
                )
            )
            return "ambiguous"
        if candidates.get(notice.path) != notice.root_name:
            self.logger.warning(
                "Discarding pending webhook import '{}': it no longer resolves to '{}' in "
                "'{}' (no import credit or automatic cleanup authorized)".format(
                    safe_child, sanitize_log_value(notice.path), safe_root
                )
            )
            return "path gone"
        if now - notice.inserted_at >= _PENDING_NOTICE_TTL_SECS:
            self.logger.warning(
                "Pending webhook import '{}' for '{}' expired after {} s without the "
                "file being seen fully transferred; no import credit recorded".format(
                    safe_child, safe_root, _PENDING_NOTICE_TTL_SECS
                )
            )
            return "expired"
        return None

    def _on_root_lifecycle_reset(self, name: str, cause: str) -> None:
        """Single reset entry point for the per-root caches that must not
        survive into a new download lifecycle: the completion gate's cached
        proof (dropped and fenced) and the root's pending import notices.

        Called by ModelPipeline on the same-name re-grab reset and when a root
        leaves the model. Runs on the controller thread with __model_lock
        already held, so it must not acquire that lock.
        """
        self.__completion_gate.invalidate(name, cause)
        self._discard_pending_notices(name, cause)
        self._cancel_auto_delete(name, cause)

    def _cancel_auto_delete(self, root_name: str, cause: str) -> None:
        """Cancel root_name's pending auto-delete and forget its deferrals.

        Called on a USER requeue and on a root lifecycle reset: a Timer armed
        for the previous lifecycle must never fire against the new copy (it
        would see no per-child tracking and grandfather the root as fully
        imported). Bumping the epoch also neutralizes a Timer that has
        already started running. Takes only __auto_delete_lock, so it is safe
        under __model_lock (lock order __model_lock -> __auto_delete_lock).
        """
        with self.__auto_delete_lock:
            self.__auto_delete_epochs[root_name] += 1
            timer = self.__pending_auto_deletes.pop(root_name, None)
            if timer is not None:
                timer.cancel()
            self.__auto_delete_rearms.pop(root_name, None)
        if timer is not None:
            self.logger.info(
                "Cancelled pending auto-delete of '{}': {}".format(
                    sanitize_log_value(root_name), cause
                )
            )

    def __auto_delete_stale(self, file_name: str, epoch: Optional[int]) -> bool:
        """True if a Timer stamped with epoch belongs to a cancelled lifecycle.

        Caller MUST hold __auto_delete_lock. epoch None (a direct call, not a
        Timer firing) is never stale.
        """
        return epoch is not None and epoch != self.__auto_delete_epochs[file_name]

    def _discard_pending_notices(self, root_name: str, cause: str) -> int:
        """Drop every pending import notice for root_name and start a new
        transfer-lifecycle generation for it. Returns the number dropped.

        Controller thread only. Called after a USER QUEUE (an explicit
        transfer reset that clears the root's import tracking), and on the
        same-name re-grab lifecycle reset and root removal. The generation is
        bumped even when nothing was pending, so no notice recorded under the
        previous lifecycle can ever be credited to the new one.
        """
        keys = [k for k, n in self.__pending_child_notices.items() if n.root_name == root_name]
        for key in keys:
            del self.__pending_child_notices[key]
        self.__root_lifecycle_generation[root_name] += 1
        if keys:
            self.logger.info(
                "Discarded {} pending import notice(s) for '{}': {}".format(
                    len(keys), sanitize_log_value(root_name), cause
                )
            )
        else:
            self.logger.debug(
                "No pending import notices to discard for '{}': {}".format(
                    sanitize_log_value(root_name), cause
                )
            )
        return len(keys)

    def __schedule_auto_delete(self, file_name: str):
        """Schedule auto-delete of local file after safety delay.

        This is the fresh arm from a webhook import: it resets the deferral
        counter so a new import cycle gets a full retry budget.
        """
        with self.__auto_delete_lock:
            self.__auto_delete_rearms.pop(file_name, None)
            delay = self.__arm_auto_delete_timer(file_name)
            self.logger.info(
                "Scheduled auto-delete of '{}' in {} seconds".format(sanitize_log_value(file_name), delay)
            )

    def __arm_auto_delete_timer(self, file_name: str) -> int:
        """Start (or restart) the auto-delete Timer for file_name; returns the delay.

        Caller MUST hold __auto_delete_lock.
        """
        # Cancel existing timer if file was re-detected
        if file_name in self.__pending_auto_deletes:
            self.__pending_auto_deletes[file_name].cancel()
            del self.__pending_auto_deletes[file_name]

        delay = self.__context.config.autodelete.delay_seconds
        timer = threading.Timer(delay, self.__execute_auto_delete,
                                args=[file_name, self.__auto_delete_epochs[file_name]])
        timer.daemon = True  # Don't prevent process exit
        self.__pending_auto_deletes[file_name] = timer
        timer.start()
        return delay

    def __defer_auto_delete(self, file_name: str, reason: str, epoch: Optional[int] = None):
        """Re-arm the auto-delete Timer after a retriable skip.

        Bounded by _AUTO_DELETE_MAX_REARMS consecutive deferrals per root; on
        exhaustion logs one WARNING and drops the root (a later webhook import
        arms it afresh). Called OUTSIDE __model_lock, same pattern as the
        webhook path. Runs under __auto_delete_lock so it is ordered against
        exit(): once the shutdown event is set no new Timer is ever armed
        (BUG-03 criterion #1 holds for re-armed timers too).
        """
        with self.__auto_delete_lock:
            if self.__shutdown_event.is_set():
                return
            if self.__auto_delete_stale(file_name, epoch):
                return  # lifecycle cancelled while this Timer ran: never re-arm
            attempt = self.__auto_delete_rearms.get(file_name, 0) + 1
            if attempt > _AUTO_DELETE_MAX_REARMS:
                self.__auto_delete_rearms.pop(file_name, None)
                self.logger.warning(
                    "Auto-delete given up for '{}' after {} deferrals; last reason: {}. "
                    "Local copy left in place".format(
                        sanitize_log_value(file_name), _AUTO_DELETE_MAX_REARMS, reason
                    )
                )
                return
            self.__auto_delete_rearms[file_name] = attempt
            delay = self.__arm_auto_delete_timer(file_name)
            self.logger.info(
                "Auto-delete deferred for '{}' (attempt {}/{}): {}; retrying in {} s".format(
                    sanitize_log_value(file_name), attempt, _AUTO_DELETE_MAX_REARMS, reason, delay
                )
            )

    def __clear_auto_delete_rearms(self, file_name: str):
        """Forget the deferral counter for file_name (success or terminal skip).

        Safe to call while holding __model_lock: the lock order is __model_lock
        THEN __auto_delete_lock, and exit() never takes __model_lock.

        The per-root reservation (__root_reservations) is the OUTERMOST lock:
        __execute_auto_delete takes it before __model_lock, so the full order
        is reservation -> __model_lock -> __auto_delete_lock. exit() never
        takes it. __defer_auto_delete may run while it is held (it only takes
        __auto_delete_lock). On the delete path the reservation outlives
        __execute_auto_delete: it is handed to delete_local and released by
        FileOperationManager.cleanup_completed_processes from process() once
        the deletion child has exited.
        """
        with self.__auto_delete_lock:
            self.__auto_delete_rearms.pop(file_name, None)

    def __execute_auto_delete(self, file_name: str, epoch: Optional[int] = None):
        """Execute auto-delete of local file (called by Timer after delay).

        Thread safety: the model.get_file() call is protected by __model_lock.
        delete_local() runs OUTSIDE the lock -- it spawns a subprocess, and
        holding the lock across a blocking subprocess call would starve model
        updates on the controller thread.

        ModelFile is frozen (immutable) after being added to the model, so
        the `file` reference is safe to use after releasing the lock.

        Skip semantics: a skip for a retriable reason (root or a child still
        mid-lifecycle, pack not fully imported yet) re-arms the Timer through
        __defer_auto_delete, bounded by _AUTO_DELETE_MAX_REARMS. Terminal skips
        (feature disabled, dry-run, file gone from the model, no download
        evidence, BFS node limit, duplicate video basenames) never re-arm and
        clear the deferral counter.

        epoch is the root's auto-delete epoch when the Timer was armed; a
        Timer whose lifecycle was cancelled (_cancel_auto_delete) is a no-op.
        """
        # Remove from tracking dict; entry guard for shutdown (BUG-03 criterion #2).
        # Checking __shutdown_event inside __auto_delete_lock is the fast-path:
        # if exit() has already set the event under the same lock, we can return
        # immediately without doing any model read — the callback is a no-op.
        with self.__auto_delete_lock:
            if self.__auto_delete_stale(file_name, epoch):
                # Cancelled lifecycle: leave any newer Timer and counter alone.
                return
            self.__pending_auto_deletes.pop(file_name, None)
            if self.__shutdown_event.is_set():
                return

        # Re-check config -- user might have disabled auto-delete after timer was scheduled
        if not self.__context.config.autodelete.enabled:
            self.logger.info(
                "Auto-delete skipped for '{}': feature was disabled".format(sanitize_log_value(file_name))
            )
            self.__clear_auto_delete_rearms(file_name)
            return

        # Check dry-run mode
        if self.__context.config.autodelete.dry_run:
            self.logger.info(
                "DRY-RUN: Would delete local file '{}'".format(sanitize_log_value(file_name))
            )
            self.__clear_auto_delete_rearms(file_name)
            return

        # Per-root reservation, taken BEFORE __model_lock (outermost lock). It
        # serializes this decision-to-deletion window against a QUEUE
        # submission for the same root: both this method and
        # __process_commands release __model_lock before acting, so the model
        # lock alone cannot stop a QUEUE landing between the guards below and
        # delete_local. Non-blocking: a held root defers (retriable, bounded
        # by the re-arm budget).
        reservation = self.__root_reservations.acquire(file_name, "auto-delete")
        if reservation is None:
            self.__defer_auto_delete(file_name, "root operation in progress", epoch)
            return
        # Set once the reservation is handed to delete_local, which then owns
        # it until the deletion child exits. Every other path releases it in
        # the finally below.
        handed_off = False
        try:
            # Get file from model under lock -- ensures file still exists in model
            # at the moment we read it, preventing use of a stale reference.
            # State guards also run under the lock so we check against a consistent
            # snapshot of the model (states can flip as scanners update).
            deletable_states = (
                ModelFile.State.DEFAULT,
                ModelFile.State.DOWNLOADED,
                ModelFile.State.EXTRACTED,
            )
            # Set to a human-readable reason when the delete must be retried later;
            # the re-arm itself happens after __model_lock is released.
            defer_reason = None
            with self.__model_lock:
                try:
                    file = self.__model.get_file(file_name)
                except ModelError:
                    self.logger.debug(
                        "File '{}' no longer in model, skipping auto-delete".format(sanitize_log_value(file_name))
                    )
                    self.__clear_auto_delete_rearms(file_name)
                    return

                # Evidence gate: refuse to delete anything SeedSyncarr never
                # downloaded. Membership in downloaded_file_names is the required
                # evidence — without it a webhook child-match under a foreign
                # directory (incident 2026-08-21: 'iplayer') would arm deletion of
                # data this app does not own.
                if file_name not in self.__persist.downloaded_file_names:
                    self.logger.warning(
                        "Auto-delete refused for '{}': not downloaded by SeedSyncarr".format(
                            sanitize_log_value(file_name)
                        )
                    )
                    self.__clear_auto_delete_rearms(file_name)
                    return

                # State guard: do not delete a file that is mid-lifecycle. Mirrors
                # __handle_delete_command so the Timer path cannot race an in-flight
                # sync, queue, or extract when a re-download arrives between
                # scheduling and firing (e.g., Deluge re-seed triggers a re-sync).
                # Retriable: the root will become deletable once the transfer or
                # extraction finishes (incident 2026-09-16: webhook accepted while
                # the root was EXTRACTING; the one-shot skip stranded the copy).
                if file.state not in deletable_states:
                    defer_reason = "file is in state {}".format(str(file.state))

                # Submitted-but-unobserved guard (DEL-01): lftp accepted a
                # QUEUE for this root but no successful status has observed
                # the job yet, so the model may still show the stale-retained
                # DOWNLOADED state (XFER-02). Never delete a copy lftp is about
                # to overwrite. Retriable through __defer_auto_delete: once a
                # successful status (even an empty one) clears the set, the
                # next firing proceeds if the other guards pass -- the job
                # need not appear active. Runs before the pack/coverage scan so
                # a submitted directory root defers without walking children.
                elif file_name in self.__lftp_manager.submitted_unobserved_file_names():
                    defer_reason = "transfer submitted, awaiting lftp status"

                # Pack guard + coverage-basename collection: delegated to AutoDeleteManager.
                # run_bfs_and_coverage performs BFS over descendants in a single pass:
                # (a) Pack guard: skip if ANY child is in an active state. Prevents wiping
                #     a season pack while a sibling is still being downloaded or extracted
                #     (Sonarr's per-episode webhook schedules the pack root).
                # (b) Coverage collection: gather lowercased basenames of all on-disk
                #     video children for the coverage guard (D-08, D-09).
                # Caller holds __model_lock; AutoDeleteManager acquires NO lock (D-03).
                elif file.is_dir:
                    skip, reason, _on_disk_videos = self.__auto_delete_mgr.run_bfs_and_coverage(
                        file, file_name, deletable_states
                    )
                    if skip:
                        if reason in _AUTO_DELETE_TERMINAL_SKIPS:
                            # Terminal skip: Timer does not re-arm. Clear the
                            # per-child entry so imported_children isn't stranded
                            # on a permanently-oversized pack or a pack with
                            # duplicate video basenames. All other skip paths are
                            # retriable and leave the entry intact.
                            self.__persist.imported_children.pop(file_name, None)
                            self.__clear_auto_delete_rearms(file_name)
                            return
                        defer_reason = _AUTO_DELETE_DEFER_REASONS.get(reason, reason)

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
                if defer_reason is None:
                    with self.__auto_delete_lock:
                        if self.__shutdown_event.is_set():
                            return  # no pop, no dispatch (D-02: shutdown has committed)
                        if self.__auto_delete_stale(file_name, epoch):
                            # USER requeue / lifecycle reset since this Timer
                            # was armed: the copy belongs to a new lifecycle.
                            return
                        # WR-02: clear the per-child entry before dispatching delete_local.
                        self.__persist.imported_children.pop(file_name, None)
                        # Success: forget any deferrals from earlier firings.
                        self.__auto_delete_rearms.pop(file_name, None)

            if defer_reason is not None:
                # Retriable skip: re-arm OUTSIDE __model_lock (Timer operations only,
                # same pattern as the webhook path) so a later firing can retry.
                self.__defer_auto_delete(file_name, defer_reason, epoch)
                return

            # delete_local is safe outside lock -- it spawns a subprocess; holding
            # __model_lock across a blocking subprocess call would starve model updates.
            # `file` is captured above; ModelFile is frozen/immutable after add.
            # Ownership of the reservation transfers at entry: delete_local
            # releases it when the child is observed dead, on launch failure,
            # or on stop(), so it outlives this method.
            handed_off = True
            self.__file_op_manager.delete_local(file, reservation=reservation)
            self.logger.info("Auto-deleted local file '{}'".format(sanitize_log_value(file_name)))
        finally:
            if not handed_off:
                reservation.release()

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

            # A USER QUEUE is an explicit transfer reset: CommandProcessor has
            # just cleared the root's downloaded/imported/per-child tracking.
            # Pending import notices from the previous attempt must not
            # outlive that reset, or a scan-lag notice could credit the
            # replacement copy without a new import webhook. Same thread, and
            # __check_webhook_imports runs later in this process() call, so
            # nothing can replay a notice in between. AUTO queues (resume or
            # retry of the same attempt) keep their notices.
            if command.action == Controller.Command.Action.QUEUE and \
                    (getattr(command, "origin", None) is None or command.origin.name != 'AUTO'):
                self._discard_pending_notices(command.filename, "user requeue")
                # The previous lifecycle's auto-delete Timer must not fire
                # against the re-queued copy (its tracking was just cleared).
                self._cancel_auto_delete(command.filename, "user requeue")

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
