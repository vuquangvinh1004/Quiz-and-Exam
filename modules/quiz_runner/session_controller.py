"""Runtime controller for quiz runner data/session operations.

Encapsulates persistence-related operations so the view layer does not
manipulate DB session/query details directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.database.models import Question
from core.database.session import get_session
from core.domain.services.quiz_service import (
    AttemptResumeDTO,
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

    def prepare_attempt(
        self,
        quiz_id: int,
        *,
        submitter_name: str = "",
        submitter_id: str = "",
        remaining_seconds: int | None = None,
    ) -> "PreparedAttemptSession":
        """Load snapshot questions and create a new attempt."""
        with get_session() as session:
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

    def load_resumable_attempt(self, quiz_id: int) -> "PreparedAttemptSession | None":
        """Load the latest resumable in-progress attempt for one quiz."""
        with get_session() as session:
            resume = self._quiz_service.get_resumable_attempt(session, quiz_id)
            if resume is None:
                return None
            qq_orm = self._quiz_service.get_quiz_questions(session, quiz_id)
            snapshots = self._build_snapshots(session, qq_orm)
            return PreparedAttemptSession.from_resume(resume, snapshots)

    def delete_attempt(self, attempt_id: int) -> bool:
        """Delete one attempt, typically when user discards stale progress."""
        with get_session() as session:
            return self._quiz_service.delete_attempt(session, attempt_id)

    def autosave_progress(
        self,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        if not answers and remaining_seconds is None:
            return
        with get_session() as session:
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


@dataclass
class PreparedAttemptSession:
    """Typed runtime bundle returned to the quiz runner view."""

    snapshots: list[QuizQuestionSnapshot]
    attempt_id: int
    answers: dict[int, dict]
    started_at: datetime | None
    remaining_seconds: int | None
    submitter_name: str = ""
    submitter_id: str = ""
    resumed: bool = False

    @classmethod
    def from_resume(
        cls,
        resume: AttemptResumeDTO,
        snapshots: list[QuizQuestionSnapshot],
    ) -> "PreparedAttemptSession":
        return cls(
            snapshots=snapshots,
            attempt_id=resume.attempt_id,
            answers=resume.answers,
            started_at=resume.started_at,
            remaining_seconds=resume.remaining_seconds,
            submitter_name=resume.submitter_name,
            submitter_id=resume.submitter_id,
            resumed=True,
        )
