# Copyright 2017, Inderpreet Singh, All rights reserved.

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
        self.initial_model_files: List[ModelFile] = []

    @overrides(IStreamHandler)
    def setup(self):
        self.initial_model_files = list(
            self.controller.get_model_files_and_add_listener(self.model_listener)
        )

    @overrides(IStreamHandler)
    def get_value(self) -> Optional[str]:
        # Send initial files one at a time as "added" events
        # The streaming loop ensures fair interleaving with other handlers
        if self.initial_model_files:
            file = self.initial_model_files.pop(0)
            event = SerializeModel.UpdateEvent(
                change=SerializeModel.UpdateEvent.Change.ADDED,
                old_file=None,
                new_file=file
            )
            return self.serialize.update_event(event)

        # After all initial files are sent, process real-time updates
        event = self.model_listener.get_next_event()
        if event is not None:
            return self.serialize.update_event(event)
        return None

    @overrides(IStreamHandler)
    def cleanup(self):
        if self.model_listener:
            self.controller.remove_model_listener(self.model_listener)
