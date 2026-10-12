"""Bounded 60-second topology hints; never store authorization or stock."""

from collections import OrderedDict
from threading import Lock
from time import monotonic
from uuid import UUID

_entries: OrderedDict[tuple, tuple[float, frozenset[UUID]]] = OrderedDict()
_lock = Lock()


def get(key: tuple) -> frozenset[UUID] | None:
    with _lock:
        entry = _entries.get(key)
        if entry is None:
            return None
        if monotonic() >= entry[0]:
            del _entries[key]
            return None
        _entries.move_to_end(key)
        return entry[1]


def put(key: tuple, ids: set[UUID]) -> None:
    with _lock:
        _entries[key] = (monotonic() + 60, frozenset(ids))
        _entries.move_to_end(key)
        while len(_entries) > 1024:
            _entries.popitem(last=False)
