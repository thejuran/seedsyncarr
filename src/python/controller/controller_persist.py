import collections
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
    __KEY_IMPORTED_CHILDREN = "imported_children"

    # Default maximum tracked files (shared between downloaded and extracted)
    DEFAULT_MAX_TRACKED_FILES = 10000

    # Default maximum children tracked per root (per-pack cap, separate from global
    # max_tracked_files which caps the number of root keys). Per-root eviction
    # prevents one noisy multi-season release from evicting another pack's
    # still-needed entries.
    DEFAULT_MAX_CHILDREN_PER_ROOT = 500

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
        # Per-child import tracking: keys are root model file names, values are
        # BoundedOrderedSet of imported child basenames. Two bounds apply:
        #   - Per-root set maxlen = DEFAULT_MAX_CHILDREN_PER_ROOT (500 children)
        #   - Global root-key cap = self._max_tracked_files (10000 roots)
        # See phase 75 (GH #19) D-01, D-02.
        self.imported_children: "collections.OrderedDict[str, BoundedOrderedSet[str]]" = collections.OrderedDict()

    def add_imported_child(self, root: str, child: str) -> None:
        """
        Record that a specific child basename has been imported for a given root.

        Creates the per-root BoundedOrderedSet on first touch. Enforces two bounds:
        per-root maxlen (DEFAULT_MAX_CHILDREN_PER_ROOT) and a global cap on the
        number of tracked roots (self._max_tracked_files, evicting the oldest
        root via OrderedDict.popitem(last=False)).

        Eviction events are logged at debug level, matching the style of
        from_str's per-collection eviction logs (see imported_file_names loader).

        :param root: Root model file name (dict key).
        :param child: Child basename to record.
        """
        if root not in self.imported_children:
            # Enforce global root-key cap BEFORE inserting the new root
            if len(self.imported_children) >= self._max_tracked_files:
                evicted_root, _ = self.imported_children.popitem(last=False)
                self._logger.debug(
                    "Evicted imported_children root '{}' (limit: {})".format(
                        evicted_root, self._max_tracked_files
                    )
                )
            self.imported_children[root] = BoundedOrderedSet(
                maxlen=self.DEFAULT_MAX_CHILDREN_PER_ROOT
            )
        evicted_child = self.imported_children[root].add(child)
        if evicted_child:
            self._logger.debug(
                "Evicted child '{}' from imported_children['{}'] (per-root limit: {})".format(
                    evicted_child, root, self.DEFAULT_MAX_CHILDREN_PER_ROOT
                )
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
            'imported_children_evictions': sum(
                bset.total_evictions for bset in self.imported_children.values()
            ),
            'imported_children_root_count': len(self.imported_children),
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

            # imported_children is optional for backwards compatibility with old persist files
            imported_children_dct = dct.get(ControllerPersist.__KEY_IMPORTED_CHILDREN, {})
            if not isinstance(imported_children_dct, dict):
                raise PersistError(
                    "Error parsing ControllerPersist: 'imported_children' must be a dict, "
                    "got {}".format(type(imported_children_dct).__name__)
                )
            for root_name, child_list in imported_children_dct.items():
                if not isinstance(root_name, str):
                    raise PersistError(
                        "Error parsing ControllerPersist: imported_children keys must be strings"
                    )
                if not isinstance(child_list, list):
                    raise PersistError(
                        "Error parsing ControllerPersist: imported_children['{}'] must be a list, "
                        "got {}".format(root_name, type(child_list).__name__)
                    )
                for child_name in child_list:
                    if not isinstance(child_name, str):
                        # Skip non-string entries silently -- tolerant of schema drift
                        continue
                    persist.add_imported_child(root_name, child_name)

            return persist
        except (json.decoder.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
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
        dct[ControllerPersist.__KEY_IMPORTED_CHILDREN] = {
            root: bset.as_list() for root, bset in self.imported_children.items()
        }
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
