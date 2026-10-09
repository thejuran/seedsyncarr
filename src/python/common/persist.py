import logging
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from .constants import Constants
from .error import AppError
from .localization import Localization

# Source: https://stackoverflow.com/a/39205612/8571324
T_Persist = TypeVar('T_Persist', bound='Persist')
T_Serializable = TypeVar('T_Serializable', bound='Serializable')

_logger = logging.getLogger(Constants.SERVICE_NAME).getChild("Persist")


def _fsync_directory(dir_path: str) -> None:
    fd = os.open(dir_path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Serializable(ABC):
    """
    Defines a class that is serializable to string.
    The string representation must be human readable (i.e. not pickle)
    """
    @classmethod
    @abstractmethod
    def from_str(cls: Type[T_Serializable], content: str) -> T_Serializable:
        pass

    @abstractmethod
    def to_str(self) -> str:
        pass

class PersistError(AppError):
    """
    Exception indicating persist loading/saving error
    """
    pass

class Persist(Serializable):
    """
    Defines state that should be persisted between runs
    Provides utility methods to persist/load content to/from file
    Concrete implementations need to implement the from_str() and
    to_str() functionality
    """
    @classmethod
    def from_file(cls: Type[T_Persist], file_path: str) -> T_Persist:
        if not os.path.isfile(file_path):
            raise AppError(Localization.Error.MISSING_FILE.format(file_path))
        os.chmod(file_path, 0o600)  # tighten permissions on existing files
        with open(file_path, "r") as f:
            return cls.from_str(f.read())

    def to_file(self, file_path: str):
        """
        Atomically write the serialized state to file_path.

        The content is serialized before the filesystem is touched. It is
        written to a 0600 temp file in the same directory as the target, so
        the final os.replace is a same-filesystem rename; os.replace is the
        commit point. Any failure before it leaves the original file intact,
        removes the temp file and re-raises the original exception. The
        directory fsync after the commit is best-effort: a failure there is
        logged and not raised.
        """
        content = self.to_str()
        target = os.path.realpath(file_path)
        dir_path = os.path.dirname(target)
        fd, tmp_path = tempfile.mkstemp(
            dir=dir_path, prefix="." + os.path.basename(target) + ".", suffix=".tmp"
        )
        try:
            try:
                f = os.fdopen(fd, "w")
            except BaseException:
                os.close(fd)
                raise
            with f:
                os.fchmod(f.fileno(), 0o600)
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            except OSError as e:
                _logger.warning("Could not remove temp file %s: %s", tmp_path, e)
            raise
        try:
            _fsync_directory(dir_path)
        except OSError as e:
            _logger.warning("Directory fsync failed for %s (file committed): %s", dir_path, e)

    @classmethod
    @abstractmethod
    def from_str(cls: Type[T_Persist], content: str) -> T_Persist:
        pass

    @abstractmethod
    def to_str(self) -> str:
        pass
