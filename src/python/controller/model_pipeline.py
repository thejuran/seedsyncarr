import copy
from typing import List, Optional, Tuple

from common import Context
from model import ModelError, ModelFile, Model, ModelDiff, ModelDiffUtil
from lftp import LftpJobStatus
from .extract import ExtractStatusResult, ExtractCompletedResult
from .scan import ScannerResult


class ModelPipeline:
    """
    Orchestrates the scan->build->diff->apply model update pipeline.

    Responsible for collecting scan/LFTP/extract results, feeding the model
    builder, building and applying model diffs, and tracking file state in persist.

    Thread-safety: build_and_apply_model acquires model_lock (the SAME Lock object
    owned by Controller, stored as self._model_lock — single-underscore to preserve
    identity, D-03 / Pitfall 3). No other lock is acquired by this collaborator.
    """

    def __init__(self,
                 context: Context,
                 persist,
                 model: Model,
                 model_lock,
                 model_builder,
                 scan_manager,
                 lftp_manager,
                 file_op_manager,
                 logger):
        """
        Receive already-constructed manager instances from Controller.__init__ (D-05).
        Do NOT construct any manager class here; that would break mock.patch binding.
        model_lock must be the SAME threading.Lock held by Controller (D-03).
        """
        self._context = context
        self._persist = persist
        self._model = model
        # Single-underscore: preserves identity with Controller._Controller__model_lock (D-03).
        self._model_lock = model_lock
        self._model_builder = model_builder
        self._scan_manager = scan_manager
        self._lftp_manager = lftp_manager
        self._file_op_manager = file_op_manager
        self.logger = logger.getChild("ModelPipeline")

    # =========================================================================
    # Public pipeline entry point
    # =========================================================================

    def update_model(self) -> Tuple[
        Optional[ScannerResult],
        Optional[ScannerResult],
        Optional[List[LftpJobStatus]],
        Optional[ExtractStatusResult],
    ]:
        """
        Run collect->feed->build pipeline stages that live in this collaborator.

        Returns (latest_remote_scan, latest_local_scan, lftp_statuses, latest_extract_statuses)
        so the coordinator can pass them to the retained stages
        (_update_active_file_tracking, _update_controller_status) without calling
        back into ModelPipeline.

        Stages _update_active_file_tracking, _update_controller_status, and
        __check_webhook_imports remain on Controller and are called by the
        coordinator after this method returns.
        """
        latest_remote_scan, latest_local_scan, latest_active_scan = self.collect_scan_results()
        lftp_statuses = self.collect_lftp_status()
        latest_extract_statuses, latest_extracted_results = self.collect_extract_results()

        self.feed_model_builder(
            latest_remote_scan,
            latest_local_scan,
            latest_active_scan,
            lftp_statuses,
            latest_extract_statuses,
            latest_extracted_results,
        )
        self.build_and_apply_model(latest_remote_scan)

        return latest_remote_scan, latest_local_scan, lftp_statuses, latest_extract_statuses

    # =========================================================================
    # Collection stage methods
    # =========================================================================

    def collect_scan_results(self) -> Tuple[Optional[ScannerResult], Optional[ScannerResult], Optional[ScannerResult]]:
        """Collect the latest scan results from all scanner processes.
        Returns (remote_scan, local_scan, active_scan); None if no new result."""
        return self._scan_manager.pop_latest_results()

    def collect_lftp_status(self) -> Optional[List[LftpJobStatus]]:
        """Collect current LFTP job statuses. Returns None if an error occurred."""
        return self._lftp_manager.status()

    def collect_extract_results(self) -> Tuple[Optional[ExtractStatusResult], List[ExtractCompletedResult]]:
        """Collect extract process status and completed extractions.
        Returns (extract_statuses, completed_extractions)."""
        latest_extract_statuses = self._file_op_manager.pop_extract_statuses()
        latest_extracted_results = self._file_op_manager.pop_completed_extractions()
        return latest_extract_statuses, latest_extracted_results

    # =========================================================================
    # Import-status helper (used internally and by Controller.__check_webhook_imports)
    # =========================================================================

    def _set_import_status(self, model: Model, file_name: str) -> None:
        """Set import_status to IMPORTED on a model file if not already set.
        Creates a mutable copy, updates status, and writes back to model."""
        try:
            file = model.get_file(file_name)
        except ModelError:
            return
        if file.import_status != ModelFile.ImportStatus.IMPORTED:
            new_file = copy.copy(file)
            new_file._unfreeze()  # intentional protected access: controller owns the freeze lifecycle
            # Deep-copy children so we don't mutate frozen objects shared with other threads
            new_children = []
            for child in new_file.get_children():
                new_child = copy.copy(child)
                new_child._unfreeze()
                new_child._set_parent(new_file)
                new_child.freeze()
                new_children.append(new_child)
            new_file._replace_children(new_children)
            new_file.import_status = ModelFile.ImportStatus.IMPORTED
            model.update_file(new_file)

    # =========================================================================
    # Feed stage
    # =========================================================================

    def feed_model_builder(self,
                           remote_scan: Optional[ScannerResult],
                           local_scan: Optional[ScannerResult],
                           active_scan: Optional[ScannerResult],
                           lftp_statuses: Optional[List[LftpJobStatus]],
                           extract_statuses: Optional[ExtractStatusResult],
                           extracted_results: List) -> None:
        """Feed the model builder with all collected data.
        Updates builder state with scan results, LFTP statuses, and extract info.
        Also updates persist state for completed extractions."""
        if remote_scan is not None and not remote_scan.failed:
            self._model_builder.set_remote_files(remote_scan.files)
        if local_scan is not None and not local_scan.failed:
            self._model_builder.set_local_files(local_scan.files)
        if active_scan is not None and not active_scan.failed:
            self._model_builder.set_active_files(active_scan.files)
        if lftp_statuses is not None:
            self._model_builder.set_lftp_statuses(lftp_statuses)
        if extract_statuses is not None:
            self._model_builder.set_extract_statuses(extract_statuses.statuses)
        if extracted_results:
            for result in extracted_results:
                self._persist.extracted_file_names.add(result.name)
            self._model_builder.set_extracted_files(self._persist.extracted_file_names)

    # =========================================================================
    # Tracking helpers (called from apply_model_diff and build_and_apply_model)
    # =========================================================================

    def detect_and_track_queued(self, diff: ModelDiff) -> None:
        """Detect if a file has started downloading and update persist state.

        Tracked when DOWNLOADING with local_size > 0. Not tracked when merely
        QUEUED — stopping a queued file returns it to DEFAULT, not DELETED.
        """
        new_file = diff.new_file
        if not new_file:
            return
        if new_file.state != ModelFile.State.DOWNLOADING:
            return
        if not new_file.local_size or new_file.local_size <= 0:
            return
        if new_file.name in self._persist.downloaded_file_names:
            return

        should_track = False
        if diff.change == ModelDiff.Change.ADDED:
            should_track = True
        elif diff.change == ModelDiff.Change.UPDATED:
            old_file = diff.old_file
            old_state = old_file.state if old_file else None
            old_local_size = old_file.local_size if old_file else None
            if old_state not in (ModelFile.State.DOWNLOADING, ModelFile.State.DOWNLOADED):
                should_track = True
            elif old_state == ModelFile.State.DOWNLOADING and (old_local_size is None or old_local_size <= 0):
                should_track = True

        if should_track:
            self._persist.downloaded_file_names.add(new_file.name)
            self._model_builder.set_downloaded_files(self._persist.downloaded_file_names)

    def detect_and_track_download(self, diff: ModelDiff) -> None:
        """Detect if a file was just downloaded and update persist state.

        "Just downloaded" = added in DOWNLOADED state, or updated TO DOWNLOADED
        from a non-DOWNLOADED state.
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
            self._persist.downloaded_file_names.add(diff.new_file.name)
            self._model_builder.set_downloaded_files(self._persist.downloaded_file_names)

    def prune_extracted_files(self) -> None:
        """Remove DELETED files from the extracted files tracking list.
        Prevents re-downloaded files from going to EXTRACTED state.
        Must be called while holding the model lock."""
        remove_extracted_file_names = set()
        existing_file_names = self._model.get_file_names()

        for extracted_file_name in self._persist.extracted_file_names:
            if extracted_file_name in existing_file_names:
                file = self._model.get_file(extracted_file_name)
                if file.state == ModelFile.State.DELETED:
                    remove_extracted_file_names.add(extracted_file_name)
            # Note: Files not in model could be because scans aren't available yet

        if remove_extracted_file_names:
            self.logger.info("Removing from extracted list: {}".format(remove_extracted_file_names))
            self._persist.extracted_file_names.difference_update(remove_extracted_file_names)
            self._model_builder.set_extracted_files(self._persist.extracted_file_names)

    def _prune_downloaded_files(self, latest_remote_scan: Optional[ScannerResult]) -> None:
        """No-op: downloaded_file_names uses BoundedOrderedSet with LRU eviction.

        Files are intentionally kept even when deleted from both local and remote,
        preventing re-downloads of files moved by external tools (e.g., Sonarr).
        BoundedOrderedSet evicts oldest entries when the configured limit is reached.
        Must be called while holding the model lock.
        """
        # No pruning needed - BoundedOrderedSet handles eviction automatically
        pass

    # =========================================================================
    # Diff application stage
    # =========================================================================

    def apply_model_diff(self, model_diff: List[ModelDiff]) -> None:
        """Apply model differences: ADDED->add_file, REMOVED->remove_file, UPDATED->update_file.
        Also tracks newly queued/downloaded files. Must be called holding the model lock."""
        for diff in model_diff:
            if diff.change == ModelDiff.Change.ADDED:
                self._model.add_file(diff.new_file)
            elif diff.change == ModelDiff.Change.REMOVED:
                self._model.remove_file(diff.old_file.name)
            elif diff.change == ModelDiff.Change.UPDATED:
                self._model.update_file(diff.new_file)

            self.detect_and_track_queued(diff)
            self.detect_and_track_download(diff)

    # =========================================================================
    # Build and apply stage
    # =========================================================================

    def build_and_apply_model(self, latest_remote_scan: Optional[ScannerResult]) -> None:
        """Build a new model and apply changes if the model builder has updates.

        Steps: build model -> apply import_status from persist -> acquire model_lock
        -> diff -> apply_model_diff -> prune_extracted_files -> _prune_downloaded_files.

        All model mutations are performed while holding self._model_lock — the
        SAME Lock object as Controller.__model_lock (D-03, single-underscore storage).
        """
        if not self._model_builder.has_changes():
            return

        new_model = self._model_builder.build_model()

        # Apply import_status from persisted set BEFORE diffing.
        # Model builder creates files with default import_status=NONE.
        # Without this, every rebuild cycle produces spurious SSE events:
        #   update(NONE) then update(IMPORTED), causing repeated frontend toasts.
        for file_name in new_model.get_file_names():
            if file_name in self._persist.imported_file_names:
                self._set_import_status(new_model, file_name)

        # Lock the model for all modifications
        with self._model_lock:
            model_diff = ModelDiffUtil.diff_models(self._model, new_model)
            self.apply_model_diff(model_diff)
            self.prune_extracted_files()
            self._prune_downloaded_files(latest_remote_scan)
