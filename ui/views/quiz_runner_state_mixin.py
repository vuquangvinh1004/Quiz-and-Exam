"""Question rendering and navigation mixin for QuizRunnerView."""
from __future__ import annotations

from PySide6.QtCore import Qt

from core.domain.services.quiz_service import QuizQuestionSnapshot, QuizService
from core.utils.constants import BLANK_PLACEHOLDER, QuizMode
from modules.quiz_runner.mode_policy import ModePolicy
from ui.widgets.quiz_result_presenter import QuizResultPresenter


def _type_label(qtype: str) -> str:
    return {
        "MC": "Trắc nghiệm 1 đáp án",
        "MA": "Trắc nghiệm nhiều đáp án",
        "TF": "Đúng/Sai",
        "BLANK": "Điền vào chỗ trống",
        "SA": "Trả lời ngắn",
        "ES": "Tự luận",
    }.get(qtype, qtype)


class QuizRunnerStateMixin:
    """Render, navigation and transient answer-state behaviors."""

    def _update_running_header(self) -> None:
        mode_label = {
            QuizMode.EXAM.value: "Kiểm tra",
            QuizMode.PRACTICE.value: "Luyện tập",
            QuizMode.STUDY.value: "Ôn tập",
        }.get(self._mode, self._mode)
        self._header_title.setText(f"{self._quiz_title}  [{mode_label}]")
        self._resume_badge.setVisible(self._resumed_from_autosave)

        if self._mode == QuizMode.EXAM.value:
            self._submitter_bar.show()
            self._submitter_info_label.setText(
                f"Người làm bài: <b>{self._submitter_name}</b>"
                f"  |  ID: <b>{self._submitter_id}</b>"
            )
        else:
            self._submitter_bar.hide()

        if ModePolicy.requires_timer(self._mode):
            self._timer_label.show()
        else:
            self._timer_label.hide()

    def _show_question(self, index: int) -> None:
        if not self._quiz_questions:
            self._question_label.setText("Không có câu hỏi nào.")
            return
        total = len(self._quiz_questions)
        index = max(0, min(index, total - 1))
        self._current_index = index
        qq = self._quiz_questions[index]
        qid = qq.quiz_question_id
        qtype = qq.type

        self._question_num.setText(
            f"Câu {qq.order} / {total}  ·  {_type_label(qtype)}"
            f"  ·  {qq.point_value} điểm"
        )
        from html import escape

        safe_content = escape(qq.content).replace(
            escape(BLANK_PLACEHOLDER),
            '<u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u>',
        )
        self._question_label.setText(safe_content)

        answered_count = len([p for p in self._answers.values() if p])
        self._progress_label.setText(
            f"Câu {index + 1}/{total}  ·  Đã trả lời: {answered_count}"
        )

        hint = qq.hint
        if hint and ModePolicy.show_hint(self._mode):
            self._hint_label.setText(f"💡 {hint}")
            self._hint_label.show()
        else:
            self._hint_label.hide()

        self._answer_renderer.render_question(qq)

        payload = self._answers.get(qid)
        if payload:
            self._answer_renderer.restore_answer(qtype, payload)
        if self._retry_submit_only:
            self._answer_renderer.set_input_enabled(False)

        is_confirmed = qid in self._confirmed
        if ModePolicy.show_per_question_feedback(self._mode):
            self._confirm_btn.show()
            self._confirm_btn.setEnabled(not is_confirmed)
            if is_confirmed:
                self._answer_renderer.set_input_enabled(False)
                self._show_study_feedback(qq, self._answers.get(qid, {}))
            else:
                self._feedback_label.hide()
                self._answer_renderer.set_input_enabled(True)
        else:
            self._confirm_btn.hide()
            self._feedback_label.hide()

        self._prev_btn.setEnabled(index > 0)
        if ModePolicy.show_per_question_feedback(self._mode):
            self._next_btn.setEnabled(is_confirmed and index < total - 1)
        else:
            self._next_btn.setEnabled(index < total - 1)

    def _get_current_payload(self) -> dict:
        if not self._quiz_questions:
            return {}
        qtype = self._quiz_questions[self._current_index].type
        return self._answer_renderer.current_payload(qtype)

    def _save_current_answer(self) -> None:
        if not self._quiz_questions:
            return
        payload = self._get_current_payload()
        qid = self._quiz_questions[self._current_index].quiz_question_id
        if payload:
            self._answers[qid] = payload
        elif qid in self._answers:
            del self._answers[qid]

    def _on_confirm_study(self) -> None:
        self._save_current_answer()
        qq = self._quiz_questions[self._current_index]
        qid = qq.quiz_question_id
        payload = self._answers.get(qid, {})

        self._confirmed.add(qid)
        self._confirm_btn.setEnabled(False)
        self._answer_renderer.set_input_enabled(False)
        self._show_study_feedback(qq, payload)

        total = len(self._quiz_questions)
        self._next_btn.setEnabled(self._current_index < total - 1)

    def _show_study_feedback(self, qq: QuizQuestionSnapshot, payload: dict) -> None:
        result = QuizService.grade_answer_from_dict(qq, payload)
        explanation = qq.explanation
        text, style = QuizResultPresenter.build_study_feedback(result, explanation)

        self._feedback_label.setText(text)
        self._feedback_label.setTextFormat(Qt.TextFormat.RichText)
        self._feedback_label.setStyleSheet(
            f"font-size: 14px; padding: 10px; border-radius: 4px; {style}"
        )
        self._feedback_label.show()

    def _on_prev(self) -> None:
        self._save_current_answer()
        self._show_question(self._current_index - 1)

    def _on_next(self) -> None:
        self._save_current_answer()
        self._show_question(self._current_index + 1)

    def _on_timer_tick(self, remaining: int) -> None:
        self._remaining_seconds = remaining
        mins, secs = divmod(remaining, 60)
        self._timer_label.setText(f"⏱ {mins:02d}:{secs:02d}")

    def _autosave(self) -> None:
        if not self._attempt_id:
            return
        self._save_current_answer()
        try:
            self._runner_controller.autosave_progress(
                self._attempt_id,
                self._answers,
                self._remaining_seconds,
            )
            self._log_runtime_event(
                "autosave_succeeded",
                attempt_id=self._attempt_id,
                remaining=self._remaining_seconds,
                answered=len(self._answers),
            )
        except Exception as exc:
            self._log_runtime_event(
                "autosave_failed",
                attempt_id=self._attempt_id,
                remaining=self._remaining_seconds,
                error=type(exc).__name__,
            )
            self._log_runtime_event("autosave_error_detail", message=str(exc))

    def _show_done(self, data) -> None:
        self._done_label.setText("✓ Đã hoàn thành bài.")
        self._done_summary.setText(
            QuizResultPresenter.build_done_summary_html(data, self._mode)
        )
        self._stack.setCurrentIndex(2)

    def _reset_to_setup(self) -> None:
        self._timer_controller.stop()
        self._autosave_timer.stop()
        self._state.reset_all()
        self._update_setup_panel()
        self._stack.setCurrentIndex(0)

    def _set_navigation_enabled(self, enabled: bool) -> None:
        self._prev_btn.setEnabled(enabled and self._current_index > 0)
        total = len(self._quiz_questions)
        if ModePolicy.show_per_question_feedback(self._mode):
            is_confirmed = False
            if self._quiz_questions:
                current_qid = self._quiz_questions[self._current_index].quiz_question_id
                is_confirmed = current_qid in self._confirmed
            self._next_btn.setEnabled(
                enabled and is_confirmed and self._current_index < total - 1
            )
            self._confirm_btn.setEnabled(enabled and not is_confirmed)
        else:
            self._next_btn.setEnabled(enabled and self._current_index < total - 1)
        self._submit_btn.setEnabled(enabled)
