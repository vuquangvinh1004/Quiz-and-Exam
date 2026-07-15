"""Shared helpers and labels for QuestionBankView."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

_TYPE_LABEL = {
    "MC": "Trắc nghiệm 1 đáp án",
    "MA": "Trắc nghiệm nhiều đáp án",
    "TF": "Đúng/Sai",
    "BLANK": "Điền vào chỗ trống",
    "SA": "Trả lời ngắn",
    "CRQ": "CRQ",
    "ES": "CRQ - Tự luận",
    "PR": "CRQ - Bài toán",
}
_TYPE_TABLE_LABEL = {
    "MC": "MC",
    "MA": "MA",
    "TF": "T/F",
    "BLANK": "Blank",
    "SA": "SA",
    "ES": "ES",
    "PR": "PR",
}
_QUESTION_LEVELS: tuple[str, ...] = ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo")
_LEGACY_DIFFICULTY_TO_LEVEL: dict[str, str] = {"easy": "Nhớ", "medium": "Hiểu", "hard": "Vận dụng"}


def cell(text: str, center: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if center:
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item
