"""Giới hạn tần suất trang công khai theo IP (S-50).

Một IP gọi quá nhiều MÃ LÔ KHÁC NHAU trong một phút bị chặn tạm để ngăn dò
quét hàng loạt. Mọi lượt gọi đều được đếm, kể cả mã không tồn tại.
"""

from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from app.core.config import settings

_MAX_TRACKED_IPS = 4096

_windows: OrderedDict[str, deque[tuple[float, str]]] = OrderedDict()
_lock = Lock()


def _prune(window: deque[tuple[float, str]], now: float, window_seconds: float) -> None:
    while window and now - window[0][0] >= window_seconds:
        window.popleft()


def reset() -> None:
    """Xóa trạng thái giới hạn; dùng để test cô lập."""
    with _lock:
        _windows.clear()


def is_over_limit(client_ip: str, lot_code: str) -> bool:
    """Ghi nhận một lượt tra cứu; True nếu IP này đã vượt giới hạn."""
    window_seconds = float(settings.PUBLIC_TRACE_RATE_WINDOW_SECONDS)
    limit = settings.PUBLIC_TRACE_RATE_LIMIT_CODES
    now = monotonic()

    with _lock:
        window = _windows.get(client_ip)
        if window is None:
            window = deque()
            _windows[client_ip] = window
            while len(_windows) > _MAX_TRACKED_IPS:
                _windows.popitem(last=False)
        else:
            _windows.move_to_end(client_ip)

        _prune(window, now, window_seconds)

        if len({code for _, code in window}) >= limit:
            return True

        window.append((now, lot_code))
        return False
