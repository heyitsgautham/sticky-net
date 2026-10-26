"""A dict with a size limit that evicts the least recently used entry."""

from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from typing import Generic, TypeVar

V = TypeVar("V")


class BoundedCache(MutableMapping[str, V], Generic[V]):
    """Mapping of at most ``maxsize`` entries; reads and writes mark a key as recent.

    Session state lives in these caches, so an active conversation, which touches
    its session every turn, stays while a flood of one-off session IDs pushes out
    only the oldest idle ones. Firestore keeps a copy of each session, so an evicted
    session is restored on its next turn when persistence is on.
    """

    def __init__(self, maxsize: int) -> None:
        if maxsize < 1:
            raise ValueError(f"maxsize must be at least 1, got {maxsize}")
        self.maxsize = maxsize
        self._data: OrderedDict[str, V] = OrderedDict()

    def __getitem__(self, key: str) -> V:
        value = self._data[key]
        self._data.move_to_end(key)
        return value

    def __setitem__(self, key: str, value: V) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)
