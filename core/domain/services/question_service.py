"""CRUD and search facade for questions and question banks."""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.database.models import Question, QuestionBank
from core.domain.services.question_service_impl import (
    QuestionAnalyticsService,
    QuestionBankMutatorService,
    QuestionMutationService,
    QuestionQueryService,
)
from core.domain.services.question_service_types import (
    BankOverviewRow,
    BankStats,
    ProblemRubricRow,
    QuestionEditData,
    QuestionTypeBreakdown,
    QuestionUsageRow,
    QuestionUsageSummary,
)
from core.utils.constants import QuestionType


class QuestionService:
    """Facade over question-bank read/write/search operations."""

    _ASSESSMENT_TYPES: tuple[str, ...] = QuestionBankMutatorService._ASSESSMENT_TYPES
    _DIFFICULTY_LEVEL_ORDER: tuple[str, ...] = (
        QuestionAnalyticsService._DIFFICULTY_LEVEL_ORDER
    )
    _DIFFICULTY_LEVELS_BY_TYPE: dict[QuestionType | str, tuple[str, ...]] = {
        QuestionType.TRUE_FALSE: ("Nhớ", "Hiểu"),
        QuestionType.TRUE_FALSE.value: ("Nhớ", "Hiểu"),
        QuestionType.MULTIPLE_CHOICE: ("Nhớ", "Hiểu", "Vận dụng"),
        QuestionType.MULTIPLE_CHOICE.value: ("Nhớ", "Hiểu", "Vận dụng"),
        QuestionType.MULTIPLE_ANSWER: ("Nhớ", "Hiểu", "Vận dụng", "Phân tích"),
        QuestionType.MULTIPLE_ANSWER.value: ("Nhớ", "Hiểu", "Vận dụng", "Phân tích"),
        QuestionType.BLANK: (
            "Nhớ",
            "Hiểu",
            "Vận dụng",
            "Phân tích",
            "Đánh giá",
            "Sáng tạo",
        ),
        QuestionType.BLANK.value: (
            "Nhớ",
            "Hiểu",
            "Vận dụng",
            "Phân tích",
            "Đánh giá",
            "Sáng tạo",
        ),
        QuestionType.SHORT_ANSWER: ("Vận dụng", "Phân tích", "Đánh giá"),
        QuestionType.SHORT_ANSWER.value: ("Vận dụng", "Phân tích", "Đánh giá"),
        QuestionType.ESSAY: ("Phân tích", "Đánh giá", "Sáng tạo"),
        QuestionType.ESSAY.value: ("Phân tích", "Đánh giá", "Sáng tạo"),
    }

    def list_banks(self, session: Session) -> list[QuestionBank]:
        return QuestionAnalyticsService.list_banks(session)

    def get_bank_stats(self, session: Session) -> list[BankStats]:
        return QuestionAnalyticsService.get_bank_stats(session)

    def get_bank_overview_rows(self, session: Session) -> list[BankOverviewRow]:
        return QuestionAnalyticsService.get_bank_overview_rows(session)

    def get_question_type_breakdown(self, session: Session) -> QuestionTypeBreakdown:
        return QuestionAnalyticsService.get_question_type_breakdown(session)

    def get_usage_banks(self, session: Session) -> list[BankStats]:
        return QuestionAnalyticsService.get_usage_banks(session)

    def get_question_usage_rows(
        self, session: Session, bank_id: int
    ) -> list[QuestionUsageRow]:
        return QuestionAnalyticsService.get_question_usage_rows(session, bank_id)

    def build_usage_summary(
        self, usage_rows: list[QuestionUsageRow]
    ) -> QuestionUsageSummary:
        return QuestionAnalyticsService.build_usage_summary(usage_rows)

    def get_question_by_id(self, session: Session, question_id: int) -> Question | None:
        return QuestionAnalyticsService.get_question_by_id(session, question_id)

    def get_bank_by_id(self, session: Session, bank_id: int) -> QuestionBank | None:
        return QuestionAnalyticsService.get_bank_by_id(session, bank_id)

    def get_question_for_edit(
        self, session: Session, question_id: int
    ) -> Question | None:
        return QuestionAnalyticsService.get_question_for_edit(session, question_id)

    def get_question_count(self, session: Session) -> int:
        return QuestionAnalyticsService.get_question_count(session)

    def get_bank_count(self, session: Session) -> int:
        return QuestionAnalyticsService.get_bank_count(session)

    def create_bank(
        self,
        session: Session,
        name: str,
        *,
        school: str = "",
        department: str = "",
        subject: str = "",
        course_code: str = "",
        exam_title: str = "",
        assessment_type: str = "",
        course_learning_outcomes: list[dict[str, str]] | None = None,
    ) -> QuestionBank:
        return QuestionBankMutatorService.create_bank(
            session,
            name,
            school=school,
            department=department,
            subject=subject,
            course_code=course_code,
            exam_title=exam_title,
            assessment_type=assessment_type,
            course_learning_outcomes=course_learning_outcomes,
        )

    def rename_bank(self, session: Session, bank_id: int, new_name: str) -> None:
        QuestionBankMutatorService.rename_bank(session, bank_id, new_name)

    def update_bank(
        self,
        session: Session,
        bank_id: int,
        name: str,
        *,
        school: str = "",
        department: str = "",
        subject: str = "",
        course_code: str = "",
        exam_title: str = "",
        assessment_type: str = "",
        course_learning_outcomes: list[dict[str, str]] | None = None,
    ) -> None:
        QuestionBankMutatorService.update_bank(
            session,
            bank_id,
            name,
            school=school,
            department=department,
            subject=subject,
            course_code=course_code,
            exam_title=exam_title,
            assessment_type=assessment_type,
            course_learning_outcomes=course_learning_outcomes,
        )

    def delete_bank(self, session: Session, bank_id: int) -> None:
        QuestionBankMutatorService.delete_bank(session, bank_id)

    def list_questions(
        self,
        session: Session,
        bank_id: int | None = None,
        search: str = "",
        question_type: str | None = None,
        difficulty: str | None = None,
        active_only: bool = False,
    ) -> list[Question]:
        return QuestionQueryService.list_questions(
            session,
            bank_id=bank_id,
            search=search,
            question_type=question_type,
            difficulty=difficulty,
            active_only=active_only,
        )

    def create_question(self, session: Session, data: QuestionEditData) -> Question:
        return QuestionMutationService.create_question(session, data)

    def update_question(
        self, session: Session, question_id: int, data: QuestionEditData
    ) -> Question:
        return QuestionMutationService.update_question(session, question_id, data)

    def delete_question(self, session: Session, question_id: int) -> None:
        QuestionMutationService.delete_question(session, question_id)

    def delete_questions_bulk(self, session: Session, question_ids: list[int]) -> int:
        return QuestionMutationService.delete_questions_bulk(session, question_ids)


__all__ = [
    "BankOverviewRow",
    "BankStats",
    "ProblemRubricRow",
    "QuestionEditData",
    "QuestionService",
    "QuestionTypeBreakdown",
    "QuestionUsageRow",
    "QuestionUsageSummary",
]
