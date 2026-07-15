"""Session lifecycle mixin for QuizRunnerView.

This module is now intentionally small: it focuses on start/resume
orchestration and leaves submit/finalize flows to dedicated mixins.
"""
from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtWidgets import QDialog, QMessageBox

from core.utils.constants import QuizMode
from modules.quiz_runner.mode_policy import ModePolicy


def _runner_module():
    from ui.views import quiz_runner_view as runner_module

    return runner_module


class QuizRunnerRuntimeMixin:
    """Runtime start and resume orchestration."""

    def _on_start(self) -> None:
        if not self._create_runtime_quiz_from_setup():
            return

        info = self._quiz_info
        if info is None or self._pending_quiz_id is None:
            QMessageBox.warning(self, "Lỗi", "Không tải được dữ liệu bài làm.")
            return
        self._mode = info.mode

        runtime = self._resolve_runtime_session(info.title)
        if runtime is None:
            return

        self._quiz_questions = runtime.snapshots
        self._attempt_id = runtime.attempt_id
        self._answers = dict(runtime.answers)
        self._confirmed = set()
        self._current_index = 0
        self._started_at = runtime.started_at or datetime.now(UTC)
        self._remaining_seconds = runtime.remaining_seconds
        self._submitter_name = runtime.submitter_name
        self._submitter_id = runtime.submitter_id
        self._resumed_from_autosave = runtime.resumed
        self._finalizing = False
        self._retry_submit_only = False
        self._quiz_title = info.title
        self._submit_btn.setText("Nộp bài")

        self._update_running_header()
        self._show_question(0)
        self._stack.setCurrentIndex(1)

        if ModePolicy.requires_timer(self._mode):
            timer_seconds = runtime.remaining_seconds
            if timer_seconds is None:
                timer_seconds = (info.time_limit or 30) * 60
            self._timer_controller.start(timer_seconds)
            self._remaining_seconds = timer_seconds
            self._on_timer_tick(timer_seconds)

        self._autosave_timer.start()

    def _resolve_runtime_session(self, quiz_title: str):
        if self._pending_quiz_id is None:
            return None

        resumed = self._runner_controller.load_resumable_attempt(self._pending_quiz_id)
        if resumed is not None:
            if not ModePolicy.can_resume_attempt(
                self._mode,
                submitter_name=resumed.submitter_name,
                submitter_id=resumed.submitter_id,
                remaining_seconds=resumed.remaining_seconds,
            ):
                self._log_runtime_event(
                    "resume_invalid",
                    attempt_id=resumed.attempt_id,
                    mode=self._mode,
                    remaining=resumed.remaining_seconds,
                    has_submitter=bool(resumed.submitter_name and resumed.submitter_id),
                )
                QMessageBox.information(
                    self,
                    "Không thể khôi phục bài làm",
                    (
                        "Bài làm đang dở không còn đủ điều kiện để tiếp tục.\n"
                        "Ứng dụng sẽ bỏ tiến độ cũ và tạo phiên mới theo policy hiện tại."
                    ),
                )
                self._runner_controller.delete_attempt(resumed.attempt_id)
                resumed = None

        if resumed is not None:
            reply = QMessageBox.question(
                self,
                "Khôi phục bài làm",
                (
                    "Phát hiện một bài làm đang dở cho bài kiểm tra này.\n"
                    "Chọn Yes để tiếp tục từ autosave gần nhất.\n"
                    "Chọn No để bỏ tiến độ cũ và bắt đầu lại."
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                self._log_runtime_event(
                    "resume_cancelled",
                    attempt_id=resumed.attempt_id,
                    mode=self._mode,
                )
                return None
            if reply == QMessageBox.StandardButton.Yes:
                self._log_runtime_event(
                    "resume_accepted",
                    attempt_id=resumed.attempt_id,
                    mode=self._mode,
                    remaining=resumed.remaining_seconds,
                    answered=len([p for p in resumed.answers.values() if p]),
                )
                return resumed
            self._log_runtime_event(
                "resume_discarded",
                attempt_id=resumed.attempt_id,
                mode=self._mode,
            )
            self._runner_controller.delete_attempt(resumed.attempt_id)

        submitter_name = ""
        submitter_id = ""
        initial_remaining_seconds = (
            (self._quiz_info.time_limit or 30) * 60
            if self._quiz_info and ModePolicy.requires_timer(self._mode)
            else None
        )

        if self._mode == QuizMode.EXAM.value:
            runner_module = _runner_module()
            dlg = runner_module.SubmitterInfoDialog(quiz_title, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self._log_runtime_event(
                    "start_cancelled_submitter_dialog",
                    quiz_id=self._pending_quiz_id,
                    mode=self._mode,
                )
                return None
            submitter_name = dlg.submitter_name
            submitter_id = dlg.submitter_id

        try:
            prepared = self._runner_controller.prepare_attempt(
                self._pending_quiz_id,
                submitter_name=submitter_name,
                submitter_id=submitter_id,
                remaining_seconds=initial_remaining_seconds,
            )
            self._log_runtime_event(
                "attempt_started",
                attempt_id=prepared.attempt_id,
                quiz_id=self._pending_quiz_id,
                mode=self._mode,
                resumed=False,
            )
            return prepared
        except Exception as exc:
            self._log_runtime_event(
                "start_failed",
                quiz_id=self._pending_quiz_id,
                mode=self._mode,
                error=type(exc).__name__,
            )
            self._log_runtime_event("start_error_detail", message=str(exc))
            QMessageBox.critical(self, "Lỗi", f"Không thể bắt đầu bài:\n{exc}")
            return None
