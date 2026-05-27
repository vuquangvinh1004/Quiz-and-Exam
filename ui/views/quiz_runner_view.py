"""Quiz runner view for setup, attempt runtime, and finalize flow."""
from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.domain.services.quiz_service import (
    QuizQuestionSnapshot,
    QuizService,
)
from core.domain.services.submission_service import (
    SubmissionService,
)
from core.utils.constants import BLANK_PLACEHOLDER, AttemptStatus, QuizMode
from core.utils.logger import get_logger
from modules.grading.result_builder import AttemptResultData
from modules.quiz_builder.selector import QuestionSelector
from modules.quiz_runner.mode_policy import ModePolicy
from modules.quiz_runner.session_controller import QuizRunnerSessionController
from modules.quiz_runner.session_state import QuizRunnerState
from modules.quiz_runner.submit_handler import build_graded_result
from modules.quiz_runner.timer_controller import QuizTimerController
from ui.dialogs.submit_dialog import SubmitDialog
from ui.dialogs.submitter_info_dialog import SubmitterInfoDialog
from ui.views.quiz_runner_layout import (
    build_done_panel,
    build_running_panel,
    build_setup_panel,
)
from ui.views.quiz_runner_setup_mixin import QuizRunnerSetupMixin
from ui.views.quiz_runner_state_proxy import QuizRunnerStateProxyMixin
from ui.widgets.quiz_answer_renderer import QuizAnswerRenderer
from ui.widgets.quiz_result_presenter import QuizResultPresenter

logger = get_logger(__name__)

_PANEL_SETUP = 0
_PANEL_RUNNING = 1
_PANEL_DONE = 2

_AUTOSAVE_INTERVAL_MS = 30_000  # 30 seconds


