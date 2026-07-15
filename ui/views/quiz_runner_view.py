"""Quiz runner view for setup, attempt runtime, and finalize flow."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QStackedWidget, QVBoxLayout, QWidget

from core.domain.services.quiz_service import QuizQuestionSnapshot, QuizService
from core.domain.services.submission_service import SubmissionService
from core.utils.logger import get_logger
from modules.grading.result_builder import AttemptResultData
from modules.quiz_builder.selector import QuestionSelector
from modules.quiz_runner.session_controller import QuizRunnerSessionController
from modules.quiz_runner.session_state import QuizRunnerState
from modules.quiz_runner.submit_handler import build_graded_result
from modules.quiz_runner.timer_controller import QuizTimerController
from ui.dialogs.submit_dialog import SubmitDialog
from ui.dialogs.submitter_info_dialog import SubmitterInfoDialog
from ui.facades.quiz_builder_facade import QuizBuilderFacade
from ui.widgets.quiz_answer_renderer import QuizAnswerRenderer
from ui.views.quiz_runner_layout import (
    build_done_panel,
    build_running_panel,
    build_setup_panel,
)
from ui.views.quiz_runner_finalize_mixin import QuizRunnerFinalizeMixin
from ui.views.quiz_runner_runtime_mixin import QuizRunnerRuntimeMixin
from ui.views.quiz_runner_setup_mixin import QuizRunnerSetupMixin
from ui.views.quiz_runner_state_mixin import QuizRunnerStateMixin
from ui.views.quiz_runner_state_proxy import QuizRunnerStateProxyMixin

logger = get_logger(__name__)


class QuizRunnerView(
    QuizRunnerSetupMixin,
    QuizRunnerStateMixin,
    QuizRunnerRuntimeMixin,
    QuizRunnerFinalizeMixin,
    QuizRunnerStateProxyMixin,
    QWidget,
):
    """Quiz runner with DB-backed questions, timer, navigation and submission."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._quiz_service = QuizService()
        self._submission_service = SubmissionService()
        self._runner_controller = QuizRunnerSessionController(self._quiz_service)
        self._selector = QuestionSelector()
        self._builder_facade = QuizBuilderFacade(self._selector)
        self._state = QuizRunnerState()
        self._selected_question_ids: list[int] = []

        self._answer_renderer = QuizAnswerRenderer(self)

        self._timer_controller = QuizTimerController(self)
        self._timer_controller.tick.connect(self._on_timer_tick)
        self._timer_controller.time_up.connect(self._on_time_up)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)
        self._autosave_timer.timeout.connect(self._autosave)

        self._build_ui()

    def _log_runtime_event(self, event: str, **context) -> None:
        parts = [f"event={event}"]
        for key in sorted(context):
            parts.append(f"{key}={context[key]}")
        if hasattr(logger, "info"):
            logger.info(" ".join(parts))
        elif hasattr(logger, "warning"):
            logger.warning(" ".join(parts))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_setup_panel())    # 0
        self._stack.addWidget(self._build_running_panel())  # 1
        self._stack.addWidget(self._build_done_panel())     # 2

        self._setup_mode_combo.currentIndexChanged.connect(self._on_setup_mode_changed)
        self._setup_bank_combo.currentIndexChanged.connect(self._on_setup_bank_changed)
        self._setup_count_spin.valueChanged.connect(self._update_setup_available_count)
        for cb in (
            self._setup_cb_mc,
            self._setup_cb_ma,
            self._setup_cb_tf,
            self._setup_cb_blank,
            self._setup_cb_sa,
            self._setup_cb_crq,
            *self._setup_difficulty_cbs,
        ):
            cb.stateChanged.connect(self._update_setup_available_count)
        self._setup_pool_btn.clicked.connect(self._on_pick_pool)

        self._setup_bank_combo.reload()
        self._on_setup_mode_changed()
        self._update_setup_available_count()
        self._update_setup_panel()

    def _build_setup_panel(self) -> QWidget:
        return build_setup_panel(self)

    def _build_running_panel(self) -> QWidget:
        return build_running_panel(self)

    def _build_done_panel(self) -> QWidget:
        return build_done_panel(self)

    def _update_setup_panel(self) -> None:
        self._setup_title.setText("Làm bài kiểm tra")
        self._setup_info.setText(
            "Chọn ngân hàng, chế độ, giới hạn thời gian và bộ lọc câu hỏi, "
            "sau đó nhấn <b>Bắt đầu làm bài</b>."
        )
        self._setup_start_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # External entrypoints
    # ------------------------------------------------------------------

    def load_quiz(self, quiz_id: int) -> None:
        """Called by MainWindow after QuizBuilderView emits quiz_started."""
        self._pending_quiz_id = quiz_id
        self._quiz_info = self._runner_controller.load_quiz_info(quiz_id)
        if self._quiz_info is None:
            logger.error(f"load_quiz failed for quiz_id={quiz_id}")
        self._update_setup_panel()
        self._stack.setCurrentIndex(0)

    def refresh(self) -> None:
        """Public refresh entrypoint for MainWindow F5 contract."""
        if self._pending_quiz_id is not None:
            self._quiz_info = self._runner_controller.load_quiz_info(self._pending_quiz_id)
        self._setup_bank_combo.reload()
        self._update_setup_available_count()
        self._update_setup_panel()
