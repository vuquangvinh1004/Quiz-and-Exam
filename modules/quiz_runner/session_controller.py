"""Runtime controller for quiz runner data/session operations.

Encapsulates persistence-related operations so the view layer does not
manipulate DB session/query details directly.
"""
from __future__ import annotations

from core.database.models import Question
from core.database.session import get_session
from core.domain.services.quiz_service import (
    GradedRow,
    QuizInfoDTO,
    QuizQuestionSnapshot,
    QuizService,
)
from core.domain.services.submission_service import SubmissionService, SubmissionSettings


class QuizRunnerSessionController:
    """Persistence orchestration for quiz runner lifecycle."""

    def __init__(self, quiz_service: QuizService | None = None) -> None:
        self._quiz_service = quiz_service or QuizService()

    def load_quiz_info(self, quiz_id: int) -> QuizInfoDTO | None:
        """Return setup info for a quiz id, or None when loading fails."""
        try:
            with get_session() as session:
                return self._quiz_service.get_quiz_info(session, quiz_id)
        except Exception:
            return None

    def prepare_attempt(self, quiz_id: int) -> tuple[list[QuizQuestionSnapshot], int]:
        """Load snapshot questions and create a new attempt."""
        with get_session() as session:
            qq_orm = self._quiz_service.get_quiz_questions(session, quiz_id)
            q_code_map: dict[int, str | None] = {}
            for qq in qq_orm:
                q = session.get(Question, qq.question_id)
                q_code_map[qq.question_id] = q.question_code if q else None

            snapshots: list[QuizQuestionSnapshot] = []
            for qq in qq_orm:
                cfg = qq.get_snapshot_answer_config()
                snapshots.append(
                    QuizQuestionSnapshot(
                        quiz_question_id=qq.id,
                        order=qq.question_order,
                        content=qq.snapshot_content or "",
                        type=qq.snapshot_type,
                        hint=qq.snapshot_hint or "",
                        explanation=qq.snapshot_explanation or "",
                        point_value=qq.snapshot_point_value or 1.0,
                        options=qq.get_snapshot_options() or [],
                        accepted_answers=qq.get_snapshot_accepted_answers(),
                        case_sensitive=cfg.get("case_sensitive", False),
                        trim_whitespace=cfg.get("trim_whitespace", True),
                        question_code=q_code_map.get(qq.question_id),
                    )
                )

            attempt = self._quiz_service.create_attempt(session, quiz_id)
            return snapshots, attempt.id

    def autosave_answers(self, attempt_id: int, answers: dict[int, dict]) -> None:
        if not answers:
            return
        with get_session() as session:
            self._quiz_service.autosave_answers(session, attempt_id, answers)

    def finalize_attempt(
        self,
        attempt_id: int,
        status: str,
        graded_rows: list[GradedRow],
        duration_seconds: int,
    ) -> None:
        with get_session() as session:
            self._quiz_service.finalize_attempt(
                session,
                attempt_id,
                status,
                graded_rows,
                duration_seconds,
            )

    @staticmethod
    def load_submission_settings(submission_service: SubmissionService) -> SubmissionSettings:
        try:
            with get_session() as session:
                return submission_service.load_settings(session)
        except Exception:
            return SubmissionSettings()
