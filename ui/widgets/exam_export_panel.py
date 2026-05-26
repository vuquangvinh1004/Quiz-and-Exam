"""Exam export panel — configures and generates .docx exam files.

Separated from QuizBuilderView so the builder focuses on quiz configuration
while this panel handles document metadata and rendering.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.paths import EXPORTS_DIR
from core.database.session import get_session
from modules.quiz_builder.selector import QuestionSelector
from modules.quiz_exporter.word_renderer import (
    ExamMeta,
    ExportConfig,
    ExportQuestionSnapshot,
    WordRenderer,
    build_output_path,
)
from ui.utils.error_handler import show_critical_error


def _wrap_layout(layout) -> QWidget:
    w = QWidget()
    w.setLayout(layout)
    return w


def _open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


# ---------------------------------------------------------------------------
# Selection state DTO — passed from QuizBuilderView to avoid field coupling
# ---------------------------------------------------------------------------

@dataclass
class ExportSelectionState:
    """Snapshot of the builder's current filter/config state for export."""

    bank_id: int | None
    question_count: int
    question_types: list        # list[str]: MC | MA | BLANK | SA
    difficulties: list          # list[str]: easy | medium | hard
    shuffle_questions: bool
    shuffle_options: bool
    time_limit_minutes: int | None   # None when STUDY mode (no timer)


# ---------------------------------------------------------------------------
# Main panel widget
# ---------------------------------------------------------------------------

_CB_STYLE = (
    "QCheckBox { spacing: 6px; font-size: 14px; padding: 2px 0; }"
    "QCheckBox::indicator {"
    "  width: 12px; height: 12px;"
    "  border: 2px solid #888;"
    "  border-radius: 2px;"
    "  background: #fff;"
    "}"
    "QCheckBox::indicator:checked {"
    "  background: #2468a8;"
    "  border-color: #2468a8;"
    "  image: none;"
    "}"
    "QCheckBox::indicator:unchecked:hover { border-color: #2468a8; }"
)


