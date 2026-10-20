"""Bộ nhớ đệm 60 giây cho phản hồi trang công khai (S-50).

Chỉ lưu phản hồi đã là bản dựng công khai (public projection), không lưu phiên,
quyền hay dữ liệu nội bộ. Khi lô bị thu hồi, recall_service gọi invalidate_all
để cảnh báo ở trang công khai không bị chậm.
"""

from collections import OrderedDict
from threading import Lock
from time import monotonic

from app.core.config import settings

_MAX_ENTRIES = 1024

_entries: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_lock = Lock()


def get(lot_code: str) -> dict | None:
    with _lock:
        entry = _entries.get(lot_code)
        if entry is None:
            return None
        if monotonic() >= entry[0]:
            del _entries[lot_code]
            return None
        _entries.move_to_end(lot_code)
        return entry[1]


def put(lot_code: str, payload: dict) -> None:
    ttl = float(settings.PUBLIC_TRACE_CACHE_TTL_SECONDS)
    if ttl <= 0:
        return
    with _lock:
        _entries[lot_code] = (monotonic() + ttl, payload)
        _entries.move_to_end(lot_code)
        while len(_entries) > _MAX_ENTRIES:
            _entries.popitem(last=False)


def invalidate(lot_code: str) -> None:
    with _lock:
        _entries.pop(lot_code, None)


def invalidate_all() -> None:
    """Vô hiệu toàn bộ khi trạng thái thu hồi thay đổi (S-50 NFR)."""
    with _lock:
        _entries.clear()
