# Copyright 2017, Inderpreet Singh, All rights reserved.

import collections
import os
import logging
import time
from typing import List, Optional
import math

# my libs
from system import SystemFile
from lftp import LftpJobStatus
from model import ModelFile, Model, ModelError
from common.bounded_ordered_set import BoundedOrderedSet
from .extract import ExtractStatus, Extract


class ModelBuilder:
    """
    ModelBuilder combines all the difference sources of file system info
    to build a model. These sources include:
      * downloading file system as a Dict[name, SystemFile]
      * local file system as a Dict[name, SystemFile]
      * remote file system as a Dict[name, SystemFile]
      * lftp status as Dict[name, LftpJobStatus]
    """
    # TTL for cached model in seconds (30 minutes)
    CACHE_TTL_SECONDS = 30 * 60

    def __init__(self):
        self.logger = logging.getLogger("ModelBuilder")
        self.__local_files = dict()
        self.__remote_files = dict()
        self.__lftp_statuses = dict()
        self.__downloaded_files: Optional[BoundedOrderedSet] = None
        self.__extract_statuses = dict()
        self.__extracted_files = set()
        self.__cached_model = None
        self.__cache_timestamp = None

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("ModelBuilder")

    def set_active_files(self, active_files: List[SystemFile]):
        # Update the local file state with this latest information
        for file in active_files:
            self.__local_files[file.name] = file
        # Invalidate the cache
        if len(active_files) > 0:
            self.__cached_model = None

    def set_local_files(self, local_files: List[SystemFile]):
        prev_local_files = self.__local_files
        self.__local_files = {file.name: file for file in local_files}
        # Invalidate the cache
        if self.__local_files != prev_local_files:
            self.__cached_model = None

    def set_remote_files(self, remote_files: List[SystemFile]):
        prev_remote_files = self.__remote_files
        self.__remote_files = {file.name: file for file in remote_files}
        # Invalidate the cache
        if self.__remote_files != prev_remote_files:
            self.__cached_model = None

    def set_lftp_statuses(self, lftp_statuses: List[LftpJobStatus]):
        prev_lftp_statuses = self.__lftp_statuses
        self.__lftp_statuses = {file.name: file for file in lftp_statuses}
        # Invalidate the cache
        if self.__lftp_statuses != prev_lftp_statuses:
            self.__cached_model = None

    def set_downloaded_files(self, downloaded_files: BoundedOrderedSet):
        prev_downloaded_files = self.__downloaded_files
        self.__downloaded_files = downloaded_files
        # Invalidate the cache
        if self.__downloaded_files != prev_downloaded_files:
            self.__cached_model = None

    def set_extract_statuses(self, extract_statuses: List[ExtractStatus]):
        prev_extract_statuses = self.__extract_statuses
        self.__extract_statuses = {status.name: status for status in extract_statuses}
        # Invalidate the cache
        if self.__extract_statuses != prev_extract_statuses:
            self.__cached_model = None

    def set_extracted_files(self, extracted_files: set):
        prev_extracted_files = self.__extracted_files
        self.__extracted_files = extracted_files
        # Invalidate the cache
        if self.__extracted_files != prev_extracted_files:
            self.__cached_model = None

    def clear(self):
        self.__local_files.clear()
        self.__remote_files.clear()
        self.__lftp_statuses.clear()
        self.__downloaded_files = None
        self.__extract_statuses.clear()
        self.__extracted_files.clear()
        self.__cached_model = None
        self.__cache_timestamp = None

    def has_changes(self) -> bool:
        """
        Returns true is model has changes and requires rebuild
        :return:
        """
        return self.__cached_model is None

    def build_model(self) -> Model:
        """
        Build a model from all data sources.

        Combines remote files, local files, and LFTP statuses to create
        a unified model with proper state for each file.
        """
        # Check cache validity
        if self._is_cache_valid():
            return self.__cached_model

        model = Model()
        model.set_base_logger(logging.getLogger("dummy"))  # ignore the logs for this temp model

        all_file_names = set().union(
            self.__local_files.keys(),
            self.__remote_files.keys(),
            self.__lftp_statuses.keys()
        )

        for name in all_file_names:
            model_file = self._build_root_file(name)
            self._determine_final_state(model_file)
            model.add_file(model_file)

        self.__cached_model = model
        self.__cache_timestamp = time.time()
        return model

    def _is_cache_valid(self) -> bool:
        """
        Check if the cached model is still valid.

        Returns False if cache is None or has exceeded TTL.
        """
        if self.__cached_model is None:
            return False

        if self.__cache_timestamp is not None:
            cache_age = time.time() - self.__cache_timestamp
            if cache_age > self.CACHE_TTL_SECONDS:
                self.logger.debug("Model cache expired after {:.0f} seconds".format(cache_age))
                self.__cached_model = None
                self.__cache_timestamp = None
                return False

        return True

    def _build_root_file(self, name: str) -> ModelFile:
        """
        Build a ModelFile for a root-level file, including all its children.

        Args:
            name: The name of the file to build

        Returns:
            A fully populated ModelFile with all children
        """
        remote = self.__remote_files.get(name, None)
        local = self.__local_files.get(name, None)
        status = self.__lftp_statuses.get(name, None)

        if remote is None and local is None and status is None:
            raise ModelError("Zero sources have a file object")

        is_dir = self._determine_is_dir(remote, local, status)
        self._validate_is_dir_consistency(is_dir, remote, local, status)

        model_file = ModelFile(name, is_dir)
        self._set_initial_state(model_file, status)

        transfer_state = (status.total_transfer_state
                          if status and status.state == LftpJobStatus.State.RUNNING
                          else None)
        self._fill_model_file(model_file, remote, local, transfer_state)

        # Build children if sources exist
        if remote or local:
            self._build_children(model_file, remote, local, status)

        # Estimate ETA if not provided
        self._estimate_root_eta(model_file)

        return model_file

    def _determine_is_dir(self,
                          remote: Optional[SystemFile],
                          local: Optional[SystemFile],
                          status: Optional[LftpJobStatus]) -> bool:
        """Determine if the file is a directory from available sources."""
        if remote:
            return remote.is_dir
        elif local:
            return local.is_dir
        else:
            return status.type == LftpJobStatus.Type.MIRROR

    def _validate_is_dir_consistency(self,
                                      is_dir: bool,
                                      remote: Optional[SystemFile],
                                      local: Optional[SystemFile],
                                      status: Optional[LftpJobStatus]) -> None:
        """Validate that is_dir is consistent across all sources."""
        if (remote and is_dir != remote.is_dir) or \
           (local and is_dir != local.is_dir) or \
           (status and is_dir != (status.type == LftpJobStatus.Type.MIRROR)):
            raise ModelError("Mismatch in is_dir between sources")

    def _set_initial_state(self,
                           model_file: ModelFile,
                           status: Optional[LftpJobStatus]) -> None:
        """
        Set the initial state for a root file based on LFTP status.

        Only sets QUEUED or DOWNLOADING; final state is determined later.
        """
        if status:
            model_file.state = (ModelFile.State.QUEUED
                                if status.state == LftpJobStatus.State.QUEUED
                                else ModelFile.State.DOWNLOADING)

    def _fill_model_file(self,
                         model_file: ModelFile,
                         remote: Optional[SystemFile],
                         local: Optional[SystemFile],
                         transfer_state: Optional[LftpJobStatus.TransferState]) -> None:
        """
        Populate a ModelFile with size, speed, timestamp, and extractable info.

        Args:
            model_file: The ModelFile to populate
            remote: Remote file info (if available)
            local: Local file info (if available)
            transfer_state: LFTP transfer state (if actively downloading)
        """
        # Set sizes from sources
        if remote:
            model_file.remote_size = remote.size
        if local:
            model_file.local_size = local.size

        # Set downloading speed and eta from transfer state
        if transfer_state:
            model_file.downloading_speed = transfer_state.speed
            model_file.eta = transfer_state.eta

        # Set transferred size (only if file exists on both ends)
        self._set_transferred_size(model_file, remote, local)

        # Set extractable flag
        self._set_extractable_flag(model_file)

        # Set timestamps
        self._set_timestamps(model_file, remote, local)

    def _set_transferred_size(self,
                               model_file: ModelFile,
                               remote: Optional[SystemFile],
                               local: Optional[SystemFile]) -> None:
        """Set the transferred size and propagate to parent directories."""
        if not (local and remote):
            return

        if model_file.is_dir:
            # Directory transferred size is updated by child files
            model_file.transferred_size = 0
        else:
            model_file.transferred_size = min(local.size, remote.size)
            # Propagate to parent directories
            parent_file = model_file.parent
            while parent_file is not None:
                parent_file.transferred_size += model_file.transferred_size
                parent_file = parent_file.parent

    def _set_extractable_flag(self, model_file: ModelFile) -> None:
        """Set the is_extractable flag and propagate to parents."""
        if model_file.is_dir:
            return

        if Extract.is_archive_fast(model_file.name):
            model_file.is_extractable = True
            # Propagate to parent directories
            parent_file = model_file.parent
            while parent_file is not None:
                parent_file.is_extractable = True
                parent_file = parent_file.parent

    def _set_timestamps(self,
                        model_file: ModelFile,
                        remote: Optional[SystemFile],
                        local: Optional[SystemFile]) -> None:
        """Set created and modified timestamps from local and remote sources."""
        if local:
            if local.timestamp_created:
                model_file.local_created_timestamp = local.timestamp_created
            if local.timestamp_modified:
                model_file.local_modified_timestamp = local.timestamp_modified
        if remote:
            if remote.timestamp_created:
                model_file.remote_created_timestamp = remote.timestamp_created
            if remote.timestamp_modified:
                model_file.remote_modified_timestamp = remote.timestamp_modified

    def _build_children(self,
                        root_model_file: ModelFile,
                        remote: Optional[SystemFile],
                        local: Optional[SystemFile],
                        status: Optional[LftpJobStatus]) -> None:
        """
        Build child ModelFiles using BFS traversal.

        Traverses the remote and local SystemFile trees, creating corresponding
        ModelFiles and determining their states.

        Args:
            root_model_file: The root ModelFile to add children to
            remote: Remote SystemFile (may have children)
            local: Local SystemFile (may have children)
            status: LFTP status for transfer state lookup
        """
        # Frontier contains (remote, local, status, parent_model_file) tuples
        frontier = collections.deque([(remote, local, status, root_model_file)])

        while frontier:
            parent_remote, parent_local, parent_status, parent_model_file = frontier.popleft()

            remote_children = {sf.name: sf for sf in parent_remote.children} if parent_remote else {}
            local_children = {sf.name: sf for sf in parent_local.children} if parent_local else {}
            all_children_names = set().union(remote_children.keys(), local_children.keys())

            for child_name in all_children_names:
                remote_child = remote_children.get(child_name, None)
                local_child = local_children.get(child_name, None)

                child_model_file = self._build_child_file(
                    child_name, remote_child, local_child, parent_status, root_model_file, parent_model_file
                )

                # Add to frontier for further traversal
                frontier.append((remote_child, local_child, parent_status, child_model_file))

    def _build_child_file(self,
                          child_name: str,
                          remote_child: Optional[SystemFile],
                          local_child: Optional[SystemFile],
                          status: Optional[LftpJobStatus],
                          root_model_file: ModelFile,
                          parent_model_file: ModelFile) -> ModelFile:
        """
        Build a single child ModelFile.

        Args:
            child_name: Name of the child file
            remote_child: Remote SystemFile for this child
            local_child: Local SystemFile for this child
            status: LFTP status for transfer state lookup
            root_model_file: The root file (for state checking)
            parent_model_file: The immediate parent to add this child to

        Returns:
            The created child ModelFile
        """
        is_dir = remote_child.is_dir if remote_child else local_child.is_dir

        # Validate is_dir consistency
        if (remote_child and is_dir != remote_child.is_dir) or \
           (local_child and is_dir != local_child.is_dir):
            raise ModelError("Mismatch in is_dir between child sources")

        child_model_file = ModelFile(child_name, is_dir)
        parent_model_file.add_child(child_model_file)

        # Find transfer state for this child
        child_transfer_state = self._find_child_transfer_state(child_model_file, status)

        # Determine child state
        child_model_file.state = self._determine_child_state(
            is_dir, remote_child, local_child, child_transfer_state, root_model_file
        )

        # Fill remaining attributes
        self._fill_model_file(child_model_file, remote_child, local_child, child_transfer_state)

        return child_model_file

    def _find_child_transfer_state(self,
                                    child_model_file: ModelFile,
                                    status: Optional[LftpJobStatus]
                                    ) -> Optional[LftpJobStatus.TransferState]:
        """
        Find the transfer state for a child file from LFTP status.

        Transfer states use full paths without the root component.
        """
        if not status:
            return None

        # Build path without root component
        path_parts = child_model_file.full_path.split(os.sep)
        child_status_path = os.path.join(*path_parts[1:])

        for name, transfer_state in status.get_active_file_transfer_states():
            if name == child_status_path:
                return transfer_state

        return None

    def _determine_child_state(self,
                                is_dir: bool,
                                remote_child: Optional[SystemFile],
                                local_child: Optional[SystemFile],
                                transfer_state: Optional[LftpJobStatus.TransferState],
                                root_model_file: ModelFile) -> ModelFile.State:
        """
        Determine the state for a child file.

        State priority (first match wins):
        1. Directory -> DEFAULT
        2. Has active transfer -> DOWNLOADING
        3. Local size >= remote size -> DOWNLOADED
        4. Remote exists and root is QUEUED/DOWNLOADING -> QUEUED
        5. Otherwise -> DEFAULT
        """
        if is_dir:
            return ModelFile.State.DEFAULT
        elif transfer_state:
            return ModelFile.State.DOWNLOADING
        elif remote_child and local_child and local_child.size >= remote_child.size:
            return ModelFile.State.DOWNLOADED
        elif remote_child and root_model_file.state in (ModelFile.State.QUEUED, ModelFile.State.DOWNLOADING):
            return ModelFile.State.QUEUED
        else:
            return ModelFile.State.DEFAULT

    def _estimate_root_eta(self, model_file: ModelFile) -> None:
        """
        Estimate ETA for a downloading root file if not already available.

        Uses first-order estimate: remaining_size / downloading_speed
        """
        if model_file.state != ModelFile.State.DOWNLOADING:
            return
        if model_file.eta is not None:
            return
        if model_file.downloading_speed is None or model_file.downloading_speed <= 0:
            return
        if model_file.transferred_size is None:
            return
        if model_file.remote_size is None:
            return

        remaining_size = max(model_file.remote_size - model_file.transferred_size, 0)
        model_file.eta = int(math.ceil(remaining_size / model_file.downloading_speed))

    def _determine_final_state(self, model_file: ModelFile) -> None:
        """
        Determine the final state for a root file.

        Checks in order: Downloaded, Deleted, Extracting, Extracted.
        Each check only applies if the file is in an appropriate initial state.
        """
        self._check_downloaded_state(model_file)
        self._check_deleted_state(model_file)
        self._check_extracting_state(model_file)
        self._check_extracted_state(model_file)

    def _check_downloaded_state(self, model_file: ModelFile) -> None:
        """
        Check if a DEFAULT file should be marked as DOWNLOADED.

        A file is DOWNLOADED if:
        - Single file with local_size >= remote_size, OR
        - Directory where all remote children are DOWNLOADED
        """
        if model_file.state != ModelFile.State.DEFAULT:
            return

        if not model_file.is_dir:
            # Single file check
            if (model_file.local_size is not None and
                    model_file.remote_size is not None and
                    model_file.local_size >= model_file.remote_size):
                model_file.state = ModelFile.State.DOWNLOADED
        elif model_file.remote_size is not None:
            # Directory check - all remote children must be downloaded
            if self._are_all_children_downloaded(model_file):
                model_file.state = ModelFile.State.DOWNLOADED

    def _are_all_children_downloaded(self, model_file: ModelFile) -> bool:
        """
        Check if all remote children of a directory are downloaded.

        Uses BFS traversal to check all descendants.
        Returns False if there are no downloadable (remote) children — a directory
        with no remote files should not be marked DOWNLOADED.
        """
        frontier = collections.deque(model_file.get_children())
        has_downloadable_children = False

        while frontier:
            child_file = frontier.popleft()
            # Only check non-directory files that exist remotely
            if not child_file.is_dir and child_file.remote_size is not None:
                has_downloadable_children = True
                if child_file.state != ModelFile.State.DOWNLOADED:
                    return False
            frontier.extend(child_file.get_children())

        return has_downloadable_children

    def _check_deleted_state(self, model_file: ModelFile) -> None:
        """
        Check if a DEFAULT file should be marked as DELETED.

        A file is DELETED if it doesn't exist locally but was downloaded before.
        Also refreshes the file's position in the LRU tracker to prevent premature eviction.
        """
        if model_file.state != ModelFile.State.DEFAULT:
            return
        if model_file.local_size is not None:
            return
        if self.__downloaded_files is None:
            return
        if model_file.name not in self.__downloaded_files:
            return

        # Refresh position in LRU tracker to prevent eviction of actively monitored files
        self.__downloaded_files.touch(model_file.name)
        model_file.state = ModelFile.State.DELETED

    def _check_extracting_state(self, model_file: ModelFile) -> None:
        """
        Check if a file should be marked as EXTRACTING.

        A file is EXTRACTING if:
        - It has an extract status
        - It's in DEFAULT or DOWNLOADED state
        - It exists locally
        """
        if model_file.name not in self.__extract_statuses:
            return

        extract_status = self.__extract_statuses[model_file.name]

        if model_file.is_dir != extract_status.is_dir:
            raise ModelError("Mismatch in is_dir between file and extract status")

        if model_file.state in (ModelFile.State.DEFAULT, ModelFile.State.DOWNLOADED) \
                and model_file.local_size is not None:
            model_file.state = ModelFile.State.EXTRACTING
        else:
            # Log warning for unexpected states
            if model_file.local_size is None:
                self.logger.warning(
                    "File {} has extract status but doesn't exist locally!".format(model_file.name)
                )
            else:
                self.logger.warning(
                    "File {} has extract status but is in state {}".format(
                        model_file.name, str(model_file.state)
                    )
                )

    def _check_extracted_state(self, model_file: ModelFile) -> None:
        """
        Check if a DOWNLOADED file should be marked as EXTRACTED.

        Only DOWNLOADED files can be marked as EXTRACTED.
        DEFAULT files remain DEFAULT even if previously extracted.
        """
        if model_file.name not in self.__extracted_files:
            return
        if model_file.state != ModelFile.State.DOWNLOADED:
            return

        model_file.state = ModelFile.State.EXTRACTED