class ExamExportPanel(QGroupBox):
    """Exam metadata form + export-to-docx action.

    Receives a *get_selection_state* callback from the parent builder so it
    can read the current question count/filter without coupling to parent
    widget fields.
    """

    def __init__(
        self,
        selector: QuestionSelector,
        get_selection_state: Callable[[], ExportSelectionState],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("📄 Xuất đề thi (.docx)", parent)
        self.setStyleSheet("QGroupBox { font-weight: bold; }")
        self._selector = selector
        self._get_selection_state = get_selection_state
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        exp_form = QFormLayout(self)
        exp_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self._exp_school = QLineEdit()
        self._exp_school.setPlaceholderText("Ví dụ: Trường ĐH Công nghệ Sài Gòn")
        exp_form.addRow("Trường:", self._exp_school)

        self._exp_department = QLineEdit()
        self._exp_department.setPlaceholderText("Ví dụ: Khoa Kinh tế - Quản trị")
        exp_form.addRow("Khoa / Đơn vị:", self._exp_department)

        self._exp_instructor = QLineEdit()
        self._exp_instructor.setPlaceholderText("Ví dụ: Nguyễn Văn A")
        exp_form.addRow("Cán bộ giảng dạy:", self._exp_instructor)

        self._exp_subject = QLineEdit()
        self._exp_subject.setPlaceholderText("Ví dụ: Nhập môn Quản lý chuỗi cung ứng")
        exp_form.addRow("Môn học:", self._exp_subject)

        self._exp_course_code = QLineEdit()
        self._exp_course_code.setPlaceholderText("Ví dụ: SCM001")
        exp_form.addRow("Mã học phần:", self._exp_course_code)

        self._exp_title = QLineEdit()
        self._exp_title.setPlaceholderText("Ví dụ: Bài kiểm tra giữa kỳ")
        exp_form.addRow("Tiêu đề bài thi *:", self._exp_title)

        self._exp_exam_type = QComboBox()
        self._exp_exam_type.addItem("Trắc nghiệm")
        self._exp_exam_type.addItem("Trắc nghiệm + Tự luận")
        exp_form.addRow("Hình thức thi:", self._exp_exam_type)

        self._exp_numbering = QComboBox()
        self._exp_numbering.addItem("Đánh số liên tục toàn bài", "global")
        self._exp_numbering.addItem("Đánh số lại theo từng phần", "per_section")
        exp_form.addRow("Đánh số câu hỏi:", self._exp_numbering)

        self._exp_group_by_type = QCheckBox("Phân nhóm theo loại câu (Phần A, B, C…)")
        self._exp_group_by_type.setChecked(True)
        exp_form.addRow("", self._exp_group_by_type)

        self._exp_cb_instructions = QCheckBox("Kèm hướng dẫn làm bài")
        self._exp_cb_instructions.setChecked(True)
        self._exp_cb_answer_sheet = QCheckBox("Kèm phiếu trả lời")
        self._exp_cb_answer_sheet.setChecked(True)
        self._exp_cb_scoring = QCheckBox("Kèm quy định chấm điểm")
        self._exp_cb_scoring.setChecked(True)
        self._exp_cb_answer_key = QCheckBox("Kèm đáp án và thang điểm")
        self._exp_cb_answer_key.setChecked(True)

        opt_row = QHBoxLayout()
        for cb in (
            self._exp_cb_instructions,
            self._exp_cb_answer_sheet,
            self._exp_cb_scoring,
            self._exp_cb_answer_key,
        ):
            cb.setStyleSheet(_CB_STYLE)
            opt_row.addWidget(cb)
        opt_row.addStretch()
        exp_form.addRow("Tùy chọn:", _wrap_layout(opt_row))

        self._export_btn = QPushButton("📄 Xuất đề thi (.docx)")
        self._export_btn.setFixedHeight(40)
        self._export_btn.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; font-size: 14px; "
            "font-weight: bold; border-radius: 6px; }"
            "QPushButton:hover { background: #1e8449; }"
            "QPushButton:disabled { background: #aaa; }"
        )
        self._export_btn.clicked.connect(self._on_export)
        exp_form.addRow("", self._export_btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def autofill_from_bank(self, bank_data: dict) -> None:
        """Fill form fields from bank metadata when the bank selection changes."""
        self._exp_school.setText(bank_data.get("school", ""))
        self._exp_department.setText(bank_data.get("department", ""))
        self._exp_subject.setText(bank_data.get("subject", ""))
        self._exp_course_code.setText(bank_data.get("course_code", ""))
        self._exp_title.setText(bank_data.get("exam_title", ""))

    def validate_required_fields(self) -> str | None:
        """Return validation error message for required export fields, if any."""
        if not self._exp_title.text().strip():
            return "Vui lòng nhập tiêu đề đề thi."
        return None

    def build_meta(self, *, duration_minutes: int) -> ExamMeta:
        """Build ExamMeta from current form values."""
        return ExamMeta(
            school=self._exp_school.text().strip(),
            department=self._exp_department.text().strip(),
            instructor=self._exp_instructor.text().strip(),
            subject=self._exp_subject.text().strip(),
            course_code=self._exp_course_code.text().strip(),
            exam_title=self._exp_title.text().strip(),
            exam_type=self._exp_exam_type.currentText(),
            duration_minutes=duration_minutes,
        )

    def build_render_config(self) -> ExportConfig:
        """Build ExportConfig from current form values."""
        return ExportConfig(
            show_instructions=self._exp_cb_instructions.isChecked(),
            show_answer_sheet=self._exp_cb_answer_sheet.isChecked(),
            show_scoring_rules=self._exp_cb_scoring.isChecked(),
            show_answer_key=self._exp_cb_answer_key.isChecked(),
            numbering_mode=self._exp_numbering.currentData(),
            group_by_type=self._exp_group_by_type.isChecked(),
            essay_questions=[],
        )

    # ------------------------------------------------------------------
    # Export logic
    # ------------------------------------------------------------------

    def _on_export(self) -> None:
        """Collect config, select questions, render .docx, prompt save path."""
        state = self._get_selection_state()

        if state.bank_id is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ngân hàng câu hỏi.")
            return

        exam_title = self._exp_title.text().strip()
        validation_error = self.validate_required_fields()
        if validation_error:
            QMessageBox.warning(
                self, "Thiếu thông tin", validation_error
            )
            return

        if not state.question_types:
            QMessageBox.warning(self, "Thiếu thông tin", "Chọn ít nhất một loại câu hỏi.")
            return
        if not state.difficulties:
            QMessageBox.warning(self, "Thiếu thông tin", "Chọn ít nhất một mức độ khó.")
            return

        # Select questions
        try:
            with get_session() as session:
                questions_orm = self._selector.select(
                    session,
                    state.bank_id,
                    count=state.question_count,
                    question_types=state.question_types,
                    difficulties=state.difficulties,
                    active_only=True,
                    shuffle=state.shuffle_questions,
                )
                if not questions_orm:
                    QMessageBox.warning(
                        self,
                        "Không đủ câu hỏi",
                        "Không tìm thấy câu hỏi phù hợp với bộ lọc đã chọn.",
                    )
                    return
                snapshots = self._selector.build_snapshots(
                    questions_orm,
                    shuffle_options=state.shuffle_options,
                )
                typed_snapshots = [
                    ExportQuestionSnapshot.from_dict(s) for s in snapshots
                ]
        except Exception as exc:
            show_critical_error(self, "Lỗi", "Không thể lấy câu hỏi.", exc=exc)
            return

        # Essay questions dialog (only for Trắc nghiệm + Tự luận)
        essay_questions: list[dict] = []
        if self._exp_exam_type.currentText() == "Trắc nghiệm + Tự luận":
            dlg = _EssayQuestionsDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            essay_questions = dlg.essay_questions()

        # Build metadata and render config
        meta = self.build_meta(duration_minutes=state.time_limit_minutes or 0)
        meta.exam_title = exam_title
        render_config = self.build_render_config()
        render_config.essay_questions = essay_questions

        # Render
        try:
            renderer = WordRenderer()
            doc = renderer.render(typed_snapshots, meta, render_config)
        except Exception as exc:
            show_critical_error(self, "Lỗi render", "Không thể tạo file Word.", exc=exc)
            return

        # Prompt save path
        default_path = str(build_output_path(exam_title, EXPORTS_DIR))
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu đề thi",
            default_path,
            "Word Document (*.docx)",
        )
        if not save_path:
            return

        try:
            doc.save(save_path)
        except Exception as exc:
            show_critical_error(self, "Lỗi lưu file", "Không thể lưu file.", exc=exc)
            return

        reply = QMessageBox.information(
            self,
            "Xuất thành công",
            f"File đã được lưu tại:\n{save_path}",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open,
        )
        if reply == QMessageBox.StandardButton.Open:
            _open_folder(Path(save_path).parent)


