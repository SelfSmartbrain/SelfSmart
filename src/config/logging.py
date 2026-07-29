"""
Structured logging configuration with correlation IDs.
"""

import logging
import sys
import uuid
from contextlib import contextmanager
from typing import Optional, Generator
from datetime import datetime

import structlog
from prometheus_client import Counter

from src.config.settings import get_settings

# Metrics
LOG_ERRORS = Counter("log_errors_total", "Total log errors", ["level", "module"])


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> None:
    """Configure structured logging."""
    settings = get_settings()

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Configure structlog
    if json_format:
        # JSON format for production
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console format for development
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(name)


@contextmanager
def log_context(
    correlation_id: Optional[str] = None, user_id: Optional[str] = None, **kwargs
) -> Generator[None, None, None]:
    """Context manager for adding log context."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    context = {
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if user_id:
        context["user_id"] = user_id

    context.update(kwargs)

    with structlog.contextvars.bind_contextvars(**context):
        try:
            yield
        finally:
            # Clean up context
            for key in context.keys():
                structlog.contextvars.unbind_contextvars(key)


class LoggerMixin:
    """Mixin for adding logging to classes."""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)
