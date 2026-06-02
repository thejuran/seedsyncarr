import collections
import os
from typing import Optional, Set, Tuple

from common import sanitize_log_value
from model import ModelFile


# Video file extensions considered for auto-delete coverage check.
# Comparison is case-insensitive on the extension. Non-allowlisted files
# (.nfo, .srt, .sample.mp4, etc.) are intentionally ignored: Sonarr skips
# these during import, so requiring them would permanently strand real-world
# packs. See phase 75 (GH #19) D-09, D-10.
_VIDEO_EXTENSIONS = frozenset({
    '.mkv', '.mp4', '.avi', '.m4v', '.mov',
    '.ts', '.wmv', '.flv', '.webm',
})

# Safety bound on the auto-delete BFS traversal. Caps pack-guard + coverage
# collection at this many nodes to prevent a pathological pack (BD rip with
# deep nesting, or a user-introduced symlink loop surfaced in the model) from
# monopolizing the timer thread. If exceeded, the auto-delete is skipped with
# a warning log; the next Timer-fire retries.
_AUTO_DELETE_BFS_NODE_LIMIT = 10_000


class AutoDeleteManager:
    """
    BFS pack-guard and coverage-check logic for the auto-delete lifecycle.

    Responsible for:
    - Running BFS traversal over a directory pack to detect unsafe child states
    - Collecting on-disk video basenames for the coverage guard (GH #19 D-08..D-10)
    - Applying the per-child coverage check against persisted imported_children data

    Thread-safety: All methods that access model state expect the caller
    (Controller.__execute_auto_delete) to hold __model_lock for the duration
    of the call. This class does NOT acquire any lock — lock acquisition and
    release is managed entirely by Controller to preserve the documented WR-02
    lock-ordering invariant (model_lock THEN auto_delete_lock). No lock object
    is injected or created here (D-03).
    """

    def __init__(self,
                 context,
                 persist,
                 file_op_manager,
                 logger):
        # Single-underscore storage only — never self.__x inside a collaborator,
        # which would mangle to _AutoDeleteManager__x and break any identity
        # check against _Controller__x (RESEARCH.md Pitfall 3 / D-03).
        self._context = context
        self._persist = persist
        self._file_op_manager = file_op_manager
        self.logger = logger.getChild("AutoDeleteManager")

    def run_bfs_and_coverage(
        self,
        file: ModelFile,
        file_name: str,
        deletable_states: tuple,
    ) -> Tuple[bool, str, Optional[Set[str]]]:
        """
        Run BFS pack-guard + coverage check under __model_lock (held by caller).

        Caller holds __model_lock for the duration of this call; this method
        acquires no lock.

        Performs two concurrent operations over the directory tree in a single BFS:
        (a) Pack guard: skip if ANY descendant is in an active (non-deletable) state.
            Prevents wiping a season pack while a sibling is still downloading/extracting.
        (b) Coverage collection: gather lowercased basenames of on-disk video children
            for the coverage guard (D-08, D-09). Only files whose extension is in
            _VIDEO_EXTENSIONS are tracked (D-10).

        Returns a (skip, reason, on_disk_videos) tuple:
          - skip=False, reason="", on_disk_videos=<set>  → proceed with delete
          - skip=True,  reason="bfs_limit",   on_disk_videos=None
              → BFS node limit exceeded; caller must pop imported_children before
                returning (terminal skip — Timer does not re-arm for this firing)
          - skip=True,  reason="unsafe_child", on_disk_videos=None
              → an unsafe (active-state) child was found; retriable
          - skip=True,  reason="partial_coverage", on_disk_videos=None
              → per-child coverage check failed; retriable

        Only called when file.is_dir is True (caller ensures this guard).

        Args:
            file: The root ModelFile whose children are BFS-traversed.
            file_name: The root file name (sanitized in log calls; user-supplied).
            deletable_states: Tuple of safe ModelFile.State values (passed from
                caller so this collaborator does not depend on ModelFile state enum
                values directly — they are defined by the caller's deletable_states
                constant which is the authoritative list).
        """
        on_disk_videos: Set[str] = set()
        unsafe_child = None
        frontier = collections.deque(file.get_children())
        nodes_visited = 0

        while frontier:
            nodes_visited += 1
            if nodes_visited > _AUTO_DELETE_BFS_NODE_LIMIT:
                self.logger.warning(
                    "Auto-delete skipped for '{}': BFS node limit ({}) exceeded".format(
                        sanitize_log_value(file_name), _AUTO_DELETE_BFS_NODE_LIMIT
                    )
                )
                # Terminal skip: Timer does not re-arm for this firing.
                # Caller must clear the per-child entry so imported_children
                # isn't stranded on a permanently-oversized pack. All other
                # skip paths are retriable and intentionally leave the entry intact.
                return True, "bfs_limit", None

            child = frontier.popleft()
            if child.state not in deletable_states:
                unsafe_child = child
                break

            # Collect video basenames for coverage check. Only files whose
            # extension is in _VIDEO_EXTENSIONS are tracked (D-09/D-10).
            # child.is_dir is the authoritative leaf signal -- using
            # `not get_children()` would let a directory with an as-yet
            # unscanned child inject its own name into on_disk_videos
            # if the folder name ends in a video extension.
            grandchildren = child.get_children()
            if not child.is_dir:
                ext = os.path.splitext(child.name)[1].lower()
                if ext in _VIDEO_EXTENSIONS:
                    on_disk_videos.add(child.name.lower())
            frontier.extend(grandchildren)

        if unsafe_child is not None:
            self.logger.info(
                "Auto-delete skipped for '{}': child '{}' is in state {}".format(
                    sanitize_log_value(file_name),
                    sanitize_log_value(unsafe_child.name),
                    str(unsafe_child.state),
                )
            )
            return True, "unsafe_child", None

        # Coverage guard (D-08): pack roots with a directory on disk require
        # every on-disk video child to appear in imported_children[root].
        # A missing child indicates Sonarr silently rejected the file;
        # deleting now would lose data. Grandfather (D-14): if no per-root
        # entry exists (legacy persist or never imported via webhook), treat
        # as fully imported and proceed.
        imported_child_bset = self._persist.imported_children.get(file_name)
        if imported_child_bset is not None:
            imported_child_set = {c.lower() for c in imported_child_bset.as_list()}
            missing = on_disk_videos - imported_child_set
            if missing:
                missing_list = sorted(missing)
                shown = missing_list[:5]
                suffix = ""
                if len(missing_list) > 5:
                    suffix = " (+{} more)".format(len(missing_list) - 5)
                self.logger.info(
                    "Auto-delete skipped for '{}': partial import "
                    "({} of {} on-disk video children imported; missing: {}{})".format(
                        sanitize_log_value(file_name),
                        len(on_disk_videos) - len(missing),
                        len(on_disk_videos),
                        shown,
                        suffix,
                    )
                )
                return True, "partial_coverage", None

        return False, "", on_disk_videos
