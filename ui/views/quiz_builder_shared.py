"""Shared constants and tiny helpers for QuizBuilderView."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QTableWidgetItem


_DIFFICULTY_LEVEL_ORDER = ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo")
_TYPE_SHORT_LABELS = {
    "MC": "MC",
    "MA": "MA",
    "TF": "T/F",
    "BLANK": "Blank",
    "SA": "SA",
    "ES": "ES",
    "PR": "PR",
}


def wrap_layout(layout) -> QWidget:
    widget = QWidget()
    widget.setLayout(layout)
    return widget


def center_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def short_type_label(code: str) -> str:
    return _TYPE_SHORT_LABELS.get(code, code)
