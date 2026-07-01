"""Màn tạo bài kiểm tra cho cấu hình đề và xuất theo quota."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.domain.services.quiz_service import QuizCreationSnapshot
from modules.quiz_builder.quota_allocator import (
    build_inventory,
    chapter_key,
)
from modules.quiz_builder.selector import QuestionSelector
from ui.dialogs.question_pool_picker_dialog import QuestionPoolPickerDialog
from ui.facades.quiz_builder_facade import QuizBuilderFacade
from ui.styles import apply_checkbox_style
from ui.views.quiz_builder_quota_support import refresh_quota_warnings, sync_quota_availability
from ui.widgets.bank_combo import BankCombo
from ui.widgets.exam_export_panel import ExamExportPanel, ExportSelectionState

_DIFFICULTY_LEVEL_ORDER = ("Nhớ", "Hiểu", "Vận dụng", "Phân tích", "Đánh giá", "Sáng tạo")
_TYPE_SHORT_LABELS = {
    "MC": "MC",
    "MA": "MA",
    "TF": "T/F",
    "BLANK": "Blank",
    "SA": "SA",
    "ES": "ES",
}


def _wrap_layout(layout) -> QWidget:
    widget = QWidget()
    widget.setLayout(layout)
    return widget


def _center_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _short_type_label(code: str) -> str:
    return _TYPE_SHORT_LABELS.get(code, code)


class QuizBuilderView(QWidget):
    """Exam generation and export view."""

    # Kept for backward-compat with smoke tests and legacy wiring.
    quiz_started = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selector = QuestionSelector()
        self._builder_facade = QuizBuilderFacade(self._selector)
        self._selected_question_ids: list[int] = []

        self._chapter_spins: dict[str, QSpinBox] = {}
        self._type_spins: dict[str, QSpinBox] = {}
        self._clo_spins: dict[tuple[str, str], QSpinBox] = {}
        self._chapter_available: dict[str, QTableWidgetItem] = {}
        self._type_available: dict[str, QTableWidgetItem] = {}
        self._clo_available: dict[tuple[str, str], QTableWidgetItem] = {}
        self._chapter_ratio: dict[str, QTableWidgetItem] = {}
        self._type_ratio: dict[str, QTableWidgetItem] = {}
        self._clo_ratio: dict[tuple[str, str], QTableWidgetItem] = {}
        self._quota_group_enabled: dict[str, QCheckBox] = {}

        self._build_ui()

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
        form.addRow("Bộ câu hỏi:", _wrap_layout(pool_row))

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
        form.addRow("Tùy chọn:", _wrap_layout(misc_row))
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

    def _reload_chapter_quota_rows(self, questions: list) -> None:
        old_values = {name: spin.value() for name, spin in self._chapter_spins.items()}
        self._chapter_spins.clear()
        self._chapter_available.clear()
        self._chapter_ratio.clear()
        self._chapter_table.setRowCount(0)

        inv = build_inventory(questions)
        chapters = sorted({chapter_key(q.category) for q in questions})
        for chap in chapters:
            spin, available_item = self._append_quota_row(
                self._chapter_table,
                chap,
                available=inv.by_chapter.get(chap, 0),
            )
            spin.setValue(min(old_values.get(chap, 0), spin.maximum()))
            self._chapter_spins[chap] = spin
            self._chapter_available[chap] = available_item

        self._reload_type_quota_rows(questions)
        self._reload_clo_quota_rows(questions)

    def _reload_type_quota_rows(self, questions: list) -> None:
        old_values = {key: spin.value() for key, spin in self._type_spins.items()}
        self._type_spins.clear()
        self._type_available.clear()
        self._type_ratio.clear()
        self._type_table.setRowCount(0)

        inv = build_inventory(questions)
        type_order = ("MC", "MA", "TF", "BLANK", "SA", "ES")
        for qtype in type_order:
            available = inv.by_type.get(qtype, 0)
            if available <= 0:
                continue
            spin, available_item = self._append_quota_row(
                self._type_table,
                _short_type_label(qtype),
                available=available,
            )
            spin.setValue(min(old_values.get(qtype, 0), spin.maximum()))
            self._type_spins[qtype] = spin
            self._type_available[qtype] = available_item

    def _reload_clo_quota_rows(self, questions: list) -> None:
        old_values = {key: spin.value() for key, spin in self._clo_spins.items()}
        self._clo_spins.clear()
        self._clo_available.clear()
        self._clo_ratio.clear()
        self._clo_table.setRowCount(0)

        inv = build_inventory(questions)
        clo_rows = sorted(
            inv.by_clo.items(),
            key=lambda item: (item[0][0].lower(), _DIFFICULTY_LEVEL_ORDER.index(item[0][1]) if item[0][1] in _DIFFICULTY_LEVEL_ORDER else len(_DIFFICULTY_LEVEL_ORDER), item[0][1].lower()),
        )
        for (clo, level), available in clo_rows:
            spin, available_item = self._append_clo_quota_row(
                self._clo_table,
                clo,
                level,
                available=available,
            )
            spin.setValue(min(old_values.get((clo, level), 0), spin.maximum()))
            self._clo_spins[(clo, level)] = spin
            self._clo_available[(clo, level)] = available_item

    def _append_quota_row(
        self,
        table: QTableWidget,
        label: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, _center_item(label))

        available_item = QTableWidgetItem(str(available))
        available_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        available_item.setFlags(available_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 1, available_item)

        spin = QSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setRange(0, max(0, available))
        spin.setFixedWidth(56)
        spin.setFixedHeight(30)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.valueChanged.connect(self._refresh_quota_warnings)
        table.setCellWidget(row, 2, spin)
        ratio_item = _center_item("0.0%")
        table.setItem(row, 3, ratio_item)
        return spin, available_item

    def _append_clo_quota_row(
        self,
        table: QTableWidget,
        clo: str,
        level: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, _center_item(clo))
        table.setItem(row, 1, _center_item(level))

        available_item = QTableWidgetItem(str(available))
        available_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        available_item.setFlags(available_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 2, available_item)

        spin = QSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setRange(0, max(0, available))
        spin.setFixedWidth(56)
        spin.setFixedHeight(30)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.valueChanged.connect(self._refresh_quota_warnings)
        table.setCellWidget(row, 3, spin)
        ratio_item = _center_item("0.0%")
        table.setItem(row, 4, ratio_item)
        return spin, available_item

    def _append_type_quota_row(
        self,
        table: QTableWidget,
        label: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        return self._append_quota_row(table, label, available=available)

    def _sync_quota_availability(self, questions: list[Question]) -> None:
        sync_quota_availability(self, questions)

    def _quota_dict(self, source: dict) -> dict:
        return {
            key: spin.value()
            for key, spin in source.items()
            if spin.value() > 0
        }

    def _active_quota_dict(self, source: dict, enabled: bool) -> dict:
        return self._quota_dict(source) if enabled else {}

    @staticmethod
    def _ratio_text(value: int, total: int) -> str:
        if total <= 0:
            return "0.0%"
        return f"{(value / total) * 100:.1f}%"

    def _update_quota_ratios(self) -> None:
        total = max(1, self._count_spin.value())

        for row in range(self._chapter_table.rowCount()):
            spin = self._chapter_table.cellWidget(row, 2)
            item = self._chapter_table.item(row, 3)
            if isinstance(spin, QSpinBox) and item is not None:
                item.setText(self._ratio_text(spin.value(), total))

        for row in range(self._type_table.rowCount()):
            spin = self._type_table.cellWidget(row, 2)
            item = self._type_table.item(row, 3)
            if isinstance(spin, QSpinBox) and item is not None:
                item.setText(self._ratio_text(spin.value(), total))

        for row in range(self._clo_table.rowCount()):
            spin = self._clo_table.cellWidget(row, 3)
            item = self._clo_table.item(row, 4)
            if isinstance(spin, QSpinBox) and item is not None:
                item.setText(self._ratio_text(spin.value(), total))

    def _total_questions_from_quota(self) -> int:
        active_totals: list[int] = []
        if self._quota_cb_chapter.isChecked():
            active_totals.append(sum(self._chapter_spins[chap].value() for chap in self._chapter_spins))
        if self._quota_cb_type.isChecked():
            active_totals.append(sum(self._type_spins[qtype].value() for qtype in self._type_spins))
        if self._quota_cb_clo.isChecked():
            active_totals.append(sum(self._clo_spins[key].value() for key in self._clo_spins))

        if active_totals:
            return max(1, max(active_totals))
        try:
            return max(1, len(self._eligible_questions()))
        except Exception:
            return max(1, self._count_spin.value())

    def _sync_total_question_count(self) -> None:
        total = self._total_questions_from_quota()
        if self._count_spin.value() != total:
            self._count_spin.blockSignals(True)
            self._count_spin.setValue(total)
            self._count_spin.blockSignals(False)

    def _build_creation_snapshots(self, questions: list) -> list[QuizCreationSnapshot]:
        """Keep typed create-quiz snapshot contract available at the view boundary."""
        return self._selector.build_creation_snapshots(
            questions,
            shuffle_options=self._cb_shuffle_opts.isChecked(),
        )

    def _clear_spin_warning(self, spin: QSpinBox) -> None:
        spin.setStyleSheet("")

    def _mark_spin_warning(self, spin: QSpinBox) -> None:
        spin.setStyleSheet(
            "QSpinBox { background-color: #f8d7da; }"
            "QSpinBox QLineEdit { background-color: #f8d7da; }"
        )

    def _refresh_quota_warnings(self, value_or_questions: object | None = None) -> None:
        self._sync_total_question_count()
        self._update_quota_ratios()
        refresh_quota_warnings(self, value_or_questions)

    def _get_selection_state(self) -> ExportSelectionState:
        return ExportSelectionState(
            bank_id=self._current_bank_id(),
            exam_count=self._exam_count_spin.value(),
            question_count=self._total_questions_from_quota(),
            candidate_question_ids=list(self._selected_question_ids),
            chapter_quota=self._active_quota_dict(self._chapter_spins, self._quota_cb_chapter.isChecked()),
            type_quota=self._active_quota_dict(self._type_spins, self._quota_cb_type.isChecked()),
            clo_quota=self._active_quota_dict(self._clo_spins, self._quota_cb_clo.isChecked()),
            shuffle_questions=self._cb_shuffle_q.isChecked(),
            shuffle_options=self._cb_shuffle_opts.isChecked(),
            no_repeat_between_exams=self._cb_no_repeat_between_exams.isChecked(),
            time_limit_minutes=self._duration_spin.value(),
        )

    def refresh(self) -> None:
        self._load_banks()
