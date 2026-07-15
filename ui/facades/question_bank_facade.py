"""Facade for question bank management workflows used by UI."""
from __future__ import annotations

from dataclasses import dataclass

from core.database.models import Question
from core.database.session import get_session
from core.domain.services.problem_template_service import ProblemTemplateService
from core.domain.services.question_service import QuestionEditData, QuestionService
from core.domain.services.question_service_types import (
    ProblemRubricRow,
    ProblemRubricTemplateData,
    ProblemRubricTemplateSummary,
)


@dataclass
class BankMetaData:
    """Bank metadata payload used by bank edit dialog."""

    name: str
    school: str
    department: str
    subject: str
    course_code: str
    exam_title: str
    assessment_type: str = ""
    course_learning_outcomes: list[dict[str, str]] | None = None


class QuestionBankFacade:
    """Centralize question bank DB/session orchestration for UI."""

    def __init__(self) -> None:
        self._service = QuestionService()

    def list_banks(self) -> list[tuple[int, str]]:
        with get_session() as session:
            banks = self._service.list_banks(session)
            return [(b.id, b.name) for b in banks]

    def list_bank_overview_items(self) -> list[dict]:
        with get_session() as session:
            rows = self._service.get_bank_overview_rows(session)
            return [
                {
                    "id": row.bank_id,
                    "name": row.bank_name,
                    "assessment_type": row.assessment_type,
                    "course_learning_outcomes": row.course_learning_outcomes,
                    "question_count": row.question_count,
                }
                for row in rows
            ]

    def list_bank_items(self) -> list[dict]:
        """Return bank metadata payloads suitable for combo-box style UI usage."""
        with get_session() as session:
            banks = self._service.list_banks(session)
            return [
                {
                    "id": bank.id,
                    "name": bank.name,
                    "school": bank.school or "",
                    "department": bank.department or "",
                    "subject": bank.subject or "",
                    "course_code": bank.course_code or "",
                    "exam_title": bank.exam_title or "",
                    "assessment_type": bank.assessment_type or "",
                    "course_learning_outcomes": bank.get_course_learning_outcomes(),
                }
                for bank in banks
            ]

    def list_questions(
        self,
        *,
        bank_id: int | None,
        search: str,
        question_type: str | None,
        difficulty: str | None,
    ) -> list[Question]:
        with get_session() as session:
            return self._service.list_questions(
                session,
                bank_id=bank_id,
                search=search,
                question_type=question_type,
                difficulty=difficulty,
            )

    def create_bank(self, data: BankMetaData) -> int:
        with get_session() as session:
            bank = self._service.create_bank(
                session,
                data.name,
                school=data.school,
                department=data.department,
                subject=data.subject,
                course_code=data.course_code,
                exam_title=data.exam_title,
                assessment_type=data.assessment_type,
                course_learning_outcomes=list(data.course_learning_outcomes or []),
            )
            return bank.id

    def get_bank_metadata(self, bank_id: int) -> BankMetaData | None:
        with get_session() as session:
            bank = self._service.get_bank_by_id(session, bank_id)
            if bank is None:
                return None
            return BankMetaData(
                name=bank.name,
                school=bank.school or "",
                department=bank.department or "",
                subject=bank.subject or "",
                course_code=bank.course_code or "",
                exam_title=bank.exam_title or "",
                assessment_type=bank.assessment_type or "",
                course_learning_outcomes=bank.get_course_learning_outcomes(),
            )

    def update_bank(self, bank_id: int, data: BankMetaData) -> None:
        with get_session() as session:
            self._service.update_bank(
                session,
                bank_id,
                data.name,
                school=data.school,
                department=data.department,
                subject=data.subject,
                course_code=data.course_code,
                exam_title=data.exam_title,
                assessment_type=data.assessment_type,
                course_learning_outcomes=list(data.course_learning_outcomes or []),
            )

    def delete_bank(self, bank_id: int) -> None:
        with get_session() as session:
            self._service.delete_bank(session, bank_id)

    def get_question_for_edit(self, question_id: int) -> Question | None:
        with get_session() as session:
            return self._service.get_question_for_edit(session, question_id)

    def delete_questions_bulk(self, ids: list[int]) -> int:
        with get_session() as session:
            return self._service.delete_questions_bulk(session, ids)

    def create_question(self, data: QuestionEditData) -> Question:
        with get_session() as session:
            return self._service.create_question(session, data)

    def update_question(self, question_id: int, data: QuestionEditData) -> Question:
        with get_session() as session:
            return self._service.update_question(session, question_id, data)

    def list_problem_templates(self, bank_id: int) -> list[ProblemRubricTemplateSummary]:
        with get_session() as session:
            return ProblemTemplateService.list_templates(session, bank_id)

    def save_problem_template(
        self,
        bank_id: int,
        name: str,
        rows: list[ProblemRubricRow],
    ) -> ProblemRubricTemplateSummary:
        with get_session() as session:
            return ProblemTemplateService.save_template(session, bank_id, name, rows)

    def get_problem_template(
        self,
        template_id: int,
    ) -> ProblemRubricTemplateData | None:
        with get_session() as session:
            return ProblemTemplateService.get_template(session, template_id)

    def delete_problem_template(self, template_id: int) -> None:
        with get_session() as session:
            ProblemTemplateService.delete_template(session, template_id)

    def rename_problem_template(
        self,
        template_id: int,
        new_name: str,
    ) -> ProblemRubricTemplateSummary:
        with get_session() as session:
            return ProblemTemplateService.rename_template(session, template_id, new_name)
