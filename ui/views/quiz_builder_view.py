"""Quiz Builder View for exam generation and quota-based export."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QFrame,
    QFormLayout,
    QHeaderView,
    QGroupBox,
    QHBoxLayout,
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

from core.database.models import Question
from core.database.session import get_session
from modules.quiz_builder.quota_allocator import (
    build_inventory,
    chapter_key,
)
from modules.quiz_builder.selector import QuestionSelector
from ui.views.quiz_builder_quota_support import refresh_quota_warnings, sync_quota_availability
from ui.dialogs.question_pool_picker_dialog import QuestionPoolPickerDialog
from ui.styles import apply_checkbox_style
from ui.widgets.bank_combo import BankCombo
from ui.widgets.exam_export_panel import ExamExportPanel, ExportSelectionState


def _wrap_layout(layout) -> QWidget:
    widget = QWidget()
    widget.setLayout(layout)
    return widget


class QuizBuilderView(QWidget):
    """Exam generation and export view."""

    # Kept for backward-compat with smoke tests and legacy wiring.
    quiz_started = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selector = QuestionSelector()
        self._selected_question_ids: list[int] = []

        self._chapter_spins: dict[str, QSpinBox] = {}
        self._type_spins: dict[str, QSpinBox] = {}
        self._difficulty_spins: dict[str, QSpinBox] = {}
        self._chapter_available: dict[str, QTableWidgetItem] = {}
        self._type_available: dict[str, QTableWidgetItem] = {}
        self._difficulty_available: dict[str, QTableWidgetItem] = {}

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
        root.addWidget(self._build_filter_group())
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

        count_row = QHBoxLayout()
        count_row.setContentsMargins(0, 0, 0, 0)
        self._count_spin = QSpinBox()
        self._count_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._count_spin.setRange(1, 500)
        self._count_spin.setValue(10)
        self._count_spin.setMinimumWidth(120)
        self._count_spin.valueChanged.connect(self._on_count_changed)
        count_row.addWidget(self._count_spin)

        self._available_lbl = QLabel("(sẵn có: 0 câu)")
        self._available_lbl.setObjectName("muted_label")
        count_row.addWidget(self._available_lbl)
        count_row.addStretch()
        form.addRow("Số câu mỗi đề:", _wrap_layout(count_row))

        self._duration_spin = QSpinBox()
        self._duration_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._duration_spin.setRange(0, 999)
        self._duration_spin.setValue(30)
        self._duration_spin.setSuffix(" phút")
        self._duration_spin.setMinimumWidth(120)
        form.addRow("Thời lượng đề:", self._duration_spin)

        pool_row = QHBoxLayout()
        pool_row.setContentsMargins(0, 0, 0, 0)
        self._pool_btn = QPushButton("Chọn câu hỏi trong pool")
        self._pool_btn.clicked.connect(self._open_pool_picker)
        pool_row.addWidget(self._pool_btn)

        self._pool_summary = QLabel("Đang dùng: tất cả câu hỏi phù hợp bộ lọc")
        self._pool_summary.setObjectName("muted_label")
        pool_row.addWidget(self._pool_summary)
        pool_row.addStretch()
        form.addRow("Pool câu hỏi:", _wrap_layout(pool_row))
        return box

    def _build_filter_group(self) -> QGroupBox:
        box = QGroupBox("Bộ lọc câu hỏi")
        form = QFormLayout(box)

        type_row = QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        self._cb_mc = QCheckBox("MC")
        self._cb_ma = QCheckBox("MA")
        self._cb_blank = QCheckBox("Blank")
        self._cb_sa = QCheckBox("SA")
        apply_checkbox_style(self._cb_mc, self._cb_ma, self._cb_blank, self._cb_sa)
        for cb in (self._cb_mc, self._cb_ma, self._cb_blank, self._cb_sa):
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_available_count)
            type_row.addWidget(cb)
        type_row.addStretch()
        form.addRow("Loại:", _wrap_layout(type_row))

        diff_row = QHBoxLayout()
        diff_row.setContentsMargins(0, 0, 0, 0)
        self._cb_easy = QCheckBox("Easy")
        self._cb_medium = QCheckBox("Medium")
        self._cb_hard = QCheckBox("Hard")
        apply_checkbox_style(self._cb_easy, self._cb_medium, self._cb_hard)
        for cb in (self._cb_easy, self._cb_medium, self._cb_hard):
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_available_count)
            diff_row.addWidget(cb)
        diff_row.addStretch()
        form.addRow("Độ khó:", _wrap_layout(diff_row))

        misc_row = QHBoxLayout()
        misc_row.setContentsMargins(0, 0, 0, 0)
        self._cb_shuffle_q = QCheckBox("Trộn thứ tự câu")
        self._cb_shuffle_q.setChecked(True)
        self._cb_shuffle_opts = QCheckBox("Trộn đáp án (MC/MA)")
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
            "Chỉ xét các quota bạn nhập (Chương / Loại / Độ khó). "
            "Bảng quota để trống sẽ được bỏ qua; tổng quota của mỗi bảng không được vượt số câu mỗi đề."
        )
        help_lbl.setWordWrap(True)
        help_lbl.setObjectName("muted_label")
        layout.addWidget(help_lbl)

        self._chapter_table = self._build_quota_table()
        self._type_table = self._build_quota_table()
        self._difficulty_table = self._build_quota_table()

        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)
        tables_row.addWidget(self._wrap_quota_table("Theo Chương", self._chapter_table), stretch=1)
        tables_row.addWidget(self._wrap_quota_table("Theo Loại", self._type_table), stretch=1)
        tables_row.addWidget(self._wrap_quota_table("Theo Độ khó", self._difficulty_table), stretch=1)
        layout.addLayout(tables_row)

        self._init_type_quota_rows()
        self._init_difficulty_quota_rows()
        return box

    def _build_quota_table(self) -> QTableWidget:
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Nhóm", "Sẵn có", "Số lượng"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.setColumnWidth(0, 170)
        table.setColumnWidth(1, 90)
        table.setColumnWidth(2, 150)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
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
        self._pool_summary.setText("Đang dùng: tất cả câu hỏi phù hợp bộ lọc")

        data = self._bank_combo.currentData(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            self._export_panel.autofill_from_bank(data)

        self._update_available_count()

    def _on_count_changed(self) -> None:
        self._refresh_quota_warnings()

    def _current_bank_id(self) -> int | None:
        return self._bank_combo.current_bank_id()

    def _selected_types(self) -> list[str]:
        mapping = {
            self._cb_mc: "MC",
            self._cb_ma: "MA",
            self._cb_blank: "BLANK",
            self._cb_sa: "SA",
        }
        return [value for cb, value in mapping.items() if cb.isChecked()]

    def _selected_difficulties(self) -> list[str]:
        mapping = {
            self._cb_easy: "easy",
            self._cb_medium: "medium",
            self._cb_hard: "hard",
        }
        return [value for cb, value in mapping.items() if cb.isChecked()]

    def _eligible_questions(self) -> list[Question]:
        bank_id = self._current_bank_id()
        if bank_id is None:
            return []

        with get_session() as session:
            return self._selector.select(
                session,
                bank_id,
                count=100000,
                question_types=self._selected_types() or None,
                difficulties=self._selected_difficulties() or None,
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
        self._count_spin.setMaximum(max(1, available))

        self._reload_chapter_quota_rows(questions)
        self._sync_quota_availability(questions)
        self._refresh_quota_warnings(questions)

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

    def _init_type_quota_rows(self) -> None:
        for key, label in (
            ("MC", "MC"),
            ("MA", "MA"),
            ("BLANK", "Blank"),
            ("SA", "SA"),
        ):
            spin, available_item = self._append_quota_row(self._type_table, label)
            self._type_spins[key] = spin
            self._type_available[key] = available_item

    def _init_difficulty_quota_rows(self) -> None:
        for key, label in (("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")):
            spin, available_item = self._append_quota_row(self._difficulty_table, label)
            self._difficulty_spins[key] = spin
            self._difficulty_available[key] = available_item

    def _reload_chapter_quota_rows(self, questions: list[Question]) -> None:
        old_values = {name: spin.value() for name, spin in self._chapter_spins.items()}
        self._chapter_spins.clear()
        self._chapter_available.clear()
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

    def _append_quota_row(
        self,
        table: QTableWidget,
        label: str,
        *,
        available: int = 0,
    ) -> tuple[QSpinBox, QTableWidgetItem]:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(label))

        available_item = QTableWidgetItem(str(available))
        available_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        available_item.setFlags(available_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 1, available_item)

        spin = QSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setRange(0, max(0, available))
        spin.setMinimumWidth(140)
        spin.setFixedHeight(30)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.valueChanged.connect(self._refresh_quota_warnings)
        table.setCellWidget(row, 2, spin)
        return spin, available_item

    def _sync_quota_availability(self, questions: list[Question]) -> None:
        sync_quota_availability(self, questions)

    def _quota_dict(self, source: dict[str, QSpinBox]) -> dict[str, int]:
        return {
            key: spin.value()
            for key, spin in source.items()
            if spin.value() > 0
        }

    def _clear_spin_warning(self, spin: QSpinBox) -> None:
        spin.setStyleSheet("")

    def _mark_spin_warning(self, spin: QSpinBox) -> None:
        spin.setStyleSheet(
            "QSpinBox { background-color: #f8d7da; }"
            "QSpinBox QLineEdit { background-color: #f8d7da; }"
        )

    def _refresh_quota_warnings(self, value_or_questions: object | None = None) -> None:
        refresh_quota_warnings(self, value_or_questions)

    def _get_selection_state(self) -> ExportSelectionState:
        return ExportSelectionState(
            bank_id=self._current_bank_id(),
            exam_count=self._exam_count_spin.value(),
            question_count=self._count_spin.value(),
            question_types=self._selected_types(),
            difficulties=self._selected_difficulties(),
            candidate_question_ids=list(self._selected_question_ids),
            chapter_quota=self._quota_dict(self._chapter_spins),
            type_quota=self._quota_dict(self._type_spins),
            difficulty_quota=self._quota_dict(self._difficulty_spins),
            shuffle_questions=self._cb_shuffle_q.isChecked(),
            shuffle_options=self._cb_shuffle_opts.isChecked(),
            no_repeat_between_exams=self._cb_no_repeat_between_exams.isChecked(),
            time_limit_minutes=self._duration_spin.value(),
        )

    def refresh(self) -> None:
        self._load_banks()
