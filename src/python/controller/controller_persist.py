# Copyright 2017, Inderpreet Singh, All rights reserved.

import json
import logging
from typing import Optional

from common import overrides, Constants, Persist, PersistError, BoundedOrderedSet


class ControllerPersist(Persist):
    """
    Persisting state for controller.

    Uses BoundedOrderedSet for downloaded and extracted file name tracking
    to prevent unbounded memory growth. Oldest entries are evicted when
    the configured limit is reached.
    """

    # Keys
    __KEY_DOWNLOADED_FILE_NAMES = "downloaded"
    __KEY_EXTRACTED_FILE_NAMES = "extracted"
    __KEY_STOPPED_FILE_NAMES = "stopped"
    __KEY_IMPORTED_FILE_NAMES = "imported"

    # Default maximum tracked files (shared between downloaded and extracted)
    DEFAULT_MAX_TRACKED_FILES = 10000

    def __init__(self, max_tracked_files: Optional[int] = None):
        """
        Initialize controller persist state.

        :param max_tracked_files: Maximum files to track in each collection.
                                  If None, uses DEFAULT_MAX_TRACKED_FILES.
        """
        self._max_tracked_files = max_tracked_files or self.DEFAULT_MAX_TRACKED_FILES
        self._logger = logging.getLogger("ControllerPersist")
        self.downloaded_file_names: BoundedOrderedSet[str] = BoundedOrderedSet(
            maxlen=self._max_tracked_files
        )
        self.extracted_file_names: BoundedOrderedSet[str] = BoundedOrderedSet(
            maxlen=self._max_tracked_files
        )
        # Track files that were explicitly stopped by user - these should not
        # be auto-queued on restart even if they have no local content
        self.stopped_file_names: BoundedOrderedSet[str] = BoundedOrderedSet(
            maxlen=self._max_tracked_files
        )
        # Track files that Sonarr has imported - used for import detection
        # and preventing duplicate processing
        self.imported_file_names: BoundedOrderedSet[str] = BoundedOrderedSet(
            maxlen=self._max_tracked_files
        )

    def set_base_logger(self, base_logger: logging.Logger):
        """Set the base logger for this persist instance."""
        self._logger = base_logger.getChild("ControllerPersist")

    @property
    def max_tracked_files(self) -> int:
        """Maximum files tracked in each collection."""
        return self._max_tracked_files

    def get_eviction_stats(self) -> dict:
        """
        Get eviction statistics for monitoring.

        :return: Dict with eviction counts for each collection
        """
        return {
            'downloaded_evictions': self.downloaded_file_names.total_evictions,
            'extracted_evictions': self.extracted_file_names.total_evictions,
            'stopped_evictions': self.stopped_file_names.total_evictions,
            'imported_evictions': self.imported_file_names.total_evictions,
            'max_tracked_files': self._max_tracked_files
        }

    @classmethod
    @overrides(Persist)
    def from_str(cls: "ControllerPersist", content: str,
                 max_tracked_files: Optional[int] = None) -> "ControllerPersist":
        """
        Create ControllerPersist from serialized string.

        If the stored data exceeds max_tracked_files, the oldest entries
        (first in the list) are evicted to fit within the limit.

        :param content: JSON string with downloaded, extracted, and stopped lists
        :param max_tracked_files: Maximum files to track (uses default if None)
        :return: ControllerPersist instance
        """
        persist = ControllerPersist(max_tracked_files=max_tracked_files)
        try:
            dct = json.loads(content)
            downloaded_list = dct[ControllerPersist.__KEY_DOWNLOADED_FILE_NAMES]
            extracted_list = dct[ControllerPersist.__KEY_EXTRACTED_FILE_NAMES]
            # stopped_list is optional for backwards compatibility with old persist files
            stopped_list = dct.get(ControllerPersist.__KEY_STOPPED_FILE_NAMES, [])

            # Add items in order - if we exceed maxlen, oldest items are evicted
            for name in downloaded_list:
                evicted = persist.downloaded_file_names.add(name)
                if evicted:
                    persist._logger.debug(
                        "Evicted '{}' from downloaded files during load (limit: {})".format(
                            evicted, persist._max_tracked_files
                        )
                    )

            for name in extracted_list:
                evicted = persist.extracted_file_names.add(name)
                if evicted:
                    persist._logger.debug(
                        "Evicted '{}' from extracted files during load (limit: {})".format(
                            evicted, persist._max_tracked_files
                        )
                    )

            for name in stopped_list:
                evicted = persist.stopped_file_names.add(name)
                if evicted:
                    persist._logger.debug(
                        "Evicted '{}' from stopped files during load (limit: {})".format(
                            evicted, persist._max_tracked_files
                        )
                    )

            # imported_list is optional for backwards compatibility with old persist files
            imported_list = dct.get(ControllerPersist.__KEY_IMPORTED_FILE_NAMES, [])
            for name in imported_list:
                evicted = persist.imported_file_names.add(name)
                if evicted:
                    persist._logger.debug(
                        "Evicted '{}' from imported files during load (limit: {})".format(
                            evicted, persist._max_tracked_files
                        )
                    )

            return persist
        except (json.decoder.JSONDecodeError, KeyError) as e:
            raise PersistError("Error parsing ControllerPersist - {}: {}".format(
                type(e).__name__, str(e))
            )

    @overrides(Persist)
    def to_str(self) -> str:
        """
        Serialize to JSON string.

        Items are stored in insertion order (oldest first).
        """
        dct = dict()
        dct[ControllerPersist.__KEY_DOWNLOADED_FILE_NAMES] = self.downloaded_file_names.as_list()
        dct[ControllerPersist.__KEY_EXTRACTED_FILE_NAMES] = self.extracted_file_names.as_list()
        dct[ControllerPersist.__KEY_STOPPED_FILE_NAMES] = self.stopped_file_names.as_list()
        dct[ControllerPersist.__KEY_IMPORTED_FILE_NAMES] = self.imported_file_names.as_list()
        return json.dumps(dct, indent=Constants.JSON_PRETTY_PRINT_INDENT)

    @classmethod
    def from_file_with_limit(cls, file_path: str,
                             max_tracked_files: Optional[int] = None) -> "ControllerPersist":
        """
        Load ControllerPersist from file with a specified limit.

        :param file_path: Path to the persist file
        :param max_tracked_files: Maximum files to track (uses default if None)
        :return: ControllerPersist instance
        """
        import os
        if not os.path.isfile(file_path):
            return cls(max_tracked_files=max_tracked_files)
        with open(file_path, "r") as f:
            return cls.from_str(f.read(), max_tracked_files=max_tracked_files)
