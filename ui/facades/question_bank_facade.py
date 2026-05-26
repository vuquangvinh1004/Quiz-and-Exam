"""Facade for question bank management workflows used by UI."""
from __future__ import annotations

from dataclasses import dataclass

from core.database.models import Question, QuestionBank
from core.database.session import get_session
from core.domain.services.question_service import QuestionEditData, QuestionService


@dataclass
class BankMetaData:
    """Bank metadata payload used by bank edit dialog."""

    name: str
    school: str
    department: str
    subject: str
    course_code: str
    exam_title: str


class QuestionBankFacade:
    """Centralize question bank DB/session orchestration for UI."""

    def __init__(self) -> None:
        self._service = QuestionService()

    def list_banks(self) -> list[tuple[int, str]]:
        with get_session() as session:
            banks = self._service.list_banks(session)
            return [(b.id, b.name) for b in banks]

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
