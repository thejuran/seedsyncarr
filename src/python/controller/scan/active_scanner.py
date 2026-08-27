import logging
from typing import Dict, List, Optional, Tuple
import multiprocessing
import queue

from .scanner_process import IScanner
from common import overrides, Constants
from system import SystemScanner, SystemScannerError, SystemFile

class ActiveScanner(IScanner):
    """
    Scanner implementation to scan the active files only
    A caller sets the names of the active files that need to be scanned.
    A multiprocessing.Queue is used to store the names because the set and scan
    methods are called by different processes.
    """
    def __init__(self, local_path: str, use_temp_file: bool = False):
        self.__scanner = SystemScanner(local_path)
        if use_temp_file:
            # Resolve '<name>.lftp' to '<name>' like the local scanner does.
            # Without this, every temp-file download misses its final name on
            # every scan and warns at 1 Hz for the whole transfer (incident
            # 2026-08-22: ~172k 'Path does not exist' lines/day).
            self.__scanner.set_lftp_temp_suffix(Constants.LFTP_TEMP_FILE_SUFFIX)
        self.__active_files_queue = multiprocessing.Queue()
        self.__active_files = []  # latest state
        # Consecutive scan misses per active file name. First miss warns,
        # further misses log at debug so a transiently- or never-resolvable
        # entry cannot spam the log once per scan interval.
        self.__miss_counts: Dict[str, int] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @overrides(IScanner)
    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild(self.__class__.__name__)

    def set_active_files(self, file_names: List[str]):
        """
        Set the list of active file names. Only these files will be scanned.
        """
        self.__active_files_queue.put(file_names)

    @overrides(IScanner)
    def scan(self) -> Tuple[List[SystemFile], Optional[int], Optional[int]]:
        # Grab the latest list of active files, if any
        try:
            while True:
                self.__active_files = self.__active_files_queue.get(block=False)
        except queue.Empty:
            pass

        # Drop miss counters for names no longer active so the backoff state
        # cannot grow unbounded and a re-activated name warns afresh
        active_set = set(self.__active_files)
        for name in list(self.__miss_counts.keys()):
            if name not in active_set:
                del self.__miss_counts[name]

        # Do the scan
        result = []
        for file_name in self.__active_files:
            try:
                result.append(self.__scanner.scan_single(file_name))
                self.__miss_counts.pop(file_name, None)
            except SystemScannerError as ex:
                # File may have been deleted, or (with temp files) not exist
                # under its final name yet. Warn once per name, then back off
                # to debug until it resolves or leaves the active list.
                misses = self.__miss_counts.get(file_name, 0)
                if misses == 0:
                    self.logger.warning(str(ex))
                else:
                    self.logger.debug(str(ex))
                self.__miss_counts[file_name] = misses + 1
        # Capacity is irrelevant for the active scanner; return None per IScanner contract.
        return result, None, None
