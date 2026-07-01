"""Facade for quiz-builder data access workflows used by UI."""
from __future__ import annotations

from core.database.models import Quiz
from core.database.models import Question
from core.database.session import get_session
from core.domain.services.quiz_service import QuizConfig, QuizCreationSnapshot, QuizService
from modules.quiz_builder.selector import QuestionSelector


class QuizBuilderFacade:
    """Centralize session orchestration for quiz-builder question selection."""

    def __init__(self, selector: QuestionSelector | None = None) -> None:
        self._selector = selector or QuestionSelector()
        self._quiz_service = QuizService()

    def list_eligible_questions(
        self,
        *,
        bank_id: int,
        question_types: list[str] | None = None,
        difficulties: list[str] | None = None,
        candidate_question_ids: list[int] | None,
        active_only: bool = True,
        shuffle: bool = False,
    ) -> list[Question]:
        """Return detached questions safe to use after the DB session closes."""
        with get_session() as session:
            questions = self._selector.select(
                session,
                bank_id,
                count=100000,
                question_types=question_types,
                difficulties=difficulties,
                candidate_question_ids=candidate_question_ids,
                active_only=active_only,
                shuffle=shuffle,
            )
            for question in questions:
                # Eagerly touch options so builder/export flows can safely use
                # detached questions outside the session boundary.
                _ = list(question.options)
                session.expunge(question)
            return questions

    def count_eligible_questions(
        self,
        *,
        bank_id: int,
        question_types: list[str] | None = None,
        difficulties: list[str] | None = None,
        candidate_question_ids: list[int] | None,
        active_only: bool = True,
    ) -> int:
        """Return how many questions match the current builder/runtime filters."""
        with get_session() as session:
            return self._selector.available_count(
                session,
                bank_id,
                question_types=question_types,
                difficulties=difficulties,
                candidate_question_ids=candidate_question_ids,
                active_only=active_only,
            )

    def create_quiz(
        self,
        config: QuizConfig,
        question_snapshots: list[QuizCreationSnapshot],
    ) -> Quiz:
        """Persist a quiz from typed snapshots and return the detached Quiz."""
        with get_session() as session:
            quiz = self._quiz_service.create_quiz(session, config, question_snapshots)
            session.expunge(quiz)
            return quiz
