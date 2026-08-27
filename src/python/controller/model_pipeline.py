import copy
import time
from typing import List, Optional, Tuple

from common import Context, sanitize_log_value
from model import ModelError, ModelFile, Model, ModelDiff, ModelDiffUtil
from lftp import LftpJobStatus
from .extract import ExtractStatusResult, ExtractCompletedResult
from .scan import ScannerResult


# Minimum continuous absence (from both local and remote) before a re-appearing
# remote file is treated as a NEW lifecycle (Sonarr/Radarr re-grab) and its stale
# downloaded/imported tracking is cleared. Long enough that a transient empty
# remote scan (seedbox-side mount flap) cannot mass-clear tracking and trigger a
# re-download storm; short enough that a re-grabbed release syncs automatically
# by the next day instead of being blacklisted forever.
_LIFECYCLE_ABSENCE_THRESHOLD_SECONDS = 24 * 3600


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

    def detect_and_track_download(self, diff: ModelDiff) -> None:
        """Detect if a file was just downloaded and update persist state.

        "Just downloaded" = added in DOWNLOADED state, or updated TO DOWNLOADED
        from a non-DOWNLOADED state.

        Only COMPLETED downloads are tracked. Files that merely started
        downloading must stay untracked: an interrupted transfer whose partial
        file later disappears would otherwise be marked DELETED and permanently
        skipped by auto-queue instead of being re-queued (GH incident 2026-07-23,
        "Eyes Wide Shut" 73.7GB never re-synced).
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
        """Track absence of downloaded files and reset tracking on a new lifecycle.

        Files in downloaded_file_names are intentionally kept when they disappear
        from both local and remote, preventing re-downloads of files moved by
        external tools (e.g., Sonarr) while the torrent still seeds remotely.

        However, when a file has been absent from the model for longer than
        _LIFECYCLE_ABSENCE_THRESHOLD_SECONDS and then RE-APPEARS remotely, that
        is a new lifecycle: Sonarr/Radarr re-grabbed a release it had previously
        imported (the torrent was re-added to the seedbox). The stale downloaded/
        imported entries from the previous lifecycle would otherwise mark the file
        DELETED and blacklist it from auto-queue forever (incident 2026-07-23:
        re-grabbed release silently never synced). On re-appearance the stale
        entries are cleared so the file syncs fresh.

        The absence clock only advances on cycles with a successful remote scan,
        so a seedbox outage (no successful scans) does not accrue absence. The
        threshold guards against transient empty-scan flaps mass-clearing
        tracking and causing a re-download storm.

        Must be called while holding the model lock.
        """
        if latest_remote_scan is None or latest_remote_scan.failed:
            return

        now = time.time()
        model_file_names = self._model.get_file_names()
        absent_since = self._persist.absent_since

        for file_name in list(self._persist.downloaded_file_names):
            if file_name in model_file_names:
                first_absent = absent_since.pop(file_name, None)
                if first_absent is None:
                    continue
                file = self._model.get_file(file_name)
                absence_duration = now - first_absent
                if file.remote_size is not None and \
                        absence_duration > _LIFECYCLE_ABSENCE_THRESHOLD_SECONDS:
                    self.logger.info(
                        "New lifecycle detected for '{}' (absent for {:.1f}h): "
                        "clearing downloaded/imported tracking so it can sync".format(
                            file_name, absence_duration / 3600.0
                        )
                    )
                    self._persist.downloaded_file_names.discard(file_name)
                    self._persist.imported_file_names.discard(file_name)
                    self._persist.imported_children.pop(file_name, None)
                    self._model_builder.set_downloaded_files(self._persist.downloaded_file_names)
            else:
                absent_since.setdefault(file_name, now)

        # Drop absence records for names no longer tracked (evicted or cleared)
        for file_name in list(absent_since.keys()):
            if file_name not in self._persist.downloaded_file_names:
                del absent_since[file_name]

    def _commit_downloaded_membership(self) -> None:
        """Ensure downloaded_file_names reflects the evidence in the current model.

        Level-triggered complement to detect_and_track_download (which is
        edge-triggered on an observed diff transition into DOWNLOADED and
        misses completions that happen across a restart, while duplicate lftp
        jobs pin the state, or when the local copy is deleted before the
        transition is observed — incident 2026-08-22, releases stuck in
        'imported' and re-queued at every restart burst).

        Two evidence rules, both idempotent:
        - A file whose current state is DOWNLOADED or EXTRACTED is complete;
          commit it. (DOWNLOADING/QUEUED stay untracked so an interrupted
          transfer can re-queue — incident 2026-07-23.)
        - A file in imported_file_names with a remote copy was really imported
          by an arr from our staging area; commit it even if the local copy is
          already gone, so the next restart burst cannot re-queue it. A file
          with no remote copy (e.g. a foreign local-only dir matched by a
          webhook) is never committed.

        Must be called while holding the model lock.
        """
        changed = False
        downloaded = self._persist.downloaded_file_names
        for name in self._model.get_file_names():
            if name in downloaded:
                continue
            file = self._model.get_file(name)
            if file.state in (ModelFile.State.DOWNLOADED, ModelFile.State.EXTRACTED):
                self.logger.info(
                    "Committing completed download '{}' to downloaded list".format(sanitize_log_value(name))
                )
                downloaded.add(name)
                changed = True
            elif name in self._persist.imported_file_names and \
                    file.remote_size is not None:
                self.logger.info(
                    "Committing imported release '{}' to downloaded list "
                    "(import is download evidence; local copy {})".format(
                        sanitize_log_value(name),
                        "absent" if file.local_size is None else "present"
                    )
                )
                downloaded.add(name)
                changed = True
        if changed:
            self._model_builder.set_downloaded_files(downloaded)

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
            # Runs after the lifecycle reset so a detected re-grab starts the
            # new lifecycle untracked instead of being immediately re-committed.
            self._commit_downloaded_membership()
