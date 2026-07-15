"""Quiz builder view facade."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from core.domain.services.quiz_service import QuizCreationSnapshot
from modules.quiz_builder.selector import QuestionSelector
from ui.facades.quiz_builder_facade import QuizBuilderFacade
from ui.views.quiz_builder_layout_mixin import QuizBuilderLayoutMixin
from ui.views.quiz_builder_quota_mixin import QuizBuilderQuotaMixin
from ui.views.quiz_builder_selection_mixin import QuizBuilderSelectionMixin


class QuizBuilderView(
    QuizBuilderLayoutMixin,
    QuizBuilderQuotaMixin,
    QuizBuilderSelectionMixin,
    QWidget,
):
    """Exam generation and export view."""

    # Kept for backward-compat with smoke tests and legacy wiring.
    quiz_started = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selector = QuestionSelector()
        self._builder_facade = QuizBuilderFacade(self._selector)
        self._selected_question_ids: list[int] = []

        self._chapter_spins: dict[str, object] = {}
        self._type_spins: dict[str, object] = {}
        self._clo_spins: dict[tuple[str, str], object] = {}
        self._chapter_available: dict[str, object] = {}
        self._type_available: dict[str, object] = {}
        self._clo_available: dict[tuple[str, str], object] = {}
        self._chapter_ratio: dict[str, object] = {}
        self._type_ratio: dict[str, object] = {}
        self._clo_ratio: dict[tuple[str, str], object] = {}
        self._quota_group_enabled: dict[str, object] = {}

        self._build_ui()

    def _build_creation_snapshots(self, questions: list) -> list[QuizCreationSnapshot]:
        return self._selector.build_creation_snapshots(
            questions,
            shuffle_options=self._cb_shuffle_opts.isChecked(),
        )

    def refresh(self) -> None:
        self._load_banks()


__all__ = ["QuizBuilderView"]
