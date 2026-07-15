"""Setup workflow mixin for QuizRunnerView.

Extracted to keep quiz_runner_view.py focused and below size guardrail.
"""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

from core.domain.services.quiz_service import QuizConfig
from core.utils.constants import QuizMode
from core.utils.logger import get_logger
from ui.dialogs.question_pool_picker_dialog import QuestionPoolPickerDialog

logger = get_logger(__name__)


class QuizRunnerSetupMixin:
    """Setup panel behaviors: source selection and runtime quiz creation."""

    def _on_setup_bank_changed(self) -> None:
        self._selected_question_ids = []
        self._setup_pool_summary.setText("Đang dùng: tất cả câu hỏi trong bộ chọn")
        self._update_setup_available_count()

    def _on_setup_mode_changed(self) -> None:
        mode = self._setup_mode_combo.currentData()
        self._setup_time_spin.setVisible(mode in (QuizMode.EXAM.value, QuizMode.PRACTICE.value))
        self._update_setup_available_count()

    def _setup_selected_types(self) -> list[str]:
        mapping = {
            self._setup_cb_mc: "MC",
            self._setup_cb_ma: "MA",
            self._setup_cb_tf: "TF",
            self._setup_cb_blank: "BLANK",
            self._setup_cb_sa: "SA",
            self._setup_cb_crq: "CRQ",
        }
        selected: list[str] = []
        for cb, code in mapping.items():
            if not cb.isChecked():
                continue
            if code == "CRQ":
                selected.extend(["ES", "PR"])
            else:
                selected.append(code)
        return selected

    def _setup_selected_difficulties(self) -> list[str]:
        return [cb.text() for cb in self._setup_difficulty_cbs if cb.isChecked()]

    def _update_setup_available_count(self) -> None:
        bank_id = self._setup_bank_combo.current_bank_id()
        if bank_id is None:
            self._setup_available_lbl.setText("Sẵn có: 0 câu")
            return

        types = self._setup_selected_types() or None
        diffs = self._setup_selected_difficulties() or None
        try:
            count = self._builder_facade.count_eligible_questions(
                bank_id=bank_id,
                question_types=types,
                difficulties=diffs,
                candidate_question_ids=self._selected_question_ids or None,
                active_only=True,
            )
        except Exception:
            count = 0

        self._setup_available_lbl.setText(f"Sẵn có: {count} câu")
        self._setup_count_spin.setMaximum(max(1, count))

    def _on_pick_pool(self) -> None:
        bank_id = self._setup_bank_combo.current_bank_id()
        if bank_id is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ngân hàng.")
            return

        dlg = QuestionPoolPickerDialog(
            bank_id,
            initial_ids=self._selected_question_ids,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selection = dlg.selection()
        self._selected_question_ids = selection.question_ids
        self._setup_pool_summary.setText(f"Đang dùng: {selection.selected_count} câu hỏi đã chọn")
        self._update_setup_available_count()

    def _create_runtime_quiz_from_setup(self) -> bool:
        bank_id = self._setup_bank_combo.current_bank_id()
        if bank_id is None:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ngân hàng câu hỏi.")
            return False

        mode = self._setup_mode_combo.currentData()
        if mode not in (QuizMode.EXAM.value, QuizMode.PRACTICE.value, QuizMode.STUDY.value):
            QMessageBox.warning(self, "Thiếu thông tin", "Chế độ làm bài không hợp lệ.")
            return False

        types = self._setup_selected_types()
        if not types:
            QMessageBox.warning(self, "Thiếu thông tin", "Chọn ít nhất một loại câu hỏi.")
            return False

        diffs = self._setup_selected_difficulties()
        if not diffs:
            QMessageBox.warning(self, "Thiếu thông tin", "Chọn ít nhất một mức độ.")
            return False

        count = self._setup_count_spin.value()
        time_limit = self._setup_time_spin.value() if mode in (QuizMode.EXAM.value, QuizMode.PRACTICE.value) else None

        try:
            questions = self._builder_facade.list_eligible_questions(
                bank_id=bank_id,
                question_types=types,
                difficulties=diffs,
                candidate_question_ids=self._selected_question_ids or None,
                active_only=True,
                shuffle=self._setup_shuffle_q.isChecked(),
            )
            if not questions:
                QMessageBox.warning(
                    self,
                    "Không đủ câu hỏi",
                    "Không tìm thấy câu hỏi phù hợp với bộ lọc đã chọn.",
                )
                return False
            if len(questions) < count:
                reply = QMessageBox.question(
                    self,
                    "Không đủ câu hỏi",
                    f"Chỉ tìm được {len(questions)} câu (yêu cầu {count}).\n"
                    "Tiếp tục với số câu hiện có?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return False

            snapshots = self._selector.build_creation_snapshots(
                questions,
                shuffle_options=self._setup_shuffle_opts.isChecked(),
            )
            config = QuizConfig(
                title=f"Bài làm {self._setup_bank_combo.currentText()}",
                bank_id=bank_id,
                mode=mode,
                time_limit_minutes=time_limit,
                question_count=len(snapshots),
                shuffle_questions=self._setup_shuffle_q.isChecked(),
                shuffle_options=self._setup_shuffle_opts.isChecked(),
            )
            quiz = self._builder_facade.create_quiz(config, snapshots)

            self._pending_quiz_id = quiz.id
            self._quiz_info = self._runner_controller.load_quiz_info(quiz.id)
            return self._quiz_info is not None
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi cấu hình", str(exc))
            return False
        except Exception as exc:
            logger.error(f"Runtime quiz creation failed: {exc}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo bài làm:\n{exc}")
            return False
