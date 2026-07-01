"""Bảng xuất đề thi - cấu hình và tạo file .docx.

Separated from QuizBuilderView so the builder focuses on quiz configuration
while this panel handles document metadata and rendering.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.paths import EXPORTS_DIR
from modules.quiz_builder.quota_allocator import (
    QuotaPlan,
    allocate_questions_for_plan,
    build_inventory,
    diagnose_quota_infeasibility,
    validate_quota_plan,
)
from modules.quiz_builder.selector import QuestionSelector
from modules.quiz_exporter.word_renderer import (
    ExamMeta,
    ExportConfig,
    ExportQuestionSnapshot,
    PrintProfile,
    WordRenderer,
    build_output_path,
)
from modules.quiz_exporter.package_builder import BatchExportPackage, create_batch_export_package
from modules.quiz_exporter.preset_store import ExportPreset
from ui.facades.export_template_facade import ExportTemplateFacade
from ui.facades.quiz_builder_facade import QuizBuilderFacade
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
    exam_count: int
    question_count: int
    candidate_question_ids: list[int]
    chapter_quota: dict[str, int]
    type_quota: dict[str, int]
    clo_quota: dict[tuple[str, str], int]
    shuffle_questions: bool
    shuffle_options: bool
    no_repeat_between_exams: bool
    time_limit_minutes: int | None   # None when Ôn tập mode (no timer)


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
        self._builder_facade = QuizBuilderFacade(selector)
        self._template_facade = ExportTemplateFacade()
        self._get_selection_state = get_selection_state
        self._current_bank_id: int | None = None
        self._current_bank_name: str = ""
        self._current_department: str = ""
        self._current_subject: str = ""
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        exp_form = QFormLayout(self)
        exp_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(240)
        self._load_presets()
        self._preset_load_btn = QPushButton("Nạp mẫu")
        self._preset_save_btn = QPushButton("Lưu mẫu")
        self._preset_save_default_btn = QPushButton("Lưu mặc định")
        self._preset_delete_btn = QPushButton("Xóa mẫu")
        self._preset_load_btn.clicked.connect(self._on_load_preset)
        self._preset_save_btn.clicked.connect(self._on_save_preset)
        self._preset_save_default_btn.clicked.connect(self._on_save_default_preset)
        self._preset_delete_btn.clicked.connect(self._on_delete_preset)
        preset_row.addWidget(self._preset_combo, stretch=1)
        preset_row.addWidget(self._preset_load_btn)
        preset_row.addWidget(self._preset_save_btn)
        preset_row.addWidget(self._preset_save_default_btn)
        preset_row.addWidget(self._preset_delete_btn)
        exp_form.addRow("Mẫu xuất đề:", _wrap_layout(preset_row))

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
        exp_form.addRow("Học phần:", self._exp_subject)

        self._exp_course_code = QLineEdit()
        self._exp_course_code.setPlaceholderText("Ví dụ: SCM001")
        exp_form.addRow("Mã học phần:", self._exp_course_code)

        self._exp_title = QLineEdit()
        self._exp_title.setPlaceholderText("Ví dụ: Bài kiểm tra giữa kỳ")
        exp_form.addRow("Tiêu đề đề thi *:", self._exp_title)

        self._exp_exam_type = QComboBox()
        self._exp_exam_type.addItem("Trắc nghiệm")
        self._exp_exam_type.addItem("Trắc nghiệm + Tự luận")
        exp_form.addRow("Loại đề:", self._exp_exam_type)

        self._exp_numbering = QComboBox()
        self._exp_numbering.addItem("Đánh số liên tục toàn bài", "global")
        self._exp_numbering.addItem("Đánh số lại theo từng phần", "per_section")
        exp_form.addRow("Đánh số câu hỏi:", self._exp_numbering)

        self._exp_group_by_type = QCheckBox("Phân nhóm theo loại câu (Phần A, B, C…)")
        self._exp_group_by_type.setChecked(True)
        exp_form.addRow("", self._exp_group_by_type)

        self._exp_cb_instructions = QCheckBox("Hướng dẫn làm")
        self._exp_cb_instructions.setChecked(True)
        self._exp_cb_answer_sheet = QCheckBox("Phiếu trả lời")
        self._exp_cb_answer_sheet.setChecked(True)
        self._exp_cb_scoring = QCheckBox("Quy định chấm")
        self._exp_cb_scoring.setChecked(True)
        self._exp_cb_answer_key = QCheckBox("Kèm đáp án và thang điểm")
        self._exp_cb_answer_key.setChecked(True)
        self._exp_cb_show_points = QCheckBox("Hiển thị điểm")
        self._exp_cb_show_points.setChecked(False)
        self._exp_cb_statistics = QCheckBox("Thống kê câu hỏi")
        self._exp_cb_statistics.setChecked(False)
        self._exp_cb_cover_sheet = QCheckBox("Cover sheet")
        self._exp_cb_cover_sheet.setChecked(False)
        self._exp_cb_split_answer_key = QCheckBox("Tách đáp án")
        self._exp_cb_split_answer_key.setChecked(False)

        opt_grid = QGridLayout()
        opt_grid.setContentsMargins(0, 0, 0, 0)
        opt_grid.setHorizontalSpacing(18)
        opt_grid.setVerticalSpacing(6)
        option_boxes = (
            self._exp_cb_instructions,
            self._exp_cb_answer_sheet,
            self._exp_cb_scoring,
            self._exp_cb_answer_key,
            self._exp_cb_show_points,
            self._exp_cb_statistics,
            self._exp_cb_cover_sheet,
            self._exp_cb_split_answer_key,
        )
        for cb in option_boxes:
            cb.setStyleSheet(_CB_STYLE)
        for idx, cb in enumerate(option_boxes):
            opt_grid.addWidget(cb, idx // 2, idx % 2)
        opt_grid.setColumnStretch(0, 1)
        opt_grid.setColumnStretch(1, 1)
        exp_form.addRow("Tùy chọn:", _wrap_layout(opt_grid))

        self._exp_watermark = QLineEdit()
        self._exp_watermark.setPlaceholderText("Ví dụ: NỘI BỘ / DRAFT / KHÔNG PHÁT TÁN")
        exp_form.addRow("Dấu mờ:", self._exp_watermark)

        self._exp_watermark_preset = QComboBox()
        self._exp_watermark_preset.addItem("Tùy chỉnh", "custom")
        self._exp_watermark_preset.addItem("NỘI BỘ", "NỘI BỘ")
        self._exp_watermark_preset.addItem("DRAFT", "DRAFT")
        self._exp_watermark_preset.addItem("KHÔNG PHÁT TÁN", "KHÔNG PHÁT TÁN")
        self._exp_watermark_preset.currentIndexChanged.connect(self._on_watermark_preset_changed)
        exp_form.addRow("Mẫu dấu mờ:", self._exp_watermark_preset)

        self._exp_cover_template = QComboBox()
        self._exp_cover_template.addItem("Chuẩn", "standard")
        self._exp_cover_template.addItem("Tối giản", "minimal")
        exp_form.addRow("Template cover:", self._exp_cover_template)

        self._exp_answer_key_naming = QComboBox()
        self._exp_answer_key_naming.addItem("Suffix: _DAP_AN", "suffix")
        self._exp_answer_key_naming.addItem("Prefix: DAP_AN_", "prefix")
        exp_form.addRow("Tên file đáp án:", self._exp_answer_key_naming)

        self._exp_page_size = QComboBox()
        self._exp_page_size.addItem("A4", "A4")
        self._exp_page_size.addItem("Letter", "LETTER")
        exp_form.addRow("Khổ giấy:", self._exp_page_size)

        margin_row = QHBoxLayout()
        margin_row.setContentsMargins(0, 0, 0, 0)
        self._margin_top = QDoubleSpinBox()
        self._margin_bottom = QDoubleSpinBox()
        self._margin_left = QDoubleSpinBox()
        self._margin_right = QDoubleSpinBox()
        for spin, value in (
            (self._margin_top, 1.5),
            (self._margin_bottom, 1.5),
            (self._margin_left, 2.0),
            (self._margin_right, 1.5),
        ):
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setDecimals(1)
            spin.setRange(0.5, 5.0)
            spin.setSingleStep(0.1)
            spin.setSuffix(" cm")
            spin.setValue(value)
        margin_row.addWidget(QLabel("Trên"))
        margin_row.addWidget(self._margin_top)
        margin_row.addWidget(QLabel("Dưới"))
        margin_row.addWidget(self._margin_bottom)
        margin_row.addWidget(QLabel("Trái"))
        margin_row.addWidget(self._margin_left)
        margin_row.addWidget(QLabel("Phải"))
        margin_row.addWidget(self._margin_right)
        exp_form.addRow("Lề in:", _wrap_layout(margin_row))

        self._exp_show_student_info = QCheckBox("Hiện khối thông tin sinh viên và chữ ký")
        self._exp_show_student_info.setChecked(True)
        exp_form.addRow("Hồ sơ in:", self._exp_show_student_info)

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
        self._current_bank_id = bank_data.get("id")
        self._current_bank_name = bank_data.get("name", "")
        self._current_department = bank_data.get("department", "")
        self._current_subject = bank_data.get("subject", "")
        self._exp_school.setText(bank_data.get("school", ""))
        self._exp_department.setText(bank_data.get("department", ""))
        self._exp_subject.setText(bank_data.get("subject", ""))
        self._exp_course_code.setText(bank_data.get("course_code", ""))
        self._exp_title.setText(bank_data.get("exam_title", ""))
        self._apply_default_preset_for_context()

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
        config = ExportConfig(
            show_instructions=self._exp_cb_instructions.isChecked(),
            show_answer_sheet=self._exp_cb_answer_sheet.isChecked(),
            show_scoring_rules=self._exp_cb_scoring.isChecked(),
            show_answer_key=self._exp_cb_answer_key.isChecked(),
            show_question_points=self._exp_cb_show_points.isChecked(),
            show_question_statistics=self._exp_cb_statistics.isChecked(),
            numbering_mode=self._exp_numbering.currentData(),
            group_by_type=self._exp_group_by_type.isChecked(),
            show_cover_sheet=self._exp_cb_cover_sheet.isChecked(),
            split_answer_key_file=self._exp_cb_split_answer_key.isChecked(),
            watermark_text=self._exp_watermark.text().strip(),
            watermark_preset=str(self._exp_watermark_preset.currentData()),
            cover_sheet_template=str(self._exp_cover_template.currentData()),
            answer_key_naming_policy=str(self._exp_answer_key_naming.currentData()),
            essay_questions=[],
        )
        config.print_profile = self.build_print_profile()
        return config

    def build_print_profile(self) -> PrintProfile:
        return PrintProfile(
            page_size=str(self._exp_page_size.currentData()),
            top_margin_cm=self._margin_top.value(),
            bottom_margin_cm=self._margin_bottom.value(),
            left_margin_cm=self._margin_left.value(),
            right_margin_cm=self._margin_right.value(),
            show_student_info_block=self._exp_show_student_info.isChecked(),
        )

    def build_preset(self, name: str) -> ExportPreset:
        """Build a serializable preset from current export form state."""
        return ExportPreset(
            name=name,
            school=self._exp_school.text().strip(),
            department=self._exp_department.text().strip(),
            instructor=self._exp_instructor.text().strip(),
            subject=self._exp_subject.text().strip(),
            course_code=self._exp_course_code.text().strip(),
            exam_title=self._exp_title.text().strip(),
            exam_type=self._exp_exam_type.currentText(),
            numbering_mode=self._exp_numbering.currentData(),
            group_by_type=self._exp_group_by_type.isChecked(),
            show_instructions=self._exp_cb_instructions.isChecked(),
            show_answer_sheet=self._exp_cb_answer_sheet.isChecked(),
            show_scoring_rules=self._exp_cb_scoring.isChecked(),
            show_answer_key=self._exp_cb_answer_key.isChecked(),
            show_question_points=self._exp_cb_show_points.isChecked(),
            show_question_statistics=self._exp_cb_statistics.isChecked(),
            show_cover_sheet=self._exp_cb_cover_sheet.isChecked(),
            split_answer_key_file=self._exp_cb_split_answer_key.isChecked(),
            watermark_text=self._exp_watermark.text().strip(),
            watermark_preset=str(self._exp_watermark_preset.currentData()),
            cover_sheet_template=str(self._exp_cover_template.currentData()),
            answer_key_naming_policy=str(self._exp_answer_key_naming.currentData()),
            page_size=str(self._exp_page_size.currentData()),
            top_margin_cm=self._margin_top.value(),
            bottom_margin_cm=self._margin_bottom.value(),
            left_margin_cm=self._margin_left.value(),
            right_margin_cm=self._margin_right.value(),
            show_student_info_block=self._exp_show_student_info.isChecked(),
        )

    def apply_preset(self, preset: ExportPreset) -> None:
        """Apply a previously saved export preset to the form."""
        self._exp_school.setText(preset.school)
        self._exp_department.setText(preset.department)
        self._exp_instructor.setText(preset.instructor)
        self._exp_subject.setText(preset.subject)
        self._exp_course_code.setText(preset.course_code)
        self._exp_title.setText(preset.exam_title)
        self._select_combo_text(self._exp_exam_type, preset.exam_type)
        self._select_combo_data(self._exp_numbering, preset.numbering_mode)
        self._exp_group_by_type.setChecked(preset.group_by_type)
        self._exp_cb_instructions.setChecked(preset.show_instructions)
        self._exp_cb_answer_sheet.setChecked(preset.show_answer_sheet)
        self._exp_cb_scoring.setChecked(preset.show_scoring_rules)
        self._exp_cb_answer_key.setChecked(preset.show_answer_key)
        self._exp_cb_show_points.setChecked(preset.show_question_points)
        self._exp_cb_statistics.setChecked(preset.show_question_statistics)
        self._exp_cb_cover_sheet.setChecked(preset.show_cover_sheet)
        self._exp_cb_split_answer_key.setChecked(preset.split_answer_key_file)
        self._exp_watermark.setText(preset.watermark_text)
        self._select_combo_data(self._exp_watermark_preset, preset.watermark_preset)
        self._select_combo_data(self._exp_cover_template, preset.cover_sheet_template)
        self._select_combo_data(self._exp_answer_key_naming, preset.answer_key_naming_policy)
        self._select_combo_data(self._exp_page_size, preset.page_size)
        self._margin_top.setValue(preset.top_margin_cm)
        self._margin_bottom.setValue(preset.bottom_margin_cm)
        self._margin_left.setValue(preset.left_margin_cm)
        self._margin_right.setValue(preset.right_margin_cm)
        self._exp_show_student_info.setChecked(preset.show_student_info_block)

    # ------------------------------------------------------------------
    # Export logic
    # ------------------------------------------------------------------

    def _load_presets(self) -> None:
        self._preset_combo.clear()
        self._preset_combo.addItem("— Chọn mẫu đã lưu —", userData=None)
        for name in self._template_facade.list_preset_names():
            self._preset_combo.addItem(name, userData=name)

    def _on_save_preset(self) -> None:
        current_name = self._preset_combo.currentData()
        suggested = current_name if isinstance(current_name, str) else self._exp_title.text().strip()
        name, accepted = QInputDialog.getText(
            self,
            "Lưu mẫu xuất đề",
            "Tên mẫu:",
            text=suggested,
        )
        if not accepted:
            return

        try:
            preset = self.build_preset(name.strip())
            self._template_facade.save_preset(preset)
        except Exception as exc:
            show_critical_error(self, "Lỗi lưu mẫu", "Không thể lưu mẫu xuất đề.", exc=exc)
            return

        self._load_presets()
        self._select_combo_data(self._preset_combo, preset.name)
        QMessageBox.information(self, "Đã lưu", f"Đã lưu mẫu xuất đề: {preset.name}")

    def _on_save_default_preset(self) -> None:
        if self._current_bank_id is None:
            QMessageBox.information(self, "Thiếu ngữ cảnh", "Vui lòng chọn ngân hàng trước khi lưu mặc định.")
            return

        scope_label, accepted = QInputDialog.getItem(
            self,
            "Lưu preset mặc định",
            "Phạm vi mặc định:",
            [
                "Ngân hàng hiện tại",
                "Khoa + Môn hiện tại",
                "Mặc định chung",
            ],
            editable=False,
        )
        if not accepted:
            return

        preset = self._build_default_preset(scope_label)
        try:
            self._template_facade.save_preset(preset)
        except Exception as exc:
            show_critical_error(self, "Lỗi lưu mặc định", "Không thể lưu preset mặc định.", exc=exc)
            return

        self._load_presets()
        self._select_combo_data(self._preset_combo, preset.name)
        QMessageBox.information(self, "Đã lưu", f"Đã lưu preset mặc định: {preset.name}")

    def _on_load_preset(self) -> None:
        name = self._preset_combo.currentData()
        if not isinstance(name, str) or not name.strip():
            QMessageBox.information(self, "Chưa chọn mẫu", "Vui lòng chọn một mẫu đã lưu.")
            return

        try:
            preset = self._template_facade.load_preset(name)
        except Exception as exc:
            show_critical_error(self, "Lỗi nạp mẫu", "Không thể nạp mẫu xuất đề.", exc=exc)
            return

        self.apply_preset(preset)
        QMessageBox.information(self, "Đã nạp", f"Đã áp dụng mẫu xuất đề: {preset.name}")

    def _on_delete_preset(self) -> None:
        name = self._preset_combo.currentData()
        if not isinstance(name, str) or not name.strip():
            QMessageBox.information(self, "Chưa chọn mẫu", "Vui lòng chọn một mẫu để xóa.")
            return

        answer = QMessageBox.question(
            self,
            "Xóa mẫu xuất đề",
            f"Bạn có chắc muốn xóa mẫu '{name}' không?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self._template_facade.delete_preset(name)
        except Exception as exc:
            show_critical_error(self, "Lỗi xóa mẫu", "Không thể xóa mẫu xuất đề.", exc=exc)
            return

        if not deleted:
            QMessageBox.warning(self, "Không tìm thấy", "Mẫu xuất đề không còn tồn tại.")
            return

        self._load_presets()
        QMessageBox.information(self, "Đã xóa", f"Đã xóa mẫu xuất đề: {name}")

    def _build_default_preset(self, scope_label: str) -> ExportPreset:
        if scope_label == "Ngân hàng hiện tại":
            preset = self.build_preset(
                f"Mặc định - Ngân hàng: {self._current_bank_name or self._current_bank_id}"
            )
            preset.default_scope = "bank"
            preset.default_bank_id = self._current_bank_id
            preset.default_bank_name = self._current_bank_name
            return preset

        if scope_label == "Khoa + Môn hiện tại":
            preset = self.build_preset(
                f"Mặc định - {self._current_department or 'Khoa'} - {self._current_subject or 'Mon'}"
            )
            preset.default_scope = "department_subject"
            preset.default_department_key = " ".join(self._current_department.strip().lower().split())
            preset.default_subject_key = " ".join(self._current_subject.strip().lower().split())
            return preset

        preset = self.build_preset("Mặc định chung - Xuất đề")
        preset.default_scope = "global"
        return preset

    def _apply_default_preset_for_context(self) -> None:
        try:
            preset = self._template_facade.resolve_default_preset(
                bank_id=self._current_bank_id,
                department=self._current_department,
                subject=self._current_subject,
            )
        except Exception:
            return
        if preset is None:
            return
        self.apply_preset(preset)
        self._load_presets()
        self._select_combo_data(self._preset_combo, preset.name)

    def _on_watermark_preset_changed(self) -> None:
        value = self._exp_watermark_preset.currentData()
        if value == "custom":
            return
        if isinstance(value, str):
            self._exp_watermark.setText(value)

    def _build_export_preview_summary(
        self,
        *,
        selection_state: ExportSelectionState,
        exam_title: str,
        exam_count: int,
        package: BatchExportPackage | None,
        package_dir: Path | None,
        single_path: Path | None,
        planned_paths: list[Path],
        separate_answer_key: bool,
        answer_key_naming_policy: str,
        render_config: ExportConfig,
    ) -> str:
        target = str(package_dir) if package_dir is not None else str(single_path)
        existing_conflicts = BatchExportPackage.find_existing_conflicts(planned_paths)
        duplicate_names = BatchExportPackage.find_duplicate_names(planned_paths)
        section_lines = self._build_section_preview_lines(render_config, separate_answer_key)
        print_profile_lines = self._build_print_profile_preview_lines(render_config.print_profile)
        content_preview_lines = self._build_content_preview_lines(
            selection_state,
            exam_count,
            render_config,
        )
        note_parts = [
            f"Đích xuất: {target}",
            f"Tổng file dự kiến: {len(planned_paths)}",
        ]
        if package is not None:
            note_parts.append(f"Mã package: {package.package_code}")
        if separate_answer_key:
            note_parts.append(f"Naming policy đáp án: {answer_key_naming_policy}")
        if existing_conflicts:
            note_parts.append(
                f"Cảnh báo overwrite: {len(existing_conflicts)} file đã tồn tại"
            )
        if duplicate_names:
            note_parts.append(
                "Cảnh báo naming conflict: " + ", ".join(duplicate_names[:3])
            )
        manifest_text = (
            package.build_manifest_text(
                exam_title=exam_title,
                exam_count=exam_count,
                note=" | ".join(note_parts),
                planned_paths=planned_paths,
                section_lines=section_lines,
                print_profile_lines=print_profile_lines,
                content_preview_lines=content_preview_lines,
            )
            if package is not None
            else self._build_single_export_manifest_text(
                selection_state=selection_state,
                exam_title=exam_title,
                exam_count=exam_count,
                note=" | ".join(note_parts),
                planned_paths=planned_paths,
                section_lines=section_lines,
                print_profile_lines=print_profile_lines,
                content_preview_lines=content_preview_lines,
            )
        )
        if existing_conflicts:
            manifest_text += "\n\nOverwrite warnings:\n" + "\n".join(
                f"- {path.name}" for path in existing_conflicts[:8]
            )
        if duplicate_names:
            manifest_text += "\n\nNaming conflicts:\n" + "\n".join(
                f"- {name}" for name in duplicate_names
            )
        return manifest_text

    def _build_single_export_manifest_text(
        self,
        *,
        selection_state: ExportSelectionState,
        exam_title: str,
        exam_count: int,
        note: str,
        planned_paths: list[Path],
        section_lines: list[str],
        print_profile_lines: list[str],
        content_preview_lines: list[str],
    ) -> str:
        lines = [
            "Gói xuất đề: single_export",
            f"Tiêu đề: {exam_title}",
            f"Số đề: {exam_count}",
            f"Ghi chú: {note}",
            f"Bộ câu hỏi: {self._describe_candidate_pool(selection_state)}",
            f"Quota Chương: {self._describe_quota(selection_state.chapter_quota)}",
            f"Quota Loại: {self._describe_quota(selection_state.type_quota)}",
            f"Quota CLO: {self._describe_clo_quota(selection_state.clo_quota)}",
            "",
            "Nội dung in:",
            *[f"- {line}" for line in section_lines],
            "",
            "Hồ sơ in:",
            *[f"- {line}" for line in print_profile_lines],
            "",
            "Xem trước nội dung:",
            *[f"- {line}" for line in content_preview_lines],
            "",
            "Danh sách file dự kiến:",
            *[f"- {path.name}" for path in planned_paths],
        ]
        return "\n".join(lines)

    def _build_section_preview_lines(
        self,
        render_config: ExportConfig,
        separate_answer_key: bool,
    ) -> list[str]:
        return [
            f"Trang bìa: {'Có' if render_config.show_cover_sheet else 'Không'}",
            f"Hướng dẫn làm: {'Có' if render_config.show_instructions else 'Không'}",
            f"Phiếu trả lời: {'Có' if render_config.show_answer_sheet else 'Không'}",
            f"Quy định chấm: {'Có' if render_config.show_scoring_rules else 'Không'}",
            f"Đáp án trong file đề: {'Không' if separate_answer_key else ('Có' if render_config.show_answer_key else 'Không')}",
            f"Hiển thị điểm: {'Có' if render_config.show_question_points else 'Không'}",
            f"Thống kê câu hỏi: {'Có' if render_config.show_question_statistics else 'Không'}",
            f"Tách đáp án: {'Có' if separate_answer_key else 'Không'}",
            f"Dấu mờ: {render_config.watermark_text or '(không có)'}",
            f"Phân nhóm theo loại câu: {'Có' if render_config.group_by_type else 'Không'}",
        ]

    def _build_print_profile_preview_lines(self, profile: PrintProfile) -> list[str]:
        return [
            f"Khổ giấy: {profile.page_size}",
            (
                "Lề in (cm): "
                f"trên {profile.top_margin_cm:.1f}, dưới {profile.bottom_margin_cm:.1f}, "
                f"trái {profile.left_margin_cm:.1f}, phải {profile.right_margin_cm:.1f}"
            ),
            (
                "Khối thông tin sinh viên: "
                + ("Hiện" if profile.show_student_info_block else "Ẩn")
            ),
        ]

    def _build_content_preview_lines(
        self,
        selection_state: ExportSelectionState,
        exam_count: int,
        render_config: ExportConfig,
    ) -> list[str]:
        numbering_mode = "toan bai" if render_config.numbering_mode == "global" else "theo tung phan"
        lines = [
            f"Số đề sẽ render: {exam_count}",
            f"Đánh số câu hỏi: {numbering_mode}",
            f"Bộ câu hỏi: {self._describe_candidate_pool(selection_state)}",
            f"Quota Chương: {self._describe_quota(selection_state.chapter_quota)}",
            f"Quota Loại: {self._describe_quota(selection_state.type_quota)}",
            f"Quota CLO: {self._describe_clo_quota(selection_state.clo_quota)}",
            f"Mẫu trang bìa: {render_config.cover_sheet_template}",
        ]
        if render_config.essay_questions:
            lines.append(f"Số câu tự luận: {len(render_config.essay_questions)}")
        return lines

    def _show_export_preview_dialog(self, manifest_text: str) -> bool:
        dlg = QDialog(self)
        dlg.setWindowTitle("Bản xem trước gói xuất")
        dlg.resize(760, 560)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Rà soát kế hoạch xuất và xem trước nội dung in trước khi render thật."))
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(manifest_text)
        layout.addWidget(editor, stretch=1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Tiếp tục xuất")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        return dlg.exec() == QDialog.DialogCode.Accepted

    def _build_single_answer_key_path(self, target_path: Path, policy: str) -> Path:
        if policy == "prefix":
            return target_path.with_name(f"DAP_AN_{target_path.name}")
        return target_path.with_name(f"{target_path.stem}_DAP_AN.docx")

    @staticmethod
    def _display_question_type(qtype: str) -> str:
        mapping = {
            "MC": "Trắc nghiệm 1 đáp án",
            "MA": "Trắc nghiệm nhiều đáp án",
            "TF": "Đúng/Sai",
            "BLANK": "Điền vào chỗ trống",
            "SA": "Trả lời ngắn",
            "ES": "Tự luận",
        }
        return mapping.get(qtype, qtype)

    @staticmethod
    def _display_difficulty(level: str) -> str:
        mapping = {
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
        return mapping.get(level, level)

    @staticmethod
    def _describe_candidate_pool(selection_state: ExportSelectionState) -> str:
        if not selection_state.candidate_question_ids:
            return "Tất cả câu hỏi trong ngân hàng"
        return f"{len(selection_state.candidate_question_ids)} câu đã chọn"

    @staticmethod
    def _describe_quota(quota: dict[str, int]) -> str:
        if not quota:
            return "(không nhập)"
        return ", ".join(f"{key}: {value}" for key, value in quota.items())

    @classmethod
    def _describe_clo_quota(cls, quota: dict[tuple[str, str], int]) -> str:
        if not quota:
            return "(không nhập)"
        return ", ".join(
            f"{clo} / {cls._display_difficulty(level)}: {count}"
            for (clo, level), count in quota.items()
        )

    @staticmethod
    def _select_combo_text(combo: QComboBox, text: str) -> None:
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: object) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _on_export(self) -> None:
        """Collect config and export one or many exam .docx files."""
        state = self._get_selection_state()

        if state.bank_id is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ngân hàng câu hỏi.")
            return

        exam_title = self._exp_title.text().strip()
        validation_error = self.validate_required_fields()
        if validation_error:
            QMessageBox.warning(self, "Thiếu thông tin", validation_error)
            return

        exam_count = max(1, state.exam_count)
        use_quota = bool(state.chapter_quota or state.type_quota or state.clo_quota)
        plan = QuotaPlan(
            total_questions=state.question_count,
            chapter_quota=state.chapter_quota,
            type_quota=state.type_quota,
            clo_quota=state.clo_quota,
        )

        # ------ Upfront validation: load a probe pool (no lazy attrs needed) ------
        try:
            _probe = self._builder_facade.list_eligible_questions(
                bank_id=state.bank_id,
                candidate_question_ids=state.candidate_question_ids or None,
                active_only=True,
                shuffle=False,
            )
        except Exception as exc:
            show_critical_error(self, "Lỗi", "Không thể lấy câu hỏi.", exc=exc)
            return

        if not _probe:
            QMessageBox.warning(
                self, "Không đủ câu hỏi",
                "Không tìm thấy câu hỏi phù hợp với bộ câu hỏi đã chọn.",
            )
            return

        if use_quota:
            _inv = build_inventory(_probe)
            _vr = validate_quota_plan(plan, _inv)
            if not _vr.is_valid:
                QMessageBox.warning(self, "Quota không hợp lệ", "\n".join(_vr.errors[:8]))
                return
        elif len(_probe) < state.question_count:
            QMessageBox.warning(
                self, "Không đủ câu hỏi",
                f"Nguồn câu hỏi chỉ có {len(_probe)} câu, không đủ {state.question_count} câu cho mỗi đề.",
            )
            return

        # ------ UI dialogs (before heavy work) ------
        essay_questions: list[dict] = []
        if self._exp_exam_type.currentText() == "Trắc nghiệm + Tự luận":
            dlg = _EssayQuestionsDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            essay_questions = dlg.essay_questions()

        output_dir: Path | None = None
        single_save_path: Path | None = None
        if exam_count > 1:
            selected_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu đề thi")
            if not selected_dir:
                return
            output_dir = Path(selected_dir)
        else:
            default_path = str(build_output_path(exam_title, EXPORTS_DIR))
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Lưu đề thi", default_path, "Word Document (*.docx)",
            )
            if not save_path:
                return
            single_save_path = Path(save_path)

        base_meta = self.build_meta(duration_minutes=state.time_limit_minutes or 0)
        base_meta.exam_title = exam_title
        render_config = self.build_render_config()
        render_config.essay_questions = essay_questions
        separate_answer_key = render_config.show_answer_key and render_config.split_answer_key_file
        if separate_answer_key:
            render_config.show_answer_key = False

        renderer = WordRenderer()
        generated_paths: list[Path] = []
        answer_key_paths: list[Path] = []
        used_across_exams: set[int] = set()
        package = None

        if exam_count > 1:
            assert output_dir is not None
            package = create_batch_export_package(
                root_dir=output_dir,
                exam_title=base_meta.exam_title,
                subject=base_meta.subject,
                course_code=base_meta.course_code,
            )
            planned_paths = package.plan_document_paths(
                exam_title=base_meta.exam_title,
                exam_count=exam_count,
                separate_answer_key=separate_answer_key,
                answer_key_policy=render_config.answer_key_naming_policy,
            )
        else:
            assert single_save_path is not None
            planned_paths = [single_save_path]
            if separate_answer_key:
                planned_paths.append(
                    self._build_single_answer_key_path(
                        single_save_path,
                        render_config.answer_key_naming_policy,
                    )
                )

        preview_summary = self._build_export_preview_summary(
            selection_state=state,
            exam_title=base_meta.exam_title,
            exam_count=exam_count,
            package=package,
            package_dir=package.package_dir if package is not None else None,
            single_path=single_save_path,
            planned_paths=planned_paths,
            separate_answer_key=separate_answer_key,
            answer_key_naming_policy=render_config.answer_key_naming_policy,
            render_config=render_config,
        )
        if not self._show_export_preview_dialog(preview_summary):
            return

        for exam_index in range(1, exam_count + 1):
            excluded = used_across_exams if state.no_repeat_between_exams else None

            typed_snapshots: list[ExportQuestionSnapshot] = []
            try:
                candidates = self._builder_facade.list_eligible_questions(
                    bank_id=state.bank_id,
                    candidate_question_ids=state.candidate_question_ids or None,
                    active_only=True,
                    shuffle=state.shuffle_questions,
                )

                if use_quota:
                    questions_orm = allocate_questions_for_plan(
                        candidates, plan, excluded_question_ids=excluded,
                    )
                    if not questions_orm:
                        diagnostic = diagnose_quota_infeasibility(
                            candidates, plan, excluded_question_ids=excluded,
                        )
                        reason = (
                            " (do bật tùy chọn không lặp câu giữa các đề)."
                            if state.no_repeat_between_exams else "."
                        )
                        detail = (
                            "\n\nChi tiết:\n- " + "\n- ".join(diagnostic[:4])
                            if diagnostic else ""
                        )
                        QMessageBox.warning(
                            self,
                            "Không thể phân bổ quota",
                            f"Không tìm được tổ hợp câu hỏi hợp lệ cho đề số {exam_index}{reason}{detail}",
                        )
                        break
                else:
                    pool = (
                        [q for q in candidates if q.id not in used_across_exams]
                        if state.no_repeat_between_exams
                        else list(candidates)
                    )
                    if len(pool) < state.question_count:
                        reason = (
                            " do bật tùy chọn không lặp câu giữa các đề"
                            if state.no_repeat_between_exams else ""
                        )
                        QMessageBox.warning(
                            self, "Không đủ câu hỏi",
                            f"Không đủ câu hỏi để tạo đề số {exam_index}{reason}.",
                        )
                        break
                    questions_orm = random.sample(pool, state.question_count)

                if state.no_repeat_between_exams:
                    used_across_exams.update(q.id for q in questions_orm)

                raw_snapshots = self._selector.build_snapshots(
                    questions_orm, shuffle_options=state.shuffle_options,
                )
                typed_snapshots = [ExportQuestionSnapshot.from_dict(s) for s in raw_snapshots]

            except Exception as exc:
                show_critical_error(
                    self, "Lỗi", f"Không thể chuẩn bị câu hỏi cho đề số {exam_index}.", exc=exc,
                )
                break

            if not typed_snapshots:
                break

            meta = ExamMeta(**vars(base_meta))
            if exam_count > 1:
                meta.exam_title = f"{base_meta.exam_title} - Đề {exam_index}"
            setattr(meta, "cover_sheet_template", render_config.cover_sheet_template)

            try:
                doc = renderer.render(typed_snapshots, meta, render_config)
            except Exception as exc:
                show_critical_error(
                    self, "Lỗi render", f"Không thể render đề số {exam_index}.", exc=exc,
                )
                break

            target_path: Path
            if exam_count > 1:
                assert package is not None
                target_path = package.build_exam_path(base_meta.exam_title, exam_index)
            else:
                assert single_save_path is not None
                target_path = single_save_path

            try:
                doc.save(target_path)
            except Exception as exc:
                show_critical_error(
                    self, "Lỗi lưu file", f"Không thể lưu đề số {exam_index}.", exc=exc,
                )
                break

            generated_paths.append(target_path)

            if separate_answer_key:
                key_config = ExportConfig(
                    show_instructions=False,
                    show_answer_sheet=False,
                    show_scoring_rules=False,
                    show_answer_key=True,
                    show_question_points=False,
                    show_question_statistics=False,
                    numbering_mode=render_config.numbering_mode,
                    group_by_type=render_config.group_by_type,
                    show_cover_sheet=False,
                    split_answer_key_file=False,
                    watermark_text=render_config.watermark_text,
                    essay_questions=list(render_config.essay_questions),
                )
                key_config.print_profile = render_config.print_profile
                try:
                    key_doc = renderer.render_answer_key_document(typed_snapshots, meta, key_config)
                except Exception as exc:
                    show_critical_error(
                        self, "Lỗi render đáp án", f"Không thể render file đáp án cho đề số {exam_index}.", exc=exc,
                    )
                    break

                if exam_count > 1:
                    assert package is not None
                    answer_key_path = package.build_answer_key_path(
                        exam_index=exam_index,
                        policy=render_config.answer_key_naming_policy,
                    )
                else:
                    assert target_path is not None
                    answer_key_path = self._build_single_answer_key_path(
                        target_path,
                        render_config.answer_key_naming_policy,
                    )
                try:
                    key_doc.save(answer_key_path)
                except Exception as exc:
                    show_critical_error(
                        self, "Lỗi lưu file đáp án", f"Không thể lưu file đáp án cho đề số {exam_index}.", exc=exc,
                    )
                    break
                answer_key_paths.append(answer_key_path)

        if not generated_paths:
            return

        if package is not None:
            package.write_manifest(
                exam_title=base_meta.exam_title,
                exam_count=len(generated_paths),
                note=(
                    "Naming convention chuẩn in ấn cho nhiều đề."
                    + (" Co file dap an rieng." if answer_key_paths else "")
                ),
            )
            manifest_path = package.package_dir / f"{package.package_code}_README.txt"
            manifest_path.write_text(
                package.build_manifest_text(
                    exam_title=base_meta.exam_title,
                    exam_count=len(generated_paths),
                    note=(
                        "Naming convention chuẩn in ấn cho nhiều đề."
                        + (" Co file dap an rieng." if answer_key_paths else "")
                    ),
                    planned_paths=generated_paths + answer_key_paths,
                    section_lines=self._build_section_preview_lines(render_config, separate_answer_key),
                    print_profile_lines=self._build_print_profile_preview_lines(render_config.print_profile),
                    content_preview_lines=self._build_content_preview_lines(state, exam_count, render_config),
                ),
                encoding="utf-8",
            )

        success_text = (
            f"File đã được lưu tại:\n{generated_paths[0]}"
            if exam_count == 1
            else f"Đã tạo {len(generated_paths)} đề tại gói in ấn:\n{generated_paths[0].parent}"
        )
        if answer_key_paths:
            success_text += f"\n\nFile đáp án riêng đầu tiên:\n{answer_key_paths[0]}"
        open_target = generated_paths[0].parent
        reply = QMessageBox.information(
            self, "Xuất thành công", success_text,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open,
        )
        if reply == QMessageBox.StandardButton.Open:
            _open_folder(open_target)


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