# ---------------------------------------------------------------------------
# Helper dialog for essay question scores
# ---------------------------------------------------------------------------

class _EssayQuestionsDialog(QDialog):
    """Dialog for entering scores of essay (tự luận) questions.

    Displays a row per essay question with a score spinbox.
    The user can add more rows via the '+' button.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cấu hình câu hỏi tự luận")
        self.setMinimumWidth(380)
        self._score_spins: list[QDoubleSpinBox] = []
        self._build_ui()

    def _build_ui(self) -> None:
        vl = QVBoxLayout(self)
        vl.setSpacing(10)

        info = QLabel(
            "Nhập điểm cho từng câu hỏi tự luận.\n"
            "Phần Tự luận sẽ được đặt ở cuối bài thi."
        )
        info.setStyleSheet("font-size: 13px;")
        vl.addWidget(info)

        self._form = QFormLayout()
        self._form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        vl.addLayout(self._form)

        self._add_row()

        add_btn = QPushButton("+ Thêm câu hỏi")
        add_btn.setFixedHeight(30)
        add_btn.clicked.connect(self._add_row)
        vl.addWidget(add_btn)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("Tiếp tục xuất")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        vl.addWidget(btn_box)

    def _add_row(self) -> None:
        n = len(self._score_spins) + 1
        spin = QDoubleSpinBox()
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setMinimum(0.0)
        spin.setMaximum(100.0)
        spin.setValue(1.0)
        spin.setDecimals(1)
        spin.setSuffix(" điểm")
        self._score_spins.append(spin)
        self._form.addRow(f"Câu {n}:", spin)

    def essay_questions(self) -> list[dict]:
        """Return list of essay question dicts with number and score."""
        return [
            {"number": i + 1, "score": spin.value()}
            for i, spin in enumerate(self._score_spins)
        ]
