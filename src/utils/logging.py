import logging
import sys
import structlog
from typing import Any, Dict

def setup_logging(level: str = "INFO", json_format: bool = True):
    """
    Configure structlog for structured logging.
    """

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_format:
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Standard logging configuration to capture logs from other libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

def get_logger(name: str):
    return structlog.get_logger(name)
