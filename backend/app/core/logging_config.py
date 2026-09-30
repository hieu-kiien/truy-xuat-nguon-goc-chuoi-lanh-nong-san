"""Structured application logging.

The authorization and tenancy layers already attach ``extra={"event": ...}``
payloads, but without a formatter that renders them those fields are silently
dropped and no security telemetry ever reaches the log stream. This module
installs a single JSON formatter for the ``app`` logger tree so every record
carries its ``event`` name and context, and exposes the single helper used to
emit security events.
"""

import json
import logging
import sys
from typing import Any

LOGGER_NAME = "app"
SECURITY_LOGGER_NAME = "app.security"

# Attributes LogRecord always defines; anything else supplied through `extra`
# is treated as structured security context.
_RESERVED_RECORD_ATTRIBUTES = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonSecurityFormatter(logging.Formatter):
    """Render records as one JSON object per line, keeping structured context."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_ATTRIBUTES or key in payload or key == "event":
                continue
            if key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON handler on the application logger exactly once."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    # Structured records are the application's responsibility; do not also emit
    # them through the root handler, which would duplicate every line.
    logger.propagate = False
    for handler in logger.handlers:
        if getattr(handler, "_ttcs_json_handler", False):
            return
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonSecurityFormatter())
    handler._ttcs_json_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)


def get_security_logger() -> logging.Logger:
    return logging.getLogger(SECURITY_LOGGER_NAME)
