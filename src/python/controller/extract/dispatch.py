import collections
from enum import Enum
from typing import List
import queue
import logging
import os
import shutil
import threading
import time
from abc import ABC, abstractmethod
import re

from .extract import Extract, ExtractError
from model import ModelFile
from common import AppError, Constants

class ExtractDispatchError(AppError):
    pass

class ExtractListener(ABC):
    @abstractmethod
    def extract_completed(self, name: str, is_dir: bool):
        pass

    @abstractmethod
    def extract_failed(self, name: str, is_dir: bool):
        pass

class ExtractStatus:
    """
    Represents the status of a single extraction request
    """

    class State(Enum):
        EXTRACTING = 0

    def __init__(self, name: str, is_dir: bool, state: State):
        self.__name = name
        self.__is_dir = is_dir
        self.__state = state

    @property
    def name(self) -> str: return self.__name

    @property
    def is_dir(self) -> bool: return self.__is_dir

    @property
    def state(self) -> State: return self.__state

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class ExtractDispatch:
    """
    Queues extraction tasks and runs them one at a time on a worker thread.

    Output is never written straight into the release folder. Each archive is
    unpacked into a staging directory on the same filesystem,
    <out_dir_path>/.seedsyncarr-extracting/<root>/<relative dir>/, and only
    after patool returns successfully is the output moved into its final
    directory with os.rename (atomic on one filesystem). Sonarr/Radarr
    completed-download handling scans the release folder, so it can only ever
    see complete files (incident 2026-09-16: a 6 GB partial of a 38.5 GB mkv
    was imported ~90 s into a 12-minute in-place unrar). A task stays in the
    queue -- and the root stays EXTRACTING -- until every archive of the task
    has been extracted AND moved.
    """

    __WORKER_SLEEP_INTERVAL_IN_SECS = 0.5

    class _Task:
        def __init__(self, root_name: str, root_is_dir: bool):
            self.root_name = root_name
            self.root_is_dir = root_is_dir
            self.archive_paths = []  # list of (archive path, out path, staging path) triples

        def add_archive(self, archive_path: str, out_dir_path: str, staging_dir_path: str):
            self.archive_paths.append((archive_path, out_dir_path, staging_dir_path))

    def __init__(self, out_dir_path: str, local_path: str):
        self.__out_dir_path = out_dir_path
        self.__local_path = local_path
        self.__staging_root_path = os.path.join(out_dir_path, Constants.EXTRACT_STAGING_DIR_NAME)

        self.__task_queue = queue.Queue()
        self.__worker = threading.Thread(name="ExtractWorker",
                                         target=self.__worker)
        self.__worker_shutdown = threading.Event()

        self.__listeners = []
        self.__listeners_lock = threading.Lock()

        self.logger = logging.getLogger(self.__class__.__name__)

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild(self.__class__.__name__)

    def start(self):
        self.__remove_stale_staging()
        self.__worker.start()

    def stop(self):
        self.__worker_shutdown.set()
        self.__worker.join()

    def add_listener(self, listener: ExtractListener):
        with self.__listeners_lock:
            self.__listeners.append(listener)

    def status(self) -> List[ExtractStatus]:
        with self.__task_queue.mutex:
            tasks = list(self.__task_queue.queue)
        statuses = []
        for task in tasks:
            status = ExtractStatus(name=task.root_name,
                                   is_dir=task.root_is_dir,
                                   state=ExtractStatus.State.EXTRACTING)
            statuses.append(status)
        return statuses

    def extract(self, model_file: ModelFile):
        self.logger.debug("Received extract for {}".format(model_file.name))

        # Build the task BEFORE acquiring mutex (no shared state access needed)
        task = ExtractDispatch._Task(model_file.name, model_file.is_dir)

        if model_file.is_dir:
            # For a directory, try and find all archives
            # Loop through all directories using BFS
            frontier = collections.deque([model_file])
            while frontier:
                curr_file = frontier.popleft()
                if curr_file.is_dir:
                    frontier += curr_file.get_children()
                else:
                    archive_full_path = os.path.join(self.__local_path, curr_file.full_path)
                    # Relative dir starts with the root name, so the staging
                    # tree for the task lives under <staging root>/<root name>/
                    relative_dir = os.path.dirname(curr_file.full_path)
                    out_dir_path = os.path.join(self.__out_dir_path, relative_dir)
                    staging_dir_path = os.path.join(self.__staging_root_path, relative_dir)
                    if curr_file.local_size is not None \
                            and curr_file.local_size > 0 \
                            and Extract.is_archive(archive_full_path):
                        task.add_archive(archive_path=archive_full_path,
                                         out_dir_path=out_dir_path,
                                         staging_dir_path=staging_dir_path)

            # Coalesce extractions
            ExtractDispatch.__coalesce_extractions(task)

            # Verify that there was at least one archive file (before acquiring mutex)
            if len(task.archive_paths) == 0:
                raise ExtractDispatchError(
                    "Directory does not contain any archives: {}".format(model_file.name)
                )
        else:
            # For a single file, it must exist locally and must be an archive
            if model_file.local_size in (None, 0):
                raise ExtractDispatchError("File does not exist locally: {}".format(model_file.name))
            archive_full_path = os.path.join(self.__local_path, model_file.name)
            if not Extract.is_archive(archive_full_path):
                raise ExtractDispatchError("File is not an archive: {}".format(model_file.name))
            task.add_archive(archive_path=archive_full_path,
                             out_dir_path=self.__out_dir_path,
                             staging_dir_path=os.path.join(self.__staging_root_path, model_file.name))

        # Atomic: duplicate check + insertion under one mutex acquisition.
        # Use queue.append + not_empty.notify instead of queue.put() to avoid
        # deadlock (put() would try to re-acquire the mutex we already hold).
        with self.__task_queue.mutex:
            for queued_task in self.__task_queue.queue:
                if queued_task.root_name == model_file.name:
                    self.logger.info("Ignoring extract for {}, already exists".format(model_file.name))
                    return
            self.__task_queue.queue.append(task)
            self.__task_queue.not_empty.notify()

    def __worker(self):
        self.logger.debug("Started worker thread")

        while not self.__worker_shutdown.is_set():
            # Copy queue snapshot under mutex to check for work
            with self.__task_queue.mutex:
                has_tasks = len(self.__task_queue.queue) > 0

            while has_tasks and not self.__worker_shutdown.is_set():
                # Peek at first task under mutex
                with self.__task_queue.mutex:
                    if len(self.__task_queue.queue) == 0:
                        break
                    task = self.__task_queue.queue[0]

                # We have a task, extract archives one by one
                completed = True

                try:
                    for archive_path, out_dir_path, staging_dir_path in task.archive_paths:
                        if self.__worker_shutdown.is_set():
                            # exit early
                            self.logger.warning("Extraction failed, shutdown requested")
                            completed = False
                            break

                        self.logger.debug("Extracting {} into staging dir {}".format(
                            archive_path, staging_dir_path
                        ))
                        try:
                            Extract.extract_archive(
                                archive_path=archive_path,
                                out_dir_path=staging_dir_path
                            )
                        except ExtractError:
                            # Leave nothing behind: the final out dir was never
                            # touched, so only the staging output needs removing
                            self.__discard_staged_output(archive_path, staging_dir_path)
                            raise
                        self.__publish_staged_output(archive_path, staging_dir_path, out_dir_path)

                except ExtractError:
                    self.logger.exception("Caught an extraction error")
                    completed = False
                finally:
                    # Drop the task's (now empty) staging tree BEFORE popping so
                    # the root stays EXTRACTING until nothing is left in staging.
                    self.__remove_task_staging(task)
                    # Pop the task (thread-safe Queue.get).
                    # Guard against queue.Empty in case of a race between peek and get.
                    try:
                        self.__task_queue.get(block=False)
                    except queue.Empty:
                        pass

                # Send notification to listeners (copy-under-lock)
                with self.__listeners_lock:
                    listeners_snapshot = list(self.__listeners)
                for listener in listeners_snapshot:
                    if completed:
                        listener.extract_completed(task.root_name, task.root_is_dir)
                    else:
                        listener.extract_failed(task.root_name, task.root_is_dir)

                # Re-check queue under mutex for next iteration
                with self.__task_queue.mutex:
                    has_tasks = len(self.__task_queue.queue) > 0

            time.sleep(ExtractDispatch.__WORKER_SLEEP_INTERVAL_IN_SECS)

        self.logger.debug("Stopped worker thread")

    def __publish_staged_output(self, archive_path: str, staging_dir_path: str, out_dir_path: str):
        """
        Move everything patool wrote under staging_dir_path into out_dir_path.

        Each top-level entry is moved with a single os.rename (atomic on one
        filesystem, so a whole extracted directory appears at once). An entry
        whose target already exists is replaced -- the newly extracted copy is
        authoritative -- and an extracted directory whose target directory
        already exists is merged into it, file by file. Raises ExtractError if
        the move fails so the task is reported as failed.
        """
        if not os.path.isdir(staging_dir_path):
            # Archive produced no output; nothing to publish
            return
        try:
            self.__strip_symlinks(staging_dir_path)
            self.__move_tree(staging_dir_path, out_dir_path)
            shutil.rmtree(staging_dir_path)
        except OSError as e:
            # Whatever is still staged never reached out_dir_path and is about
            # to be removed by the task cleanup; say what it was (it can be
            # regenerated from the archive)
            self.__warn_unpublished_output(archive_path, staging_dir_path, out_dir_path)
            raise ExtractError("Failed to move extracted output of {} into {}: {}".format(
                archive_path, out_dir_path, str(e)
            ))
        self.logger.debug("Moved extracted output of {} into {}".format(archive_path, out_dir_path))

    def __strip_symlinks(self, staging_dir_path: str):
        """
        Remove every symlink from the staged output before it is published.

        An archive can carry a symlink pointing anywhere on the filesystem;
        publishing it would expose that target inside the arr-visible release
        folder. Symlinks are never part of a media release, so each one is
        dropped with a warning naming its target.
        """
        for dirpath, dirnames, filenames in os.walk(staging_dir_path):
            for name in dirnames + filenames:
                path = os.path.join(dirpath, name)
                if os.path.islink(path):
                    self.logger.warning(
                        "Skipping symlink '{}' -> '{}' in extracted output; "
                        "symlinks are never published into the release folder".format(
                            path, os.readlink(path)
                        )
                    )
                    os.remove(path)
            # Do not descend into (now removed) symlinked directories
            dirnames[:] = [d for d in dirnames if os.path.isdir(os.path.join(dirpath, d))]

    def __move_tree(self, src_dir: str, dst_dir: str):
        os.makedirs(dst_dir, exist_ok=True)
        for entry in list(os.scandir(src_dir)):
            src = entry.path
            dst = os.path.join(dst_dir, entry.name)
            if entry.is_dir(follow_symlinks=False) \
                    and os.path.isdir(dst) and not os.path.islink(dst):
                # Both are real directories: merge, then drop the emptied staging dir
                self.__move_tree(src, dst)
                os.rmdir(src)
            elif os.path.lexists(dst):
                self.logger.warning(
                    "Replacing existing '{}' with the newly extracted copy".format(dst)
                )
                if os.path.isdir(dst) and not os.path.islink(dst):
                    # Type mismatch (extracted file over an existing directory);
                    # os.replace cannot overwrite a directory with a file
                    shutil.rmtree(dst)
                elif entry.is_dir(follow_symlinks=False):
                    # Type mismatch (extracted directory over an existing file
                    # or symlink); os.replace cannot overwrite a non-directory
                    # with a directory
                    os.remove(dst)
                os.replace(src, dst)
            else:
                os.rename(src, dst)

    def __warn_unpublished_output(self, archive_path: str, staging_dir_path: str, out_dir_path: str):
        """
        A move into out_dir_path failed partway. Log what is still in the
        staging dir -- it never reached the release folder and will be
        discarded by __remove_task_staging. Never raises: this runs inside an
        OSError handler and must not mask the original failure.
        """
        if not os.path.isdir(staging_dir_path):
            return
        try:
            file_count, entries = ExtractDispatch.__list_staged_output(staging_dir_path)
        except OSError:
            self.logger.exception("Failed to list staging dir {}".format(staging_dir_path))
            return
        self.logger.warning(
            "Discarding unpublished extraction output of {}: {} file(s) {} in staging dir {} "
            "never reached {} and will be removed".format(
                archive_path, file_count, entries, staging_dir_path, out_dir_path
            )
        )

    def __discard_staged_output(self, archive_path: str, staging_dir_path: str):
        """
        Remove whatever a failed extraction left in its staging dir, logging what was removed
        """
        if not os.path.isdir(staging_dir_path):
            return
        file_count, entries = ExtractDispatch.__list_staged_output(staging_dir_path)
        try:
            shutil.rmtree(staging_dir_path)
        except OSError:
            self.logger.exception("Failed to remove staging dir {}".format(staging_dir_path))
            return
        self.logger.warning(
            "Discarded partial extraction output of {}: removed {} file(s) {} from staging dir {}".format(
                archive_path, file_count, entries, staging_dir_path
            )
        )

    @staticmethod
    def __list_staged_output(staging_dir_path: str):
        """
        (file count, sorted top-level entry names) of what is under staging_dir_path
        """
        entries = sorted(entry.name for entry in os.scandir(staging_dir_path))
        file_count = sum(len(files) for _, _, files in os.walk(staging_dir_path))
        return file_count, entries

    def __remove_task_staging(self, task: "_Task"):
        """
        Remove the task's staging tree (<staging root>/<root name>) and the
        staging root itself once it is empty. Called after every task, whether
        it completed or failed; anything still in there is partial by definition.
        """
        task_staging_path = os.path.join(self.__staging_root_path, task.root_name)
        try:
            if os.path.isdir(task_staging_path):
                shutil.rmtree(task_staging_path)
            if os.path.isdir(self.__staging_root_path) and not os.listdir(self.__staging_root_path):
                os.rmdir(self.__staging_root_path)
        except OSError:
            self.logger.exception("Failed to clean up staging dir {}".format(task_staging_path))

    def __remove_stale_staging(self):
        """
        Startup hygiene: a staging root that survived a restart means an
        extraction was interrupted mid-write. Its contents are partial by
        definition and the archives are still in place, so delete it.
        """
        if not os.path.isdir(self.__staging_root_path):
            return
        self.logger.warning(
            "Removing stale extraction staging dir {} left by an interrupted extraction; "
            "its contents are partial and the archives remain in place to be re-extracted".format(
                self.__staging_root_path
            )
        )
        try:
            shutil.rmtree(self.__staging_root_path)
        except OSError:
            self.logger.exception("Failed to remove stale staging dir {}".format(self.__staging_root_path))

    @staticmethod
    def __coalesce_extractions(task: _Task):
        """
        Remove duplicate extractions due to split files
        """
        # Filter out any rxx files for a split rar
        filtered_paths = []
        for archive_path, out_path, staging_path in task.archive_paths:
            file_ext = os.path.splitext(os.path.basename(archive_path))[1]
            if not re.match(r"^\.r\d{2,}$", file_ext):
                filtered_paths.append((archive_path, out_path, staging_path))
        task.archive_paths = filtered_paths
