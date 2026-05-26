"""Question pool picker dialog for quiz generation.

Allows selecting candidate questions by:
- all questions
- chapter filter
- question type filter
- manual checkbox selection
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.database.models import Question
from ui.facades.question_bank_facade import QuestionBankFacade
from modules.quiz_builder.quota_allocator import chapter_key
from ui.styles import apply_checkbox_style

_TYPE_LABEL = {
    "MC": "MC",
    "MA": "MA",
    "BLANK": "Blank",
    "SA": "SA",
}


@dataclass(frozen=True)
class QuestionPoolSelection:
    question_ids: list[int]
    selected_count: int


class QuestionPoolPickerDialog(QDialog):
    """Dialog to choose candidate question ids for quiz generation."""

    def __init__(
        self,
        bank_id: int,
        *,
        initial_ids: list[int] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._bank_id = bank_id
        self._initial_ids = set(initial_ids or [])
        self._facade = QuestionBankFacade()
        self._questions: list[Question] = []

        self.setWindowTitle("Chọn pool câu hỏi")
        self.setMinimumSize(860, 540)
        self._build_ui()
        self._load_questions()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        top = QHBoxLayout()
        self._select_all_cb = QCheckBox("Chọn tất cả theo bộ lọc")
        apply_checkbox_style(self._select_all_cb)
        self._select_all_cb.stateChanged.connect(self._on_select_all_changed)
        top.addWidget(self._select_all_cb)

        top.addWidget(QLabel("Chương:"))
        self._chapter_filter = QComboBox()
        self._chapter_filter.addItem("Tất cả", userData=None)
        self._chapter_filter.currentIndexChanged.connect(self._populate_table)
        top.addWidget(self._chapter_filter)

        top.addWidget(QLabel("Loại:"))
        self._type_filter = QComboBox()
        self._type_filter.addItem("Tất cả", userData=None)
        self._type_filter.addItem("MC", userData="MC")
        self._type_filter.addItem("MA", userData="MA")
        self._type_filter.addItem("Blank", userData="BLANK")
        self._type_filter.addItem("SA", userData="SA")
        self._type_filter.currentIndexChanged.connect(self._populate_table)
        top.addWidget(self._type_filter)

        top.addStretch()

        self._selected_label = QLabel("Đã chọn: 0")
        top.addWidget(self._selected_label)

        root.addLayout(top)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Chọn", "ID", "Mã", "Nội dung", "Chương", "Loại", "Độ khó"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnWidth(0, 60)
        self._table.setColumnWidth(1, 56)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(4, 140)
        self._table.setColumnWidth(5, 80)
        self._table.setColumnWidth(6, 80)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._table, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Áp dụng")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_questions(self) -> None:
        self._questions = self._facade.list_questions(
            bank_id=self._bank_id,
            search="",
            question_type=None,
            difficulty=None,
        )

        chapters = sorted({chapter_key(q.category) for q in self._questions})
        self._chapter_filter.blockSignals(True)
        for chap in chapters:
            self._chapter_filter.addItem(chap, userData=chap)
        self._chapter_filter.blockSignals(False)
        self._populate_table()

    def _filtered_questions(self) -> list[Question]:
        chapter = self._chapter_filter.currentData()
        qtype = self._type_filter.currentData()

        result: list[Question] = []
        for q in self._questions:
            if chapter and chapter_key(q.category) != chapter:
                continue
            if qtype and q.question_type != qtype:
                continue
            result.append(q)
        return result

    def _populate_table(self) -> None:
        filtered = self._filtered_questions()
        self._table.blockSignals(True)
        self._table.setRowCount(len(filtered))

        selected_count = 0
        for row, q in enumerate(filtered):
            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            checked = q.id in self._initial_ids or not self._initial_ids
            check_item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            check_item.setData(Qt.ItemDataRole.UserRole, q.id)
            self._table.setItem(row, 0, check_item)

            if checked:
                selected_count += 1

            self._table.setItem(row, 1, _cell(str(q.id), center=True))
            self._table.setItem(row, 2, _cell(q.question_code or ""))
            self._table.setItem(row, 3, _cell((q.content or "")[:140]))
            self._table.setItem(row, 4, _cell(chapter_key(q.category)))
            self._table.setItem(row, 5, _cell(_TYPE_LABEL.get(q.question_type, q.question_type), center=True))
            self._table.setItem(row, 6, _cell((q.difficulty or "").capitalize(), center=True))

        self._table.blockSignals(False)
        self._selected_label.setText(f"Đã chọn: {selected_count}")

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        self._selected_label.setText(f"Đã chọn: {len(self.selected_question_ids())}")

    def _on_select_all_changed(self, _state: int) -> None:
        checked = self._select_all_cb.isChecked()
        self._table.blockSignals(True)
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._table.blockSignals(False)
        self._selected_label.setText(f"Đã chọn: {len(self.selected_question_ids())}")

    def selected_question_ids(self) -> list[int]:
        ids: list[int] = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                qid = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(qid, int):
                    ids.append(qid)
        return ids

    def selection(self) -> QuestionPoolSelection:
        ids = self.selected_question_ids()
        return QuestionPoolSelection(question_ids=ids, selected_count=len(ids))

    def _on_accept(self) -> None:
        if not self.selected_question_ids():
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng chọn ít nhất 1 câu hỏi.")
            return
        self.accept()


def _cell(text: str, *, center: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if center:
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item
