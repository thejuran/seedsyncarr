from queue import Queue, Empty
from typing import Dict, List, Tuple

from common import Context, sanitize_log_value


def _format_capped(values: List[str], limit: int = 10) -> str:
    """
    Render a list of names for a log line: each value sanitized (CWE-117),
    at most `limit` shown, with a " (+N more)" suffix for the remainder.
    """
    shown = [sanitize_log_value(v) for v in values[:limit]]
    suffix = " (+{} more)".format(len(values) - limit) if len(values) > limit else ""
    return "[{}]{}".format(", ".join("'{}'".format(v) for v in shown), suffix)


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

    def enqueue_import(self, source: str, file_name: str, provenance: str = ""):
        """
        Enqueue an import event from webhook.
        Called from web server thread.

        Args:
            source: Source service ("Sonarr" or "Radarr")
            file_name: Name of the imported file
            provenance: Description of the webhook event/field that produced
                file_name (e.g. "eventType=Download, movieFile.sourcePath"),
                logged so every imported-mark is traceable to its webhook
        """
        self.__import_queue.put((source, file_name, provenance))
        # Sanitize newlines and control chars before logging -- file_name is
        # webhook-supplied and could otherwise be used for log injection (CWE-117).
        safe_file_name = sanitize_log_value(file_name)
        self.logger.info("{} webhook import enqueued: '{}' ({})".format(
            source, safe_file_name, sanitize_log_value(provenance)))

    def process(self, name_to_paths: Dict[str, Dict[str, str]]) -> List[Tuple[str, str]]:
        """
        Process queued import events and match against SeedSyncarr model.
        Called from controller thread each cycle.

        Matching is case-insensitive on the basename. The lookup maps each
        lowercased file name (root-level and child files) to every model path
        carrying that name, so a child file name reported by Sonarr/Radarr
        (e.g., an episode inside a downloaded directory) can be resolved, and
        a name that matches more than one path can be detected.

        A name that resolves to two or more distinct model paths is ambiguous:
        it is rejected with a single warning and nothing is returned for it,
        so no import credit is recorded and no auto-delete is armed. The same
        path referenced twice is one dict key and is never ambiguous.

        Args:
            name_to_paths: Dict mapping lowercased basename to a dict of
                {case-preserving relative model path -> root-level model file
                name}. Root entries map {root_name: root_name}; child entries
                map {"Root/sub/child": root_name}.

        Returns:
            List of (root_name, matched_name) tuples for imports that matched
            exactly one tracked model path. root_name is the canonical-cased
            root model file name; matched_name is the webhook-supplied file
            name (preserves original casing). When the webhook name IS the
            root, matched_name equals root_name. Ambiguous names are omitted.
        """
        newly_imported = []

        # Drain queue
        while not self.__import_queue.empty():
            try:
                source, file_name, provenance = self.__import_queue.get_nowait()
            except Empty:
                # Queue empty (race condition between empty() and get_nowait())
                break

            # Case-insensitive matching against root and child names
            candidates = name_to_paths.get(file_name.lower())
            # Sanitize webhook-supplied file_name for log output (CWE-117). The
            # queue value is used raw for matching (correct), but log sinks must
            # escape control chars so crafted payloads can't split log entries.
            safe_file_name = sanitize_log_value(file_name)
            if not candidates:
                self.logger.warning(
                    "{} webhook file '{}' not found in SeedSyncarr model "
                    "(checked {} names including children)".format(
                        source, safe_file_name, len(name_to_paths)
                    )
                )
            elif len(candidates) == 1:
                root_name = next(iter(candidates.values()))
                newly_imported.append((root_name, file_name))
                self.logger.info(
                    "{} import detected: '{}' (matched SeedSyncarr file '{}'; {})".format(
                        source, safe_file_name, sanitize_log_value(root_name),
                        sanitize_log_value(provenance)
                    )
                )
            else:
                # Root and path names come from the remote scan and are
                # attacker-influenceable; _format_capped sanitizes each one.
                roots = sorted(set(candidates.values()))
                paths = sorted(candidates)
                self.logger.warning(
                    "{} webhook import '{}' is ambiguous: matches {} distinct "
                    "SeedSyncarr paths in release(s) {} ({}); "
                    "no import credit or automatic cleanup authorized ({})".format(
                        source, safe_file_name, len(paths),
                        _format_capped(roots), _format_capped(paths),
                        sanitize_log_value(provenance)
                    )
                )

        return newly_imported
