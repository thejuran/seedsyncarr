import logging
from typing import Optional, List

from ..web_app import IStreamHandler
from ..utils import StreamQueue
from ..serialize import SerializeModel
from model import IModelListener, ModelFile
from common import overrides
from controller import Controller

class WebResponseModelListener(IModelListener, StreamQueue[SerializeModel.UpdateEvent]):
    """
    Model listener used by streams to listen to model updates
    One listener should be created for each new request
    """
    def __init__(self):
        super().__init__()

    @overrides(IModelListener)
    def file_added(self, file: ModelFile):
        self.put(SerializeModel.UpdateEvent(change=SerializeModel.UpdateEvent.Change.ADDED,
                                            old_file=None,
                                            new_file=file))

    @overrides(IModelListener)
    def file_removed(self, file: ModelFile):
        self.put(SerializeModel.UpdateEvent(change=SerializeModel.UpdateEvent.Change.REMOVED,
                                            old_file=file,
                                            new_file=None))

    @overrides(IModelListener)
    def file_updated(self, old_file: ModelFile, new_file: ModelFile):
        self.put(SerializeModel.UpdateEvent(change=SerializeModel.UpdateEvent.Change.UPDATED,
                                            old_file=old_file,
                                            new_file=new_file))

class ModelStreamHandler(IStreamHandler):
    def __init__(self, controller: Controller):
        self.controller = controller
        self.serialize = SerializeModel()
        self.model_listener = WebResponseModelListener()
        # None until setup() runs; a list (possibly empty) afterwards
        self.initial_model_files: Optional[List[ModelFile]] = None
        self.logger = logging.getLogger("ModelStreamHandler")
        # Overflow-resync state (STRM-02): a single bool, never a list of
        # pending snapshots -- at most one resync is ever in flight per tab.
        self._last_seen_dropped = 0
        self._resync_pending = False
        self._resync_count = 0

    @overrides(IStreamHandler)
    def setup(self):
        self.initial_model_files = list(
            self.controller.get_model_files_and_add_listener(self.model_listener)
        )

    def _discard_backlog(self) -> None:
        """
        Runs under Controller.__model_lock via resync_model_files: clears the
        stale backlog and rebaselines the dropped count inside the lock, so
        any drop before this point is covered by the snapshot and any later
        drop triggers a new resync (D-03, D-04).
        """
        self.model_listener.clear()
        self._last_seen_dropped = self.model_listener.get_dropped_count()

    @overrides(IStreamHandler)
    def get_value(self) -> Optional[str]:
        # Send the entire initial model as a single "model-init" event.
        # Sending per-file "added" events instead (one per stream iteration,
        # 10ms apart) made the frontend re-sort and re-render the file list
        # once per file — with hundreds of root files the initial page load
        # starved the browser main thread and could stall the dashboard.
        # An empty model still sends model-init so the frontend knows the
        # initial state has loaded.
        if self.initial_model_files is not None:
            files = self.initial_model_files
            self.initial_model_files = None
            return self.serialize.model(files)

        # Overflow resync gate: if this tab's listener dropped events since
        # the last check, a stalled connection would otherwise keep
        # delivering a stale backlog. Resend a fresh "model-init" in place
        # of the next incremental event instead -- the frontend already
        # replaces its whole list on model-init, so no frontend change is
        # needed (D-02). This must run strictly before get_next_event() so
        # the first value after a drop is never a stale backlog event.
        if self.model_listener.get_dropped_count() != self._last_seen_dropped:
            self._resync_pending = True

        if self._resync_pending:
            self._resync_pending = False
            files = self.controller.resync_model_files(self._discard_backlog)
            self._resync_count += 1
            if self._resync_count % 100 == 1:
                self.logger.warning(
                    "Model stream resynced after queue overflow: {} resyncs, "
                    "{} events dropped total".format(
                        self._resync_count, self.model_listener.get_dropped_count()
                    )
                )
            return self.serialize.model(files)

        # After the initial model is sent, process real-time updates
        event = self.model_listener.get_next_event()
        if event is not None:
            return self.serialize.update_event(event)
        return None

    @overrides(IStreamHandler)
    def cleanup(self):
        if self.model_listener:
            self.controller.remove_model_listener(self.model_listener)
