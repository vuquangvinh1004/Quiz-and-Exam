"""Submit/finalize workflow mixin for QuizRunnerView."""
from __future__ import annotations

from modules.quiz_runner.mode_policy import ModePolicy
from ui.widgets.quiz_result_presenter import QuizResultPresenter


def _runner_module():
    from ui.views import quiz_runner_view as runner_module

    return runner_module


class QuizRunnerFinalizeMixin:
    """Submit, autosave and recovery behaviors."""

    def _on_time_up(self) -> None:
        self._log_runtime_event(
            "time_up",
            attempt_id=self._attempt_id,
            mode=self._mode,
            answered=len([p for p in self._answers.values() if p]),
            total=len(self._quiz_questions),
        )
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(
            self, "Hết giờ", "Hết thời gian! Bài làm sẽ được nộp tự động."
        )
        self._finalize_session(time_up=True)

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

    def _on_submit_clicked(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        if self._finalizing:
            return
        self._log_runtime_event(
            "submit_clicked",
            attempt_id=self._attempt_id,
            mode=self._mode,
            retry_only=self._retry_submit_only,
        )
        self._save_current_answer()
        total = len(self._quiz_questions)
        answered = len([p for p in self._answers.values() if p])
        if answered < total:
            reply = QMessageBox.question(
                self,
                "Xác nhận nộp bài",
                f"Bạn mới trả lời {answered}/{total} câu.\nBạn có chắc muốn nộp bài không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._finalize_session(time_up=False)

    def _finalize_session(self, *, time_up: bool) -> None:
        from PySide6.QtWidgets import QMessageBox

        if self._finalizing:
            return

        self._finalizing = True
        self._set_navigation_enabled(False)
        self._save_current_answer()
        self._timer_controller.stop()
        self._autosave_timer.stop()
        self._log_runtime_event(
            "finalize_started",
            attempt_id=self._attempt_id,
            mode=self._mode,
            time_up=time_up,
            retry_only=self._retry_submit_only,
            answered=len([p for p in self._answers.values() if p]),
            total=len(self._quiz_questions),
            remaining=self._remaining_seconds,
        )

        if self._attempt_id:
            try:
                self._runner_controller.autosave_progress(
                    self._attempt_id,
                    self._answers,
                    0 if time_up else self._remaining_seconds,
                )
            except Exception as exc:
                self._log_runtime_event(
                    "finalize_presave_failed",
                    attempt_id=self._attempt_id,
                    mode=self._mode,
                    time_up=time_up,
                    error=type(exc).__name__,
                )
                self._log_runtime_event("finalize_presave_error_detail", message=str(exc))

        runner_module = _runner_module()
        graded_rows, result_data = runner_module.build_graded_result(
            self._quiz_questions,
            self._answers,
            self._started_at,
            self._submitter_name,
            self._submitter_id,
            self._quiz_title,
            self._mode,
        )

        if self._attempt_id:
            status = (
                "TIME_UP" if time_up else "SUBMITTED"
            )
            try:
                self._runner_controller.finalize_attempt(
                    self._attempt_id,
                    status,
                    graded_rows,
                    result_data.duration_seconds,
                )
            except Exception as exc:
                self._log_runtime_event(
                    "finalize_failed",
                    attempt_id=self._attempt_id,
                    mode=self._mode,
                    time_up=time_up,
                    retry_only=self._retry_submit_only,
                    error=type(exc).__name__,
                )
                self._log_runtime_event("finalize_error_detail", message=str(exc))
                self._recover_after_finalize_failure(time_up=time_up)
                QMessageBox.critical(
                    self,
                    "Chưa thể hoàn tất nộp bài",
                    self._finalize_failure_message(time_up=time_up),
                )
                return

        self._log_runtime_event(
            "finalize_succeeded",
            attempt_id=self._attempt_id,
            mode=self._mode,
            time_up=time_up,
            duration=result_data.duration_seconds,
        )
        if self._mode == "EXAM":
            self._show_exam_submit_dialog(result_data)
        else:
            self._show_non_exam_summary(result_data)
        self._finalizing = False

    def _show_exam_submit_dialog(self, data: AttemptResultData) -> None:
        runner_module = _runner_module()
        cfg = self._runner_controller.load_submission_settings(self._submission_service)
        dlg = runner_module.SubmitDialog(data, cfg, self._submission_service, parent=self)
        dlg.exec()
        self._show_done(data)

    def _show_non_exam_summary(self, data: AttemptResultData) -> None:
        QuizResultPresenter.show_non_exam_summary(self, data)
        self._show_done(data)

    def _recover_after_finalize_failure(self, *, time_up: bool) -> None:
        self._finalizing = False
        self._retry_submit_only = bool(
            time_up and ModePolicy.lock_answer_editing_after_time_up_finalize_failure(self._mode)
        )
        allow_interaction = not self._retry_submit_only
        self._set_navigation_enabled(allow_interaction)
        if allow_interaction:
            self._autosave_timer.start()
        if ModePolicy.requires_timer(self._mode) and not time_up:
            remaining = self._remaining_seconds or 0
            if remaining > 0:
                self._timer_controller.start(remaining)
                self._on_timer_tick(remaining)
            else:
                self._timer_label.setText("⏱ 00:00")
        elif ModePolicy.requires_timer(self._mode):
            self._remaining_seconds = 0
            self._timer_label.setText("⏱ 00:00")
        if self._retry_submit_only:
            self._answer_renderer.set_input_enabled(False)
            self._submit_btn.setEnabled(True)
            self._submit_btn.setText("Thử nộp lại")
        else:
            self._submit_btn.setText("Nộp bài")
        self._log_runtime_event(
            "finalize_retry_ready",
            attempt_id=self._attempt_id,
            mode=self._mode,
            retry_only=self._retry_submit_only,
            time_up=time_up,
            remaining=self._remaining_seconds,
        )

    def _finalize_failure_message(self, *, time_up: bool) -> str:
        if time_up and ModePolicy.lock_answer_editing_after_time_up_finalize_failure(
            self._mode
        ):
            return (
                "Đã hết giờ nhưng hệ thống chưa ghi nhận được kết quả.\n"
                "Câu trả lời đã bị khóa theo policy của chế độ Kiểm tra.\n"
                "Bạn có thể nhấn 'Thử nộp lại' để gửi lại cùng bài làm."
            )
        return (
            "Không thể ghi nhận kết quả lúc này.\n"
            "Bài làm đã được giữ ở trạng thái đang làm để bạn có thể thử lại."
        )
