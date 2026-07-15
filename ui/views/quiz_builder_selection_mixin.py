"""Selection/export state helpers for QuizBuilderView."""
from __future__ import annotations

from core.domain.services.quiz_service import QuizCreationSnapshot
from ui.widgets.exam_export_panel import ExportSelectionState


class QuizBuilderSelectionMixin:
    """Typed export-state helpers exposed by the view."""

    def _build_creation_snapshots(self, questions: list) -> list[QuizCreationSnapshot]:
        """Keep typed create-quiz snapshot contract available at the view boundary."""
        return self._selector.build_creation_snapshots(
            questions,
            shuffle_options=self._cb_shuffle_opts.isChecked(),
        )

    def _get_selection_state(self) -> ExportSelectionState:
        return ExportSelectionState(
            bank_id=self._current_bank_id(),
            exam_count=self._exam_count_spin.value(),
            question_count=self._total_questions_from_quota(),
            candidate_question_ids=list(self._selected_question_ids),
            chapter_quota=self._active_quota_dict(
                self._chapter_spins, self._quota_cb_chapter.isChecked()
            ),
            type_quota=self._active_quota_dict(
                self._type_spins, self._quota_cb_type.isChecked()
            ),
            clo_quota=self._active_quota_dict(
                self._clo_spins, self._quota_cb_clo.isChecked()
            ),
            shuffle_questions=self._cb_shuffle_q.isChecked(),
            shuffle_options=self._cb_shuffle_opts.isChecked(),
            no_repeat_between_exams=self._cb_no_repeat_between_exams.isChecked(),
            time_limit_minutes=self._duration_spin.value(),
        )
