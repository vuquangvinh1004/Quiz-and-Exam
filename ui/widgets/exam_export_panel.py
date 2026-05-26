"""Exam export panel — configures and generates .docx exam files.

Separated from QuizBuilderView so the builder focuses on quiz configuration
while this panel handles document metadata and rendering.
"""
from __future__ import annotations

import os
import random
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
    exam_count: int
    question_count: int
    question_types: list        # list[str]: MC | MA | BLANK | SA
    difficulties: list          # list[str]: easy | medium | hard
    candidate_question_ids: list[int]
    chapter_quota: dict[str, int]
    type_quota: dict[str, int]
    difficulty_quota: dict[str, int]
    shuffle_questions: bool
    shuffle_options: bool
    no_repeat_between_exams: bool
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

        if not state.question_types:
            QMessageBox.warning(self, "Thiếu thông tin", "Chọn ít nhất một loại câu hỏi.")
            return
        if not state.difficulties:
            QMessageBox.warning(self, "Thiếu thông tin", "Chọn ít nhất một mức độ khó.")
            return

        exam_count = max(1, state.exam_count)
        use_quota = bool(state.chapter_quota or state.type_quota or state.difficulty_quota)
        plan = QuotaPlan(
            total_questions=state.question_count,
            chapter_quota=state.chapter_quota,
            type_quota=state.type_quota,
            difficulty_quota=state.difficulty_quota,
        )

        # ------ Upfront validation: load a probe pool (no lazy attrs needed) ------
        try:
            with get_session() as _probe_session:
                _probe = self._selector.select(
                    _probe_session,
                    state.bank_id,
                    count=100000,
                    question_types=state.question_types,
                    difficulties=state.difficulties,
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
                "Không tìm thấy câu hỏi phù hợp với bộ lọc đã chọn.",
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

        renderer = WordRenderer()
        generated_paths: list[Path] = []
        used_across_exams: set[int] = set()

        for exam_index in range(1, exam_count + 1):
            excluded = used_across_exams if state.no_repeat_between_exams else None

            # Open a fresh session per exam so build_snapshots can access
            # lazy-loaded relationships (q.options) while the session is live.
            typed_snapshots: list[ExportQuestionSnapshot] = []
            try:
                with get_session() as session:
                    candidates = self._selector.select(
                        session,
                        state.bank_id,
                        count=100000,
                        question_types=state.question_types,
                        difficulties=state.difficulties,
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

                    # update no-repeat tracking before snapshots so IDs are stable
                    if state.no_repeat_between_exams:
                        used_across_exams.update(q.id for q in questions_orm)

                    # build_snapshots MUST run inside the session:
                    # q.options is a lazy relationship; outside the session it raises
                    # DetachedInstanceError.
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
                # Reached by break inside the with block (warning already shown)
                break

            # Render outside session: typed_snapshots are plain dataclasses, safe.
            meta = ExamMeta(**vars(base_meta))
            if exam_count > 1:
                meta.exam_title = f"{base_meta.exam_title} - Đề {exam_index}"

            try:
                doc = renderer.render(typed_snapshots, meta, render_config)
            except Exception as exc:
                show_critical_error(
                    self, "Lỗi render", f"Không thể render đề số {exam_index}.", exc=exc,
                )
                break

            target_path: Path
            if exam_count > 1:
                assert output_dir is not None
                target_path = build_output_path(
                    f"{base_meta.exam_title}_De_{exam_index:02d}", output_dir,
                )
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

        if not generated_paths:
            return

        success_text = (
            f"File đã được lưu tại:\n{generated_paths[0]}"
            if exam_count == 1
            else f"Đã tạo {len(generated_paths)} đề tại:\n{generated_paths[0].parent}"
        )
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
