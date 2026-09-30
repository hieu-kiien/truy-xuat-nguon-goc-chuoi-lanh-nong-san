"""Single entry point for emitting security-relevant log events.

Every authorization, tenant-isolation and authentication decision worth
auditing goes through :func:`log_security_event` so the event name and context
keys stay consistent and machine-parseable.
"""

import logging
from typing import Any

from fastapi import Request

from app.core.logging_config import get_security_logger

_LOGGER: logging.Logger = get_security_logger()

# Never let a logging call take down a request path.
_SENSITIVE_KEYS = frozenset({"password", "token", "session_token", "authorization"})


def _request_context(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {}
    client = request.client
    return {
        "method": request.method,
        "path": request.url.path,
        "client_ip": client.host if client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": getattr(request.state, "request_id", None),
    }


def log_security_event(
    event: str,
    *,
    level: int = logging.WARNING,
    request: Request | None = None,
    **context: Any,
) -> None:
    """Emit a structured security event.

    ``extra`` keys prefixed with ``security_`` are stripped because they would
    collide with :class:`logging.LogRecord` internals.
    """
    payload: dict[str, Any] = {"event": event}
    payload.update(_request_context(request))
    for key, value in context.items():
        if value is None:
            continue
        payload[key] = "<redacted>" if key in _SENSITIVE_KEYS else value
    _LOGGER.log(level, event, extra=payload)
