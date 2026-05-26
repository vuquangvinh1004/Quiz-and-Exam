"""Centralised logging setup using loguru.

Usage anywhere in the application:
    from core.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as _loguru_logger

_configured = False


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    """Configure loguru sinks.  Called once at application startup.

    Args:
        log_dir: Directory where rotating log files are stored.
        level:   Minimum log level string (DEBUG, INFO, WARNING, ERROR).
    """
    global _configured
    if _configured:
        return

    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove the default loguru sink first
    _loguru_logger.remove()

    # Console sink – only when stderr is available (i.e. not pythonw.exe)
    if sys.stderr is not None:
        _loguru_logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{line}</cyan> – {message}",
            colorize=True,
        )

    # File sink – rotating, retained for 30 days
    _loguru_logger.add(
        log_dir / "quiz_app_{time:YYYY-MM-DD}.log",
        level=level,
        rotation="00:00",      # new file each day
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} – {message}",
    )

    _configured = True


def get_logger(name: str):
    """Return a loguru logger bound with the given module name.

    Args:
        name: Typically ``__name__`` of the calling module.
    """
    return _loguru_logger.bind(name=name)
