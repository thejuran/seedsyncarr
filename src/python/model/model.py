import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Set, Tuple

from common import AppError, sanitize_log_value
from .file import ModelFile

class ModelError(AppError):
    """
    Exception indicating a model error
    """
    pass

class IModelListener(ABC):
    """
    Interface to listen to model events
    """
    @abstractmethod
    def file_added(self, file: ModelFile):
        """
        Event indicating a file was added to the model
        """
        pass

    @abstractmethod
    def file_removed(self, file: ModelFile):
        """
        Event indicating that the given file was removed from the model
        """
        pass

    @abstractmethod
    def file_updated(self, old_file: ModelFile, new_file: ModelFile):
        """
        Event indicating that the given file was updated
        """
        pass

# A file is identified by the path pair it belongs to and its name
ModelKey = Tuple[Optional[str], str]


class Model:
    """
    Represents the entire state of lftp

    Thread-safety: Listener operations are protected by __listeners_lock.
    The copy-under-lock pattern is used when notifying listeners to prevent
    race conditions with concurrent add/remove operations.
    """
    def __init__(self, pair_id: Optional[str] = None):
        """
        :param pair_id: path pair this model holds the files of. Lookups and
            removals that do not name a pair use it, so the controller of a
            pair does not repeat its id on every call.
        """
        self.logger = logging.getLogger("Model")
        self.__pair_id = pair_id
        self.__files = {}  # (pair_id, name)->ModelFile
        self.__listeners = []
        self.__listeners_lock = threading.Lock()

    def set_base_logger(self, base_logger: logging.Logger):
        self.logger = base_logger.getChild("Model")

    def add_listener(self, listener: IModelListener):
        """
        Add a model listener
        """
        self.logger.debug("LftpModel: Adding a listener")
        with self.__listeners_lock:
            if listener not in self.__listeners:
                self.__listeners.append(listener)

    def remove_listener(self, listener: IModelListener):
        """
        Remove a model listener
        """
        self.logger.debug("LftpModel: Removing a listener")
        with self.__listeners_lock:
            if listener not in self.__listeners:
                self.logger.error("LftpModel: listener does not exist!")
            else:
                self.__listeners.remove(listener)

    def add_file(self, file: ModelFile):
        """
        Add a file to the model
        """
        self.logger.debug("LftpModel: Adding file '{}'".format(sanitize_log_value(file.name)))
        key = (file.pair_id, file.name)
        if key in self.__files:
            raise ModelError("File already exists in the model")
        # Freeze the file to make it immutable before storing
        file.freeze()
        self.__files[key] = file
        # Copy-under-lock: copy listeners while holding lock, then iterate outside lock
        with self.__listeners_lock:
            listeners = list(self.__listeners)
        for listener in listeners:
            listener.file_added(file)

    def remove_file(self, filename: str, pair_id: Optional[str] = None):
        """
        Remove the file from the model
        """
        self.logger.debug("LftpModel: Removing file '{}'".format(sanitize_log_value(filename)))
        key = (pair_id if pair_id is not None else self.__pair_id, filename)
        if key not in self.__files:
            raise ModelError("File does not exist in the model")
        file = self.__files[key]
        del self.__files[key]
        # Copy-under-lock: copy listeners while holding lock, then iterate outside lock
        with self.__listeners_lock:
            listeners = list(self.__listeners)
        for listener in listeners:
            listener.file_removed(file)

    def update_file(self, file: ModelFile):
        """
        Update an already existing file
        """
        self.logger.debug("LftpModel: Updating file '{}'".format(sanitize_log_value(file.name)))
        key = (file.pair_id, file.name)
        if key not in self.__files:
            raise ModelError("File does not exist in the model")
        old_file = self.__files[key]
        new_file = file
        # Freeze the new file to make it immutable before storing
        new_file.freeze()
        self.__files[key] = new_file
        # Copy-under-lock: copy listeners while holding lock, then iterate outside lock
        with self.__listeners_lock:
            listeners = list(self.__listeners)
        for listener in listeners:
            listener.file_updated(old_file, new_file)

    def get_file(self, name: str, pair_id: Optional[str] = None) -> ModelFile:
        """
        Returns the file of the given name in the given path pair.
        The returned file is frozen (immutable) and safe to use across threads.
        """
        key = (pair_id if pair_id is not None else self.__pair_id, name)
        if key not in self.__files:
            raise ModelError("File does not exist in the model")
        return self.__files[key]

    def get_file_names(self) -> Set[str]:
        """
        Names of all files. A name shared by several pairs appears once; use
        get_file_keys() to tell them apart.
        """
        return {name for _, name in self.__files}

    def get_file_keys(self) -> Set[ModelKey]:
        return set(self.__files.keys())
