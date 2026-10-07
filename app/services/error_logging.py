"""Central, privacy-conscious error logging for the desktop application."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import re
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from app.paths import get_session_log


P = ParamSpec("P")
R = TypeVar("R")
_LOGGER_NAME = "costprofit"
_MAX_LOG_BYTES = 1_000_000
_BACKUP_COUNT = 3
_SENSITIVE_VALUE = re.compile(
    r"(?i)(password|security[_ ]?answer|password_hash|password_salt|"
    r"security_answer_hash|security_answer_salt)\s*([:=])\s*([^,;\s]+)"
)


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _SENSITIVE_VALUE.sub(r"\1\2[REDACTED]", super().format(record))


def configure_error_logging() -> logging.Logger:
    """Configure the rotating application log once and return its logger."""
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    log_path = get_session_log()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path, maxBytes=_MAX_LOG_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    handler.setFormatter(_RedactingFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def get_error_logger(component: str) -> logging.Logger:
    configure_error_logging()
    return logging.getLogger(f"{_LOGGER_NAME}.{component}")


def log_failures(operation: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Log an operation failure while preserving its existing error behavior."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except Exception:
                get_error_logger(func.__module__).exception("Failed to %s", operation)
                raise
        return wrapped
    return decorator
