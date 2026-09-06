import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Set, List, Callable, Tuple, Optional
import fnmatch

from common import overrides, Constants, Context, Persist, PersistError, Serializable
from model import IModelListener, ModelFile
from .controller import Controller

class AutoQueuePattern(Serializable):
    # Keys
    __KEY_PATTERN = "pattern"

    def __init__(self, pattern: str):
        self.__pattern = pattern

    @property
    def pattern(self) -> str:
        return self.__pattern

    def __eq__(self, other: "AutoQueuePattern") -> bool:
        return self.__pattern == other.__pattern

    def __hash__(self) -> int:
        return hash(self.__pattern)

    def to_str(self) -> str:
        dct = dict()
        dct[AutoQueuePattern.__KEY_PATTERN] = self.__pattern
        return json.dumps(dct)

    @classmethod
    def from_str(cls, content: str) -> "AutoQueuePattern":
        dct = json.loads(content)
        return AutoQueuePattern(pattern=dct[AutoQueuePattern.__KEY_PATTERN])

class IAutoQueuePersistListener(ABC):
    """Listener for receiving AutoQueuePersist events"""

    @abstractmethod
    def pattern_added(self, pattern: AutoQueuePattern):
        pass

    @abstractmethod
    def pattern_removed(self, pattern: AutoQueuePattern):
        pass

class AutoQueuePersist(Persist):
    """
    Persisting state for auto-queue

    Thread-safety: Listener operations are protected by __listeners_lock.
    The copy-under-lock pattern is used when notifying listeners to prevent
    race conditions with concurrent add/remove operations.
    """

    # Keys
    __KEY_PATTERNS = "patterns"

    def __init__(self):
        self.__patterns = []
        self.__listeners = []
        self.__listeners_lock = threading.Lock()

    @property
    def patterns(self) -> Set[AutoQueuePattern]:
        return set(self.__patterns)

    def add_pattern(self, pattern: AutoQueuePattern):
        # Check values
        if not pattern.pattern.strip():
            raise ValueError("Cannot add blank pattern")

        if pattern not in self.__patterns:
            self.__patterns.append(pattern)
            # Copy-under-lock: copy listeners while holding lock, then iterate outside lock
            with self.__listeners_lock:
                listeners = list(self.__listeners)
            for listener in listeners:
                listener.pattern_added(pattern)

    def remove_pattern(self, pattern: AutoQueuePattern):
        if pattern in self.__patterns:
            self.__patterns.remove(pattern)
            # Copy-under-lock: copy listeners while holding lock, then iterate outside lock
            with self.__listeners_lock:
                listeners = list(self.__listeners)
            for listener in listeners:
                listener.pattern_removed(pattern)

    def add_listener(self, listener: IAutoQueuePersistListener):
        with self.__listeners_lock:
            self.__listeners.append(listener)

    @classmethod
    @overrides(Persist)
    def from_str(cls: "AutoQueuePersist", content: str) -> "AutoQueuePersist":
        persist = AutoQueuePersist()
        try:
            dct = json.loads(content)
            pattern_list = dct[AutoQueuePersist.__KEY_PATTERNS]
            for pattern in pattern_list:
                persist.add_pattern(AutoQueuePattern.from_str(pattern))
            return persist
        except (json.decoder.JSONDecodeError, KeyError) as e:
            raise PersistError("Error parsing AutoQueuePersist - {}: {}".format(
                type(e).__name__, str(e))
            )

    @overrides(Persist)
    def to_str(self) -> str:
        dct = dict()
        dct[AutoQueuePersist.__KEY_PATTERNS] = list(p.to_str() for p in self.__patterns)
        return json.dumps(dct, indent=Constants.JSON_PRETTY_PRINT_INDENT)

class AutoQueueModelListener(IModelListener):
    """Keeps track of added and modified files"""
    def __init__(self):
        self.new_files = []  # list of new files
        self.modified_files = []  # list of pairs (old_file, new_file)

    @overrides(IModelListener)
    def file_added(self, file: ModelFile):
        self.new_files.append(file)

    @overrides(IModelListener)
    def file_updated(self, old_file: ModelFile, new_file: ModelFile):
        self.modified_files.append((old_file, new_file))

    @overrides(IModelListener)
    def file_removed(self, file: ModelFile):
        pass

