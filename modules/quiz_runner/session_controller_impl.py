"""Implementation helpers for quiz runner session orchestration."""
from __future__ import annotations

from core.database.models import Question
from core.domain.services.quiz_service import (
    AttemptResumeDTO,
    GradedRow,
    QuizInfoDTO,
    QuizQuestionSnapshot,
    QuizService,
)
from core.domain.services.submission_service import SubmissionService, SubmissionSettings
from modules.quiz_runner.session_controller_types import PreparedAttemptSession


class QuizRunnerSessionControllerService:
    """Persistence orchestration for quiz runner lifecycle."""

    def __init__(self, quiz_service: QuizService | None = None) -> None:
        self._quiz_service = quiz_service or QuizService()

    @staticmethod
    def _get_session_factory():
        from modules.quiz_runner import session_controller as controller_module

        return controller_module.get_session

    def load_quiz_info(self, quiz_id: int) -> QuizInfoDTO | None:
        try:
            with self._get_session_factory()() as session:
                return self._quiz_service.get_quiz_info(session, quiz_id)
        except (RuntimeError, ValueError, OSError):
            return None

    def prepare_attempt(
        self,
        quiz_id: int,
        *,
        submitter_name: str = "",
        submitter_id: str = "",
        remaining_seconds: int | None = None,
    ) -> PreparedAttemptSession:
        with self._get_session_factory()() as session:
            qq_orm = self._quiz_service.get_quiz_questions(session, quiz_id)
            snapshots = self._build_snapshots(session, qq_orm)
            attempt = self._quiz_service.create_attempt(
                session,
                quiz_id,
                submitter_name=submitter_name,
                submitter_id=submitter_id,
                remaining_seconds=remaining_seconds,
            )
            return PreparedAttemptSession(
                snapshots=snapshots,
                attempt_id=attempt.id,
                answers={},
                started_at=attempt.started_at,
                remaining_seconds=remaining_seconds,
                submitter_name=submitter_name,
                submitter_id=submitter_id,
                resumed=False,
            )

    def load_resumable_attempt(self, quiz_id: int) -> PreparedAttemptSession | None:
        with self._get_session_factory()() as session:
            resume = self._quiz_service.get_resumable_attempt(session, quiz_id)
            if resume is None:
                return None
            qq_orm = self._quiz_service.get_quiz_questions(session, quiz_id)
            snapshots = self._build_snapshots(session, qq_orm)
            return PreparedAttemptSession.from_resume(resume, snapshots)

    def delete_attempt(self, attempt_id: int) -> bool:
        with self._get_session_factory()() as session:
            return self._quiz_service.delete_attempt(session, attempt_id)

    def autosave_progress(
        self,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        if not answers and remaining_seconds is None:
            return
        with self._get_session_factory()() as session:
            self._quiz_service.autosave_progress(
                session,
                attempt_id,
                answers,
                remaining_seconds,
            )

    def finalize_attempt(
        self,
        attempt_id: int,
        status: str,
        graded_rows: list[GradedRow],
        duration_seconds: int,
    ) -> None:
        with self._get_session_factory()() as session:
            self._quiz_service.finalize_attempt(
                session,
                attempt_id,
                status,
                graded_rows,
                duration_seconds,
            )

    @staticmethod
    def load_submission_settings(
        submission_service: SubmissionService,
    ) -> SubmissionSettings:
        try:
            from modules.quiz_runner import session_controller as controller_module

            with controller_module.get_session() as session:
                return submission_service.load_settings(session)
        except (RuntimeError, ValueError, OSError):
            return SubmissionSettings()

    @staticmethod
    def _build_snapshots(session, qq_orm) -> list[QuizQuestionSnapshot]:
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
        return snapshots
