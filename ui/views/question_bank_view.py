"""Màn Ngân hàng câu hỏi - CRUD cho ngân hàng và câu hỏi, tìm kiếm, lọc."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from core.database.models import Question
from ui.facades.question_bank_facade import QuestionBankFacade
from ui.views.question_bank_actions_mixin import QuestionBankActionsMixin
from ui.views.question_bank_shared import _QUESTION_LEVELS, _TYPE_LABEL


class QuestionBankView(QuestionBankActionsMixin, QWidget):
    """Quản lý ngân hàng câu hỏi - CRUD, tìm kiếm, lọc."""

    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._facade = QuestionBankFacade()
        self._current_bank_id: int | None = None
        self._questions: list[Question] = []
        self._loaded: bool = False
        self._build_ui()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            self._load_banks()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Ngân hàng câu hỏi")
        title.setObjectName("view_title")
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        splitter.addWidget(self._build_bank_panel())
        splitter.addWidget(self._build_question_panel())
        splitter.setSizes([220, 720])

    def _build_bank_panel(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 4, 4, 8)
        vl.setSpacing(6)

        hdr = QLabel("<b>Ngân hàng</b>")
        vl.addWidget(hdr)

        self._bank_list = QListWidget()
        self._bank_list.currentItemChanged.connect(self._on_bank_selected)
        vl.addWidget(self._bank_list, stretch=1)

        btn_hl = QHBoxLayout()
        add_btn = self._make_btn("+ Thêm", "Thêm ngân hàng mới", self._add_bank, 80)
        rename_btn = self._make_btn("Sửa", "Đổi tên ngân hàng", self._rename_bank, 58)
        del_btn = self._make_btn("Xóa", "Xóa ngân hàng", self._delete_bank, 58)
        btn_hl.addWidget(add_btn)
        btn_hl.addWidget(rename_btn)
        btn_hl.addWidget(del_btn)
        btn_hl.addStretch()
        vl.addLayout(btn_hl)
        return w

    def _build_question_panel(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 8, 8)
        vl.setSpacing(6)

        tb_hl = QHBoxLayout()
        tb_hl.addWidget(self._make_btn("+ Thêm câu hỏi", None, self._add_question))
        tb_hl.addWidget(self._make_btn("+ Thêm CRQ", None, self._add_crq))
        tb_hl.addWidget(self._make_btn("Sửa", None, self._edit_question))
        tb_hl.addWidget(self._make_btn("Xóa", None, self._delete_questions))
        refresh_btn = self._make_btn("Cập nhật", "Làm mới dữ liệu ngân hàng và đồng bộ với Tạo bài kiểm tra", self._on_refresh_clicked)
        tb_hl.addWidget(refresh_btn)
        tb_hl.addStretch()
        tb_hl.addWidget(QLabel("🔍"))

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Tìm kiếm câu hỏi…")
        self._search_edit.setMinimumWidth(180)
        self._search_edit.textChanged.connect(self._refresh_questions)

        self._type_filter = QComboBox()
        self._type_filter.addItem("Tất cả loại câu hỏi", userData=None)
        for code, label in _TYPE_LABEL.items():
            self._type_filter.addItem(label, userData=code)
        self._type_filter.currentIndexChanged.connect(self._refresh_questions)

        self._diff_filter = QComboBox()
        self._diff_filter.addItem("Tất cả mức độ", userData=None)
        for level in _QUESTION_LEVELS:
            self._diff_filter.addItem(level, userData=level)
        self._diff_filter.currentIndexChanged.connect(self._refresh_questions)

        tb_hl.addWidget(self._search_edit)
        tb_hl.addWidget(self._type_filter)
        tb_hl.addWidget(self._diff_filter)
        vl.addLayout(tb_hl)

        self._q_table = QTableWidget(0, 9)
        self._q_table.setHorizontalHeaderLabels(
            ["STT", "Mã", "Nội dung", "Chương", "CLO", "Mức độ", "Loại", "Điểm", "Trạng thái"]
        )
        self._q_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._q_table.horizontalHeader().setDefaultSectionSize(90)
        self._q_table.setColumnWidth(0, 44)
        self._q_table.setColumnWidth(1, 82)
        self._q_table.setColumnWidth(3, 78)
        self._q_table.setColumnWidth(4, 96)
        self._q_table.setColumnWidth(5, 82)
        self._q_table.setColumnWidth(6, 84)
        self._q_table.setColumnWidth(7, 54)
        self._q_table.setColumnWidth(8, 100)
        self._q_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._q_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._q_table.setAlternatingRowColors(True)
        self._q_table.setWordWrap(True)
        self._q_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._q_table.verticalHeader().setVisible(False)
        self._q_table.verticalHeader().setDefaultSectionSize(58)
        self._q_table.verticalHeader().setMinimumSectionSize(54)
        self._q_table.horizontalHeader().setSortIndicatorShown(True)
        self._q_table.setSortingEnabled(True)
        self._q_table.doubleClicked.connect(self._edit_question)
        vl.addWidget(self._q_table, stretch=1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("muted_label")
        vl.addWidget(self._status_lbl)
        return w

    def _make_btn(self, text: str, tooltip: str | None, slot, width: int | None = None):
        from PySide6.QtWidgets import QPushButton

        btn = QPushButton(text)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        if width is not None:
            btn.setFixedWidth(width)
        return btn

    def refresh(self) -> None:
        self._load_banks()


__all__ = ["QuestionBankView"]
