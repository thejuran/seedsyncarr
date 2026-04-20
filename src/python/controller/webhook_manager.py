from queue import Queue, Empty
from typing import Dict, List, Tuple

from common import Context

class WebhookManager:
    """
    Manages webhook-triggered import events via thread-safe queue.

    Responsible for:
    - Receiving import events from web server thread via enqueue_import()
    - Processing queued events in controller thread via process()
    - Matching imported file names against SeedSyncarr model
    - Reporting newly imported files

    Thread-safety: Queue is thread-safe. enqueue_import() called from web
    thread, process() called from controller thread.
    """

    def __init__(self, context: Context):
        self.__context = context
        self.logger = context.logger.getChild("WebhookManager")
        self.__import_queue = Queue()

    def enqueue_import(self, source: str, file_name: str):
        """
        Enqueue an import event from webhook.
        Called from web server thread.

        Args:
            source: Source service ("Sonarr" or "Radarr")
            file_name: Name of the imported file
        """
        self.__import_queue.put((source, file_name))
        # Sanitize newlines before logging -- file_name is webhook-supplied and
        # could otherwise be used for log injection (CWE-117).
        safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")
        self.logger.info("{} webhook import enqueued: '{}'".format(source, safe_file_name))

    def process(self, name_to_root: Dict[str, str]) -> List[Tuple[str, str]]:
        """
        Process queued import events and match against SeedSyncarr model.
        Called from controller thread each cycle.

        Matching is case-insensitive. The lookup dict maps lowercased file names
        (both root-level and child files) to their root-level model file name.
        This allows matching when Sonarr/Radarr reports a child file name
        (e.g., an episode inside a downloaded directory).

        Args:
            name_to_root: Dict mapping lowercased file names to their root-level
                model file name. Includes both root names and child file names.

        Returns:
            List of (root_name, matched_name) tuples for imports that matched a
            tracked model file. root_name is the canonical-cased root model file
            name; matched_name is the webhook-supplied file name (preserves
            original casing). When the webhook name IS the root, matched_name
            equals root_name.
        """
        newly_imported = []

        # Drain queue
        while not self.__import_queue.empty():
            try:
                source, file_name = self.__import_queue.get_nowait()
            except Empty:
                # Queue empty (race condition between empty() and get_nowait())
                break

            # Case-insensitive matching against root and child names
            root_name = name_to_root.get(file_name.lower())
            # Sanitize webhook-supplied file_name for log output (CWE-117). The
            # queue value is used raw for matching (correct), but log sinks must
            # strip newlines so crafted payloads can't split log entries.
            safe_file_name = file_name.replace("\n", "\\n").replace("\r", "\\r")
            if root_name is not None:
                newly_imported.append((root_name, file_name))
                self.logger.info(
                    "{} import detected: '{}' (matched SeedSyncarr file '{}')".format(
                        source, safe_file_name, root_name
                    )
                )
            else:
                self.logger.warning(
                    "{} webhook file '{}' not found in SeedSyncarr model "
                    "(checked {} names including children)".format(
                        source, safe_file_name, len(name_to_root)
                    )
                )

        return newly_imported
