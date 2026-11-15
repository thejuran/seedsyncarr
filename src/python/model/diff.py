from enum import Enum
from typing import List, Optional

from .file import ModelFile
from .model import Model

class ModelDiff:
    """
    Represents a single change in the model
    """
    class Change(Enum):
        ADDED = 0
        REMOVED = 1
        UPDATED = 2

    def __init__(self, change: Change, old_file: Optional[ModelFile], new_file: Optional[ModelFile]):
        self.__change = change
        self.__old_file = old_file
        self.__new_file = new_file

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return str(self.__dict__)

    @property
    def change(self) -> Change:
        return self.__change

    @property
    def old_file(self) -> Optional[ModelFile]:
        return self.__old_file

    @property
    def new_file(self) -> Optional[ModelFile]:
        return self.__new_file

class ModelDiffUtil:
    @staticmethod
    def diff_models(model_before: Model, model_after: Model) -> List[ModelDiff]:
        """
        Compare two models and generate their diff
        """
        diffs = []
        keys_before = model_before.get_file_keys()
        keys_after = model_after.get_file_keys()

        # 'after minus before' gives added files
        keys_added = keys_after.difference(keys_before)
        if keys_added:
            diffs += [
                ModelDiff(
                    ModelDiff.Change.ADDED,
                    None,
                    model_after.get_file(name, pair_id=pair_id)
                ) for pair_id, name in keys_added
            ]

        # 'before minus after' gives removed files
        keys_removed = keys_before.difference(keys_after)
        if keys_removed:
            diffs += [
                ModelDiff(
                    ModelDiff.Change.REMOVED,
                    model_before.get_file(name, pair_id=pair_id),
                    None
                ) for pair_id, name in keys_removed
            ]

        # 'before intersect after' gives potentially updated files
        keys_updated = keys_before.intersection(keys_after)
        for pair_id, name in keys_updated:
            file_before = model_before.get_file(name, pair_id=pair_id)
            file_after = model_after.get_file(name, pair_id=pair_id)
            if file_before != file_after:
                diffs.append(ModelDiff(ModelDiff.Change.UPDATED, file_before, file_after))

        return diffs
