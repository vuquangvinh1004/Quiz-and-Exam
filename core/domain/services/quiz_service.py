"""Quiz lifecycle service: create quizzes, manage attempts and answers."""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.database.models import Attempt, Quiz, QuizQuestion
from core.domain.services.quiz_service_impl import (
    QuizAttemptService,
    QuizCatalogService,
    QuizGradingService,
)
from core.domain.services.quiz_service_types import (
    AttemptResumeDTO,
    GradedRow,
    QuizConfig,
    QuizCreationSnapshot,
    QuizInfoDTO,
    QuizQuestionSnapshot,
)
from modules.grading.evaluators import GradeResult


class QuizService:
    """Facade over quiz catalog, attempt lifecycle and grading helpers."""

    def create_quiz(
        self,
        session: Session,
        config: QuizConfig,
        question_snapshots: list[QuizCreationSnapshot | dict],
    ) -> Quiz:
        return QuizCatalogService.create_quiz(session, config, question_snapshots)

    def get_quiz(self, session: Session, quiz_id: int) -> Quiz:
        return QuizCatalogService.get_quiz(session, quiz_id)

    def get_quiz_info(self, session: Session, quiz_id: int) -> QuizInfoDTO:
        return QuizCatalogService.get_quiz_info(session, quiz_id)

    def get_quiz_questions(
        self, session: Session, quiz_id: int
    ) -> list[QuizQuestion]:
        return QuizCatalogService.get_quiz_questions(session, quiz_id)

    def create_attempt(
        self,
        session: Session,
        quiz_id: int,
        *,
        submitter_name: str = "",
        submitter_id: str = "",
        remaining_seconds: int | None = None,
    ) -> Attempt:
        return QuizAttemptService.create_attempt(
            session,
            quiz_id,
            submitter_name=submitter_name,
            submitter_id=submitter_id,
            remaining_seconds=remaining_seconds,
        )

    def save_answer(
        self,
        session: Session,
        attempt_id: int,
        quiz_question_id: int,
        payload: dict,
    ):
        return QuizAttemptService.save_answer(
            session,
            attempt_id,
            quiz_question_id,
            payload,
        )

    def autosave_answers(
        self,
        session: Session,
        attempt_id: int,
        answers: dict[int, dict],
    ) -> None:
        QuizAttemptService.autosave_answers(session, attempt_id, answers)

    def autosave_progress(
        self,
        session: Session,
        attempt_id: int,
        answers: dict[int, dict],
        remaining_seconds: int | None,
    ) -> None:
        QuizAttemptService.autosave_progress(
            session,
            attempt_id,
            answers,
            remaining_seconds,
        )

    def get_resumable_attempt(
        self,
        session: Session,
        quiz_id: int,
    ) -> AttemptResumeDTO | None:
        return QuizAttemptService.get_resumable_attempt(session, quiz_id)

    def delete_attempt(self, session: Session, attempt_id: int) -> bool:
        return QuizAttemptService.delete_attempt(session, attempt_id)

    def finalize_attempt(
        self,
        session: Session,
        attempt_id: int,
        status: str,
        graded_rows: list[GradedRow],
        duration_seconds: int,
    ) -> Attempt:
        return QuizAttemptService.finalize_attempt(
            session,
            attempt_id,
            status,
            graded_rows,
            duration_seconds,
        )

    @staticmethod
    def grade_answer(qq: QuizQuestion, payload: dict) -> GradeResult:
        return QuizGradingService.grade_answer(qq, payload)

    @staticmethod
    def grade_answer_from_dict(
        qq_dict: dict | QuizQuestionSnapshot,
        payload: dict,
    ) -> GradeResult:
        return QuizGradingService.grade_answer_from_dict(qq_dict, payload)


__all__ = [
    "AttemptResumeDTO",
    "GradedRow",
    "QuizConfig",
    "QuizCreationSnapshot",
    "QuizInfoDTO",
    "QuizQuestionSnapshot",
    "QuizService",
]
