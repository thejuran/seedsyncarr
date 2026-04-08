from typing import List
from datetime import datetime

class SystemFile:
    """
    Represents a system file or directory
    """
    def __init__(self,
                 name: str,
                 size: int,
                 is_dir: bool = False,
                 time_created: datetime = None,
                 time_modified: datetime = None):
        if size < 0:
            raise ValueError("File size must be greater than zero")
        self.__name = name
        self.__size = size  # in bytes
        self.__is_dir = is_dir
        self.__timestamp_created = time_created
        self.__timestamp_modified = time_modified
        self.__children = []

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return str(self.__dict__)

    @property
    def name(self) -> str: return self.__name

    @property
    def size(self) -> int: return self.__size

    @property
    def is_dir(self) -> bool: return self.__is_dir

    @property
    def timestamp_created(self) -> datetime: return self.__timestamp_created

    @property
    def timestamp_modified(self) -> datetime: return self.__timestamp_modified

    @property
    def children(self) -> List["SystemFile"]: return self.__children

    def add_child(self, file: "SystemFile"):
        if not self.__is_dir:
            raise TypeError("Cannot add children to a file")
        self.__children.append(file)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        d = {
            "name": self.__name,
            "size": self.__size,
            "is_dir": self.__is_dir,
        }
        if self.__timestamp_created is not None:
            d["time_created"] = self.__timestamp_created.isoformat()
        if self.__timestamp_modified is not None:
            d["time_modified"] = self.__timestamp_modified.isoformat()
        if self.__children:
            d["children"] = [child.to_dict() for child in self.__children]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SystemFile":
        """Reconstruct SystemFile from a dictionary."""
        from datetime import datetime
        time_created = None
        time_modified = None
        if "time_created" in data and data["time_created"] is not None:
            time_created = datetime.fromisoformat(data["time_created"])
        if "time_modified" in data and data["time_modified"] is not None:
            time_modified = datetime.fromisoformat(data["time_modified"])
        sf = cls(
            name=data["name"],
            size=data["size"],
            is_dir=data.get("is_dir", False),
            time_created=time_created,
            time_modified=time_modified,
        )
        for child_data in data.get("children", []):
            sf.add_child(cls.from_dict(child_data))
        return sf
