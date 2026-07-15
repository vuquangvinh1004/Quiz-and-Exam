"""Layout and bank/picker wiring for QuizBuilderView."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs.question_pool_picker_dialog import QuestionPoolPickerDialog
from ui.styles import apply_checkbox_style
from ui.views.quiz_builder_shared import wrap_layout
from ui.widgets.bank_combo import BankCombo
from ui.widgets.exam_export_panel import ExamExportPanel


class QuizBuilderLayoutMixin:
    """UI construction and bank-selection plumbing."""

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel("Tạo bài kiểm tra")
        title_lbl.setObjectName("view_title")
        outer.addWidget(title_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        root = QVBoxLayout(content)
        root.setContentsMargins(20, 12, 20, 20)
        root.setSpacing(14)

        root.addWidget(self._build_basic_group())
        root.addWidget(self._build_quota_group())

        self._export_panel = ExamExportPanel(self._selector, self._get_selection_state)
        root.addWidget(self._export_panel)
        root.addStretch()

        self._load_banks()

    def _build_basic_group(self) -> QGroupBox:
        box = QGroupBox("Thông tin tạo đề")
        form = QFormLayout(box)

        self._bank_combo = BankCombo()
        self._bank_combo.currentIndexChanged.connect(self._update_available_count)
        self._bank_combo.currentIndexChanged.connect(self._on_bank_changed)
        form.addRow("Ngân hàng *:", self._bank_combo)

        self._exam_count_spin = QSpinBox()
        self._exam_count_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._exam_count_spin.setRange(1, 100)
        self._exam_count_spin.setValue(1)
        self._exam_count_spin.setMinimumWidth(120)
        form.addRow("Số đề cần tạo:", self._exam_count_spin)

        self._count_spin = QSpinBox()
        self._count_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._count_spin.setRange(1, 500)
        self._count_spin.setValue(10)
        self._count_spin.setMinimumWidth(120)
        self._count_spin.hide()
        self._count_spin.valueChanged.connect(self._on_count_changed)

        self._available_lbl = QLabel("(sẵn có: 0 câu)")
        self._available_lbl.setObjectName("muted_label")

        self._duration_spin = QSpinBox()
        self._duration_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._duration_spin.setRange(0, 999)
        self._duration_spin.setValue(30)
        self._duration_spin.setSuffix(" phút")
        self._duration_spin.setMinimumWidth(120)
        form.addRow("Thời lượng đề:", self._duration_spin)

        pool_row = QHBoxLayout()
        pool_row.setContentsMargins(0, 0, 0, 0)
        self._pool_btn = QPushButton("Chọn bộ câu hỏi")
        self._pool_btn.clicked.connect(self._open_pool_picker)
        pool_row.addWidget(self._pool_btn)

        self._pool_summary = QLabel("Đang dùng: tất cả câu hỏi trong bộ chọn")
        self._pool_summary.setObjectName("muted_label")
        pool_row.addWidget(self._pool_summary)
        pool_row.addStretch()
        form.addRow("Bộ câu hỏi:", wrap_layout(pool_row))

        misc_row = QHBoxLayout()
        misc_row.setContentsMargins(0, 0, 0, 0)
        self._cb_shuffle_q = QCheckBox("Trộn thứ tự câu")
        self._cb_shuffle_q.setChecked(True)
        self._cb_shuffle_opts = QCheckBox("Trộn đáp án (trắc nghiệm/đúng-sai)")
        self._cb_shuffle_opts.setChecked(True)
        self._cb_no_repeat_between_exams = QCheckBox("Không lặp câu giữa các đề")
        self._cb_no_repeat_between_exams.setChecked(False)
        apply_checkbox_style(
            self._cb_shuffle_q,
            self._cb_shuffle_opts,
            self._cb_no_repeat_between_exams,
        )
        misc_row.addWidget(self._cb_shuffle_q)
        misc_row.addWidget(self._cb_shuffle_opts)
        misc_row.addWidget(self._cb_no_repeat_between_exams)
        misc_row.addStretch()
        form.addRow("Tùy chọn:", wrap_layout(misc_row))
        return box

    def _build_quota_group(self) -> QGroupBox:
        box = QGroupBox("Hạn mức (quota) cho mỗi đề")
        layout = QVBoxLayout(box)

        help_lbl = QLabel(
            "Chỉ xét các quota bạn nhập (CLO / Chương / Loại). "
            "Bảng quota để trống sẽ được bỏ qua; tổng quota của mỗi bảng không được vượt số câu mỗi đề."
        )
        help_lbl.setWordWrap(True)
        help_lbl.setObjectName("muted_label")
        layout.addWidget(help_lbl)

        self._quota_note = QLabel(
            "Lưu ý: nếu không chọn checkbox quota nào, toàn bộ câu hỏi đã chọn trong bộ lọc ở popup "
            "\"Chọn bộ câu hỏi\" sẽ được đưa vào đề thi."
        )
        self._quota_note.setWordWrap(True)
        self._quota_note.setStyleSheet("color: #c0392b; font-weight: 600;")
        layout.addWidget(self._quota_note)

        toggles_row = QHBoxLayout()
        toggles_row.setContentsMargins(0, 0, 0, 0)
        self._quota_cb_clo = QCheckBox("Lập hạn mức theo CLO")
        self._quota_cb_chapter = QCheckBox("Lập hạn mức theo Chương")
        self._quota_cb_type = QCheckBox("Lập hạn mức theo Loại")
        self._quota_cb_clo.setChecked(False)
        self._quota_cb_chapter.setChecked(False)
        self._quota_cb_type.setChecked(False)
        apply_checkbox_style(
            self._quota_cb_clo,
            self._quota_cb_chapter,
            self._quota_cb_type,
        )
        self._quota_cb_clo.stateChanged.connect(self._on_quota_mode_changed)
        self._quota_cb_chapter.stateChanged.connect(self._on_quota_mode_changed)
        self._quota_cb_type.stateChanged.connect(self._on_quota_mode_changed)
        toggles_row.addWidget(self._quota_cb_clo)
        toggles_row.addWidget(self._quota_cb_chapter)
        toggles_row.addWidget(self._quota_cb_type)
        toggles_row.addStretch()
        layout.addLayout(toggles_row)

        self._clo_table = self._build_clo_quota_table()
        self._chapter_table = self._build_quota_table()
        self._type_table = self._build_type_quota_table()

        tables_row = QHBoxLayout()
        tables_row.setSpacing(8)
        self._clo_table_wrap = self._wrap_quota_table("Theo CLO", self._clo_table)
        self._chapter_table_wrap = self._wrap_quota_table("Theo Chương", self._chapter_table)
        self._type_table_wrap = self._wrap_quota_table("Theo Loại", self._type_table)
        tables_row.addWidget(self._clo_table_wrap, stretch=2)
        tables_row.addWidget(self._chapter_table_wrap, stretch=1)
        tables_row.addWidget(self._type_table_wrap, stretch=1)
        layout.addLayout(tables_row)

        self._quota_group_enabled = {
            "clo": self._quota_cb_clo,
            "chapter": self._quota_cb_chapter,
            "type": self._quota_cb_type,
        }
        self._on_quota_mode_changed()

        return box

    def _build_quota_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Chương", "Sẵn có", "Số lượng", "Tỷ lệ"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setColumnWidth(0, 108)
        table.setColumnWidth(1, 62)
        table.setColumnWidth(2, 82)
        table.setColumnWidth(3, 70)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setMinimumHeight(235)
        table.setMaximumHeight(285)
        return table

    def _build_clo_quota_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["CLO", "Mức độ", "Sẵn có", "Số lượng", "Tỷ lệ"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setColumnWidth(0, 116)
        table.setColumnWidth(1, 92)
        table.setColumnWidth(2, 62)
        table.setColumnWidth(3, 82)
        table.setColumnWidth(4, 70)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        table.setMinimumHeight(235)
        table.setMaximumHeight(285)
        return table

    def _build_type_quota_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Loại", "Sẵn có", "Số lượng", "Tỷ lệ"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setColumnWidth(0, 108)
        table.setColumnWidth(1, 62)
        table.setColumnWidth(2, 82)
        table.setColumnWidth(3, 70)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setMinimumHeight(235)
        table.setMaximumHeight(285)
        return table

    def _wrap_quota_table(self, title: str, table: QTableWidget) -> QFrame:
        container = QFrame()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)
        header = QLabel(title)
        header.setStyleSheet("font-weight: 600;")
        vl.addWidget(header)
        vl.addWidget(table)
        return container

    def _load_banks(self) -> None:
        self._bank_combo.reload()
        self._on_bank_changed()

    def _on_bank_changed(self) -> None:
        self._selected_question_ids = []
        self._pool_summary.setText("Đang dùng: tất cả câu hỏi trong bộ chọn")

        data = self._bank_combo.currentData(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            self._export_panel.autofill_from_bank(data)

        self._update_available_count()

    def _on_count_changed(self) -> None:
        self._refresh_quota_warnings()

    def _current_bank_id(self) -> int | None:
        return self._bank_combo.current_bank_id()

    def _eligible_questions(self) -> list:
        bank_id = self._current_bank_id()
        if bank_id is None:
            return []
        return self._builder_facade.list_eligible_questions(
            bank_id=bank_id,
            question_types=None,
            difficulties=None,
            candidate_question_ids=self._selected_question_ids or None,
            active_only=True,
            shuffle=False,
        )

    def _update_available_count(self) -> None:
        try:
            questions = self._eligible_questions()
        except Exception:
            questions = []

        available = len(questions)
        self._available_lbl.setText(f"(sẵn có: {available} câu)")

        self._reload_chapter_quota_rows(questions)
        self._sync_quota_availability(questions)
        self._refresh_quota_warnings(questions)

    def _on_quota_mode_changed(self, _state: int | None = None) -> None:
        clo_enabled = self._quota_cb_clo.isChecked()
        chapter_enabled = self._quota_cb_chapter.isChecked()
        type_enabled = self._quota_cb_type.isChecked()

        self._clo_table_wrap.setVisible(clo_enabled)
        self._chapter_table_wrap.setVisible(chapter_enabled)
        self._type_table_wrap.setVisible(type_enabled)

        self._refresh_quota_warnings()

    def _open_pool_picker(self) -> None:
        bank_id = self._current_bank_id()
        if bank_id is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ngân hàng.")
            return

        dlg = QuestionPoolPickerDialog(
            bank_id,
            initial_ids=self._selected_question_ids,
            parent=self,
        )
        if dlg.exec() != QuestionPoolPickerDialog.DialogCode.Accepted:
            return

        selection = dlg.selection()
        self._selected_question_ids = selection.question_ids
        self._pool_summary.setText(f"Đang dùng: {selection.selected_count} câu hỏi đã chọn")
        self._update_available_count()