class QuizRunnerView(QuizRunnerSetupMixin, QuizRunnerStateProxyMixin, QWidget):
    """Quiz runner with DB-backed questions, timer, navigation and submission."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Services
        self._quiz_service = QuizService()
        self._submission_service = SubmissionService()
        self._runner_controller = QuizRunnerSessionController(self._quiz_service)
        self._selector = QuestionSelector()
        self._state = QuizRunnerState()
        self._selected_question_ids: list[int] = []

        self._answer_renderer = QuizAnswerRenderer(self)

        # Timers
        self._timer_controller = QuizTimerController(self)
        self._timer_controller.tick.connect(self._on_timer_tick)
        self._timer_controller.time_up.connect(self._on_time_up)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(_AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._autosave)

        self._build_ui()

    def load_quiz(self, quiz_id: int) -> None:
        """Called by MainWindow after QuizBuilderView emits quiz_started."""
        self._pending_quiz_id = quiz_id
        self._quiz_info = self._runner_controller.load_quiz_info(quiz_id)
        if self._quiz_info is None:
            logger.error(f"load_quiz failed for quiz_id={quiz_id}")
        self._update_setup_panel()
        self._stack.setCurrentIndex(_PANEL_SETUP)

    def refresh(self) -> None:
        """Public refresh entrypoint for MainWindow F5 contract."""
        if self._pending_quiz_id is not None:
            self._quiz_info = self._runner_controller.load_quiz_info(self._pending_quiz_id)
        self._setup_bank_combo.reload()
        self._update_setup_available_count()
        self._update_setup_panel()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_setup_panel())    # 0
        self._stack.addWidget(self._build_running_panel())  # 1
        self._stack.addWidget(self._build_done_panel())     # 2

        # Setup panel interactions
        self._setup_mode_combo.currentIndexChanged.connect(self._on_setup_mode_changed)
        self._setup_bank_combo.currentIndexChanged.connect(self._on_setup_bank_changed)
        self._setup_count_spin.valueChanged.connect(self._update_setup_available_count)
        for cb in (
            self._setup_cb_mc,
            self._setup_cb_ma,
            self._setup_cb_blank,
            self._setup_cb_sa,
            self._setup_cb_easy,
            self._setup_cb_medium,
            self._setup_cb_hard,
        ):
            cb.stateChanged.connect(self._update_setup_available_count)
        self._setup_pool_btn.clicked.connect(self._on_pick_pool)

        self._setup_bank_combo.reload()
        self._on_setup_mode_changed()
        self._update_setup_available_count()
        self._update_setup_panel()

    def _build_setup_panel(self) -> QWidget:
        return build_setup_panel(self)

    def _update_setup_panel(self) -> None:
        self._setup_title.setText("Làm bài kiểm tra")
        self._setup_info.setText(
            "Chọn ngân hàng, chế độ, giới hạn thời gian và bộ lọc câu hỏi, "
            "sau đó nhấn <b>Bắt đầu làm bài</b>."
        )
        self._setup_start_btn.setEnabled(True)

    def _build_running_panel(self) -> QWidget:
        return build_running_panel(self)

    def _build_done_panel(self) -> QWidget:
        return build_done_panel(self)

    # ------------------------------------------------------------------
    # Session start
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if not self._create_runtime_quiz_from_setup():
            return

        info = self._quiz_info
        if info is None or self._pending_quiz_id is None:
            QMessageBox.warning(self, "Lỗi", "Không tải được dữ liệu bài làm.")
            return
        self._mode = info.mode

        # EXAM: collect submitter info
        if self._mode == QuizMode.EXAM.value:
            dlg = SubmitterInfoDialog(info.title, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            self._submitter_name = dlg.submitter_name
            self._submitter_id = dlg.submitter_id
        else:
            self._submitter_name = ""
            self._submitter_id = ""

        # Load quiz questions + create attempt
        try:
            self._quiz_questions, self._attempt_id = self._runner_controller.prepare_attempt(
                self._pending_quiz_id
            )
        except Exception as exc:
            logger.error(f"Session start failed: {exc}")
            QMessageBox.critical(self, "Lỗi", f"Không thể bắt đầu bài:\n{exc}")
            return

        # Reset in-memory state
        self._answers = {}
        self._confirmed = set()
        self._current_index = 0
        self._started_at = datetime.now(UTC)
        self._quiz_title = info.title

        self._update_running_header()
        self._show_question(0)
        self._stack.setCurrentIndex(_PANEL_RUNNING)

        if ModePolicy.requires_timer(self._mode):
            time_limit = info.time_limit or 30
            self._timer_controller.start(time_limit * 60)

        self._autosave_timer.start()

    # ------------------------------------------------------------------
    # Running panel logic
    # ------------------------------------------------------------------

    def _update_running_header(self) -> None:
        mode_label = {
            QuizMode.EXAM.value: "Kiểm tra",
            QuizMode.PRACTICE.value: "Luyện tập",
            QuizMode.STUDY.value: "Học tập",
        }.get(self._mode, self._mode)
        self._header_title.setText(f"{self._quiz_title}  [{mode_label}]")

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
            f"Câu {qq.order} / {total}  \u00b7  {_type_label(qtype)}"
            f"  \u00b7  {qq.point_value} điểm"
        )
        from html import escape
        safe_content = escape(qq.content).replace(
            escape(BLANK_PLACEHOLDER),
            '<u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u>'
        )
        self._question_label.setText(safe_content)

        answered_count = len([p for p in self._answers.values() if p])
        self._progress_label.setText(
            f"Câu {index + 1}/{total}  \u00b7  Đã trả lời: {answered_count}"
        )

        # Hint (PRACTICE and STUDY only)
        hint = qq.hint
        if hint and ModePolicy.show_hint(self._mode):
            self._hint_label.setText(f"\U0001f4a1 {hint}")
            self._hint_label.show()
        else:
            self._hint_label.hide()

        self._answer_renderer.render_question(qq)

        payload = self._answers.get(qid)
        if payload:
            self._answer_renderer.restore_answer(qtype, payload)

        # STUDY mode state
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

    # -- STUDY mode confirm --------------------------------------------

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

    # -- Navigation ----------------------------------------------------

    def _on_prev(self) -> None:
        self._save_current_answer()
        self._show_question(self._current_index - 1)

    def _on_next(self) -> None:
        self._save_current_answer()
        self._show_question(self._current_index + 1)

    # -- Timer ---------------------------------------------------------

    def _on_timer_tick(self, remaining: int) -> None:
        mins, secs = divmod(remaining, 60)
        self._timer_label.setText(f"\u23f1 {mins:02d}:{secs:02d}")

    def _on_time_up(self) -> None:
        QMessageBox.warning(
            self, "Hết giờ", "Hết thời gian! Bài làm sẽ được nộp tự động."
        )
        self._finalize_session(time_up=True)

    # -- Autosave ------------------------------------------------------

    def _autosave(self) -> None:
        if not self._attempt_id or not self._answers:
            return
        try:
            self._runner_controller.autosave_answers(self._attempt_id, self._answers)
            logger.debug(f"Autosaved {len(self._answers)} answers for attempt {self._attempt_id}")
        except Exception as exc:
            logger.warning(f"Autosave failed: {exc}")

    # -- Submit --------------------------------------------------------

    def _on_submit_clicked(self) -> None:
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
        self._timer_controller.stop()
        self._autosave_timer.stop()

        graded_rows, result_data = build_graded_result(
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
                AttemptStatus.TIME_UP.value
                if time_up
                else AttemptStatus.SUBMITTED.value
            )
            try:
                self._runner_controller.finalize_attempt(
                    self._attempt_id,
                    status,
                    graded_rows,
                    result_data.duration_seconds,
                )
            except Exception as exc:
                logger.error(f"finalize_attempt failed: {exc}")

        if self._mode == QuizMode.EXAM.value:
            self._show_exam_submit_dialog(result_data)
        else:
            self._show_non_exam_summary(result_data)

    # -- Result display ------------------------------------------------

    def _show_exam_submit_dialog(self, data: AttemptResultData) -> None:
        cfg = self._runner_controller.load_submission_settings(self._submission_service)
        dlg = SubmitDialog(data, cfg, self._submission_service, parent=self)
        dlg.exec()
        self._show_done(data)

    def _show_non_exam_summary(self, data: AttemptResultData) -> None:
        QuizResultPresenter.show_non_exam_summary(self, data)
        self._show_done(data)

    def _show_done(self, data: AttemptResultData) -> None:
        self._done_label.setText("\u2713 Đã hoàn thành bài.")
        self._done_summary.setText(
            QuizResultPresenter.build_done_summary_html(data, self._mode)
        )
        self._stack.setCurrentIndex(_PANEL_DONE)

    # -- Reset ---------------------------------------------------------

    def _reset_to_setup(self) -> None:
        self._timer_controller.stop()
        self._autosave_timer.stop()
        self._state.reset_all()
        self._update_setup_panel()
        self._stack.setCurrentIndex(_PANEL_SETUP)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _type_label(qtype: str) -> str:
    return {
        "MC": "Multiple Choice",
        "MA": "Multiple Answer",
        "BLANK": "Điền khuyết",
        "SA": "Trả lời ngắn",
    }.get(qtype, qtype)

