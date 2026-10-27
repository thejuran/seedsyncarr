"""
Wire-format SSE client helpers for the model stream.

Mirrors the frontend's ModelFileService.parseEvent reducer rules in Python so
tests can assert against the real SSE wire format the server emits (the exact
JSON strings SerializeModel produces), rather than a hand-rolled
reimplementation of ModelFile objects that never actually cross the wire.
"""
import json
from typing import Dict, Iterable, List, Tuple

from model import ModelFile
from web.serialize import SerializeModel

_EVENT_PREFIX = "event: "
_DATA_PREFIX = "data: "
_MODEL_EVENT_PREFIX = "model-"
_EVENT_INIT = "model-init"
_EVENT_ADDED = "model-added"
_EVENT_REMOVED = "model-removed"
_EVENT_UPDATED = "model-updated"


def parse_sse_events(chunks: Iterable) -> List[Tuple[str, str]]:
    """
    Parse an iterable of SSE chunks (str or bytes) into (event_name, data)
    pairs.

    Each chunk may contain zero or more complete "event: X\\ndata: Y\\n\\n"
    blocks (the exact format `Serialize._sse_pack` produces). Blocks without
    an "event:" line are skipped. Ping events are returned like any other
    event; callers filter by event name (status/log/ping events share the
    same stream as model events).
    """
    events: List[Tuple[str, str]] = []
    for chunk in chunks:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")
        for block in chunk.split("\n\n"):
            if not block.strip():
                continue
            event_name = None
            data = None
            for line in block.split("\n"):
                if line.startswith(_EVENT_PREFIX):
                    event_name = line[len(_EVENT_PREFIX):]
                elif line.startswith(_DATA_PREFIX):
                    data = line[len(_DATA_PREFIX):]
            if event_name is None:
                continue
            events.append((event_name, data if data is not None else ""))
    return events


class ModelStreamClient:
    """
    Python mirror of ModelFileService.parseEvent's four reducer rules, so a
    test can reconstruct what a browser tab's model would look like after
    applying a sequence of server-emitted SSE events:

    - model-init: replaces the whole file map with the parsed list, keyed by
      each dict's "name".
    - model-added: ignores (and counts) if the name already exists; otherwise
      sets new_file.
    - model-removed: ignores (and counts) if the name is absent; otherwise
      deletes the entry (reads old_file for the name).
    - model-updated: ignores (and counts) if the name is absent; otherwise
      sets new_file.
    """

    def __init__(self):
        self.files: Dict[str, dict] = {}
        self.ignored_added = 0
        self.ignored_removed = 0
        self.ignored_updated = 0
        self.init_count = 0
        self.update_count = 0

    def apply(self, event_name: str, data: str) -> None:
        if event_name == _EVENT_INIT:
            parsed = json.loads(data)
            self.files = {f["name"]: f for f in parsed}
            self.init_count += 1
            return

        if not event_name.startswith(_MODEL_EVENT_PREFIX):
            # status/log/ping events share the stream; not relevant here
            return

        self.update_count += 1
        parsed = json.loads(data)

        if event_name == _EVENT_ADDED:
            new_file = parsed["new_file"]
            name = new_file["name"]
            if name in self.files:
                self.ignored_added += 1
            else:
                self.files[name] = new_file
        elif event_name == _EVENT_REMOVED:
            old_file = parsed["old_file"]
            name = old_file["name"]
            if name in self.files:
                del self.files[name]
            else:
                self.ignored_removed += 1
        elif event_name == _EVENT_UPDATED:
            new_file = parsed["new_file"]
            name = new_file["name"]
            if name in self.files:
                self.files[name] = new_file
            else:
                self.ignored_updated += 1

    def apply_all(self, events: Iterable[Tuple[str, str]]) -> None:
        for event_name, data in events:
            self.apply(event_name, data)


def server_snapshot(model_files: List[ModelFile]) -> Dict[str, dict]:
    """
    Serialize model_files exactly the way the server does for model-init,
    then parse the result back into a name-keyed dict, so the server's
    current state is compared to a ModelStreamClient in the same wire
    representation.
    """
    sse_text = SerializeModel().model(model_files)
    events = parse_sse_events([sse_text])
    _, data = events[0]
    parsed = json.loads(data)
    return {f["name"]: f for f in parsed}
