"""Question pool picker dialog for quiz generation.

Allows selecting candidate questions by:
- all questions
- chapter filter
- question type filter
- difficulty filter
- manual checkbox selection
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QFrame,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database.models import Question
from modules.quiz_builder.quota_allocator import chapter_key
from ui.facades.question_bank_facade import QuestionBankFacade
from ui.styles import apply_checkbox_style

_TYPE_LABEL = {
    "MC": "MC",
    "MA": "MA",
    "TF": "T/F",
    "BLANK": "Blank",
    "SA": "SA",
    "ES": "ES",
    "PR": "PR",
}

_TYPE_ORDER = ("MC", "MA", "TF", "BLANK", "SA", "ES", "PR")

_DIFFICULTY_LABELS = ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo")
_DIFFICULTY_MAP = {
    "easy": "Nhớ",
    "medium": "Hiểu",
    "hard": "Vận dụng",
    "Nhớ": "Nhớ",
    "Hiểu": "Hiểu",
    "Vận dụng": "Vận dụng",
    "Phân tích": "Phân tích",
    "Đánh giá": "Đánh giá",
    "Sáng tạo": "Sáng tạo",
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
        self._selected_ids = set(initial_ids or [])
        self._select_all_initial = not self._selected_ids
        self._facade = QuestionBankFacade()
        self._questions: list[Question] = []

        self.setWindowTitle("Chọn bộ câu hỏi")
        self.setMinimumSize(860, 540)
        self._build_ui()
        self._load_questions()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(8, 6, 8, 8)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addStretch()

        self._selected_label = QLabel("Đã chọn: 0")
        top.addWidget(self._selected_label)

        root.addLayout(top)

        self._chapter_filters = {}
        self._clo_filters = {}
        self._difficulty_filters = {}
        self._type_filters = {}

        filters_box = QFrame()
        filters_box.setFrameShape(QFrame.Shape.NoFrame)
        filters_box.setObjectName("question_filters_box")
        filters_box.setStyleSheet(
            "#question_filters_box, #question_filters_box QTableWidget { border: none; background: transparent; }"
            "#question_filters_box QTableWidget::item { border: none; padding: 0px; }"
        )
        self._filters_table = QTableWidget(4, 2)
        self._filters_table.setObjectName("question_filters_table")
        self._filters_table.setShowGrid(False)
        self._filters_table.setFrameShape(QFrame.Shape.NoFrame)
        self._filters_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._filters_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._filters_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._filters_table.horizontalHeader().setVisible(False)
        self._filters_table.verticalHeader().setVisible(False)
        self._filters_table.horizontalHeader().setStretchLastSection(False)
        self._filters_table.verticalHeader().setDefaultSectionSize(30)
        self._filters_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._filters_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._filters_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._filters_table.setColumnWidth(0, 118)
        self._filters_table.setColumnWidth(1, 16)
        self._filters_table.setItem(0, 0, _filter_label_item("Chương:"))
        self._filters_table.setItem(1, 0, _filter_label_item("CLO:"))
        self._filters_table.setItem(2, 0, _filter_label_item("Mức độ:"))
        self._filters_table.setItem(3, 0, _filter_label_item("Loại câu hỏi:"))
        filters_layout = QVBoxLayout(filters_box)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(0)
        filters_layout.addWidget(self._filters_table)
        filters_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(filters_box, stretch=0)

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["Chọn", "ID", "Mã", "Nội dung", "Chương", "CLO", "Mức độ", "Loại câu hỏi"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnWidth(0, 60)
        self._table.setColumnWidth(1, 56)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(4, 120)
        self._table.setColumnWidth(5, 120)
        self._table.setColumnWidth(6, 90)
        self._table.setColumnWidth(7, 120)
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
        clos = sorted({(q.learning_outcome_code or "").strip() or "(Chưa gắn CLO)" for q in self._questions})
        levels = sorted(
            {
                _DIFFICULTY_MAP.get(q.difficulty or "", q.difficulty or "")
                for q in self._questions
                if _DIFFICULTY_MAP.get(q.difficulty or "", q.difficulty or "")
            },
            key=lambda lvl: _DIFFICULTY_LABELS.index(lvl) if lvl in _DIFFICULTY_LABELS else 999,
        )
        available_types = sorted(
            {q.question_type for q in self._questions if q.question_type in _TYPE_ORDER},
            key=_TYPE_ORDER.index,
        )
        self._rebuild_filters_table(chapters, clos, levels, available_types)
        self._populate_table()

    def _rebuild_filters_table(
        self,
        chapters: list[str],
        clos: list[str],
        levels: list[str],
        available_types: list[str],
    ) -> None:
        specs = [
            ("Chương:", chapters, "chapter"),
            ("CLO:", clos, "clo"),
            ("Mức độ:", levels, "difficulty"),
            ("Loại câu hỏi:", available_types, "type"),
        ]
        self._type_filters.clear()
        max_options = max((len(values) for _, values, _ in specs), default=0)
        column_count = 2 + max(0, max_options * 2)
        self._filters_table.blockSignals(True)
        self._filters_table.clear()
        self._filters_table.setRowCount(len(specs))
        self._filters_table.setColumnCount(column_count)
        self._filters_table.horizontalHeader().setVisible(False)
        self._filters_table.verticalHeader().setVisible(False)

        label_width = 118
        spacer_width = 16
        checkbox_width = 18
        text_width = 68
        self._filters_table.setColumnWidth(0, label_width)
        self._filters_table.setColumnWidth(1, spacer_width)
        for index in range(max_options):
            cb_col = 2 + index * 2
            text_col = cb_col + 1
            self._filters_table.setColumnWidth(cb_col, checkbox_width)
            self._filters_table.setColumnWidth(text_col, text_width)

        for row, (label, values, kind) in enumerate(specs):
            self._filters_table.setItem(row, 0, _filter_label_item(label))
            target: dict[str, QCheckBox]
            if kind == "chapter":
                target = self._chapter_filters
            elif kind == "clo":
                target = self._clo_filters
            elif kind == "difficulty":
                target = self._difficulty_filters
            else:
                target = self._type_filters

            for index, value in enumerate(values):
                cb_col = 2 + index * 2
                text_col = cb_col + 1
                cb = QCheckBox()
                cb.setChecked(True)
                cb.setFixedWidth(checkbox_width)
                cb.setFixedHeight(24)
                apply_checkbox_style(cb)
                cb.stateChanged.connect(self._on_filter_changed)
                target[value] = cb
                self._filters_table.setCellWidget(row, cb_col, _wrap_right_aligned(cb))

                if kind == "type":
                    text = _TYPE_LABEL.get(value, value)
                else:
                    text = value
                text_item = QTableWidgetItem(text)
                text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                text_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self._filters_table.setItem(row, text_col, text_item)

        for row in range(self._filters_table.rowCount()):
            self._filters_table.setRowHeight(row, 28)
        filter_height = max(4, len(specs)) * 28 + 2
        self._filters_table.setFixedHeight(filter_height)
        parent = self._filters_table.parentWidget()
        if parent is not None:
            parent.setFixedHeight(filter_height)
        self._filters_table.blockSignals(False)

    def _filtered_questions(self) -> list[Question]:
        chapters = {key for key, cb in self._chapter_filters.items() if cb.isChecked()}
        clos = {key for key, cb in self._clo_filters.items() if cb.isChecked()}
        difficulties = {key for key, cb in self._difficulty_filters.items() if cb.isChecked()}
        types = {key for key, cb in self._type_filters.items() if cb.isChecked()}

        result: list[Question] = []
        for q in self._questions:
            qchapter = chapter_key(q.category)
            if chapters and qchapter not in chapters:
                continue
            qclo = (q.learning_outcome_code or "").strip() or "(Chưa gắn CLO)"
            if clos and qclo not in clos:
                continue
            if types and q.question_type not in types:
                continue
            qdiff = _DIFFICULTY_MAP.get(q.difficulty or "", q.difficulty or "")
            if difficulties and qdiff not in difficulties:
                continue
            result.append(q)
        return result

    def _on_filter_changed(self, _state: int) -> None:
        self._populate_table()

    def _populate_table(self) -> None:
        filtered = self._filtered_questions()
        self._table.blockSignals(True)
        self._table.setRowCount(len(filtered))

        for row, q in enumerate(filtered):
            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            checked = q.id in self._selected_ids or self._select_all_initial
            check_item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            check_item.setData(Qt.ItemDataRole.UserRole, q.id)
            self._table.setItem(row, 0, check_item)
            if checked:
                self._selected_ids.add(q.id)

            self._table.setItem(row, 1, _cell(str(q.id), center=True))
            self._table.setItem(row, 2, _cell(q.question_code or ""))
            self._table.setItem(row, 3, _cell((q.content or "")[:140]))
            self._table.setItem(row, 4, _cell(chapter_key(q.category), center=True))
            self._table.setItem(
                row,
                5,
                _cell((q.learning_outcome_code or "").strip() or "(Chưa gắn CLO)", center=True),
            )
            self._table.setItem(
                row,
                6,
                _cell(_DIFFICULTY_MAP.get(q.difficulty or "", q.difficulty or ""), center=True),
            )
            self._table.setItem(
                row,
                7,
                _cell(_TYPE_LABEL.get(q.question_type, q.question_type), center=True),
            )

        self._table.blockSignals(False)
        self._select_all_initial = False
        self._selected_label.setText(f"Đã chọn: {len(self._selected_ids)}")

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        qid = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(qid, int):
            if item.checkState() == Qt.CheckState.Checked:
                self._selected_ids.add(qid)
            else:
                self._selected_ids.discard(qid)
        self._selected_label.setText(f"Đã chọn: {len(self._selected_ids)}")

    def selected_question_ids(self) -> list[int]:
        return sorted(self._selected_ids)

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


def _filter_label_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    font = item.font()
    font.setBold(True)
    item.setFont(font)
    return item


def _wrap_right_aligned(widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addStretch()
    layout.addWidget(widget)
    return container
