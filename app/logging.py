"""Logging configuration for the application.

Called once at import time from ``app.bootstrap``.
Filters out the noisiest third-party loggers (SQLAlchemy engine, httpx).
"""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logging(level: str = "INFO", **kwargs: Any) -> None:
    """Configure application-wide logging.

    Replaces any existing handlers so that log format and destination
    are predictable in both development and Docker production.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Purge any handlers already attached (e.g. uvicorn's default)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Single stdout handler with timestamped structured format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress the noisiest third-party loggers at the package level
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