class AutoQueuePersistListener(IAutoQueuePersistListener):
    """Keeps track of newly added patterns"""
    def __init__(self):
        self.new_patterns = set()

    @overrides(IAutoQueuePersistListener)
    def pattern_added(self, pattern: AutoQueuePattern):
        self.new_patterns.add(pattern)

    @overrides(IAutoQueuePersistListener)
    def pattern_removed(self, pattern: AutoQueuePattern):
        if pattern in self.new_patterns:
            self.new_patterns.remove(pattern)

class AutoQueue:
    """
    Implements auto-queue functionality by sending commands to controller
    as matching files are discovered
    AutoQueue is in the same thread as Controller, so no synchronization is
    needed for now

    Queueing is a level-triggered sweep over the current model, not an
    edge-triggered reaction to model events (postmortem v1.7.0 001-postmortem:
    a partial file whose remote finished growing across a restart or missed
    event window was never re-queued, and in-progress seedbox torrents were
    grabbed at a truncated snapshot size). Every cycle, any DEFAULT file whose
    remote copy is bigger than its local copy (or has no local copy) is a
    queue candidate once its remote size has been stable for
    remote_stability_seconds of the remote-scan clock. Stability is measured
    against latest_remote_scan_time, never wall-clock, so a paused scanner
    cannot fake stability.

    A second, local-side gate guards the sweep against its own input skew
    (incident 2026-09-05, Road to Perdition): lftp job status is polled
    synchronously each cycle while local scan results arrive asynchronously,
    so the first cycle after a transfer completes can pair "no lftp job" with
    a stale scan that still shows the partial temp-file size -- which reads
    exactly like a stranded partial. A file is therefore only a candidate
    once it has been continuously DEFAULT with an unchanged local size for
    local_stability_seconds of the LOCAL scan clock
    (latest_local_scan_time). Leaving DEFAULT restarts that window
    regardless of size history (a sparse pget temp file can sit at an
    unchanged apparent size for minutes), so a completed transfer is always
    re-read by a fresh scan -- as DOWNLOADED -- before the sweep may act.
    """

    # Minimum remote-scan-clock seconds between repeated sweep attempts for the
    # same file, so a file stuck in DEFAULT (e.g. lftp errors) is retried
    # instead of spammed every cycle.
    REQUEUE_COOLDOWN_SECONDS = 300

    def __init__(self,
                 context: Context,
                 persist: AutoQueuePersist,
                 controller: Controller):
        self.logger = context.logger.getChild("AutoQueue")
        self.__context = context
        self.__persist = persist
        self.__controller = controller
        self.__model_listener = AutoQueueModelListener()
        self.__persist_listener = AutoQueuePersistListener()
        self.__enabled = context.config.autoqueue.enabled
        self.__patterns_only = context.config.autoqueue.patterns_only
        self.__auto_extract_enabled = context.config.autoqueue.auto_extract
        # None (unset, e.g. bare Config()) behaves as 0: no stability gating,
        # no cooldown -- the sweep queues eligible files immediately.
        self.__stability_seconds = context.config.autoqueue.remote_stability_seconds or 0
        self.__local_stability_seconds = context.config.autoqueue.local_stability_seconds or 0
        # name -> (remote_size, remote scan time when this size was first seen)
        self.__remote_size_history = {}
        # name -> (local_size, local scan time when the file was first seen
        # DEFAULT at this size); entries exist only while the file is DEFAULT
        self.__local_idle_history = {}
        # name -> remote scan time of the last sweep queue attempt
        self.__last_queue_attempt = {}

        if self.__enabled:
            persist.add_listener(self.__persist_listener)

            initial_model_files = self.__controller.get_model_files_and_add_listener(self.__model_listener)
            # pass the initial model files through to our listener
            for file in initial_model_files:
                self.__model_listener.file_added(file)

            # Print the initial persist state
            self.logger.debug("Auto-Queue Patterns:")
            for pattern in self.__persist.patterns:
                self.logger.debug("    {}".format(pattern.pattern))

    def process(self):
        """
        Advance the auto queue state
        """
        if not self.__enabled:
            return

        # Log new/modified file counts entering process (debug-level: fires every
        # ~0.5s while downloads progress, since in-flight files emit file_updated
        # events on each scan — keep at debug to avoid steady INFO log spam)
        new_count = len(self.__model_listener.new_files)
        modified_count = len(self.__model_listener.modified_files)
        if new_count > 0 or modified_count > 0:
            self.logger.debug(
                "Process cycle: {} new files, {} modified files".format(
                    new_count, modified_count
                )
            )

        ###
        # Queue
        ###
        # Level-triggered sweep over the whole model. A file is a candidate
        # when it is DEFAULT with a remote copy bigger than its local copy (or
        # no local copy at all), and its remote size has been stable for the
        # configured window of the remote-scan clock. This covers new files,
        # remote updates, AND partials stranded by any missed-event window
        # (restart, scanner outage) with one rule -- the same edge-vs-level
        # lesson as ModelPipeline._commit_downloaded_membership.
        model_files = self.__controller.get_model_files()
        # latest_remote_scan_time is a datetime in production
        # (Controller._update_controller_status stores remote_scan.timestamp);
        # tests may inject raw epoch numbers. Fetched regardless of the
        # stability gate because the requeue cooldown below needs the scan
        # clock even when stability gating is disabled.
        scan_time = AutoQueue.__scan_clock(
            self.__context.status.controller.latest_remote_scan_time)
        local_scan_time = AutoQueue.__scan_clock(
            self.__context.status.controller.latest_local_scan_time)
        if self.__stability_seconds > 0 and scan_time is not None:
            self.__update_remote_size_history(model_files, scan_time)
        if self.__local_stability_seconds > 0 and local_scan_time is not None:
            self.__update_local_idle_history(model_files, local_scan_time)

        def sweep_accept(f: ModelFile) -> bool:
            if f.remote_size is None or f.state != ModelFile.State.DEFAULT:
                return False
            if f.local_size is not None and f.local_size >= f.remote_size:
                return False
            if self.__stability_seconds > 0:
                if scan_time is None:
                    # No remote scan yet -- stability cannot be established
                    return False
                entry = self.__remote_size_history.get(f.name)
                if entry is None or scan_time - entry[1] < self.__stability_seconds:
                    return False
            if self.__local_stability_seconds > 0:
                if local_scan_time is None:
                    # No local scan yet -- the local copy has not been read
                    return False
                entry = self.__local_idle_history.get(f.name)
                if entry is None or \
                        local_scan_time - entry[1] < self.__local_stability_seconds:
                    return False
            return True

        sweep_matches = self.__filter_candidates(
            candidates=model_files,
            accept=sweep_accept
        )

        # Filter out files that were explicitly stopped by user, files already
        # downloaded previously (prevents re-queueing files that were
        # moved/deleted by external tools like Sonarr), and files attempted
        # within the cooldown window.
        files_to_queue = []
        for name, pattern in sweep_matches:
            is_stopped = self.__controller.is_file_stopped(name)
            is_downloaded = self.__controller.is_file_downloaded(name)
            self.logger.debug(
                "Filter check '{}': stopped={}, downloaded={}".format(
                    name, is_stopped, is_downloaded
                )
            )
            if is_stopped or is_downloaded:
                continue
            # Cooldown applies whenever a scan clock exists, INDEPENDENT of the
            # stability gate: with the gate disabled the sweep would otherwise
            # re-queue the same DEFAULT file every process cycle until lftp
            # status is observed, stacking duplicate lftp jobs (the incident
            # class the class docstring warns about).
            if scan_time is not None:
                last_attempt = self.__last_queue_attempt.get(name)
                if last_attempt is not None and \
                        scan_time - last_attempt < AutoQueue.REQUEUE_COOLDOWN_SECONDS:
                    continue
                self.__last_queue_attempt[name] = scan_time
            files_to_queue.append((name, pattern))

        ###
        # Extract
        ###
        files_to_extract = []

        if self.__auto_extract_enabled:
            extract_candidate_files = []

            # Candidate all new files
            extract_candidate_files += self.__model_listener.new_files

            # Candidate modified files that just became DOWNLOADED
            # But not files that went EXTRACTING -> DOWNLOADED (failed extraction)
            for old_file, new_file in self.__model_listener.modified_files:
                if old_file.state != ModelFile.State.DOWNLOADED and \
                        old_file.state != ModelFile.State.EXTRACTING and \
                        new_file.state == ModelFile.State.DOWNLOADED:
                    extract_candidate_files.append(new_file)

            files_to_extract = self.__filter_candidates(
                candidates=extract_candidate_files,
                accept=lambda f:
                    f.state == ModelFile.State.DOWNLOADED and
                    f.local_size is not None and
                    f.local_size > 0 and
                    f.is_extractable
            )

        ###
        # Send commands
        ###

        # Send the queue commands
        for filename, pattern in files_to_queue:
            self.logger.info(
                "Auto queueing '{}'".format(filename) +
                (" for pattern '{}'".format(pattern.pattern) if pattern else "")
            )
            command = Controller.Command(
                Controller.Command.Action.QUEUE, filename,
                origin=Controller.Command.Origin.AUTO
            )
            self.__controller.queue_command(command)

        # Send the extract commands
        for filename, pattern in files_to_extract:
            self.logger.info(
                "Auto extracting '{}'".format(filename) +
                (" for pattern '{}'".format(pattern.pattern) if pattern else "")
            )
            command = Controller.Command(Controller.Command.Action.EXTRACT, filename)
            self.__controller.queue_command(command)

        # Clear the processed files
        self.__model_listener.new_files.clear()
        self.__model_listener.modified_files.clear()
        # Clear the new patterns
        self.__persist_listener.new_patterns.clear()

    @staticmethod
    def __scan_clock(scan_time) -> Optional[float]:
        """
        Normalise a controller-status scan timestamp to epoch seconds.
        Production stores datetimes (Controller._update_controller_status
        stores ScannerResult.timestamp); tests may inject raw epoch numbers.
        """
        if scan_time is None:
            return None
        return scan_time.timestamp() \
            if isinstance(scan_time, datetime) else float(scan_time)

    def __update_local_idle_history(self,
                                    model_files: List[ModelFile],
                                    local_scan_time: float) -> None:
        """
        Track, on the local-scan clock, how long each file has been
        continuously DEFAULT at an unchanged local size. Any non-DEFAULT
        sighting drops the entry so the window restarts from the next DEFAULT
        sighting; a local size change re-stamps it. Entries for files gone
        from the model are pruned.
        """
        current_names = set()
        for f in model_files:
            current_names.add(f.name)
            if f.state != ModelFile.State.DEFAULT:
                self.__local_idle_history.pop(f.name, None)
                continue
            entry = self.__local_idle_history.get(f.name)
            if entry is None or entry[0] != f.local_size:
                self.__local_idle_history[f.name] = (f.local_size, local_scan_time)
        for name in list(self.__local_idle_history.keys()):
            if name not in current_names:
                del self.__local_idle_history[name]

    def __update_remote_size_history(self,
                                     model_files: List[ModelFile],
                                     scan_time: float) -> None:
        """
        Track when each file's remote size was last observed to change, on the
        remote-scan clock. A size change (or first sighting) resets the file's
        stability window. Entries for files gone from the model are pruned.
        """
        current_names = set()
        for f in model_files:
            current_names.add(f.name)
            if f.remote_size is None:
                self.__remote_size_history.pop(f.name, None)
                continue
            entry = self.__remote_size_history.get(f.name)
            if entry is None or entry[0] != f.remote_size:
                self.__remote_size_history[f.name] = (f.remote_size, scan_time)
        for name in list(self.__remote_size_history.keys()):
            if name not in current_names:
                del self.__remote_size_history[name]
                self.__last_queue_attempt.pop(name, None)

    def __filter_candidates(self,
                            candidates: List[ModelFile],
                            accept: Callable[[ModelFile], bool]) -> List[Tuple[str, AutoQueuePattern]]:
        """
        Given a list of candidate files, filter out those that match the accept criteria
        Also takes into consideration new patterns that were added
        The accept criteria is applied to candidates AND all existing files in case of
        new patterns
        :return: list of (filename, pattern) pairs
        """
        # Files accepted and matched, filename -> pattern map
        # Filename key prevents a file from being accepted twice
        files_matched = dict()

        # Step 1: run candidates through all the patterns if they are enabled
        #         otherwise accept all files
        for file in candidates:
            if self.__patterns_only:
                for pattern in self.__persist.patterns:
                    if accept(file) and self.__match(pattern, file):
                        files_matched[file.name] = pattern
                        break
            elif accept(file):
                files_matched[file.name] = None

        # Step 2: run new pattern through all the files
        if self.__persist_listener.new_patterns:
            model_files = self.__controller.get_model_files()
            for new_pattern in self.__persist_listener.new_patterns:
                for file in model_files:
                    if accept(file) and self.__match(new_pattern, file):
                        files_matched[file.name] = new_pattern

        return list(files_matched.items())

    @staticmethod
    def __match(pattern: AutoQueuePattern, file: ModelFile) -> bool:
        """
        Returns true is file matches the pattern
        """
        # make the search case insensitive
        pattern = pattern.pattern.lower()
        filename = file.name.lower()
        # 1. pattern match
        # 2. wildcard match
        return pattern in filename or \
            fnmatch.fnmatch(filename, pattern)
