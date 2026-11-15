import copy
import json
import re
import threading
import uuid
from typing import Any, Dict, List, Optional

from .persist import Persist, PersistError


class PathPair:
    """
    A single remote-to-local directory mapping
    """

    DEFAULT_NAME = "Default"
    # Id of the pair migrated from the legacy single remote_path/local_path.
    # It keeps using the original controller.persist file.
    LEGACY_ID = "default"

    def __init__(
        self,
        name: str,
        remote_path: str,
        local_path: str,
        enabled: bool = True,
        auto_queue: bool = True,
        pair_id: Optional[str] = None,
    ):
        self.id = pair_id or str(uuid.uuid4())
        self.name = name
        self.remote_path = remote_path
        self.local_path = local_path
        self.enabled = enabled
        self.auto_queue = auto_queue

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "remote_path": self.remote_path,
            "local_path": self.local_path,
            "enabled": self.enabled,
            "auto_queue": self.auto_queue,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PathPair":
        required = (
            ("id", str),
            ("name", str),
            ("remote_path", str),
            ("local_path", str),
        )
        optional = (("enabled", bool), ("auto_queue", bool))
        for key, expected in required:
            if key not in d:
                raise KeyError(key)
            if not isinstance(d[key], expected):
                raise TypeError(
                    "{} must be {}, got {}".format(
                        key, expected.__name__, type(d[key]).__name__
                    )
                )
        for key, expected in optional:
            if key in d and not isinstance(d[key], expected):
                raise TypeError(
                    "{} must be {}, got {}".format(
                        key, expected.__name__, type(d[key]).__name__
                    )
                )
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", d["id"]):
            # The id names a persist file, so it must be safe as a file name
            raise ValueError("id must be 1-64 letters, digits, '-' or '_'")
        for key in ("id", "name", "remote_path", "local_path"):
            if not d[key].strip():
                raise ValueError("{} must not be empty".format(key))
        return PathPair(
            name=d["name"],
            remote_path=d["remote_path"],
            local_path=d["local_path"],
            enabled=d.get("enabled", True),
            auto_queue=d.get("auto_queue", True),
            pair_id=d["id"],
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PathPair):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return "PathPair({})".format(self.to_dict())


class PathPairsConfig(Persist):
    """
    The set of configured path pairs, persisted as path_pairs.json.
    Accessors return copies, so callers cannot mutate internal state.
    """

    __CURRENT_VERSION = 1
    __KEY_VERSION = "version"
    __KEY_PAIRS = "path_pairs"

    def __init__(self):
        self.__lock = threading.RLock()
        self.__pairs: List[PathPair] = []

    @property
    def pairs(self) -> List[PathPair]:
        with self.__lock:
            return [copy.deepcopy(p) for p in self.__pairs]

    def get_pair(self, pair_id: str) -> Optional[PathPair]:
        with self.__lock:
            for p in self.__pairs:
                if p.id == pair_id:
                    return copy.deepcopy(p)
        return None

    def add_pair(self, pair: PathPair):
        with self.__lock:
            if any(p.id == pair.id for p in self.__pairs):
                raise ValueError("PathPair with id '{}' already exists".format(pair.id))
            if any(p.name == pair.name for p in self.__pairs):
                raise ValueError(
                    "PathPair with name '{}' already exists".format(pair.name)
                )
            self.__pairs.append(copy.deepcopy(pair))

    def update_pair(self, pair: PathPair):
        with self.__lock:
            for i, p in enumerate(self.__pairs):
                if p.id == pair.id:
                    if any(
                        o.name == pair.name and o.id != pair.id for o in self.__pairs
                    ):
                        raise ValueError(
                            "PathPair with name '{}' already exists".format(pair.name)
                        )
                    self.__pairs[i] = copy.deepcopy(pair)
                    return
            raise ValueError("PathPair with id '{}' not found".format(pair.id))

    def remove_pair(self, pair_id: str):
        with self.__lock:
            remaining = [p for p in self.__pairs if p.id != pair_id]
            if len(remaining) == len(self.__pairs):
                raise ValueError("PathPair with id '{}' not found".format(pair_id))
            self.__pairs = remaining

    @classmethod
    def from_legacy(cls, remote_path: str, local_path: str) -> "PathPairsConfig":
        """
        Build a config holding one pair from the legacy single remote_path/local_path
        """
        config = cls()
        config.add_pair(
            PathPair(
                name=PathPair.DEFAULT_NAME,
                remote_path=remote_path,
                local_path=local_path,
                pair_id=PathPair.LEGACY_ID,
            )
        )
        return config

    def sync_legacy(self, remote_path: str, local_path: str) -> bool:
        """
        Make the legacy pair follow the lftp remote_path/local_path in settings.cfg,
        which stays the source of truth for it. Creates the pair if there is none.
        Returns True if anything changed.
        """
        with self.__lock:
            for p in self.__pairs:
                if p.id == PathPair.LEGACY_ID:
                    if p.remote_path == remote_path and p.local_path == local_path:
                        return False
                    p.remote_path = remote_path
                    p.local_path = local_path
                    return True
            if not self.__pairs:
                self.__pairs.append(
                    PathPair(
                        name=PathPair.DEFAULT_NAME,
                        remote_path=remote_path,
                        local_path=local_path,
                        pair_id=PathPair.LEGACY_ID,
                    )
                )
                return True
        return False

    @classmethod
    def from_str(cls, content: str) -> "PathPairsConfig":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise PersistError("Error parsing PathPairsConfig: {}".format(str(e)))
        if not isinstance(data, dict):
            raise PersistError("Expected JSON object in PathPairsConfig")
        version = data.get(cls.__KEY_VERSION, cls.__CURRENT_VERSION)
        if (
            not isinstance(version, int)
            or isinstance(version, bool)
            or version > cls.__CURRENT_VERSION
        ):
            raise PersistError(
                "Unsupported PathPairsConfig version: {!r}".format(version)
            )
        raw_pairs = data.get(cls.__KEY_PAIRS, [])
        if not isinstance(raw_pairs, list):
            raise PersistError("Expected '{}' to be a list".format(cls.__KEY_PAIRS))
        config = cls()
        for raw in raw_pairs:
            if not isinstance(raw, dict):
                raise PersistError("Malformed path pair entry: expected an object")
            try:
                config.add_pair(PathPair.from_dict(raw))
            except (KeyError, TypeError, ValueError) as e:
                raise PersistError("Malformed path pair entry: {}".format(e))
        return config

    def to_str(self) -> str:
        with self.__lock:
            data = {
                self.__KEY_VERSION: self.__CURRENT_VERSION,
                self.__KEY_PAIRS: [p.to_dict() for p in self.__pairs],
            }
        return json.dumps(data, indent=2)
