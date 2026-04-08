# Copyright 2017, Inderpreet Singh, All rights reserved.

from collections import OrderedDict
from typing import TypeVar, Generic, Iterator, Iterable, Optional, Set

T = TypeVar('T')


class BoundedOrderedSet(Generic[T]):
    """
    A set-like container with a maximum size that evicts oldest entries.

    This class provides:
    - Set semantics (unique elements, membership testing)
    - Insertion order preservation
    - Automatic LRU-style eviction when maxlen is reached
    - O(1) membership testing, add, and remove operations

    When maxlen is reached and a new item is added, the oldest item
    (first inserted that hasn't been removed) is automatically evicted.

    Thread-safety: Not thread-safe. Callers must provide external synchronization.

    Example:
        >>> bset = BoundedOrderedSet(maxlen=3)
        >>> bset.add('a')
        >>> bset.add('b')
        >>> bset.add('c')
        >>> bset.add('d')  # 'a' is evicted
        >>> list(bset)
        ['b', 'c', 'd']
    """

    # Default maximum size (10,000 files is reasonable for most use cases)
    DEFAULT_MAXLEN = 10000

    def __init__(self, maxlen: Optional[int] = None, iterable: Optional[Iterable[T]] = None):
        """
        Initialize a bounded ordered set.

        :param maxlen: Maximum number of elements. If None, uses DEFAULT_MAXLEN.
                       Must be positive.
        :param iterable: Optional iterable of initial elements.
        """
        self._maxlen = maxlen if maxlen is not None else self.DEFAULT_MAXLEN
        if self._maxlen < 1:
            raise ValueError("maxlen must be positive, got {}".format(self._maxlen))

        # Use OrderedDict as backing store - keys are elements, values are ignored
        self._data: OrderedDict[T, None] = OrderedDict()

        # Track total evictions for monitoring/debugging
        self._total_evictions = 0

        if iterable is not None:
            for item in iterable:
                self.add(item)

    @property
    def maxlen(self) -> int:
        """Maximum number of elements allowed."""
        return self._maxlen

    @property
    def total_evictions(self) -> int:
        """Total number of elements evicted since creation."""
        return self._total_evictions

    def add(self, item: T) -> Optional[T]:
        """
        Add an item to the set.

        If the item already exists, this is a no-op (it does NOT update order).
        If adding would exceed maxlen, the oldest item is evicted first.

        :param item: Item to add
        :return: The evicted item if eviction occurred, None otherwise
        """
        # If item exists, do nothing (standard set behavior)
        if item in self._data:
            return None

        evicted = None

        # Evict oldest if at capacity
        if len(self._data) >= self._maxlen:
            # popitem(last=False) removes the first (oldest) item
            evicted, _ = self._data.popitem(last=False)
            self._total_evictions += 1

        self._data[item] = None
        return evicted

    def touch(self, item: T) -> bool:
        """
        Move an item to the end (most recent position) if it exists.

        This refreshes the item's position in the LRU order, preventing
        it from being evicted soon. If the item doesn't exist, does nothing.

        :param item: Item to refresh
        :return: True if item was found and touched, False otherwise
        """
        if item not in self._data:
            return False
        # Move to end (most recent position)
        self._data.move_to_end(item)
        return True

    def discard(self, item: T) -> None:
        """
        Remove an item from the set if present.

        Does not raise an error if the item is not present.

        :param item: Item to remove
        """
        self._data.pop(item, None)

    def remove(self, item: T) -> None:
        """
        Remove an item from the set.

        :param item: Item to remove
        :raises KeyError: If item is not in the set
        """
        del self._data[item]

    def clear(self) -> None:
        """Remove all items from the set."""
        self._data.clear()

    def difference_update(self, other: Iterable[T]) -> None:
        """
        Remove all items that are in 'other' from this set.

        Equivalent to: self -= other

        :param other: Iterable of items to remove
        """
        for item in other:
            self.discard(item)

    def __contains__(self, item: T) -> bool:
        """Check if item is in the set."""
        return item in self._data

    def __len__(self) -> int:
        """Return the number of items in the set."""
        return len(self._data)

    def __iter__(self) -> Iterator[T]:
        """Iterate over items in insertion order."""
        return iter(self._data)

    def __bool__(self) -> bool:
        """Return True if the set is non-empty."""
        return bool(self._data)

    def __repr__(self) -> str:
        items = list(self._data.keys())
        return "BoundedOrderedSet({}, maxlen={})".format(items, self._maxlen)

    def __eq__(self, other) -> bool:
        """
        Test equality with another BoundedOrderedSet or regular set.

        Only compares contents, not maxlen or eviction count.
        """
        if isinstance(other, BoundedOrderedSet):
            return set(self._data.keys()) == set(other._data.keys())
        elif isinstance(other, (set, frozenset)):
            return set(self._data.keys()) == other
        return NotImplemented

    def copy(self) -> "BoundedOrderedSet[T]":
        """
        Create a shallow copy of this set.

        The copy has the same maxlen but eviction count is reset to 0.
        """
        new_set: BoundedOrderedSet[T] = BoundedOrderedSet(maxlen=self._maxlen)
        new_set._data = self._data.copy()
        return new_set

    def as_set(self) -> Set[T]:
        """Return a regular set containing all items."""
        return set(self._data.keys())

    def as_list(self) -> list:
        """Return a list of items in insertion order."""
        return list(self._data.keys())

    @classmethod
    def from_iterable(cls, iterable: Iterable[T], maxlen: Optional[int] = None) -> "BoundedOrderedSet[T]":
        """
        Create a BoundedOrderedSet from an iterable.

        If the iterable has more items than maxlen, only the last maxlen
        items (in iteration order) will be retained.

        :param iterable: Source iterable
        :param maxlen: Maximum size (uses DEFAULT_MAXLEN if None)
        :return: New BoundedOrderedSet
        """
        return cls(maxlen=maxlen, iterable=iterable)
