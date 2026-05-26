"""Shared UI error handling helpers.

Keeps user-facing error messages consistent while logging root causes.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from core.utils.error_mapper import map_exception_to_user_message
from core.utils.logger import get_logger

_logger = get_logger(__name__)


def show_critical_error(
    parent: QWidget | None,
    title: str,
    message: str,
    *,
    exc: Exception | None = None,
) -> None:
    """Show a critical dialog and log details for diagnostics."""
    if exc is not None:
        mapped = map_exception_to_user_message(exc)
        _logger.error(f"{title}: {message}: {exc}")
        details = f"{message}\n{mapped}"
    else:
        _logger.error(f"{title}: {message}")
        details = message
    QMessageBox.critical(parent, title, details)


def show_warning_error(
    parent: QWidget | None,
    title: str,
    message: str,
    *,
    exc: Exception | None = None,
) -> None:
    """Show a warning dialog and log details for diagnostics."""
    if exc is not None:
        mapped = map_exception_to_user_message(exc)
        _logger.warning(f"{title}: {message}: {exc}")
        details = f"{message}\n{mapped}"
    else:
        _logger.warning(f"{title}: {message}")
        details = message
    QMessageBox.warning(parent, title, details)
