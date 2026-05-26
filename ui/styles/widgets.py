"""Reusable style helpers for widgets."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox

CHECKBOX_STYLE_QSS = (
    "QCheckBox { spacing: 7px; font-size: 14px; padding: 2px 0; }"
    "QCheckBox::indicator {"
    " width: 16px; height: 16px;"
    " border: 1px solid #9aa4b2; border-radius: 3px; background: #ffffff;"
    " }"
    "QCheckBox::indicator:hover { border-color: #5f6f85; }"
    "QCheckBox::indicator:checked {"
    " background: #16a34a; border: 1px solid #16a34a;"
    " }"
)


def apply_checkbox_style(*checkboxes: QCheckBox) -> None:
    """Apply unified checkbox style for clear checked/unchecked state."""
    for checkbox in checkboxes:
        checkbox.setStyleSheet(CHECKBOX_STYLE_QSS)
